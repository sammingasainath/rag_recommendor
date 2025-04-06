#!/usr/bin/env python
"""
Standalone script to convert SHL assessment JSON files to CSV format.
"""

import os
import logging
from pathlib import Path
from shl_scraper.json_to_csv import json_to_csv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

def main():
    """Convert SHL assessment JSON files to CSV format."""
    # Define directories
    data_dir = os.path.join("shl_scraper", "data")
    raw_dir = os.path.join(data_dir, "raw")
    processed_dir = os.path.join(data_dir, "processed")
    
    # Ensure directories exist
    Path(processed_dir).mkdir(parents=True, exist_ok=True)
    
    # Define file paths
    prepack_json = os.path.join(raw_dir, "shl_prepack_assessments.json")
    individual_json = os.path.join(raw_dir, "shl_individual_assessments.json")
    prepack_csv = os.path.join(processed_dir, "shl_prepack_assessments.csv")
    individual_csv = os.path.join(processed_dir, "shl_individual_assessments.csv")
    
    # Convert pre-packaged assessments
    logging.info("Starting conversion of JSON files to CSV...")
    
    if os.path.exists(prepack_json):
        json_to_csv(prepack_json, prepack_csv)
    else:
        logging.warning(f"File not found: {prepack_json}")
    
    # Convert individual assessments
    if os.path.exists(individual_json):
        json_to_csv(individual_json, individual_csv)
    else:
        logging.warning(f"File not found: {individual_json}")
    
    logging.info("JSON to CSV conversion complete!")

if __name__ == "__main__":
    main() 