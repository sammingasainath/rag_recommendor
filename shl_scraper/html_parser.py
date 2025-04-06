"""
HTML parsing utilities for SHL assessment catalog data extraction.
"""

from bs4 import BeautifulSoup, Tag
from typing import Dict, List, Optional, Any
import logging
import re
import json

logger = logging.getLogger(__name__)

class HTMLParser:
    """Parser for SHL HTML content."""
    
    def __init__(self):
        """Initialize the HTML parser."""
        self.test_type_map = {
            'A': 'Ability & Aptitude',
            'B': 'Biodata & Situational Judgement',
            'C': 'Competencies',
            'D': 'Development & 360',
            'E': 'Assessment Exercises',
            'K': 'Knowledge & Skills',
            'P': 'Personality & Behavior',
            'S': 'Simulations'
        }

    def parse_catalog_page(self, html_content: str, page_num: int = 1, catalog_type: str = None) -> List[Dict[str, Any]]:
        """Parse the catalog page to extract assessments.
        
        Args:
            html_content: HTML content of the page
            page_num: Page number being parsed
            catalog_type: Type of catalog to parse ("prepack" or "individual")
            
        Returns:
            List of assessment dictionaries
        """
        assessments = []
            soup = BeautifulSoup(html_content, 'html.parser')
            
        # Find all tables
            tables = soup.find_all('table')
            if not tables:
            logger.warning("No tables found in HTML content")
                return assessments

        # Try multiple approaches to find the right table
        target_table = None
        
        # Look for table with the appropriate catalog type header
        header_indicator = 'individual test solutions' if catalog_type == 'individual' else 'pre-packaged job solutions'
        
        # Approach 1: Look for table with specific catalog type header
        for table in tables:
            # Check the table headers
            headers = table.find_all('th')
            header_texts = [h.get_text(strip=True).lower() for h in headers]
            
            # Look specifically for the right catalog type
            if any(header_indicator in text for text in header_texts):
                target_table = table
                logger.debug(f"Found target table for {catalog_type} using headers: {header_texts}")
                break
        
        # Approach 2: If no specific table found by catalog type, use generic headers
        if not target_table:
            for table in tables:
                headers = table.find_all('th')
                header_texts = [h.get_text(strip=True).lower() for h in headers]
                if any(text in header_texts for text in ['product', 'remote testing', 'test type']):
                    target_table = table
                    logger.debug(f"Found target table using generic headers: {header_texts}")
                    break
        
        # Approach 3: If still no table found, use the first table with enough rows
        if not target_table:
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) > 3:  # Need header + at least some data rows
                    target_table = table
                    logger.debug("Found target table based on row count")
                    break
        
        # Fallback: Just use the first table
        if not target_table and tables:
            target_table = tables[0]
            logger.debug("Using first table as fallback")
        
        if not target_table:
            logger.warning("Could not identify a suitable table in the HTML")
            return assessments
        
        # Get all rows, skip the header row
        rows = target_table.find_all('tr')
        if len(rows) <= 1:  # Only header or empty
            logger.warning("Not enough rows found in table")
            return assessments
        
        # Skip header row and process up to 12 rows
        data_rows = rows[1:min(13, len(rows))]
        logger.info(f"Found {len(data_rows)} rows in product table")
        
                # Process each row
        for row in data_rows:
                    try:
                        cells = row.find_all('td')
                if len(cells) < 3:  # Need at least name and remote/adaptive indicators
                            continue
                            
                # Extract name and URL from the first cell
                name_cell = cells[0]
                name_link = name_cell.find('a')
                if not name_link:
                    # Try to find any link in the cell
                    name_link = name_cell.find('a', href=True)
                    if not name_link:
                        # If still no link, just use the cell text as name and a placeholder URL
                        name = name_cell.get_text(strip=True)
                        url = f"/solutions/products/product-catalog/view/{name.lower().replace(' ', '-')}/"
                    else:
                        name = name_link.get_text(strip=True)
                        url = name_link.get('href', '')
                else:
                    name = name_link.get_text(strip=True)
                    url = name_link.get('href', '')
                
                # Skip if no name could be extracted
                if not name:
                            continue
                            
                # Default values
                remote_testing = False
                adaptive_irt = False
                test_types = []
                
                # Extract remote testing if there are enough cells
                if len(cells) > 1:
                    remote_cell = cells[1]
                    # Check for green dot (either as content or as an element with content)
                    remote_testing = bool(remote_cell.find('span')) or len(remote_cell.get_text(strip=True)) > 0
                
                # Extract adaptive testing if there are enough cells
                if len(cells) > 2:
                    adaptive_cell = cells[2]
                    # Check for green dot (either as content or as an element with content)
                    adaptive_irt = bool(adaptive_cell.find('span')) or len(adaptive_cell.get_text(strip=True)) > 0
                
                # Extract test types from the last cell if there are enough cells
                if len(cells) > 3:
                    test_type_cell = cells[3]
                    test_types = self._parse_test_types(test_type_cell.get_text(strip=True))
                else:
                    # Default test types if we can't extract from the table
                    test_types = ["Knowledge & Skills"]
                        
                        # Extract job levels from the name
                job_levels = self._extract_job_levels(name)
                
                # Generate key features
                key_features = self._generate_key_features(test_types)
                
                # Create the assessment dictionary
                        assessment = {
                            'name': name,
                            'url': url,
                            'remote_testing': remote_testing,
                            'adaptive_irt': adaptive_irt,
                    'test_types': test_types,
                    'description': f"Assessment for {name}", # Basic description, will be enhanced
                            'job_levels': job_levels,
                    'duration': "",  # Will be calculated based on test types
                    'languages': [],  # Will be populated from detail page or defaulted
                            'key_features': key_features
                        }
                        
                        assessments.append(assessment)
                        
                    except Exception as e:
                logger.error(f"Error parsing row: {str(e)}")
                        continue
                    
        logger.info(f"Extracted {len(assessments)} assessments from page {page_num}")
            return assessments
            
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """Parse the detail page for individual assessment information.
        
        Args:
            html_content: HTML content of the detail page
            
        Returns:
            Dictionary with assessment details
        """
        details = {}
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find the main content section - try multiple approaches
        content_section = None
        for selector in [
            # Try class-based selectors
            ('main', {'class_': 'main'}),
            ('div', {'class_': 'content'}),
            ('div', {'class_': 'product-detail'}),
            ('article', {}),
            ('div', {'id': 'main-content'}),
            # If all else fails, take the body
            ('body', {})
        ]:
            content_section = soup.find(selector[0], **selector[1])
            if content_section:
                logger.debug(f"Found content section using {selector}")
                break
        
        if not content_section:
            logger.warning("Main content section not found in detail page")
            return details
        
        # Extract name using different approaches
        name_elem = None
        for selector in [
            # Try to find the main heading
            ('h1', {}),
            ('h2', {'class_': 'product-title'}),
            ('h2', {}),
            ('div', {'class_': 'product-title'}),
        ]:
            name_elem = content_section.find(selector[0], **selector[1])
            if name_elem:
                break
                
        if name_elem:
            details['name'] = name_elem.get_text(strip=True)
        
        # Extract description - more robust approach
        description_text = ""
        
        # Try with heading
        description_header = None
        for selector in [
            ('h3', {'text': re.compile('Description', re.IGNORECASE)}),
            ('h2', {'text': re.compile('Description', re.IGNORECASE)}),
            ('h4', {'text': re.compile('Description', re.IGNORECASE)}),
            ('strong', {'text': re.compile('Description', re.IGNORECASE)}),
            ('div', {'class_': 'product-description'}),
        ]:
            try:
                if selector[0] == 'h3' and 'text' in selector[1]:
                    description_header = content_section.find(selector[0], string=selector[1]['text'])
                else:
                    description_header = content_section.find(selector[0], **selector[1])
                if description_header:
                    break
                    except Exception as e:
                        continue
                
        if description_header:
            # Get the next element that could contain the description
            desc_elem = description_header.find_next(['p', 'div', 'span'])
            if desc_elem:
                description_text = desc_elem.get_text(strip=True)
                
        # If still no description, try to find paragraphs in the content
        if not description_text and content_section:
            paragraphs = content_section.find_all('p')
            if paragraphs and len(paragraphs) > 0:
                # Try to find a substantial paragraph (likely the description)
                for p in paragraphs:
                    p_text = p.get_text(strip=True)
                    if len(p_text) > 100:  # Descriptions are typically longer
                        description_text = p_text
                        break
        
        if description_text:
            details['description'] = description_text
        
        # Extract job levels - more robust approach
        job_levels = []
        job_level_header = self._find_section_header(content_section, ['Job level', 'Job levels', 'Position level', 'Suitable for'])
        
        if job_level_header:
            # Find the next element that could contain job levels
            job_level_elem = job_level_header.find_next(['p', 'ul', 'ol', 'div', 'span'])
            if job_level_elem:
                if job_level_elem.name in ['ul', 'ol']:
                    job_levels = [li.get_text(strip=True) for li in job_level_elem.find_all('li')]
                else:
                    # If it's a paragraph or div, clean and split by commas
                    job_level_text = job_level_elem.get_text(strip=True)
                    job_levels = [level.strip() for level in re.split(r'[,\n]', job_level_text) if level.strip()]
        
        if job_levels:
            details['job_levels'] = job_levels
        
        # Extract languages - more robust approach
        languages = []
        language_header = self._find_section_header(content_section, ['Language', 'Languages', 'Available in'])
        
        if language_header:
            # Find the next element that could contain languages
            language_elem = language_header.find_next(['p', 'ul', 'ol', 'div', 'span'])
            if language_elem:
                if language_elem.name in ['ul', 'ol']:
                    languages = [li.get_text(strip=True) for li in language_elem.find_all('li')]
                else:
                    # If it's a paragraph or div, clean and split by commas
                    language_text = language_elem.get_text(strip=True)
                    languages = [lang.strip() for lang in re.split(r'[,\n]', language_text) if lang.strip()]
        
        if languages:
            details['languages'] = languages
        
        # Extract assessment length/duration - more robust approach
        duration_header = self._find_section_header(content_section, [
            'Assessment length', 'Duration', 'Test Time', 'Time to Complete', 'Completion Time'
        ])
        
        if duration_header:
            duration_elem = duration_header.find_next(['p', 'div', 'span'])
            if duration_elem:
                duration_text = duration_elem.get_text(strip=True)
                if duration_text:
                    # Extract numerical duration if possible
                    duration_match = re.search(r'(\d+)\s*(min|minute)', duration_text, re.IGNORECASE)
                    if duration_match:
                        minutes = duration_match.group(1)
                        details['duration'] = f"Approximate Completion Time in minutes = {minutes}"
                    else:
                        details['duration'] = duration_text
        
        # Extract remote testing status
        remote_testing_text = soup.find(text=re.compile('Remote Testing', re.IGNORECASE))
        if remote_testing_text:
            # Find any element or content near the remote testing text
            parent = remote_testing_text.parent
            if parent:
                # Check siblings or nearby elements for content
                next_sibling = parent.next_sibling
                nearby_element = parent.find_next(['span', 'div', 'p'])
                
                # If there's any content or elements, consider it as true
                if next_sibling and (str(next_sibling).strip() or nearby_element):
                    details['remote_testing'] = True
                else:
                    details['remote_testing'] = False
        
        # Extract adaptive IRT status
        adaptive_irt_text = soup.find(text=re.compile('Adaptive|IRT', re.IGNORECASE))
        if adaptive_irt_text:
            # Find any element or content near the adaptive IRT text
            parent = adaptive_irt_text.parent
            if parent:
                # Check siblings or nearby elements for content
                next_sibling = parent.next_sibling
                nearby_element = parent.find_next(['span', 'div', 'p'])
                
                # If there's any content or elements, consider it as true
                if next_sibling and (str(next_sibling).strip() or nearby_element):
                    details['adaptive_irt'] = True
                else:
                    details['adaptive_irt'] = False
        
        # Extract key features
        features = []
        features_header = self._find_section_header(content_section, ['Key Features', 'Features', 'Highlights'])
        
        if features_header:
            features_list = features_header.find_next(['ul', 'ol'])
                if features_list:
                features = [li.get_text(strip=True) for li in features_list.find_all('li')]
        
        if features:
            details['key_features'] = features
        
        # Extract test types if available
        test_types = []
        test_types_section = soup.find(text=re.compile('Test Type', re.IGNORECASE))
        if test_types_section:
            parent = test_types_section.parent
            if parent:
                test_types_text = parent.get_text(strip=True)
                # Extract test type codes like PSAB
                type_codes = re.findall(r'[ABCDEKPS]', test_types_text)
                if type_codes:
                    test_types = [self.test_type_map.get(code, code) for code in type_codes]
        
        if test_types:
            details['test_types'] = test_types
        
        return details
        
    def _find_section_header(self, content_section: Tag, possible_texts: List[str]) -> Optional[Tag]:
        """Find a section header in the content with any of the possible texts.
        
        Args:
            content_section: The content section to search in
            possible_texts: List of possible header texts to look for
            
        Returns:
            The found header tag, or None if not found
        """
        for text in possible_texts:
            # Try different header tags
            for tag in ['h2', 'h3', 'h4', 'h5', 'strong', 'b']:
                # Try to find by text content
                header = content_section.find(tag, string=re.compile(text, re.IGNORECASE))
                if header:
                    return header
                
                # Try to find by partial text match
                for elem in content_section.find_all(tag):
                    if elem.get_text(strip=True) and re.search(text, elem.get_text(strip=True), re.IGNORECASE):
                        return elem
        
        return None

    def _parse_test_types(self, test_type_text: str) -> List[str]:
        """Parse test types from the test type cell.
        
        Args:
            test_type_text: Text from the test type cell
            
        Returns:
            List of test type strings
        """
        test_types = []
        
        # Clean and split the text to get individual test type codes
        codes = re.findall(r'[ABCDEKPS]', test_type_text)
        
        # Map codes to full test type names
        for code in codes:
            if code in self.test_type_map:
                test_types.append(self.test_type_map[code])
        
        return test_types
    
    def _extract_job_levels(self, name: str) -> List[str]:
        """Extract job levels from the assessment name.
        
        Args:
            name: Assessment name
            
        Returns:
            List of job level strings
        """
        job_levels = []
        
        # Look for job level indicators in the name
        level_patterns = {
            r'Manager': 'Manager',
            r'Director': 'Director',
            r'Supervisor': 'Supervisor',
            r'Team Lead': 'Team Lead',
            r'Executive': 'Executive',
            r'Entry[ -]Level': 'Entry-Level',
            r'Professional': 'Professional',
            r'Graduate': 'Graduate',
            r'Senior': 'Senior'
        }
        
        for pattern, level in level_patterns.items():
            if re.search(pattern, name, re.IGNORECASE):
                job_levels.append(level)
        
        # If it contains "Short Form" as a job level (though it's not a job level)
        if re.search(r'Short Form', name, re.IGNORECASE):
            pass  # No longer treating "Short Form" as a job level
        
        return job_levels
    
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