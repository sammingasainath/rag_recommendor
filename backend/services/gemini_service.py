import logging
import os
import time
import random
import json
import re
from typing import List, Dict, Any, Optional, Tuple
import tenacity
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from backend.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class GeminiService:
    """Service for interacting with Google's Gemini API."""
    
    def __init__(self):
        """Initialize the Gemini API client."""
        self.api_key = settings.GEMINI_API_KEY
        self.initialized = False
        self.client = None
        self.embedding_model = settings.GEMINI_EMBEDDING_MODEL
        self.generation_model = settings.GEMINI_TEXT_MODEL
        self.use_mock = settings.USE_MOCK_DATA
        
        # If mock mode is enabled, don't attempt real initialization
        if self.use_mock:
            logger.info("Mock mode enabled. Using simulated Gemini API.")
            return
        
        try:
            import google.generativeai as genai
            
            # Configure the Gemini API
            genai.configure(api_key=self.api_key)
            self.client = genai
            
            # Test the connection
            self._test_connection()
            
            self.initialized = True
            logger.info("Successfully initialized Gemini API")
            
        except ImportError:
            logger.error("Google Generative AI library not found. Cannot initialize Gemini service.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini API: {e}")
            logger.warning("Using mock embedding generation as Gemini API is not initialized")
    
    def _test_connection(self):
        """Test the connection to the Gemini API."""
        if not self.client:
            raise RuntimeError("Gemini API client is not initialized")
        
        try:
            # Test embedding generation with a simple text
            test_text = "This is a test."
            
            # Using the embed_content method from version 0.8.4
            embedding_result = self.client.embed_content(
                model=self.embedding_model,
                content=test_text,
                task_type="retrieval_document"
            )
            
            # Check if we got a valid response
            if not embedding_result:
                raise RuntimeError("Failed to generate test embedding")
                
            # Try to extract embedding to validate the response format
            if hasattr(embedding_result, "embedding"):
                # Direct embedding property access
                _ = embedding_result.embedding
            elif hasattr(embedding_result, "embeddings"):
                # If embeddings is a list
                _ = embedding_result.embeddings[0]
            else:
                # Try dictionary access
                _ = embedding_result["embedding"]
                
            logger.debug("Gemini API connection test successful")
            
        except Exception as e:
            logger.error(f"Gemini API connection test failed: {e}")
            raise
    
    def _get_mock_embedding(self, text: str) -> List[float]:
        """
        Generate a mock embedding for testing purposes.
        This creates a deterministic but unique embedding based on the input text.
        """
        # Use a seeded random generator for deterministic results
        random.seed(hash(text) % 10000)
        
        # Generate a 768-dimensional mock embedding vector
        mock_embedding = [random.uniform(-1, 1) for _ in range(768)]
        
        # Normalize the vector (just like real embeddings would be)
        magnitude = sum(x**2 for x in mock_embedding) ** 0.5
        normalized = [x/magnitude for x in mock_embedding]
        
        logger.info(f"Generated mock embedding for text: {text[:50]}...")
        return normalized
    
    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        reraise=True,
    )
    async def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for a text using Gemini API.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        # Always use mock embeddings if mock mode is enabled
        if self.use_mock:
            logger.info(f"Mock mode: Using simulated embeddings for text: {text[:50]}...")
            return self._get_mock_embedding(text)
        
        if not self.initialized or not self.client:
            logger.warning("Using mock embedding generation as Gemini API is not initialized")
            return self._get_mock_embedding(text)
        
        try:
            # Per Google docs - Use embed_content with correct parameters for version 0.8.4+
            embedding_result = self.client.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document"
            )
            
            # Extract the embedding values based on API response format
            if hasattr(embedding_result, "embedding"):
                # Direct embedding property access if available
                embedding = embedding_result.embedding
            elif hasattr(embedding_result, "embeddings"):
                # If embeddings is a list, take the first one
                embedding = embedding_result.embeddings[0]
            else:
                # Try dictionary access if it's in that format
                embedding = embedding_result["embedding"]
                
            logger.info(f"Generated embedding for text: {text[:50]}...")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise RuntimeError(f"Failed to generate embedding: {e}")
    
    def _get_mock_recommendations(self, query: str, context_docs: List[str], top_k: int) -> List[int]:
        """
        Generate mock recommendations for testing purposes.
        
        Args:
            query: User query
            context_docs: List of document texts
            top_k: Number of recommendations to return
            
        Returns:
            List of indices for recommended documents
        """
        # Get at most top_k indices, but no more than available docs
        max_idx = min(len(context_docs), top_k)
        
        if max_idx == 0:
            return []
            
        # Create a deterministic but seemingly varied ordering based on the query
        random.seed(hash(query) % 10000)
        
        # Create a list of available indices and shuffle them
        indices = list(range(len(context_docs)))
        random.shuffle(indices)
        
        # Return the top indices based on our shuffle
        result = indices[:max_idx]
        
        logger.info(f"Generated mock recommendations for query: {query[:50]}...")
        return result
    
    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        reraise=True,
    )
    async def generate_recommendations(self, query: str, context_docs: List[str], top_k: int) -> List[int]:
        """
        Generate personalized recommendations using Gemini API.
        
        Args:
            query: User query
            context_docs: List of document texts
            top_k: Number of recommendations to return
            
        Returns:
            List of indices for recommended documents
        """
        # Always use mock recommendations if mock mode is enabled
        if self.use_mock:
            logger.info(f"Mock mode: Using simulated recommendations for query: {query[:50]}...")
            return self._get_mock_recommendations(query, context_docs, top_k)
        
        if not self.initialized or not self.client:
            logger.warning("Using mock recommendations as Gemini API is not initialized")
            return self._get_mock_recommendations(query, context_docs, top_k)
            
        if not context_docs:
            logger.warning("No context documents provided for recommendation generation")
            return []
            
        try:
            # Build the context string
            context = "\n\n".join([f"DOCUMENT {i+1}:\n{doc}" for i, doc in enumerate(context_docs)])
            
            # Build the prompt for the LLM
            prompt = f"""Your task is to rank the most relevant documents for a given query. 
            
QUERY: {query}

Below are the available documents with their scores from a vector search:

{context}

INSTRUCTIONS:
1. Analyze the query to understand the user's intent and requirements
2. Evaluate each document for its relevance to the query
3. Consider both the semantic similarity and the assessment characteristics
4. Return a JSON array containing the indices of the top {top_k} most relevant documents 
   (0-indexed, based on the DOCUMENT numbers above minus 1)

Example valid outputs:
[0, 2, 1] - This means DOCUMENT 1, DOCUMENT 3, and DOCUMENT 2 are the most relevant, in that order
[5, 3] - This means DOCUMENT 6 and DOCUMENT 4 are the most relevant, in that order

YOUR RESPONSE (just a JSON array of indices):
"""
            
            # Configure generation parameters
            generation_config = {
                "temperature": 0.2,  # Low temperature for more deterministic results
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 100,
            }
            
            # Create the model
            model = self.client.GenerativeModel(
                model_name=self.generation_model,
                generation_config=generation_config,
            )
            
            # Generate content
            response = model.generate_content(prompt)
            
            if not response or not hasattr(response, 'text'):
                raise RuntimeError("Failed to generate recommendations: No response text")
                
            # Parse the response
            response_text = response.text.strip()
            
            # Extract the JSON array from the response
            try:
                # First try to parse the entire response as JSON
                indices = json.loads(response_text)
                
                # Validate that we got a list of integers
                if not isinstance(indices, list):
                    raise ValueError("Response is not a list")
                    
                # Filter out any non-integer values
                indices = [idx for idx in indices if isinstance(idx, int)]
                
                # Validate indices are in range
                indices = [idx for idx in indices if 0 <= idx < len(context_docs)]
                
                logger.info(f"Generated recommendations for query: {query[:50]}...")
                return indices
                
            except json.JSONDecodeError:
                # If that fails, try to extract a JSON array from the text
                import re
                match = re.search(r'\[\s*\d+(?:\s*,\s*\d+)*\s*\]', response_text)
                
                if match:
                    try:
                        indices = json.loads(match.group(0))
                        # Validate indices
                        indices = [idx for idx in indices if isinstance(idx, int) and 0 <= idx < len(context_docs)]
                        return indices
                    except:
                        pass
                        
                logger.error(f"Failed to parse LLM response as JSON: {response_text}")
                raise RuntimeError(f"Failed to parse recommendation indices from response: {response_text}")
                
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            raise RuntimeError(f"Failed to generate recommendations: {e}")

    async def extract_filters_from_query(self, query: str) -> Dict[str, Any]:
        """
        Extract structured filters from a natural language query.
        
        Args:
            query: Natural language query to extract filters from
            
        Returns:
            Dictionary of extracted filters
        """
        # Default empty filters
        default_filters = {
            "job_levels": [],
            "test_types": [],
            "languages": [],
            "max_duration_minutes": None,
            "remote_testing": None,
            "min_similarity": None
        }
        
        # Always use mock filters if mock mode is enabled
        if self.use_mock:
            logger.info(f"Mock mode: Using simulated filters for query: {query[:50]}...")
            return self._get_mock_filters(query)
        
        if not self.initialized or not self.client:
            logger.warning("Using mock filters as Gemini API is not initialized")
            return self._get_mock_filters(query)
        
        try:
            # Define the filter schema
            schema = {
                "type": "object",
                "properties": {
                    "job_levels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Job levels mentioned in the query (Entry-Level, Graduate, Mid-Professional, Professional Individual Contributor, Front Line Manager, Supervisor, Manager, Director, Executive, General Population)"
                    },
                    "test_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Types of tests mentioned in the query (Knowledge & Skills, Simulations, Personality & Behavior, Competencies, Assessment Exercises, Biodata & Situational Judgement, Development & 360, Ability & Aptitude)"
                    },
                    "languages": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Languages mentioned in the query (English (USA), English International, Spanish, French, etc.)"
                    },
                    "max_duration_minutes": {
                        "type": ["integer", "null"],
                        "description": "Maximum duration in minutes"
                    },
                    "remote_testing": {
                        "type": ["boolean", "null"],
                        "description": "Whether remote testing is required"
                    },
                    "min_similarity": {
                        "type": ["number", "null"],
                        "description": "Minimum similarity threshold (0.0 to 1.0)"
                    }
                },
                "required": []
            }
            
            # Prepare the prompt
            prompt = """
            I need to extract structured filters from the following job requirement or assessment query:
            
            "{0}"
            
            Extract only filters that are EXPLICITLY mentioned and return them as a valid JSON object. Only include non-empty values. If a filter is not mentioned, leave it out of the JSON or set it to null.
            
            These are the available filters:
            - job_levels: array of strings (Entry-Level, Graduate, Mid-Professional, Professional Individual Contributor, Front Line Manager, Supervisor, Manager, Director, Executive, General Population)
            - test_types: array of strings (Knowledge & Skills, Simulations, Personality & Behavior, Competencies, Assessment Exercises, Biodata & Situational Judgement, Development & 360, Ability & Aptitude)
            - languages: array of strings (English (USA), English International, Spanish, French, etc.)
            - max_duration_minutes: integer representing maximum duration in minutes
            - remote_testing: boolean (true if remote testing is mentioned, false if in-person is required)
            
            Examples of extracting duration information:
            - "within 30 minutes" → {{"max_duration_minutes": 30}}
            - "less than 1 hour" → {{"max_duration_minutes": 60}}
            
            Return ONLY a valid JSON object with no additional text or explanation. For example:
            
            {{
              "job_levels": ["Entry-Level", "Graduate"],
              "test_types": ["Knowledge & Skills"],
              "max_duration_minutes": 30
            }}
            
            Ensure your response can be parsed by JSON.parse() without any modifications.
            """.format(query)
            
            # Get the Gemini model
            model = self.client.GenerativeModel(self.generation_model)
            
            # Run with structured output mode
            generation_config = {
                "temperature": 0.0,
                "max_output_tokens": 2048,
                "top_p": 0.95,
            }
            
            safety_settings = [{
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            }, {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            }, {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            }, {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            }]
            
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            if not response or not response.text:
                logger.warning("Empty response from Gemini for filter extraction")
                return default_filters
            
            # Log the actual response for debugging
            logger.debug(f"Raw Gemini response: {response.text}")
            
            # Parse the response as JSON
            try:
                response_text = response.text.strip()
                
                # First try to parse the entire response as JSON
                try:
                    filters = json.loads(response_text)
                except json.JSONDecodeError:
                    # Check for markdown code blocks or backticks
                    code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
                    backticks_pattern = r'`([\s\S]*?)`'
                    json_pattern = r'(\{[\s\S]*\})'
                    
                    # Try to extract from markdown code block
                    code_match = re.search(code_block_pattern, response_text)
                    if code_match:
                        logger.debug("Found JSON in code block")
                        filters = json.loads(code_match.group(1).strip())
                    else:
                        # Try to extract from backticks
                        backtick_match = re.search(backticks_pattern, response_text)
                        if backtick_match:
                            logger.debug("Found JSON in backticks")
                            filters = json.loads(backtick_match.group(1).strip())
                        else:
                            # Try to extract any JSON-like structure
                            json_match = re.search(json_pattern, response_text)
                            if json_match:
                                logger.debug("Found JSON-like structure")
                                filters = json.loads(json_match.group(1).strip())
                            else:
                                raise json.JSONDecodeError("Could not find valid JSON in response", response_text, 0)
                
                logger.info(f"Extracted filters from query: {filters}")
                
                # Clean up filters (remove empty arrays and null values)
                for key in list(filters.keys()):
                    if filters[key] is None or (isinstance(filters[key], list) and len(filters[key]) == 0):
                        filters.pop(key)
                        
                # Merge default filters with extracted filters
                merged_filters = {**default_filters, **filters}
                
                return merged_filters
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini's response as JSON: {e}, response: '{response.text}'")
                return default_filters
            except Exception as e:
                logger.error(f"Error processing filter extraction response: {e}")
                return default_filters
                
        except Exception as e:
            logger.error(f"Error extracting filters from query: {e}")
            return default_filters

    def _get_mock_filters(self, query: str) -> Dict[str, Any]:
        """Generate mock filters based on query content for testing or fallback."""
        filters = {
            "job_levels": [],
            "test_types": [],
            "languages": [],
            "max_duration_minutes": None,
            "remote_testing": None,
            "min_similarity": None
        }
        
        # Simple keyword based extraction for testing
        query = query.lower()
        
        # Try to extract job levels
        job_level_keywords = {
            "entry": "Entry-Level",
            "graduate": "Graduate",
            "mid": "Mid-Professional",
            "senior": "Professional Individual Contributor",
            "manager": "Manager",
            "executive": "Executive",
            "director": "Director",
            "supervisor": "Supervisor"
        }
        
        for keyword, level in job_level_keywords.items():
            if keyword in query:
                filters["job_levels"].append(level)
        
        # Try to extract test types
        if "knowledge" in query or "skill" in query:
            filters["test_types"].append("Knowledge & Skills")
        if "personality" in query:
            filters["test_types"].append("Personality & Behavior")
        if "cognitive" in query or "ability" in query or "aptitude" in query:
            filters["test_types"].append("Ability & Aptitude")
        if "simulation" in query:
            filters["test_types"].append("Simulations")
        if "situational" in query:
            filters["test_types"].append("Biodata & Situational Judgement")
        
        # Try to extract duration
        duration_pattern = r'(\d+)\s*(?:min|minute|minutes|hour|hours)'
        duration_match = re.search(duration_pattern, query)
        if duration_match:
            duration = int(duration_match.group(1))
            # Convert hours to minutes if needed
            if "hour" in duration_match.group(0):
                duration *= 60
            filters["max_duration_minutes"] = duration
        
        # Check for remote testing preference
        if "remote" in query or "online" in query:
            filters["remote_testing"] = True
        if "in-person" in query or "in person" in query or "on-site" in query:
            filters["remote_testing"] = False
        
        logger.info(f"Generated mock filters for query: {filters}")
        return filters

# Create a global instance
gemini_service = GeminiService() 