import pandas as pd
import re

# Read the CSV file
df = pd.read_csv('shl_scraper/data/processed/shl_individual_assessments.csv')

# Check if duration column exists
if 'duration' not in df.columns:
    print("Duration column not found. Available columns:")
    print(df.columns.tolist())
    exit(1)

# Get all unique duration values
unique_durations = df['duration'].dropna().unique()
print(f"Total unique duration values: {len(unique_durations)}")
print("\nSample of duration values:")
for val in sorted(unique_durations):
    print(f"'{val}'")

# Categorize duration values
categories = {
    'numeric': [],     # Just numbers, like '30', '17', etc.
    'max': [],         # Values like 'max 20', 'max 30', etc.
    'range': [],       # Values like '15 to 35'
    'untimed': [],     # Specifically 'Untimed'
    'variable': [],    # 'Variable', 'TBC', etc.
    'other': []        # Everything else
}

# Parse each duration value
for duration in unique_durations:
    duration_str = str(duration).strip()
    
    if re.match(r'^\d+$', duration_str):
        # Just a number
        categories['numeric'].append(duration_str)
    elif re.match(r'^\s*max\s+\d+\s*$', duration_str, re.IGNORECASE):
        # Max format
        categories['max'].append(duration_str)
    elif re.match(r'^\s*\d+\s+to\s+\d+\s*$', duration_str, re.IGNORECASE):
        # Range format
        categories['range'].append(duration_str)
    elif re.match(r'^\s*Untimed\s*', duration_str, re.IGNORECASE):
        # Untimed
        categories['untimed'].append(duration_str)
    elif re.match(r'^\s*(Variable|TBC|N/A|-)\s*$', duration_str, re.IGNORECASE):
        # Variable, TBC, N/A, etc.
        categories['variable'].append(duration_str)
    else:
        # Everything else
        categories['other'].append(duration_str)

# Print categorization results
print("\nDuration Categorization:")
for category, values in categories.items():
    if values:
        print(f"\n{category.upper()} ({len(values)}):")
        for val in sorted(values):
            print(f"  '{val}'")

# Calculate statistics and recommendations
print("\nDATABASE REPRESENTATION ANALYSIS:")
all_numeric = []

# Numeric values
if categories['numeric']:
    numeric_values = [int(val) for val in categories['numeric']]
    all_numeric.extend(numeric_values)
    print(f"NUMERIC: Range {min(numeric_values)}-{max(numeric_values)} minutes")

# Max values
if categories['max']:
    max_values = []
    for val in categories['max']:
        match = re.search(r'max\s+(\d+)', val, re.IGNORECASE)
        if match:
            max_values.append(int(match.group(1)))
    if max_values:
        all_numeric.extend(max_values)
        print(f"MAX VALUES: Range max {min(max_values)}-{max(max_values)} minutes")

# Range values
if categories['range']:
    min_values = []
    max_values = []
    for val in categories['range']:
        match = re.search(r'(\d+)\s+to\s+(\d+)', val, re.IGNORECASE)
        if match:
            min_val = int(match.group(1))
            max_val = int(match.group(2))
            min_values.append(min_val)
            max_values.append(max_val)
    if min_values and max_values:
        all_numeric.extend(min_values)
        all_numeric.extend(max_values)
        print(f"RANGE VALUES: Min {min(min_values)}-{max(min_values)}, Max {min(max_values)}-{max(max_values)} minutes")

# Overall range
if all_numeric:
    print(f"OVERALL NUMERIC RANGE: {min(all_numeric)}-{max(all_numeric)} minutes")

# Recommendation
print("\nRECOMMENDATION FOR DATABASE SCHEMA:")
print("We should modify the database schema to properly handle all duration formats:")
print("""
ALTER TABLE public.assessments 
  ADD COLUMN duration_min_minutes INTEGER NULL,
  ADD COLUMN duration_max_minutes INTEGER NULL,
  ADD COLUMN is_untimed BOOLEAN DEFAULT FALSE,
  ADD COLUMN is_variable_duration BOOLEAN DEFAULT FALSE;

-- Update existing data (using PL/pgSQL function so we can use regex and conditionals)
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

-- Execute the function
SELECT public.update_duration_fields();
""")

print("\nRECOMMENDATION FOR DATA LOADING SCRIPT:")
print("""
Changes to the load_data.py script:

1. Define new parsing functions:

def parse_duration_min(duration_text: str) -> int:
    \"\"\"Parse minimum duration from text into minutes.\"\"\"
    if not duration_text or pd.isna(duration_text):
        return None
    
    text = str(duration_text).strip().lower()
    
    # Handle exact numeric values
    if re.match(r'^\\d+$', text):
        return int(text)
    
    # Handle range format ("15 to 35")
    range_match = re.search(r'(\\d+)\\s+to', text)
    if range_match:
        return int(range_match.group(1))
    
    return None

def parse_duration_max(duration_text: str) -> int:
    \"\"\"Parse maximum duration from text into minutes.\"\"\"
    if not duration_text or pd.isna(duration_text):
        return None
    
    text = str(duration_text).strip().lower()
    
    # Handle exact numeric values
    if re.match(r'^\\d+$', text):
        return int(text)
    
    # Handle max format
    max_match = re.search(r'max\\s+(\\d+)', text)
    if max_match:
        return int(max_match.group(1))
    
    # Handle range format ("15 to 35")
    range_match = re.search(r'to\\s+(\\d+)', text)
    if range_match:
        return int(range_match.group(1))
    
    return None

def is_untimed_duration(duration_text: str) -> bool:
    \"\"\"Check if duration is untimed.\"\"\"
    if not duration_text or pd.isna(duration_text):
        return False
    
    return 'untimed' in str(duration_text).strip().lower()

def is_variable_duration(duration_text: str) -> bool:
    \"\"\"Check if duration is variable/TBC.\"\"\"
    if not duration_text or pd.isna(duration_text):
        return False
    
    text = str(duration_text).strip().lower()
    return text in ['variable', 'tbc', 'n/a', '-'] or 'variable' in text

2. Update the record dictionary creation:

record = {
    'name': row['name'],
    'url': row['url'],
    'remote_testing': parse_boolean(row.get('remote_testing', False)),
    'adaptive_irt': parse_boolean(row.get('adaptive_irt', False)),
    'test_types': parse_list_string(row.get('test_types')),
    'description': row.get('description'),
    'job_levels': parse_list_string(row.get('job_levels')),
    'duration_text': row.get('duration'),
    'duration_min_minutes': parse_duration_min(row.get('duration')),
    'duration_max_minutes': parse_duration_max(row.get('duration')),
    'is_untimed': is_untimed_duration(row.get('duration')),
    'is_variable_duration': is_variable_duration(row.get('duration')),
    'languages': parse_list_string(row.get('languages')),
    'key_features': parse_list_string(row.get('key_features')),
    'source': row.get('source', 'shl_individual_assessments.csv')
}
""") 