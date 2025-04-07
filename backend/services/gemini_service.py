import logging
import os
import time
import random
import json
from typing import List, Dict, Any, Optional
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


# Create a global instance
gemini_service = GeminiService() 