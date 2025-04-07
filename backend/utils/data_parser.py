import ast
import re
import logging
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import timedelta

# Configure logging
logger = logging.getLogger(__name__)

def parse_duration_text(duration_text: str) -> Dict[str, Any]:
    """
    Parse duration text into standardized duration fields.
    
    Args:
        duration_text: The duration text to parse (e.g. "30 minutes", "1 hour", "15-25 minutes")
        
    Returns:
        A dictionary with duration fields:
        - duration_min_minutes: Minimum duration in minutes (or exact duration)
        - duration_max_minutes: Maximum duration in minutes (if a range)
        - is_untimed: Whether the assessment is untimed
        - is_variable_duration: Whether the duration is variable
    """
    if not duration_text or duration_text.lower() in ['', 'na', 'n/a', 'unknown']:
        return {
            'duration_min_minutes': None,
            'duration_max_minutes': None,
            'is_untimed': False,
            'is_variable_duration': False
        }
    
    # Check for untimed
    if re.search(r'untimed|no time limit', duration_text.lower()):
        return {
            'duration_min_minutes': None,
            'duration_max_minutes': None,
            'is_untimed': True,
            'is_variable_duration': False
        }
    
    # Check for variable duration without specific times
    if re.search(r'varies|variable', duration_text.lower()) and not re.search(r'\d', duration_text):
        return {
            'duration_min_minutes': None,
            'duration_max_minutes': None,
            'is_untimed': False,
            'is_variable_duration': True
        }
    
    # Handle ranges like "15-25 minutes"
    range_match = re.search(r'(\d+)\s*(?:-|to)\s*(\d+)\s*(min|minute|minutes|hr|hour|hours)', duration_text.lower())
    if range_match:
        min_val = int(range_match.group(1))
        max_val = int(range_match.group(2))
        unit = range_match.group(3)
        
        # Convert to minutes if needed
        if unit.startswith('hr'):
            min_val *= 60
            max_val *= 60
            
        return {
            'duration_min_minutes': min_val,
            'duration_max_minutes': max_val,
            'is_untimed': False,
            'is_variable_duration': True
        }
    
    # Handle single values like "30 minutes" or "1 hour"
    single_match = re.search(r'(\d+(?:\.\d+)?)\s*(min|minute|minutes|hr|hour|hours)', duration_text.lower())
    if single_match:
        val = float(single_match.group(1))
        unit = single_match.group(2)
        
        # Convert to minutes if needed
        if unit.startswith('hr'):
            val *= 60
            
        minutes = int(val)
        return {
            'duration_min_minutes': minutes,
            'duration_max_minutes': minutes,
            'is_untimed': False,
            'is_variable_duration': False
        }
    
    # If no specific pattern matched but contains numbers, try to extract
    if re.search(r'\d', duration_text):
        logger.warning(f"Could not precisely parse duration: '{duration_text}', extracting numbers only")
        numbers = re.findall(r'\d+', duration_text)
        if numbers:
            # Assume minutes if not specified otherwise
            minutes = int(numbers[0])
            if 'hour' in duration_text.lower():
                minutes *= 60
            return {
                'duration_min_minutes': minutes,
                'duration_max_minutes': minutes,
                'is_untimed': False,
                'is_variable_duration': False
            }
    
    # If all else fails
    logger.warning(f"Could not parse duration: '{duration_text}'")
    return {
        'duration_min_minutes': None,
        'duration_max_minutes': None,
        'is_untimed': False,
        'is_variable_duration': True
    }

def parse_list_string(list_str: str) -> List[str]:
    """
    Convert a string representation of a list into an actual list.
    
    Args:
        list_str: String representation of a list (e.g. "['item1', 'item2']" or "item1, item2")
        
    Returns:
        A list of strings
    """
    if not list_str or list_str in ['', 'na', 'n/a', None]:
        return []
    
    # If it's already a list, return it
    if isinstance(list_str, list):
        return list_str
    
    # Try to parse as Python literal (for lists formatted as string literals)
    try:
        if list_str.startswith('[') and list_str.endswith(']'):
            parsed = ast.literal_eval(list_str)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if item]
    except (ValueError, SyntaxError):
        pass
    
    # If not a valid Python list literal, split by commas
    items = [item.strip() for item in list_str.split(',') if item.strip()]
    return items

def parse_boolean(value: Any) -> bool:
    """
    Convert various boolean representations to Python bool.
    
    Args:
        value: The value to convert to boolean
        
    Returns:
        Boolean value
    """
    if isinstance(value, bool):
        return value
    
    if isinstance(value, (int, float)):
        return bool(value)
    
    if isinstance(value, str):
        value = value.lower().strip()
        return value in ['true', 'yes', 'y', '1', 't']
    
    return False

def parse_csv_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse a single row from a CSV file into a dictionary with proper types.
    
    Args:
        row: Dictionary representing a row from the CSV
        
    Returns:
        Parsed dictionary with correct data types
    """
    parsed = {}
    
    # Map fields and convert types
    if 'name' in row:
        parsed['name'] = str(row['name']).strip() if row['name'] else ''
    
    if 'description' in row:
        parsed['description'] = str(row['description']).strip() if row['description'] else None
    
    if 'url' in row:
        parsed['url'] = str(row['url']).strip() if row['url'] else None
    
    # Parse boolean fields
    if 'remote_testing' in row:
        parsed['remote_testing'] = parse_boolean(row['remote_testing'])
    
    if 'adaptive_irt' in row:
        parsed['adaptive_irt'] = parse_boolean(row['adaptive_irt'])
    
    # Parse list fields
    if 'test_types' in row:
        parsed['test_types'] = parse_list_string(row['test_types'])
    
    if 'job_levels' in row:
        parsed['job_levels'] = parse_list_string(row['job_levels'])
    
    if 'languages' in row:
        parsed['languages'] = parse_list_string(row['languages'])
    
    if 'key_features' in row:
        parsed['key_features'] = parse_list_string(row['key_features'])
    
    # Parse duration
    if 'duration_text' in row:
        parsed['duration_text'] = str(row['duration_text']).strip() if row['duration_text'] else None
        duration_fields = parse_duration_text(parsed['duration_text'])
        parsed.update(duration_fields)
    
    return parsed

def parse_csv_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Read a CSV file and parse each row into a dictionary with the correct data types.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        List of dictionaries representing the parsed data
    """
    try:
        # Read CSV with pandas
        df = pd.read_csv(file_path)
        
        # Convert column names to lowercase and replace spaces with underscores
        df.columns = [col.lower().replace(' ', '_') for col in df.columns]
        
        # Convert to list of dictionaries and parse each row
        rows = df.to_dict(orient='records')
        parsed_rows = [parse_csv_row(row) for row in rows]
        
        logger.info(f"Successfully parsed {len(parsed_rows)} rows from {file_path}")
        return parsed_rows
    
    except Exception as e:
        logger.error(f"Error parsing CSV file {file_path}: {str(e)}")
        raise
