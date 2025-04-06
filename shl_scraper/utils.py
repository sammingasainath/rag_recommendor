"""
LLM Utilities for enhanced text processing using Google's Gemini API.
"""

from google import genai
from typing import Dict, List, Optional
import logging
import os
from tenacity import retry, stop_after_attempt, wait_exponential
import json

class GeminiProcessor:
    """Handles text processing using Google's Gemini API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Gemini processor."""
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("Gemini API key must be provided either directly or via GOOGLE_API_KEY environment variable")
            
        self.logger = logging.getLogger(__name__)
        
        try:
            # Configure the Gemini API
            self.client = genai.Client(api_key=self.api_key)
            
            # Set up the model with specific parameters
            generation_config = {
                "temperature": 0.1,  # Low temperature for more focused outputs
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
            
            # Initialize the model
            self.model = "gemini-2.0-pro-exp"
            
        except Exception as e:
            self.logger.error(f"Error initializing Gemini: {str(e)}")
            raise
            
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def extract_assessment_details(self, html_content: str) -> Dict:
        """Extract assessment details from HTML content using Gemini."""
        prompt = f"""
        Extract the following information from this HTML content of an SHL assessment page:
        1. Description: The main description/overview of the assessment
        2. Job Levels: List of job levels this assessment is suitable for
        3. Duration: The time required to complete the assessment
        4. Languages: Available languages for this assessment
        5. Key Features: Any notable features or capabilities
        
        Format the response as a JSON object with these keys: description, job_levels (list), 
        duration, languages (list), key_features (list).
        
        HTML Content:
        {html_content}
        """
        
        try:
            # Generate content with proper error handling
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            
            if not response or not response.text:
                raise ValueError("Empty response from Gemini API")
            
            # Parse the response to extract the JSON
            result = response.text.strip()
            if result.startswith('```json'):
                result = result[7:-3]  # Remove ```json and ``` markers
            
            try:
                # Try to parse as JSON first
                parsed_result = json.loads(result)
            except json.JSONDecodeError:
                # If JSON parsing fails, try eval as fallback
                parsed_result = eval(result)
            
            self.logger.info("Successfully extracted details using Gemini")
            return parsed_result
            
        except Exception as e:
            self.logger.error(f"Error extracting details with Gemini: {str(e)}")
            return {
                'description': "",
                'job_levels': [],
                'duration': "",
                'languages': [],
                'key_features': []
            }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def analyze_assessment_type(self, name: str, description: str) -> str:
        """Analyze and categorize the assessment type using Gemini."""
        prompt = f"""
        Based on this assessment name and description, categorize it into one of these types:
        - Cognitive Ability
        - Personality
        - Skills Assessment
        - Situational Judgment
        - Leadership Assessment
        - Technical Assessment
        - Other (specify)

        Name: {name}
        Description: {description}
        
        Return only the category name.
        """
        
        try:
            # Generate content with proper error handling
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            
            if not response or not response.text:
                raise ValueError("Empty response from Gemini API")
                
            return response.text.strip()
            
        except Exception as e:
            self.logger.error(f"Error analyzing assessment type: {str(e)}")
            return "Other" 