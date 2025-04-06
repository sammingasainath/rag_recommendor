"""
Main script to run the SHL assessment catalog scraper.
"""

import logging
import os
import argparse
from pathlib import Path

from .scraper import Scraper
from .json_to_csv import json_to_csv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def main():
    """Run the SHL scraper."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='SHL Assessment Catalog Scraper')
    parser.add_argument('--convert-csv', action='store_true', help='Convert JSON to CSV after scraping')
    parser.add_argument('--csv-only', action='store_true', help='Only convert existing JSON to CSV without scraping')
    args = parser.parse_args()
    
    # Define directories
    output_dir = os.path.join("data", "raw")
    processed_dir = os.path.join("data", "processed")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    Path(processed_dir).mkdir(parents=True, exist_ok=True)
    
    # JSON file paths
    prepack_json = os.path.join(output_dir, "shl_prepack_assessments.json")
    individual_json = os.path.join(output_dir, "shl_individual_assessments.json")
    
    # CSV file paths
    prepack_csv = os.path.join(processed_dir, "shl_prepack_assessments.csv")
    individual_csv = os.path.join(processed_dir, "shl_individual_assessments.csv")
    
    if not args.csv_only:
        # Initialize scraper
        scraper = Scraper(output_dir=output_dir)
        
        # Run scraper for both pre-packaged (12 pages) and individual (32 pages) solutions
        scraper.run(prepack_pages=12, individual_pages=32)
    
    if args.convert_csv or args.csv_only:
        logging.info("Converting JSON files to CSV...")
        
        # Convert pre-packaged assessments
        if os.path.exists(prepack_json):
            json_to_csv(prepack_json, prepack_csv)
        else:
            logging.warning(f"File not found: {prepack_json}")
        
        # Convert individual assessments
        if os.path.exists(individual_json):
            json_to_csv(individual_json, individual_csv)
        else:
            logging.warning(f"File not found: {individual_json}")
        
        logging.info("CSV conversion complete!")

if __name__ == "__main__":
    main() 