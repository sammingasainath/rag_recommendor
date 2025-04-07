import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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

def update_schema():
    """Update the database schema for duration fields."""
    try:
        # Get database connection
        conn = get_db_connection()
        print("Successfully connected to database")
        
        # Create cursor
        cursor = conn.cursor()

        # Add duration fields
        add_columns_sql = """
        -- Check if columns exist before adding
        DO $$
        BEGIN
            -- Add duration_min_minutes if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='assessments' AND column_name='duration_min_minutes') THEN
                ALTER TABLE public.assessments ADD COLUMN duration_min_minutes INTEGER NULL;
            END IF;

            -- Add duration_max_minutes if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='assessments' AND column_name='duration_max_minutes') THEN
                ALTER TABLE public.assessments ADD COLUMN duration_max_minutes INTEGER NULL;
            END IF;

            -- Add is_untimed if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='assessments' AND column_name='is_untimed') THEN
                ALTER TABLE public.assessments ADD COLUMN is_untimed BOOLEAN DEFAULT FALSE;
            END IF;

            -- Add is_variable_duration if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='assessments' AND column_name='is_variable_duration') THEN
                ALTER TABLE public.assessments ADD COLUMN is_variable_duration BOOLEAN DEFAULT FALSE;
            END IF;
        END
        $$;
        """
        
        cursor.execute(add_columns_sql)
        conn.commit()
        print("Added duration columns to schema")
        
        # Create function to update duration fields
        update_function_sql = """
        CREATE OR REPLACE FUNCTION public.update_duration_fields()
        RETURNS void AS $$
        DECLARE
            assessment_record RECORD;
        BEGIN
            FOR assessment_record IN SELECT id, duration_text FROM public.assessments LOOP
                -- Handle numeric values
                IF assessment_record.duration_text ~ '^\\d+$' THEN
                    UPDATE public.assessments 
                    SET 
                        duration_min_minutes = assessment_record.duration_text::integer,
                        duration_max_minutes = assessment_record.duration_text::integer
                    WHERE id = assessment_record.id;
                    
                -- Handle max values
                ELSIF assessment_record.duration_text ~* '^\\s*max\\s+(\\d+)\\s*$' THEN
                    UPDATE public.assessments 
                    SET 
                        duration_max_minutes = (regexp_matches(assessment_record.duration_text, 'max\\s+(\\d+)', 'i'))[1]::integer
                    WHERE id = assessment_record.id;
                    
                -- Handle range values (e.g., "15 to 35")
                ELSIF assessment_record.duration_text ~* '^\\s*(\\d+)\\s+to\\s+(\\d+)\\s*$' THEN
                    UPDATE public.assessments 
                    SET 
                        duration_min_minutes = (regexp_matches(assessment_record.duration_text, '(\\d+)\\s+to', 'i'))[1]::integer,
                        duration_max_minutes = (regexp_matches(assessment_record.duration_text, 'to\\s+(\\d+)', 'i'))[1]::integer
                    WHERE id = assessment_record.id;
                    
                -- Handle "Untimed"
                ELSIF assessment_record.duration_text ~* '^\\s*untimed' THEN
                    UPDATE public.assessments 
                    SET is_untimed = TRUE
                    WHERE id = assessment_record.id;
                    
                -- Handle variable/TBC/etc.
                ELSIF assessment_record.duration_text ~* '^\\s*(variable|tbc|n/a|-)\\s*$' THEN
                    UPDATE public.assessments 
                    SET is_variable_duration = TRUE
                    WHERE id = assessment_record.id;
                    
                END IF;
            END LOOP;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        cursor.execute(update_function_sql)
        conn.commit()
        print("Created update_duration_fields function")
        
        # Execute the function
        cursor.execute("SELECT public.update_duration_fields();")
        conn.commit()
        print("Executed update_duration_fields to populate duration data")
        
        # Close cursor and connection
        cursor.close()
        conn.close()
        print("Schema update completed successfully!")
        
    except Exception as e:
        print(f"\nError updating schema: {e}")
        raise

if __name__ == "__main__":
    try:
        update_schema()
    except Exception as e:
        print(f"\nFailed to update schema: {e}")
        exit(1) 