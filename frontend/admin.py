import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
import json
import os
import asyncio
import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
EVALUATION_ENDPOINT = f"{API_BASE_URL}/api/evaluation"

# Page config
st.set_page_config(
    page_title="SHL Assessment Recommendation System - Admin",
    page_icon="📊",
    layout="wide"
)

# Async helper functions
async def fetch_data(url, method="GET", json_data=None, params=None):
    async with aiohttp.ClientSession() as session:
        if method == "GET":
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json()
        elif method == "POST":
            async with session.post(url, json=json_data, params=params) as response:
                response.raise_for_status()
                return await response.json()

def run_async(coroutine):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()

# Cached data fetching functions
@st.cache_data(ttl=60)
def get_evaluation_history():
    try:
        return run_async(fetch_data(f"{EVALUATION_ENDPOINT}/history"))
    except Exception as e:
        st.error(f"Error fetching evaluation history: {str(e)}")
        return []

@st.cache_data(ttl=60)
def get_ground_truth():
    try:
        return run_async(fetch_data(f"{EVALUATION_ENDPOINT}/ground-truth"))
    except Exception as e:
        st.error(f"Error fetching ground truth data: {str(e)}")
        return []

# Get a sample of assessments for the examples
@st.cache_data(ttl=3600)
def get_sample_assessments():
    try:
        response = requests.get(f"{API_BASE_URL}/api/assessments?limit=100")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching sample assessments: {str(e)}")
        return []

# Title
st.title("SHL Assessment Recommendation System - Admin")

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["Evaluation Metrics", "Ground Truth Management", "Run Evaluation", "Documentation"])

# Evaluation Metrics Tab
with tab1:
    st.header("Evaluation Metrics")
    evaluation_history = get_evaluation_history()
    
    if not evaluation_history:
        st.info("No evaluation results found. Run an evaluation first.")
    else:
        # Display summary table
        history_data = []
        for eval_run in evaluation_history:
            history_data.append({
                "Date": eval_run.get("timestamp", "Unknown"),
                "Mean Recall@K": f"{eval_run.get('mean_recall_at_k', 0):.4f}",
                "MAP@K": f"{eval_run.get('mean_average_precision', 0):.4f}",
                "K Value": eval_run.get("k_value", 0),
                "Queries": eval_run.get("total_queries", 0),
                "Filename": eval_run.get("filename", "")
            })
        
        history_df = pd.DataFrame(history_data)
        st.subheader("Evaluation History")
        st.dataframe(history_df, use_container_width=True)
        
        # Select an evaluation to view details
        selected_eval = st.selectbox(
            "Select an evaluation to view details",
            options=range(len(evaluation_history)),
            format_func=lambda x: f"{history_data[x]['Date']} - MAP@K: {history_data[x]['MAP@K']}"
        )
        
        if selected_eval is not None:
            eval_data = evaluation_history[selected_eval]
            
            # Display metrics
            col1, col2 = st.columns(2)
            
            with col1:
                # Mean Recall@K Gauge
                fig_recall = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=eval_data.get("mean_recall_at_k", 0),
                    title={"text": f"Mean Recall@{eval_data.get('k_value', 0)}"},
                    gauge={
                        "axis": {"range": [0, 1]},
                        "bar": {"color": "blue"},
                        "steps": [
                            {"range": [0, 0.33], "color": "lightgray"},
                            {"range": [0.33, 0.67], "color": "gray"},
                            {"range": [0.67, 1], "color": "darkgray"}
                        ]
                    }
                ))
                st.plotly_chart(fig_recall, use_container_width=True)
            
            with col2:
                # MAP@K Gauge
                fig_map = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=eval_data.get("mean_average_precision", 0),
                    title={"text": f"MAP@{eval_data.get('k_value', 0)}"},
                    gauge={
                        "axis": {"range": [0, 1]},
                        "bar": {"color": "green"},
                        "steps": [
                            {"range": [0, 0.33], "color": "lightgray"},
                            {"range": [0.33, 0.67], "color": "gray"},
                            {"range": [0.67, 1], "color": "darkgray"}
                        ]
                    }
                ))
                st.plotly_chart(fig_map, use_container_width=True)
            
            # Display per-query results
            eval_results = eval_data.get("evaluation_results", [])
            
            if eval_results:
                query_data = []
                for result in eval_results:
                    query_data.append({
                        "Query ID": result.get("query_id", ""),
                        "Query Text": result.get("query_text", "")[:50] + "...",
                        "Recall@K": result.get("recall_at_k", 0),
                        "Average Precision": result.get("average_precision", 0),
                        "Relevant Found": len(result.get("relevant_recommended", [])),
                        "Total Relevant": result.get("total_relevant", 0)
                    })
                
                query_df = pd.DataFrame(query_data)
                st.subheader("Per-Query Results")
                st.dataframe(query_df, use_container_width=True)
                
                # Bar chart comparing metrics across queries
                fig_queries = px.bar(
                    query_df,
                    x="Query ID",
                    y=["Recall@K", "Average Precision"],
                    barmode="group",
                    title="Metrics by Query",
                    labels={"value": "Score", "variable": "Metric"}
                )
                st.plotly_chart(fig_queries, use_container_width=True)
                
                # Select a query to view detailed precision@k
                selected_query = st.selectbox(
                    "Select a query to view precision@k details",
                    options=range(len(eval_results)),
                    format_func=lambda x: f"{eval_results[x].get('query_id', '')} - {eval_results[x].get('query_text', '')[:50]}..."
                )
                
                if selected_query is not None:
                    query_result = eval_results[selected_query]
                    precision_k = query_result.get("precision_at_k", [])
                    
                    if precision_k:
                        positions = list(range(1, len(precision_k) + 1))
                        precision_df = pd.DataFrame({
                            "Position": positions,
                            "Precision@k": precision_k
                        })
                        
                        fig_precision = px.line(
                            precision_df,
                            x="Position",
                            y="Precision@k",
                            markers=True,
                            title=f"Precision@k for Query: {query_result.get('query_id', '')}"
                        )
                        st.plotly_chart(fig_precision, use_container_width=True)
                        
                        # Show which recommended items were relevant
                        recommended = query_result.get("recommended_assessments", [])
                        relevant = set(query_result.get("relevant_recommended", []))
                        
                        relevance_data = []
                        for i, rec_id in enumerate(recommended):
                            relevance_data.append({
                                "Position": i + 1,
                                "Assessment Name": rec_id,
                                "Is Relevant": rec_id in relevant
                            })
                        
                        relevance_df = pd.DataFrame(relevance_data)
                        st.subheader("Relevance of Recommendations")
                        st.dataframe(relevance_df, use_container_width=True)

# Ground Truth Management Tab
with tab2:
    st.header("Ground Truth Management")
    
    ground_truth = get_ground_truth()
    
    if not ground_truth:
        st.info("No ground truth data found.")
    else:
        # Display ground truth table
        gt_data = []
        for query in ground_truth:
            gt_data.append({
                "ID": query.get("id", ""),
                "Query": query.get("query", ""),
                "Relevant Assessments": len(query.get("relevant_assessments", [])),
                "Description": query.get("description", "")
            })
        
        gt_df = pd.DataFrame(gt_data)
        st.subheader("Ground Truth Queries")
        st.dataframe(gt_df, use_container_width=True)
        
        # Select a query to view details
        selected_gt = st.selectbox(
            "Select a query to view details",
            options=range(len(ground_truth)),
            format_func=lambda x: f"{ground_truth[x].get('id', '')} - {ground_truth[x].get('query', '')[:50]}..."
        )
        
        if selected_gt is not None:
            gt_query = ground_truth[selected_gt]
            
            st.subheader(f"Query: {gt_query.get('query', '')}")
            st.write(f"Description: {gt_query.get('description', 'No description')}")
            
            # Show relevant assessments
            relevant_names = gt_query.get("relevant_assessments", [])
            if relevant_names:
                st.write(f"Relevant Assessment Names ({len(relevant_names)}):")
                st.json(relevant_names)
            else:
                st.write("No relevant assessments defined.")
    
    # File upload for ground truth
    st.subheader("Upload Ground Truth Data")
    
    # Show ground truth format explanation
    with st.expander("Ground Truth JSON Format Guidelines", expanded=False):
        st.markdown("""
        ## Ground Truth JSON Format

        The ground truth JSON file should follow this specific structure:

        ```json
        [
          {
            "id": "query_id",
            "query": "Your natural language query text",
            "relevant_assessments": [
              "Assessment Name 1",
              "Assessment Name 2",
              "Assessment Name 3"
            ],
            "description": "Optional description of the query scenario"
          },
          {
            "id": "another_query_id",
            "query": "Another query text",
            "relevant_assessments": [
              "Assessment Name 4",
              "Assessment Name 5"
            ],
            "description": "Optional description"
          }
        ]
        ```

        ### Required Fields:

        1. **id**: A unique identifier for each query (e.g., "query_programming", "query_leadership")
        2. **query**: The actual natural language query text that will be sent to the recommendation system
        3. **relevant_assessments**: Array of assessment names (exact matches) that are considered relevant to this query
        4. **description**: (Optional) A brief description of the query scenario

        ### Important Notes:

        - The ground truth file must be a valid JSON array of objects
        - Each assessment name in `relevant_assessments` must match **exactly** as it appears in the SHL assessment catalog
        - Names are case-sensitive
        - The system will calculate metrics by comparing recommended assessment names against these ground truth relevant assessments
        """)
        
        # Sample ground truth file
        st.markdown("### Example Ground Truth File:")
        sample_json = [
            {
                "id": "query_programming",
                "query": "Find assessments for software developers with programming skills",
                "relevant_assessments": [
                    "Automata (New)",
                    "C Programming (New)", 
                    "Python (New)"
                ],
                "description": "Query for programming skill assessments"
            },
            {
                "id": "query_leadership",
                "query": "Find assessments for leadership roles",
                "relevant_assessments": [
                    "Executive Scenarios",
                    "Enterprise Leadership Report 2.0",
                    "HiPo Assessment Report 2.0"
                ],
                "description": "Query for leadership assessment tools"
            }
        ]
        st.json(sample_json)
    
    # List available assessment names
    with st.expander("Available Assessment Names", expanded=False):
        st.markdown("""
        ### Available Assessment Names
        
        Below is a sample of assessment names from the SHL catalog. Use these exact names (case-sensitive) 
        in your ground truth JSON file when specifying relevant assessments.
        """)
        
        try:
            # Try to read directly from the CSV file
            csv_path = "shl_scraper/data/processed/shl_individual_assessments.csv"
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                assessment_names = df['name'].tolist()
                # Display in chunks to avoid overwhelming the UI
                chunk_size = 20
                st.write(f"Total assessments: {len(assessment_names)}")
                
                # Let user search through assessments
                search_term = st.text_input("Search assessments by name:")
                if search_term:
                    filtered_names = [name for name in assessment_names if search_term.lower() in name.lower()]
                    st.write(f"Found {len(filtered_names)} assessments matching '{search_term}':")
                    st.dataframe(pd.DataFrame(filtered_names, columns=["Assessment Name"]))
                else:
                    # Show first chunk by default
                    st.write(f"Showing first {chunk_size} assessments:")
                    st.dataframe(pd.DataFrame(assessment_names[:chunk_size], columns=["Assessment Name"]))
                    
                    # Let user choose which chunk to view
                    if len(assessment_names) > chunk_size:
                        chunk_number = st.slider("View more assessments:", 1, (len(assessment_names) // chunk_size) + 1, 1)
                        start_idx = (chunk_number - 1) * chunk_size
                        end_idx = min(start_idx + chunk_size, len(assessment_names))
                        st.write(f"Assessments {start_idx+1}-{end_idx}:")
                        st.dataframe(pd.DataFrame(assessment_names[start_idx:end_idx], columns=["Assessment Name"]))
            else:
                # Fallback: fetch from API
                assessments = get_sample_assessments()
                if assessments:
                    assessment_names = [a.get("name", "") for a in assessments]
                    st.dataframe(pd.DataFrame(assessment_names, columns=["Assessment Name"]))
                else:
                    st.warning("Could not load assessment names. Please check the CSV file or API connection.")
        except Exception as e:
            st.error(f"Error loading assessment names: {str(e)}")
    
    # Actual file uploader
    uploaded_file = st.file_uploader("Choose a JSON file", type="json")
    
    if uploaded_file is not None:
        try:
            content = json.loads(uploaded_file.read())
            st.write(f"File contains {len(content)} ground truth queries.")
            
            if st.button("Upload Ground Truth Data"):
                try:
                    result = run_async(fetch_data(
                        f"{EVALUATION_ENDPOINT}/ground-truth",
                        method="POST",
                        json_data=content
                    ))
                    st.success("Ground truth data uploaded successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error uploading ground truth data: {str(e)}")
        except Exception as e:
            st.error(f"Error parsing JSON file: {str(e)}")

# Run Evaluation Tab
with tab3:
    st.header("Run Evaluation")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        k_value = st.slider("K value (number of recommendations to evaluate)", 1, 20, 10)
    
    with col2:
        run_button = st.button("Run Evaluation")
    
    if run_button:
        with st.spinner("Running evaluation..."):
            try:
                results = run_async(fetch_data(
                    f"{EVALUATION_ENDPOINT}/run",
                    method="POST",
                    params={"k": k_value}
                ))
                
                st.success(f"Evaluation completed successfully!")
                st.json(results)
                
                # Switch to the Evaluation Metrics tab
                st.experimental_set_query_params(tab="metrics")
                st.rerun()
            except Exception as e:
                st.error(f"Error running evaluation: {str(e)}")
                
    # Evaluate single query
    st.subheader("Evaluate Single Query")
    ground_truth = get_ground_truth()
    
    if ground_truth:
        query_options = [f"{q.get('id', '')} - {q.get('query', '')[:50]}..." for q in ground_truth]
        selected_query = st.selectbox("Select a query to evaluate", options=range(len(query_options)), format_func=lambda x: query_options[x])
        
        if selected_query is not None:
            query_id = ground_truth[selected_query].get("id", "")
            
            if st.button("Evaluate Query"):
                with st.spinner(f"Evaluating query {query_id}..."):
                    try:
                        result = run_async(fetch_data(
                            f"{EVALUATION_ENDPOINT}/query",
                            method="POST",
                            json_data={"query_id": query_id},
                            params={"k": k_value}
                        ))
                        
                        st.success(f"Query evaluation completed successfully!")
                        
                        # Display results
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.metric("Recall@K", f"{result.get('recall_at_k', 0):.4f}")
                        
                        with col2:
                            st.metric("Average Precision", f"{result.get('average_precision', 0):.4f}")
                        
                        # Show precision@k curve
                        precision_k = result.get("precision_at_k", [])
                        
                        if precision_k:
                            positions = list(range(1, len(precision_k) + 1))
                            precision_df = pd.DataFrame({
                                "Position": positions,
                                "Precision@k": precision_k
                            })
                            
                            fig_precision = px.line(
                                precision_df,
                                x="Position",
                                y="Precision@k",
                                markers=True,
                                title=f"Precision@k for Query: {result.get('query_id', '')}"
                            )
                            st.plotly_chart(fig_precision, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error evaluating query: {str(e)}")
    else:
        st.info("No ground truth queries available. Please add ground truth data first.")

# Documentation Tab
with tab4:
    st.header("Evaluation Metrics Documentation")
    
    st.markdown("""
    ## Metrics to Compute Accuracy
    
    The SHL Assessment Recommendation System is evaluated using the following ranking evaluation metrics:
    
    ### 1. Mean Recall@K
    
    This metric measures how many of the **relevant assessments** were retrieved in the **top K recommendations**, averaged across all test queries.
    
    $$Recall@K = \\frac{\\text{Number of relevant assessments in top K}}{\\text{Total relevant assessments for the query}}$$
    
    $$MeanRecall@K = \\frac{1}{N}\\sum_{i=1}^{N} Recall@K_i$$
    
    where N is the total number of test queries.
    
    ### 2. Mean Average Precision @K (MAP@K)
    
    MAP@K evaluates both the **relevance** and **ranking order** of retrieved assessments by calculating Precision@k at each relevant result and averaging it over all queries.
    
    $$AP@K = \\frac{1}{\\min(K,R)}\\sum_{k=1}^{K} P(k) \\cdot rel(k)$$
    
    $$MAP@K = \\frac{1}{N}\\sum_{i=1}^{N} AP@K_i$$
    
    where:
    - R = total relevant assessments for the query
    - P(k) = precision at position k
    - rel(k) = 1 if the result at position k is relevant, otherwise 0
    - N = total number of test queries
    
    A higher **Mean Recall@K** and **MAP@K** indicate a better-performing recommendation system.
    
    ## API Response Format
    
    When you call the recommendation API endpoint (`/api/recommendations`), the response has the following structure:
    
    ```json
    {
      "recommendations": [
        {
          "name": "Assessment Name",
          "url": "/solutions/products/product-catalog/view/assessment-name/",
          "description": "Description of the assessment",
          "explanation": "Explanation of why this assessment is recommended",
          "similarity_score": 0.85,
          "relevance_score": 0.92,
          "remote_testing": true,
          "adaptive_irt": false,
          "test_types": ["Knowledge & Skills", "Ability & Aptitude"],
          "job_levels": ["Mid-Professional", "Professional Individual Contributor"],
          "duration_text": "30",
          "duration_min_minutes": 25,
          "duration_max_minutes": 35,
          "is_untimed": false,
          "is_variable_duration": false,
          "languages": ["English (USA)"],
          "key_features": ["Job-specific knowledge assessment"]
        },
        // More recommendations...
      ],
      "query_embedding": [...],  // Vector embedding of the query
      "processing_time": 0.456,  // Time in seconds to process the request
      "total_assessments": 120,  // Total number of assessments searched
      "timestamp": "2023-04-07T12:34:56.789Z"  // Timestamp of the recommendation
    }
    ```
    
    This response format is compared against the ground truth data to calculate the evaluation metrics.
    """)
    
    # Show example of API call and response
    with st.expander("Example API Call and Response", expanded=False):
        st.markdown("""
        ### Example API Call
        
        ```python
        import requests
        
        response = requests.post(
            "http://localhost:8000/api/recommendations",
            json={
                "query": "Find assessments for software developers with programming skills",
                "top_k": 5
            }
        )
        
        results = response.json()
        ```
        
        ### Example Response
        
        ```json
        {
          "recommendations": [
            {
              "name": "Python (New)",
              "url": "/solutions/products/product-catalog/view/python-new/",
              "description": "Multi-choice test that measures the knowledge of Python programming language basics, object oriented concepts, and advanced Python concepts.",
              "explanation": "This assessment directly tests Python programming skills which are essential for software developers.",
              "similarity_score": 0.89,
              "relevance_score": 0.95,
              "remote_testing": true,
              "adaptive_irt": false,
              "test_types": ["Knowledge & Skills"],
              "job_levels": ["Mid-Professional", "Professional Individual Contributor"],
              "duration_text": "30",
              "duration_min_minutes": 25,
              "duration_max_minutes": 35,
              "is_untimed": false,
              "is_variable_duration": false,
              "languages": ["English (USA)"],
              "key_features": ["Job-specific knowledge assessment"]
            },
            {
              "name": "C Programming (New)",
              "url": "/solutions/products/product-catalog/view/c-programming-new/",
              "description": "Multi-choice test that measures the knowledge of C programming basics, functions, arrays, composed data types, and advanced C concepts like SLF, file handling and dynamic memory.",
              "explanation": "C is a fundamental programming language that demonstrates core programming skills relevant for software developers.",
              "similarity_score": 0.82,
              "relevance_score": 0.86,
              "remote_testing": true,
              "adaptive_irt": false,
              "test_types": ["Knowledge & Skills"],
              "job_levels": ["Mid-Professional", "Professional Individual Contributor"],
              "duration_text": "10",
              "duration_min_minutes": 8,
              "duration_max_minutes": 12,
              "is_untimed": false,
              "is_variable_duration": false,
              "languages": ["English (USA)"],
              "key_features": ["Job-specific knowledge assessment"]
            },
            {
              "name": "Automata (New)",
              "url": "/solutions/products/product-catalog/view/automata-new/",
              "description": "An AI-powered coding simulation assessment that evaluates candidate's programming ability. Offers a familiar IDE environment available in over 40 different programming languages and tests candidates using real-world coding problems.",
              "explanation": "This practical coding assessment directly evaluates software development skills in a realistic environment.",
              "similarity_score": 0.78,
              "relevance_score": 0.90,
              "remote_testing": true,
              "adaptive_irt": false,
              "test_types": ["Simulations"],
              "job_levels": ["Mid-Professional", "Professional Individual Contributor"],
              "duration_text": "max 45",
              "duration_min_minutes": null,
              "duration_max_minutes": 45,
              "is_untimed": false,
              "is_variable_duration": true,
              "languages": ["English (USA)"],
              "key_features": ["Interactive simulation"]
            }
          ],
          "processing_time": 1.25,
          "total_assessments": 120,
          "timestamp": "2023-04-07T12:34:56.789Z"
        }
        ```
        """) 