import os
import psycopg2
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

def split_sql_statements(sql_script):
    """Split SQL script into statements, preserving dollar-quoted strings."""
    statements = []
    current_statement = []
    in_dollar_quote = False
    dollar_quote_tag = None
    
    # Split into lines and remove comments
    lines = [line.strip() for line in sql_script.split('\n')]
    lines = [line for line in lines if line and not line.startswith('--')]
    
    for line in lines:
        # Check for dollar quotes
        if not in_dollar_quote:
            # Look for start of dollar quote
            match = re.match(r'.*(\$[A-Za-z0-9]*\$).*', line)
            if match:
                in_dollar_quote = True
                dollar_quote_tag = match.group(1)
        else:
            # Look for matching end dollar quote
            if dollar_quote_tag in line:
                in_dollar_quote = False
                dollar_quote_tag = None
        
        current_statement.append(line)
        
        # If we're not in a dollar quote and the line ends with a semicolon,
        # we've reached the end of a statement
        if not in_dollar_quote and line.rstrip().endswith(';'):
            statements.append('\n'.join(current_statement))
            current_statement = []
    
    # Add any remaining statement
    if current_statement:
        statements.append('\n'.join(current_statement))
    
    return statements

def get_db_connection():
    """Get PostgreSQL connection using session pooler."""
    try:
        # Connection parameters for session pooler
        db_host = "aws-0-ap-southeast-1.pooler.supabase.com"
        db_port = 5432  # Session pooler port
        db_name = "postgres"
        db_user = "postgres.bnttogysmtleyoybordu"  # Project-specific username
        db_password = os.getenv("SUPABASE_DB_PASSWORD")  # Database password
        
        if not db_password:
            raise ValueError("Missing SUPABASE_DB_PASSWORD in environment variables")
        
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

def setup_database():
    """Set up the database schema and functions."""
    try:
        # Get database connection
        conn = get_db_connection()
        print("Successfully connected to database")
        
        # Create cursor
        cursor = conn.cursor()
        
        # First, set up the schema
        print("\nSetting up database schema...")
        with open('backend/scripts/setup_supabase.sql', 'r') as f:
            schema_script = f.read()
        
        schema_statements = split_sql_statements(schema_script)
        
        # Execute schema statements
        for i, statement in enumerate(schema_statements, 1):
            try:
                print(f"\nExecuting schema statement {i}/{len(schema_statements)}...")
                cursor.execute(statement)
                print(f"Successfully executed schema statement {i}")
            except Exception as e:
                print(f"Error executing schema statement {i}: {e}")
                print(f"Statement: {statement}")
                if "permission denied" in str(e).lower():
                    print("This error might be due to insufficient permissions. Please check your database role and permissions.")
                conn.rollback()
                raise
                
        # Commit schema changes
        conn.commit()
        print("\nSchema setup completed successfully!")
        
        # Then, set up the vector search function
        print("\nSetting up vector search function...")
        with open('backend/scripts/create_vector_search_function.sql', 'r') as f:
            function_script = f.read()
        
        function_statements = split_sql_statements(function_script)
        
        # Execute function statements
        for i, statement in enumerate(function_statements, 1):
            try:
                print(f"\nExecuting function statement {i}/{len(function_statements)}...")
                cursor.execute(statement)
                print(f"Successfully executed function statement {i}")
            except Exception as e:
                print(f"Error executing function statement {i}: {e}")
                print(f"Statement: {statement}")
                if "permission denied" in str(e).lower():
                    print("This error might be due to insufficient permissions. Please check your database role and permissions.")
                conn.rollback()
                raise
        
        # Commit function changes
        conn.commit()
        print("\nVector search function setup completed successfully!")
        
        # Close cursor and connection
        cursor.close()
        conn.close()
        print("Connection closed.")
    except Exception as e:
        print(f"\nError setting up database: {e}")
        raise

if __name__ == "__main__":
    try:
        setup_database()
    except Exception as e:
        print(f"\nFailed to set up database: {e}")
        exit(1) 