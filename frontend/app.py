import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from typing import List, Dict
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
RECOMMEND_ENDPOINT = f"{API_BASE_URL}/api/recommendations"
TOP_K = 10  # Constant for top K recommendations

# Page config
st.set_page_config(
    page_title="SHL Assessment Recommendation System",
    page_icon="📊",
    layout="wide"
)

# Function to configure column display
def get_column_config(df):
    config = {
        "rank": st.column_config.NumberColumn(
            "Rank",
            help="Ranking based on relevance score"
        ),
        "name": st.column_config.TextColumn(
            "Name",
            help="Assessment name",
            width="medium"
        ),
        "description": st.column_config.TextColumn(
            "Description",
            help="Assessment description",
            width="large"
        ),
        "job_levels": st.column_config.TextColumn(
            "Job Levels",
            help="Suitable job levels",
            width="medium"
        ),
        "test_types": st.column_config.TextColumn(
            "Test Types",
            help="Types of tests included",
            width="medium"
        ),
        "duration_text": st.column_config.TextColumn(
            "Duration",
            help="Assessment duration",
            width="small"
        ),
        "remote_testing": st.column_config.CheckboxColumn(
            "Remote Testing",
            help="Whether remote testing is available"
        ),
        "languages": st.column_config.TextColumn(
            "Languages",
            help="Available languages",
            width="medium"
        ),
        "relevance_score": st.column_config.NumberColumn(
            "Relevance",
            help="Relevance score (higher is better)",
            format="%.2f",
            width="small"
        ),
        "url": st.column_config.LinkColumn(
            "Assessment Link",
            help="Link to the assessment details",
            width="medium",
            display_text="View Assessment"
        )
    }
    
    # Only include columns that exist in the DataFrame
    return {k: v for k, v in config.items() if k in df.columns}

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_recommendations" not in st.session_state:
    st.session_state.current_recommendations = None
if "filters" not in st.session_state:
    st.session_state.filters = {
        "job_levels": [],
        "test_types": [],
        "max_duration": 0,  # 0 means no limit
        "remote_testing": None,  # None means not filtering by remote
        "languages": []
    }
if "apply_filters_clicked" not in st.session_state:
    st.session_state.apply_filters_clicked = False

# Title
st.title("SHL Assessment Recommendation System")

# Function to parse duration string and return numeric value
def parse_duration(row):
    if row.get('is_untimed', False):
        return None
    if row.get('is_variable_duration', False):
        return None
    
    # Use max_duration if available, otherwise min_duration
    if row.get('duration_max_minutes') is not None:
        return row['duration_max_minutes']
    if row.get('duration_min_minutes') is not None:
        return row['duration_min_minutes']
    
    return None

# Function to filter DataFrame based on current filters
def apply_filters(df):
    if df is None or df.empty:
        return df
        
    filtered_df = df.copy()
    
    # Create numeric duration column for filtering
    try:
        filtered_df['duration_minutes'] = filtered_df.apply(parse_duration, axis=1)
    except Exception as e:
        st.warning(f"Error processing duration: {str(e)}. Duration filtering will be skipped.")
        filtered_df['duration_minutes'] = None
    
    # Apply job level filter only if values are selected (empty means all allowed)
    if st.session_state.filters["job_levels"] and len(st.session_state.filters["job_levels"]) > 0:
        try:
            filtered_df = filtered_df[filtered_df["job_levels"].apply(
                lambda x: any(level in st.session_state.filters["job_levels"] for level in (x if isinstance(x, list) else [str(x)]))
            )]
        except Exception as e:
            st.info("Could not apply job level filter.")
    
    # Apply test type filter only if values are selected (empty means all allowed)
    if st.session_state.filters["test_types"] and len(st.session_state.filters["test_types"]) > 0:
        try:
            filtered_df = filtered_df[filtered_df["test_types"].apply(
                lambda x: any(test in st.session_state.filters["test_types"] for test in (x if isinstance(x, list) else [str(x)]))
            )]
        except Exception as e:
            st.info("Could not apply test type filter.")
    
    # Apply duration filter only if set to non-zero (0 means no duration limit)
    if st.session_state.filters["max_duration"] > 0:
        try:
            # Create a mask for valid durations
            valid_duration_mask = (
                (filtered_df['duration_minutes'].notna()) & 
                (filtered_df['duration_minutes'] <= st.session_state.filters["max_duration"])
            )
            
            # Apply the duration filter
            filtered_df = filtered_df[valid_duration_mask]
        except Exception as e:
            st.info("Could not apply duration filter.")
    
    # Apply remote testing filter only if explicitly set (None means both allowed)
    if st.session_state.filters["remote_testing"] is not None:
        try:
            # If remote_testing is True, filter for True values
            # If remote_testing is False, filter for False values
            filtered_df = filtered_df[filtered_df["remote_testing"].fillna(False) == st.session_state.filters["remote_testing"]]
        except Exception as e:
            st.info("Could not apply remote testing filter.")
    
    # Apply language filter only if values are selected (empty means all allowed)
    if st.session_state.filters["languages"] and len(st.session_state.filters["languages"]) > 0:
        try:
            filtered_df = filtered_df[filtered_df["languages"].apply(
                lambda x: any(lang in st.session_state.filters["languages"] for lang in (x if isinstance(x, list) else [str(x)]))
            )]
        except Exception as e:
            st.info("Could not apply language filter.")
    
    # Do not limit to TOP_K here, as we want to return all filtered results
    # Format for display
    display_df = filtered_df.copy()
    
    # Add https://shl.com prefix to URLs
    if 'url' in display_df.columns:
        display_df['url'] = display_df['url'].apply(lambda x: f"https://shl.com{x}" if x and not x.startswith('http') else x)
    
    # Convert list columns to strings for better display
    if 'job_levels' in display_df.columns:
        display_df['job_levels'] = display_df['job_levels'].apply(lambda x: ', '.join(x) if isinstance(x, list) else str(x))
    if 'test_types' in display_df.columns:
        display_df['test_types'] = display_df['test_types'].apply(lambda x: ', '.join(x) if isinstance(x, list) else str(x))
    if 'languages' in display_df.columns:
        display_df['languages'] = display_df['languages'].apply(lambda x: ', '.join(x) if isinstance(x, list) else str(x))
    
    # Sort by relevance_score in descending order
    if 'relevance_score' in display_df.columns:
        display_df = display_df.sort_values(by='relevance_score', ascending=False)
    elif 'similarity_score' in display_df.columns:
        display_df = display_df.sort_values(by='similarity_score', ascending=False)
    
    # Reset index to show correct ranking
    display_df = display_df.reset_index(drop=True)
    
    # Add rank column
    display_df.insert(0, 'rank', range(1, len(display_df) + 1))
    
    return display_df

# Function to prepare DataFrame for display
def prepare_display_df(df):
    if df is None or df.empty:
        return None
    
    display_df = df.copy()
    
    # Add https://shl.com prefix to URLs
    if 'url' in display_df.columns:
        display_df['url'] = display_df['url'].apply(lambda x: f"https://shl.com{x}" if x and not x.startswith('http') else x)
    
    # Convert list columns to strings for better display
    if 'job_levels' in display_df.columns:
        display_df['job_levels'] = display_df['job_levels'].apply(lambda x: ', '.join(x) if isinstance(x, list) else str(x))
    if 'test_types' in display_df.columns:
        display_df['test_types'] = display_df['test_types'].apply(lambda x: ', '.join(x) if isinstance(x, list) else str(x))
    if 'languages' in display_df.columns:
        display_df['languages'] = display_df['languages'].apply(lambda x: ', '.join(x) if isinstance(x, list) else str(x))
    
    # Sort by relevance_score in descending order
    if 'relevance_score' in display_df.columns:
        display_df = display_df.sort_values(by='relevance_score', ascending=False)
    elif 'similarity_score' in display_df.columns:
        display_df = display_df.sort_values(by='similarity_score', ascending=False)
    
    # Take top K results - ensuring we get exactly 10 (or all if less than 10)
    display_df = display_df.head(TOP_K)
    
    # Reset index to show correct ranking
    display_df = display_df.reset_index(drop=True)
    
    # Add rank column
    display_df.insert(0, 'rank', range(1, len(display_df) + 1))
    
    return display_df

# Sidebar with filters
with st.sidebar:
    st.header("Advanced Filters")
    st.caption("Optional: Use these filters to refine your search")
    
    # Store filter selections temporarily
    temp_filters = {
        "job_levels": st.multiselect(
            "Filter by Job Level(s)",
            options=[
                "Entry-Level",
                "Graduate",
                "Mid-Professional",
                "Professional Individual Contributor",
                "Front Line Manager",
                "Supervisor",
                "Manager",
                "Director",
                "Executive",
                "General Population"
            ],
            default=st.session_state.filters["job_levels"],
            help="Leave empty to include all job levels"
        ),
        "test_types": st.multiselect(
            "Filter by Test Type(s)",
            options=[
                "Knowledge & Skills",
                "Simulations",
                "Personality & Behavior",
                "Competencies",
                "Assessment Exercises",
                "Biodata & Situational Judgement",
                "Development & 360",
                "Ability & Aptitude"
            ],
            default=st.session_state.filters["test_types"],
            help="Leave empty to include all test types"
        ),
        "max_duration": st.number_input(
            "Maximum Duration (minutes)",
            help="Set to 0 for no duration limit",
            min_value=0,
            max_value=120,
            value=st.session_state.filters["max_duration"],
            step=5
        ),
        # Use a selectbox for remote testing to allow None option
        "remote_testing": st.selectbox(
            "Remote Testing",
            options=["Any", "Remote Only", "In-person Only"],
            index=0 if st.session_state.filters["remote_testing"] is None else 
                  (1 if st.session_state.filters["remote_testing"] else 2),
            help="Choose 'Any' to include both remote and in-person assessments"
        ),
        "languages": st.multiselect(
            "Filter by Language(s)",
            options=[
                "English (USA)",
                "English International",
                "English (Australia)",
                "English (Canada)",
                "English (South Africa)",
                "Arabic",
                "Chinese Simplified",
                "Chinese Traditional",
                "Danish",
                "Dutch",
                "Finnish",
                "French",
                "French (Canada)",
                "German",
                "Icelandic",
                "Indonesian",
                "Italian",
                "Japanese",
                "Korean",
                "Latin American Spanish",
                "Norwegian",
                "Polish",
                "Portuguese",
                "Portuguese (Brazil)",
                "Romanian",
                "Russian",
                "Spanish",
                "Swedish",
                "Thai",
                "Turkish",
                "Vietnamese"
            ],
            default=st.session_state.filters["languages"],
            help="Leave empty to include all languages"
        )
    }
    
    # Convert remote testing selection to boolean or None
    if temp_filters["remote_testing"] == "Any":
        temp_filters["remote_testing"] = None
    elif temp_filters["remote_testing"] == "Remote Only":
        temp_filters["remote_testing"] = True
    else:  # "In-person Only"
        temp_filters["remote_testing"] = False
    
    # Add Apply Filters button
    if st.button("Apply Filters"):
        st.session_state.filters = temp_filters.copy()
        st.session_state.apply_filters_clicked = True
    
    # Add Reset Filters button
    if st.button("Reset Filters"):
        st.session_state.filters = {
            "job_levels": [],
            "test_types": [],
            "max_duration": 0,  # 0 means no limit
            "remote_testing": None,  # None means not filtering by remote
            "languages": []
        }
        st.session_state.apply_filters_clicked = False
        st.rerun()

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Describe the role and assessment requirements..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Show assistant response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing requirements..."):
            try:
                # Prepare filters for API request - ONLY send filters that are explicitly set
                api_filters = {}

                # Only add non-empty filters
                if st.session_state.apply_filters_clicked:
                    if st.session_state.filters["job_levels"] and len(st.session_state.filters["job_levels"]) > 0:
                        api_filters["job_levels"] = st.session_state.filters["job_levels"]
                        
                    if st.session_state.filters["test_types"] and len(st.session_state.filters["test_types"]) > 0:
                        api_filters["test_types"] = st.session_state.filters["test_types"]
                        
                    if st.session_state.filters["max_duration"] > 0:
                        api_filters["max_duration_minutes"] = st.session_state.filters["max_duration"]
                        
                    if st.session_state.filters["remote_testing"] is not None:
                        api_filters["remote_testing"] = st.session_state.filters["remote_testing"]
                        
                    if st.session_state.filters["languages"] and len(st.session_state.filters["languages"]) > 0:
                        api_filters["languages"] = st.session_state.filters["languages"]

                # Prepare request payload
                payload = {
                    "query": prompt,
                    "top_k": 10,  # Set in body
                    "filters": api_filters if api_filters else None
                }
                
                # Make API request with query parameter
                response = requests.post(f"{RECOMMEND_ENDPOINT}?top_k=10", json=payload)
                response.raise_for_status()
                data = response.json()
                
                # Add assistant response to chat history
                response_text = f"Based on your requirements, here are my top 10 recommendations:"
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                st.markdown(response_text)
                
                if data["recommendations"]:
                    # Log the number of recommendations received
                    num_recommendations = len(data["recommendations"])
                    if num_recommendations < 10:
                        st.info(f"The API returned only {num_recommendations} recommendations (requested 10).")
                        
                    # Convert recommendations to DataFrame and store in session state
                    st.session_state.current_recommendations = pd.DataFrame(data["recommendations"])
                    
                    # Apply filters and prepare for display
                    filtered_df = apply_filters(st.session_state.current_recommendations)
                    
                    if filtered_df is not None and not filtered_df.empty:
                        # Display filtered recommendations
                        st.dataframe(
                            filtered_df,
                            column_config=get_column_config(filtered_df),
                            hide_index=True,
                            use_container_width=True
                        )
                        
                        # Display metrics
                        metrics_text = f"""
                        **Evaluation Metrics:**
                        - Processing Time: {data['processing_time']:.2f} seconds
                        - Total Assessments Searched: {data['total_assessments']}
                        - Top {len(filtered_df)} Recommendations Displayed
                        """
                        st.markdown(metrics_text)
                    else:
                        st.warning("No recommendations match the current filters. Try adjusting the filter criteria.")
                    
                else:
                    no_results_text = "I couldn't find any recommendations matching your criteria. Could you please provide more details or try adjusting the filters?"
                    st.session_state.messages.append({"role": "assistant", "content": no_results_text})
                    st.markdown(no_results_text)
                
            except requests.exceptions.RequestException as e:
                error_text = f"I'm having trouble connecting to the recommendation service. Error: {str(e)}"
                st.session_state.messages.append({"role": "assistant", "content": error_text})
                st.error(error_text)
            except Exception as e:
                error_text = f"An unexpected error occurred: {str(e)}"
                st.session_state.messages.append({"role": "assistant", "content": error_text})
                st.error(error_text)

# If we have existing recommendations, show them with current filters
elif st.session_state.current_recommendations is not None:
    # Show unfiltered results if filters haven't been applied
    if not st.session_state.apply_filters_clicked:
        display_df = prepare_display_df(st.session_state.current_recommendations)
        if display_df is not None:
            st.subheader("Current Top Recommendations")
            st.dataframe(
                display_df,
                column_config=get_column_config(display_df),
                hide_index=True,
                use_container_width=True
            )
            st.markdown(f"""
            **Current Results:**
            - Showing all {len(display_df)} recommendations
            """)
    else:
        # Apply filters only when the Apply Filters button has been clicked
        filtered_df = apply_filters(st.session_state.current_recommendations)
        if filtered_df is not None:
            st.subheader("Current Top Recommendations")
            st.dataframe(
                filtered_df,
                column_config=get_column_config(filtered_df),
                hide_index=True,
                use_container_width=True
            )
            
            # Display current filter metrics
            if len(filtered_df) < len(st.session_state.current_recommendations):
                st.markdown(f"""
                **Current Results:**
                - Showing {len(filtered_df)} filtered recommendations
                - From total pool of {len(st.session_state.current_recommendations)} recommendations
                """)
            else:
                st.markdown(f"""
                **Current Results:**
                - Showing all {len(filtered_df)} recommendations
                """)

# Add helpful information at the bottom
with st.expander("How to use this tool"):
    st.markdown("""
    1. **Chat Interface**: 
        - Type your requirements in natural language
        - Example: "I am hiring for Java developers who can collaborate effectively with business teams"
        - Example: "Looking for mid-level Python developers, need assessment package under 60 minutes"
    
    2. **Advanced Filters** (Optional):
        - Use the sidebar to refine your search
        - Filter by specific job levels or test types
        - Set maximum assessment duration
        - Choose language preferences
        - Specify remote testing requirements
        - Filters are applied in real-time to your current results
    
    3. **Understanding Results**:
        - Top 10 recommendations are shown, ranked by relevance
        - Each recommendation shows its rank and relevance score
        - Use the table's built-in sorting and filtering
        - Review processing metrics
        - Hover over column headers for additional information
    
    4. **Sample Queries**:
        - "Looking to hire mid-level professionals who are proficient in Python, SQL and JavaScript"
        - "Need an assessment for analysts with cognitive and personality tests under 45 minutes"
        - "Here is a JD text, can you recommend assessments for screening applications under 30 minutes"
    """) 