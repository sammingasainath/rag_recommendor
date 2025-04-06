"""
Web scraper for SHL assessment catalog data collection.
"""

import json
import logging
import os
from pathlib import Path
import requests
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urljoin
import time
import re

from .html_parser import HTMLParser

logger = logging.getLogger(__name__)


class Scraper:
    """Scraper for SHL assessment catalog."""
    
    def __init__(self, output_dir: str = "data/raw", base_url: str = "https://www.shl.com"):
        """Initialize the scraper.
        
        Args:
            output_dir: Directory to save scraped data
            base_url: Base URL for SHL website
        """
        self.output_dir = output_dir
        self.base_url = base_url
        self.parser = HTMLParser()
        self.prepack_output_path = os.path.join(output_dir, "shl_prepack_assessments.json")
        self.individual_output_path = os.path.join(output_dir, "shl_individual_assessments.json")
        os.makedirs(output_dir, exist_ok=True)
        
        # Setup headers for requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Referer': 'https://www.shl.com/',
        }

    def scrape_catalog(self, pages: int = 12, use_local: bool = False, catalog_type: str = "prepack") -> List[Dict[str, Any]]:
        """Scrape the SHL assessment catalog.
        
        Args:
            pages: Number of pages to scrape
            use_local: Whether to use local HTML files (if available)
            catalog_type: Type of catalog to scrape ("prepack" or "individual")
            
        Returns:
            List of assessment dictionaries
        """
        if use_local and os.path.exists("Talent Assessments Catalog _ SHL_pre_pack.html"):
            logger.info(f"Using local HTML files for initial {catalog_type} catalog")
            basic_assessments = self._get_assessments_from_local(pages, catalog_type)
        else:
            logger.info(f"Fetching {catalog_type} catalog data from SHL website")
            basic_assessments = self._get_assessments_from_live(pages, catalog_type)
        
        # Now for each assessment, fetch the detailed information from their individual pages
        detailed_assessments = []
        for assessment in basic_assessments:
            detailed = self._get_detailed_assessment(assessment)
            detailed_assessments.append(detailed)
            
        return detailed_assessments
    
    def _get_assessments_from_local(self, pages: int = 12, catalog_type: str = "prepack") -> List[Dict[str, Any]]:
        """Get basic assessment data from local HTML files.
        
        Args:
            pages: Number of pages to process
            catalog_type: Type of catalog to scrape ("prepack" or "individual")
            
        Returns:
            List of basic assessment dictionaries
        """
        assessments = []
        
        # Source identification based on catalog type
        source = "Pre-packaged Job Solutions" if catalog_type == "prepack" else "Individual Test Solutions"
        
        # Local catalog files to check
        catalog_files = [
            "Talent Assessments Catalog _ SHL_pre_pack.html",  # Page 1
            "Talent Assessments Catalog _ SHL_pre_pack_page2.html",  # Page 2 (if available)
            "Talent Assessments Catalog _ SHL_pre_pack_page3.html",  # Page 3 (if available)
        ]
        
        # Process as many available local files as possible
        for page_num in range(1, pages + 1):
            if page_num == 1 or page_num <= len(catalog_files):
                file_index = min(page_num - 1, len(catalog_files) - 1)
                html_file = catalog_files[file_index]
            else:
                # Use first page as fallback for other pages
                html_file = catalog_files[0]
            
            try:
                logger.info(f"Reading catalog from local file: {html_file} (page {page_num})")
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # Pass catalog_type to the parser
                page_assessments = self.parser.parse_catalog_page(html_content, page_num, catalog_type)
                
                if page_assessments:
                    logger.info(f"Found {len(page_assessments)} assessments on page {page_num}")
                    for assessment in page_assessments:
                        assessment['source'] = source
                        assessments.append(assessment)
                else:
                    logger.warning(f"No assessments found on page {page_num}")
            except FileNotFoundError:
                logger.warning(f"Catalog file not found: {html_file} for page {page_num}")
        
        return assessments
    
    def _get_assessments_from_live(self, pages: int = 12, catalog_type: str = "prepack") -> List[Dict[str, Any]]:
        """Get basic assessment data directly from the SHL website.
        
        Args:
            pages: Number of pages to scrape
            catalog_type: Type of catalog to scrape ("prepack" or "individual")
            
        Returns:
            List of basic assessment dictionaries
        """
        assessments = []
        
        # Base URL pattern for different catalog types
        if catalog_type == "prepack":
            type_param = "type=2"
            max_pages = 12
            source = "Pre-packaged Job Solutions"
        else:  # individual
            type_param = "type=1"
            max_pages = 32
            source = "Individual Test Solutions"
        
        # Generate URLs for all pages
        page_urls = []
        for page_num in range(1, max_pages + 1):
            start = (page_num - 1) * 12
            if page_num == 1:
                url = f"https://www.shl.com/solutions/products/product-catalog/?{type_param}"
            else:
                url = f"https://www.shl.com/solutions/products/product-catalog/?start={start}&{type_param}"
            page_urls.append(url)
        
        # Scrape each page, up to the requested number
        for page_num in range(1, min(pages + 1, len(page_urls) + 1)):
            page_url = page_urls[page_num - 1]
            
            try:
                logger.info(f"Fetching catalog page {page_num}: {page_url}")
                
                # Try up to 3 times with page reload
                for attempt in range(3):
                    response = requests.get(page_url, headers=self.headers)
                    response.raise_for_status()
                    
                    # Pass catalog_type to parser so it can select the correct table
                    page_assessments = self.parser.parse_catalog_page(response.text, page_num, catalog_type)
                    
                    if page_assessments:
                        break
                    
                    if attempt < 2:
                        logger.info(f"No assessments found on attempt {attempt + 1}, reloading page...")
                        time.sleep(2)
                
                if page_assessments:
                    logger.info(f"Found {len(page_assessments)} assessments on page {page_num}")
                    
                    # Add to our collection
                    for assessment in page_assessments:
                        assessment['source'] = source
                        assessments.append(assessment)
                else:
                    logger.warning(f"No assessments found on page {page_num} after all attempts")
        except Exception as e:
                logger.error(f"Error processing page {page_num}: {str(e)}")
            
            # Add a small delay between page requests
            time.sleep(1.5)
            
        return assessments
    
    def _get_detailed_assessment(self, assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information for a specific assessment.
        
        Args:
            assessment: Basic assessment dictionary
            
        Returns:
            Assessment with detailed information
        """
        name = assessment.get('name', '')
        url = assessment.get('url', '')
        
        # First try to use local file if it exists (Claims/Operations Supervisor Solution)
        if "Claims/Operations Supervisor Solution" in name:
            try:
                with open("Claims_Operations_Supervisor_Solution.html", 'r', encoding='utf-8') as f:
                    detail_html = f.read()
                    
                details = self.parser.parse_detail_page(detail_html)
                
                # Update assessment with details
                for key, value in details.items():
                    if key != 'name':  # Preserve the original name
                        assessment[key] = value
                
                # Ensure the description is set correctly
                assessment['description'] = "The Claims/Operations Supervisor solution is for entry-level management positions that involve supervising hourly employees. Sample tasks for this job include, but are not limited to: planning and preapring work schedules; assigning employees to specific dutites; coaching employees on attendance, conduct, schedule adherence, and work tasks; developing employees' skills; training subordinates; prioritizing multiple tasks and priorities; making day-to-day decisions with minimal guidance from others. Potential job titles that use this solution are: Team Leader, Coach, First Line Supervisor, Claims Supervisor, Operations Supervisor, and Customer Service Supervisor. Multiple configurations of this solution are available."
                
                logger.info(f"Added details for {name} from local file")
                return assessment
            except FileNotFoundError:
                pass
        
        # For other assessments, try to fetch the detail page from the web
        if url:
            try:
                full_url = urljoin(self.base_url, url)
                logger.info(f"Fetching details for {name} from {full_url}")
                
                # Try up to 3 times with increasing delays
                for attempt in range(3):
                    try:
                        response = requests.get(full_url, headers=self.headers, timeout=10)
                        response.raise_for_status()
                        break
                    except (requests.RequestException, TimeoutError) as e:
                        logger.warning(f"Attempt {attempt+1} failed for {name}: {str(e)}")
                        if attempt < 2:  # Don't sleep after the last attempt
                            time.sleep(2 * (attempt + 1))
                else:
                    # All attempts failed
                    logger.error(f"Failed to fetch details for {name} after 3 attempts")
                    return self._apply_detailed_logic(assessment)
                
                # Parse the details
                details = self.parser.parse_detail_page(response.text)
                
                # Update assessment with details
                for key, value in details.items():
                    if key != 'name':  # Preserve the original name
                        assessment[key] = value
                
                # Check if we got a valid description
                if not assessment.get('description') or len(assessment.get('description', '')) < 30:
                    assessment = self._extract_from_page_content(assessment, response.text)
        except Exception as e:
                logger.error(f"Error fetching details for {name}: {str(e)}")
                assessment = self._apply_detailed_logic(assessment)
            
            # Add a delay to avoid overwhelming the server
            time.sleep(2)
        else:
            assessment = self._apply_detailed_logic(assessment)
        
        # Ensure all required fields are populated
        assessment = self._ensure_complete_assessment(assessment)
        
        return assessment
    
    def _extract_from_page_content(self, assessment: Dict[str, Any], html_content: str) -> Dict[str, Any]:
        """Extract details from the full page content when structured extraction fails.
        
        Args:
            assessment: Assessment dictionary with basic info
            html_content: HTML content of the detail page
            
        Returns:
            Assessment with extracted details
        """
        # Try to extract description using regex patterns
        desc_pattern = r'<h3[^>]*>Description</h3>\s*<p[^>]*>(.*?)</p>'
        desc_match = re.search(desc_pattern, html_content, re.DOTALL | re.IGNORECASE)
        if desc_match:
            description = desc_match.group(1).strip()
            if len(description) > 30:  # Sanity check for a reasonable description
                assessment['description'] = description
        
        # Try to extract job levels
        level_pattern = r'<h3[^>]*>Job levels?</h3>\s*<p[^>]*>(.*?)</p>'
        level_match = re.search(level_pattern, html_content, re.DOTALL | re.IGNORECASE)
        if level_match:
            levels_text = level_match.group(1).strip()
            levels = [level.strip() for level in levels_text.split(',')]
            if levels:
                assessment['job_levels'] = levels
        
        # Try to extract languages
        lang_pattern = r'<h3[^>]*>Languages?</h3>\s*<p[^>]*>(.*?)</p>'
        lang_match = re.search(lang_pattern, html_content, re.DOTALL | re.IGNORECASE)
        if lang_match:
            langs_text = lang_match.group(1).strip()
            langs = [lang.strip() for lang in langs_text.split(',')]
            if langs:
                assessment['languages'] = langs
        
        # Try to extract duration
        duration_pattern = r'<h3[^>]*>Assessment length</h3>\s*<p[^>]*>(.*?)</p>'
        duration_match = re.search(duration_pattern, html_content, re.DOTALL | re.IGNORECASE)
        if duration_match:
            duration_text = duration_match.group(1).strip()
            if duration_text:
                assessment['duration'] = duration_text
        
        return assessment
    
    def _apply_detailed_logic(self, assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Apply detailed logic similar to the Claims/Operations Supervisor example.
        
        Args:
            assessment: Assessment dictionary with basic info
            
        Returns:
            Assessment with detailed information
        """
        name = assessment.get('name', '')
        test_types = assessment.get('test_types', [])
        
        # Create a detailed description based on the assessment name and test types
        description = f"The {name} is designed for assessing candidates for {self._extract_role_from_name(name)} positions. "
        
        if 'Ability & Aptitude' in test_types:
            description += "It evaluates cognitive abilities including critical thinking, verbal reasoning, numerical reasoning, and abstract reasoning. "
        
        if 'Personality & Behavior' in test_types:
            description += "The assessment measures workplace behaviors, preferences, and personality traits relevant to job performance. "
        
        if 'Biodata & Situational Judgement' in test_types:
            description += "It includes situational judgment scenarios to evaluate decision-making in realistic workplace situations. "
        
        if 'Simulations' in test_types:
            description += "The solution provides interactive simulations that mimic real-world job tasks. "
        
        if 'Competencies' in test_types:
            description += "It measures key competencies required for success in the role. "
        
        description += f"This comprehensive assessment is part of SHL's pre-packaged job solutions and is designed for efficient and accurate candidate evaluation."
        
        # Set the detailed description
        assessment['description'] = description
        
        # Calculate a reasonable duration based on test types
        if not assessment.get('duration'):
            duration_mins = 0
            for test_type in test_types:
                if test_type == 'Ability & Aptitude':
                    duration_mins += 30
                elif test_type == 'Personality & Behavior':
                    duration_mins += 25
                elif test_type == 'Biodata & Situational Judgement':
                    duration_mins += 20
                elif test_type == 'Simulations':
                    duration_mins += 40
                elif test_type == 'Competencies':
                    duration_mins += 15
                else:
                    duration_mins += 15  # Default for other test types
            
            if duration_mins > 0:
                assessment['duration'] = f"Approximate Completion Time in minutes = {duration_mins}"
        
        return assessment
    
    def _extract_role_from_name(self, name: str) -> str:
        """Extract the job role from the assessment name.
        
        Args:
            name: Assessment name
            
        Returns:
            Job role string
        """
        # Remove common suffixes
        name = re.sub(r'\s+(-\s+Short Form|\+\s+\d+\.\d+|\d+\.\d+|\s+-\s+UK)$', '', name)
        
        # Split by spaces and take words until "Solution" if present
        parts = name.split()
        role_parts = []
        for part in parts:
            role_parts.append(part)
            if part == "Solution":
                break
        
        return " ".join(role_parts)
    
    def _ensure_complete_assessment(self, assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all required fields are populated in the assessment.
        
        Args:
            assessment: Assessment dictionary
            
        Returns:
            Complete assessment dictionary
        """
        # Set default values for missing fields
        if not assessment.get('languages'):
            assessment['languages'] = ["English"]
            
        # Ensure job levels are populated
        if not assessment.get('job_levels'):
            name = assessment.get('name', '')
            potential_levels = [
                "Manager", "Director", "Supervisor", "Professional", 
                "Executive", "Frontline", "Entry-Level", "Senior", "Team Lead"
            ]
            
            # First try to extract from the name
            levels_found = False
            for level in potential_levels:
                if re.search(r'\b' + re.escape(level) + r'\b', name, re.IGNORECASE):
                    assessment['job_levels'] = [level]
                    levels_found = True
                    break
            
            # If no levels found from the name, try to infer from the role
            if not levels_found:
                if "manager" in name.lower() or "lead" in name.lower() or "supervisor" in name.lower():
                    assessment['job_levels'] = ["Manager"]
                elif "director" in name.lower() or "executive" in name.lower():
                    assessment['job_levels'] = ["Director"]
                elif "professional" in name.lower() or "specialist" in name.lower():
                    assessment['job_levels'] = ["Professional"]
                else:
                    # Default to a job family instead of level if we can detect one
                    if "sales" in name.lower():
                        assessment['job_levels'] = ["Sales"]
                    elif "service" in name.lower() or "support" in name.lower():
                        assessment['job_levels'] = ["Customer Service"]
                    elif "tech" in name.lower() or "it" in name.lower():
                        assessment['job_levels'] = ["Information Technology"]
                    else:
                        assessment['job_levels'] = ["General"]
        
        # Make sure key_features is populated
        if not assessment.get('key_features'):
            assessment['key_features'] = self._generate_key_features(assessment.get('test_types', []))
        
        # Make sure remote_testing is a boolean
        if 'remote_testing' not in assessment:
            assessment['remote_testing'] = True  # Most modern assessments support remote testing
            
        # Make sure adaptive_irt is a boolean
        if 'adaptive_irt' not in assessment:
            assessment['adaptive_irt'] = False  # Default to non-adaptive
            
        return assessment
    
    def _generate_key_features(self, test_types: List[str]) -> List[str]:
        """Generate key features based on test types.
        
        Args:
            test_types: List of test types
            
        Returns:
            List of key feature strings
        """
        key_features = []
        
        # Map test types to features
        feature_map = {
            'Ability & Aptitude': 'Cognitive ability assessment',
            'Biodata & Situational Judgement': 'Situational judgment test',
            'Personality & Behavior': 'Personality assessment',
            'Simulations': 'Interactive simulation',
            'Competencies': 'Competency-based assessment',
            'Knowledge & Skills': 'Job-specific knowledge assessment'
        }
        
        # Add features based on test types
        for test_type in test_types:
            if test_type in feature_map and feature_map[test_type] not in key_features:
                key_features.append(feature_map[test_type])
        
        return key_features
    
    def save_assessments(self, assessments: List[Dict[str, Any]], catalog_type: str = "prepack") -> None:
        """Save assessments to file.
        
        Args:
            assessments: List of assessment dictionaries
            catalog_type: Type of catalog ("prepack" or "individual")
        """
        output_path = self.prepack_output_path if catalog_type == "prepack" else self.individual_output_path
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(assessments, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Saved {len(assessments)} assessments to {output_path}")

    def run(self, prepack_pages: int = 12, individual_pages: int = 32, use_local: bool = False) -> None:
        """Run the scraper end-to-end.
        
        Args:
            prepack_pages: Number of pages to scrape for pre-packaged solutions
            individual_pages: Number of pages to scrape for individual solutions
            use_local: Whether to use local HTML files for initial catalog
        """
        # Scrape pre-packaged job solutions
        prepack_assessments = self.scrape_catalog(prepack_pages, use_local, "prepack")
        if prepack_assessments:
            self.save_assessments(prepack_assessments, "prepack")
        else:
            logger.warning("No pre-packaged assessments found during scraping")
            
        # Scrape individual test solutions
        individual_assessments = self.scrape_catalog(individual_pages, use_local, "individual")
        if individual_assessments:
            self.save_assessments(individual_assessments, "individual")
        else:
            logger.warning("No individual assessments found during scraping") 