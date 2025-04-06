import json
import csv
import os
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def json_to_csv(json_file, csv_file):
    """
    Convert JSON assessments to CSV format.
    
    Args:
        json_file: Path to the JSON file
        csv_file: Path to the output CSV file
    """
    try:
        # Load JSON data
        with open(json_file, 'r', encoding='utf-8') as f:
            assessments = json.load(f)
        
        logger.info(f"Loaded {len(assessments)} assessments from {json_file}")
        
        if not assessments:
            logger.warning(f"No assessments found in {json_file}")
            return
        
        # Extract field names from the first assessment
        fieldnames = list(assessments[0].keys())
        
        # Write to CSV
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for assessment in assessments:
                # Process list fields
                for key, value in assessment.items():
                    if isinstance(value, list):
                        assessment[key] = "; ".join(str(item) for item in value)
                
                writer.writerow(assessment)
        
        logger.info(f"Successfully wrote {len(assessments)} assessments to {csv_file}")
        
    except Exception as e:
        logger.error(f"Error converting {json_file} to CSV: {str(e)}")

def main():
    # Define file paths
    data_dir = os.path.join(os.getcwd(), "data")
    raw_dir = os.path.join(data_dir, "raw")
    processed_dir = os.path.join(data_dir, "processed")
    
    # Ensure processed directory exists
    os.makedirs(processed_dir, exist_ok=True)
    
    # Define input and output files
    prepack_json = os.path.join(raw_dir, "shl_prepack_assessments.json")
    individual_json = os.path.join(raw_dir, "shl_individual_assessments.json")
    prepack_csv = os.path.join(processed_dir, "shl_prepack_assessments.csv")
    individual_csv = os.path.join(processed_dir, "shl_individual_assessments.csv")
    
    # Convert both JSON files to CSV
    logger.info("Starting conversion of JSON files to CSV...")
    
    # Convert pre-packaged assessments
    if os.path.exists(prepack_json):
        json_to_csv(prepack_json, prepack_csv)
    else:
        logger.warning(f"File not found: {prepack_json}")
    
    # Convert individual assessments
    if os.path.exists(individual_json):
        json_to_csv(individual_json, individual_csv)
    else:
        logger.warning(f"File not found: {individual_json}")
    
    logger.info("Conversion complete!")

if __name__ == "__main__":
    main() 