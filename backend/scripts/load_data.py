import os
import pandas as pd
import ast
import re
import psycopg2
import psycopg2.extras
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def parse_duration_text(duration_text: str) -> str:
    """Keep original duration text for display."""
    if not duration_text or pd.isna(duration_text):
        return None
    return str(duration_text).strip()

def parse_duration_min(duration_text: str) -> int:
    """Parse minimum duration from text into minutes."""
    if not duration_text or pd.isna(duration_text):
        return None
    
    text = str(duration_text).strip().lower()
    
    # Handle exact numeric values
    if re.match(r'^\d+$', text):
        return int(text)
    
    # Handle range format ("15 to 35")
    range_match = re.search(r'(\d+)\s+to', text)
    if range_match:
        return int(range_match.group(1))
    
    return None

def parse_duration_max(duration_text: str) -> int:
    """Parse maximum duration from text into minutes."""
    if not duration_text or pd.isna(duration_text):
        return None
    
    text = str(duration_text).strip().lower()
    
    # Handle exact numeric values
    if re.match(r'^\d+$', text):
        return int(text)
    
    # Handle max format
    max_match = re.search(r'max\s+(\d+)', text)
    if max_match:
        return int(max_match.group(1))
    
    # Handle range format ("15 to 35")
    range_match = re.search(r'to\s+(\d+)', text)
    if range_match:
        return int(range_match.group(1))
    
    return None

def is_untimed_duration(duration_text: str) -> bool:
    """Check if duration is untimed."""
    if not duration_text or pd.isna(duration_text):
        return False
    
    return 'untimed' in str(duration_text).strip().lower()

def is_variable_duration(duration_text: str) -> bool:
    """Check if duration is variable/TBC."""
    if not duration_text or pd.isna(duration_text):
        return False
    
    text = str(duration_text).strip().lower()
    return text in ['variable', 'tbc', 'n/a', '-'] or 'variable' in text

def parse_list_string(list_str: str) -> list:
    """Convert string representation of list into actual list."""
    if not list_str or pd.isna(list_str):
        return []
    
    try:
        # If it's already a list, return it
        if isinstance(list_str, list):
            return list_str
        
        # Try to evaluate the string as a literal
        result = ast.literal_eval(str(list_str))
        if isinstance(result, list):
            return result
        return []
    except Exception:
        # If parsing fails, split by comma (fallback)
        try:
            return [item.strip() for item in str(list_str).split(',') if item.strip()]
        except Exception:
            return []

def parse_boolean(value) -> bool:
    """Convert various boolean representations to Python bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ['true', 'yes', '1', 't', 'y']
    if isinstance(value, (int, float)):
        return bool(value)
    return False

def get_db_connection():
    """Get PostgreSQL connection using session pooler."""
    try:
        # Connection parameters for session pooler
        db_host = "aws-0-ap-southeast-1.pooler.supabase.com"
        db_port = 5432  # Session pooler port
        db_name = "postgres"
        db_user = "postgres.bnttogysmtleyoybordu"  # Project-specific username
        db_password = os.getenv("SUPABASE_KEY")  # Database password
        
        if not db_password:
            raise ValueError("Missing SUPABASE_KEY in environment variables")
        
        # Connect to database
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            dbname=db_name,
            sslmode="require"
        )
        return conn
    except Exception as e:
        print(f"Connection error: {e}")
        raise

def load_data():
    """Load assessment data from CSV into Supabase."""
    try:
        # Get database connection
        conn = get_db_connection()
        print("Successfully connected to database")
        
        # Create cursor
        cursor = conn.cursor()
        
        # Read CSV file
        csv_path = 'shl_scraper/data/processed/shl_individual_assessments.csv'
        df = pd.read_csv(csv_path)
        print(f"Read {len(df)} rows from CSV")
        
        # Process each row
        records = []
        for _, row in df.iterrows():
            record = {
                'name': row['name'],
                'url': row['url'],
                'remote_testing': parse_boolean(row.get('remote_testing', False)),
                'adaptive_irt': parse_boolean(row.get('adaptive_irt', False)),
                'test_types': parse_list_string(row.get('test_types')),
                'description': row.get('description'),
                'job_levels': parse_list_string(row.get('job_levels')),
                'duration_text': parse_duration_text(row.get('duration')),
                'duration_min_minutes': parse_duration_min(row.get('duration')),
                'duration_max_minutes': parse_duration_max(row.get('duration')),
                'is_untimed': is_untimed_duration(row.get('duration')),
                'is_variable_duration': is_variable_duration(row.get('duration')),
                'languages': parse_list_string(row.get('languages')),
                'key_features': parse_list_string(row.get('key_features')),
                'source': row.get('source', 'shl_individual_assessments.csv')
            }
            records.append(record)
        
        print(f"Processed {len(records)} records")
        
        # Insert data in batches
        batch_size = 100
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            # Create the SQL query for upsert
            insert_query = """
            INSERT INTO public.assessments (
                name, url, remote_testing, adaptive_irt, test_types,
                description, job_levels, duration_text, duration_min_minutes,
                duration_max_minutes, is_untimed, is_variable_duration,
                languages, key_features, source
            ) VALUES %s
            ON CONFLICT (name) DO UPDATE SET
                url = EXCLUDED.url,
                remote_testing = EXCLUDED.remote_testing,
                adaptive_irt = EXCLUDED.adaptive_irt,
                test_types = EXCLUDED.test_types,
                description = EXCLUDED.description,
                job_levels = EXCLUDED.job_levels,
                duration_text = EXCLUDED.duration_text,
                duration_min_minutes = EXCLUDED.duration_min_minutes,
                duration_max_minutes = EXCLUDED.duration_max_minutes,
                is_untimed = EXCLUDED.is_untimed,
                is_variable_duration = EXCLUDED.is_variable_duration,
                languages = EXCLUDED.languages,
                key_features = EXCLUDED.key_features,
                source = EXCLUDED.source,
                updated_at = NOW()
            """
            
            # Prepare values for batch insert
            values = []
            for record in batch:
                values.append((
                    record['name'],
                    record['url'],
                    record['remote_testing'],
                    record['adaptive_irt'],
                    record['test_types'],
                    record['description'],
                    record['job_levels'],
                    record['duration_text'],
                    record['duration_min_minutes'],
                    record['duration_max_minutes'],
                    record['is_untimed'],
                    record['is_variable_duration'],
                    record['languages'],
                    record['key_features'],
                    record['source']
                ))
            
            # Execute the query
            psycopg2.extras.execute_values(cursor, insert_query, values)
            conn.commit()
            print(f"Inserted batch {i//batch_size + 1}/{(len(records)-1)//batch_size + 1}")
        
        print("\nData loading completed successfully!")
        
        # Close cursor and connection
        cursor.close()
        conn.close()
        print("Connection closed.")
        
    except Exception as e:
        print(f"\nError loading data: {e}")
        raise

if __name__ == "__main__":
    try:
        load_data()
    except Exception as e:
        print(f"\nFailed to load data: {e}")
        exit(1) 