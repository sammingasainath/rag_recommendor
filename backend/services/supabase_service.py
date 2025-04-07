import logging
import os
from typing import List, Dict, Any, Optional, Tuple
import httpx
import json
import importlib.util

from backend.core.config import settings
from backend.models.assessment import AssessmentResponse, AssessmentInDB, AssessmentCreate, AssessmentUpdate

# Configure logging
logger = logging.getLogger(__name__)

class SupabaseService:
    """Service for interacting with Supabase database."""
    
    def __init__(self):
        """Initialize the Supabase service."""
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_key = settings.SUPABASE_KEY
        self.service_key = settings.SUPABASE_SERVICE_KEY
        self.assessments_table = settings.SUPABASE_ASSESSMENTS_TABLE
        self.embeddings_column = settings.SUPABASE_EMBEDDINGS_COLUMN
        self.client = None
        self.initialized = False
        self.use_mock = settings.USE_MOCK_DATA
        
        # If mock mode is enabled, don't attempt real initialization
        if self.use_mock:
            logger.info("Mock mode enabled. Using simulated Supabase database.")
            return
            
        # Validate required settings
        if not self.supabase_url or not self.service_key:
            logger.warning("Missing required Supabase configuration")
            logger.warning("Falling back to mock implementation")
            self.use_mock = True
            return
        
        try:
            # Check if supabase is installed
            if importlib.util.find_spec("supabase") is None:
                logger.warning("Supabase Python library not found. Cannot initialize client.")
                self.use_mock = True
                return
                
            # Import create_client dynamically
            from supabase.client import create_client
            import supabase
            
            try:
                # Initialize with direct instantiation to avoid proxy settings
                logger.info(f"Initializing Supabase client with URL: {self.supabase_url}")
                self.client = supabase.Client(
                    self.supabase_url,
                    self.service_key
                )
                
                # Test connection
                self._test_connection()
                self.initialized = True
                logger.info("Successfully initialized Supabase client")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                logger.warning("Falling back to mock implementation")
                self.use_mock = True
                        
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            logger.warning("Falling back to mock implementation")
            self.use_mock = True
    
    def _test_connection(self):
        """Test the connection to Supabase."""
        if not self.client:
            raise RuntimeError("Supabase client is not initialized")
            
        try:
            # Simple query to test connection
            result = self.client.table(self.assessments_table).select('id').limit(1).execute()
            
            # Handle different response formats
            if hasattr(result, 'get') and callable(getattr(result, 'get')):
                # Dictionary-like object with get method
                if result.get('error'):
                    raise RuntimeError(f"Supabase query error: {result.get('error')}")
            elif hasattr(result, 'error') and result.error:
                # Object with error attribute
                raise RuntimeError(f"Supabase query error: {result.error}")
            elif isinstance(result, dict) and 'error' in result and result['error']:
                # Plain dictionary with error key
                raise RuntimeError(f"Supabase query error: {result['error']}")
                
            logger.debug("Supabase connection test successful")
        except Exception as e:
            logger.error(f"Supabase connection test failed: {e}")
            raise
    
    def _get_mock_assessments(self) -> List[AssessmentResponse]:
        """Return mock assessments for testing."""
        return [
            AssessmentResponse(
                id="1",
                name="Verbal Reasoning Assessment",
                description="Test for verbal reasoning skills and language comprehension. Evaluates ability to understand and analyze written information.",
                test_types=["Verbal Reasoning"],
                job_levels=["Professional", "Manager"],
                duration_text="30 minutes",
                duration_min_minutes=30,
                duration_max_minutes=30,
                is_untimed=False,
                is_variable_duration=False,
                remote_testing=True,
                languages=["English"],
                key_features=["Online", "Standardized"],
                similarity_score=0.9,
                relevance_score=0.85
            ),
            AssessmentResponse(
                id="2",
                name="Numerical Reasoning Assessment",
                description="Test for numerical reasoning skills and data interpretation. Measures ability to analyze numerical data and make logical decisions.",
                test_types=["Numerical Reasoning"],
                job_levels=["Professional", "Manager"],
                duration_text="40 minutes",
                duration_min_minutes=40,
                duration_max_minutes=40,
                is_untimed=False,
                is_variable_duration=False,
                remote_testing=True,
                languages=["English"],
                key_features=["Online", "Standardized"],
                similarity_score=0.8,
                relevance_score=0.75
            ),
            AssessmentResponse(
                id="3",
                name="Inductive Reasoning Assessment",
                description="Test for inductive reasoning skills and pattern recognition. Evaluates ability to identify patterns and apply logical thinking.",
                test_types=["Inductive Reasoning"],
                job_levels=["Professional", "Manager"],
                duration_text="25 minutes",
                duration_min_minutes=25,
                duration_max_minutes=25,
                is_untimed=False,
                is_variable_duration=False,
                remote_testing=True,
                languages=["English"],
                key_features=["Online", "Standardized"],
                similarity_score=0.7,
                relevance_score=0.65
            )
        ]
    
    def _get_mock_assessment(self, assessment_id: str) -> Optional[AssessmentResponse]:
        """Return a mock assessment by ID for testing."""
        mock_assessments = {
            "1": AssessmentResponse(
                id="1",
                name="Verbal Reasoning Assessment",
                description="Test for verbal reasoning skills and language comprehension. Evaluates ability to understand and analyze written information.",
                test_types=["Verbal Reasoning"],
                job_levels=["Professional", "Manager"],
                duration_text="30 minutes",
                duration_min_minutes=30,
                duration_max_minutes=30,
                is_untimed=False,
                is_variable_duration=False,
                remote_testing=True,
                languages=["English"],
                key_features=["Online", "Standardized"]
            ),
            "2": AssessmentResponse(
                id="2",
                name="Numerical Reasoning Assessment",
                description="Test for numerical reasoning skills and data interpretation. Measures ability to analyze numerical data and make logical decisions.",
                test_types=["Numerical Reasoning"],
                job_levels=["Professional", "Manager"],
                duration_text="40 minutes",
                duration_min_minutes=40,
                duration_max_minutes=40,
                is_untimed=False,
                is_variable_duration=False,
                remote_testing=True,
                languages=["English"],
                key_features=["Online", "Standardized"]
            ),
            "3": AssessmentResponse(
                id="3",
                name="Inductive Reasoning Assessment",
                description="Test for inductive reasoning skills and pattern recognition. Evaluates ability to identify patterns and apply logical thinking.",
                test_types=["Inductive Reasoning"],
                job_levels=["Professional", "Manager"],
                duration_text="25 minutes",
                duration_min_minutes=25,
                duration_max_minutes=25,
                is_untimed=False,
                is_variable_duration=False,
                remote_testing=True,
                languages=["English"],
                key_features=["Online", "Standardized"]
            )
        }
        return mock_assessments.get(assessment_id)
    
    async def get_assessments(self, filters: Dict[str, Any] = None, skip: int = 0, limit: int = 100) -> List[AssessmentResponse]:
        """
        Get a list of assessments with optional filtering.
        
        Args:
            filters: Dictionary of filters to apply
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of assessment response objects
        """
        # Always use mock data if mock mode is enabled
        if self.use_mock:
            logger.info(f"Mock mode: Using simulated assessments with filters={filters}, skip={skip}, limit={limit}")
            return self._get_mock_assessments()
        
        if not self.initialized or not self.client:
            logger.warning("Using mock assessments as Supabase client is not initialized")
            # Return mock assessments
            return self._get_mock_assessments()
        
        try:
            # Build the query
            query = self.client.table(self.assessments_table).select('*')
            
            # Apply filters if provided
            if filters:
                if 'job_level' in filters and filters['job_level']:
                    query = query.filter('job_levels', 'cs', f"{{'{filters['job_level']}'}}")
                
                if 'test_type' in filters and filters['test_type']:
                    query = query.filter('test_types', 'cs', f"{{'{filters['test_type']}'}}")
                
                if 'remote_testing' in filters:
                    query = query.eq('remote_testing', filters['remote_testing'])
            
            # Apply pagination
            query = query.range(skip, skip + limit - 1)
            
            # Execute the query
            result = query.execute()
            
            if 'error' in result:
                raise RuntimeError(f"Error retrieving assessments: {result['error']}")
            
            # Parse the results
            assessments = []
            for data in result.data:
                assessment = AssessmentResponse(
                    id=data.get('id'),
                    name=data.get('name'),
                    description=data.get('description'),
                    url=data.get('url'),
                    remote_testing=data.get('remote_testing', False),
                    adaptive_irt=data.get('adaptive_irt', False),
                    test_types=data.get('test_types', []),
                    job_levels=data.get('job_levels', []),
                    duration_text=data.get('duration_text'),
                    duration_min_minutes=data.get('duration_min_minutes'),
                    duration_max_minutes=data.get('duration_max_minutes'),
                    is_untimed=data.get('is_untimed', False),
                    is_variable_duration=data.get('is_variable_duration', False),
                    languages=data.get('languages', []),
                    key_features=data.get('key_features', []),
                    created_at=data.get('created_at'),
                    updated_at=data.get('updated_at')
                )
                assessments.append(assessment)
            
            return assessments
        
        except Exception as e:
            logger.error(f"Error retrieving assessments: {e}")
            raise RuntimeError(f"Failed to retrieve assessments: {e}")
    
    async def get_assessment(self, assessment_id: str) -> Optional[AssessmentResponse]:
        """
        Get a single assessment by ID.
        
        Args:
            assessment_id: ID of the assessment to retrieve
            
        Returns:
            Assessment response object if found, None otherwise
        """
        # Always use mock data if mock mode is enabled
        if self.use_mock:
            logger.info(f"Mock mode: Using simulated assessment with id={assessment_id}")
            return self._get_mock_assessment(assessment_id)
        
        if not self.initialized or not self.client:
            logger.warning("Using mock assessment as Supabase client is not initialized")
            # Return a mock assessment
            return self._get_mock_assessment(assessment_id)
        
        try:
            # Query the assessment by ID
            result = self.client.table(self.assessments_table).select('*').eq('id', assessment_id).execute()
            
            if 'error' in result:
                raise RuntimeError(f"Error retrieving assessment: {result['error']}")
            
            # Check if assessment was found
            if not result.data or len(result.data) == 0:
                return None
            
            # Parse the result
            data = result.data[0]
            assessment = AssessmentResponse(
                id=data.get('id'),
                name=data.get('name'),
                description=data.get('description'),
                url=data.get('url'),
                remote_testing=data.get('remote_testing', False),
                adaptive_irt=data.get('adaptive_irt', False),
                test_types=data.get('test_types', []),
                job_levels=data.get('job_levels', []),
                duration_text=data.get('duration_text'),
                duration_min_minutes=data.get('duration_min_minutes'),
                duration_max_minutes=data.get('duration_max_minutes'),
                is_untimed=data.get('is_untimed', False),
                is_variable_duration=data.get('is_variable_duration', False),
                languages=data.get('languages', []),
                key_features=data.get('key_features', []),
                created_at=data.get('created_at'),
                updated_at=data.get('updated_at')
            )
            
            return assessment
            
        except Exception as e:
            logger.error(f"Error retrieving assessment {assessment_id}: {e}")
            raise RuntimeError(f"Failed to retrieve assessment: {e}")
    
    async def create_assessment(self, assessment_data: Dict[str, Any]) -> Optional[AssessmentResponse]:
        """
        Create a new assessment.
        
        Args:
            assessment_data: Dictionary containing assessment data
            
        Returns:
            Created assessment response object if successful, None otherwise
        """
        # Always use mock data if mock mode is enabled
        if self.use_mock:
            logger.info(f"Mock mode: Simulating assessment creation with data={assessment_data}")
            # Create a fake ID
            assessment_data["id"] = "new-mock-assessment-id"
            # Return a mock assessment
            return AssessmentResponse(**assessment_data)
        
        if not self.initialized or not self.client:
            logger.warning("Using mock create_assessment as Supabase client is not initialized")
            # Create a fake ID
            assessment_data["id"] = "new-assessment-id"
            
            # Return a mock assessment
            return AssessmentResponse(**assessment_data)
        
        try:
            # Insert the assessment
            result = self.client.table(self.assessments_table).insert(assessment_data).execute()
            
            if 'error' in result:
                raise RuntimeError(f"Error creating assessment: {result['error']}")
            
            # Get the created assessment
            if not result.data or len(result.data) == 0:
                raise RuntimeError("No data returned after creating assessment")
            
            # Parse the result
            data = result.data[0]
            assessment = AssessmentResponse(
                id=data.get('id'),
                name=data.get('name'),
                description=data.get('description'),
                url=data.get('url'),
                remote_testing=data.get('remote_testing', False),
                adaptive_irt=data.get('adaptive_irt', False),
                test_types=data.get('test_types', []),
                job_levels=data.get('job_levels', []),
                duration_text=data.get('duration_text'),
                duration_min_minutes=data.get('duration_min_minutes'),
                duration_max_minutes=data.get('duration_max_minutes'),
                is_untimed=data.get('is_untimed', False),
                is_variable_duration=data.get('is_variable_duration', False),
                languages=data.get('languages', []),
                key_features=data.get('key_features', []),
                created_at=data.get('created_at'),
                updated_at=data.get('updated_at')
            )
            
            return assessment
            
        except Exception as e:
            logger.error(f"Error creating assessment: {e}")
            raise RuntimeError(f"Failed to create assessment: {e}")
    
    async def update_assessment(self, assessment_id: str, assessment_data: Dict[str, Any]) -> Optional[AssessmentResponse]:
        """
        Update an existing assessment.
        
        Args:
            assessment_id: ID of the assessment to update
            assessment_data: Dictionary containing updated assessment data
            
        Returns:
            Updated assessment response object if successful, None otherwise
        """
        # Always use mock data if mock mode is enabled
        if self.use_mock:
            logger.info(f"Mock mode: Simulating assessment update with id={assessment_id}, data={assessment_data}")
            # Mock the update operation
            existing = self._get_mock_assessment(assessment_id)
            if not existing:
                return None
            
            # Merge the existing data with the update data
            updated_data = existing.model_dump()
            updated_data.update(assessment_data)
            
            # Return a mock assessment
            return AssessmentResponse(**updated_data)
        
        if not self.initialized or not self.client:
            logger.warning("Using mock update_assessment as Supabase client is not initialized")
            # Mock the update operation
            existing = await self.get_assessment(assessment_id)
            if not existing:
                return None
            
            # Merge the existing data with the update data
            updated_data = existing.model_dump()
            updated_data.update(assessment_data)
            
            # Return a mock assessment
            return AssessmentResponse(**updated_data)
        
        try:
            # Update the assessment
            result = self.client.table(self.assessments_table).update(assessment_data).eq('id', assessment_id).execute()
            
            if 'error' in result:
                raise RuntimeError(f"Error updating assessment: {result['error']}")
            
            # Check if assessment was found and updated
            if not result.data or len(result.data) == 0:
                return None
            
            # Parse the result
            data = result.data[0]
            assessment = AssessmentResponse(
                id=data.get('id'),
                name=data.get('name'),
                description=data.get('description'),
                url=data.get('url'),
                remote_testing=data.get('remote_testing', False),
                adaptive_irt=data.get('adaptive_irt', False),
                test_types=data.get('test_types', []),
                job_levels=data.get('job_levels', []),
                duration_text=data.get('duration_text'),
                duration_min_minutes=data.get('duration_min_minutes'),
                duration_max_minutes=data.get('duration_max_minutes'),
                is_untimed=data.get('is_untimed', False),
                is_variable_duration=data.get('is_variable_duration', False),
                languages=data.get('languages', []),
                key_features=data.get('key_features', []),
                created_at=data.get('created_at'),
                updated_at=data.get('updated_at')
            )
            
            return assessment
            
        except Exception as e:
            logger.error(f"Error updating assessment {assessment_id}: {e}")
            raise RuntimeError(f"Failed to update assessment: {e}")
    
    async def delete_assessment(self, assessment_id: str) -> bool:
        """
        Delete an assessment.
        
        Args:
            assessment_id: ID of the assessment to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if not self.initialized or not self.client:
            logger.warning("Using mock delete_assessment as Supabase client is not initialized")
            # Return success if the assessment exists
            existing = await self.get_assessment(assessment_id)
            return existing is not None
        
        try:
            # Delete the assessment
            result = self.client.table(self.assessments_table).delete().eq('id', assessment_id).execute()
            
            if 'error' in result:
                raise RuntimeError(f"Error deleting assessment: {result['error']}")
            
            # Check if assessment was found and deleted
            return result.data and len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error deleting assessment {assessment_id}: {e}")
            raise RuntimeError(f"Failed to delete assessment: {e}")
    
    async def match_assessments(self, embedding: List[float] = None, match_count: int = 10, min_similarity: float = 0.5, query: str = None) -> List[Dict[str, Any]]:
        """
        Match assessments based on embedding similarity.
        
        Args:
            embedding: Query embedding vector to match against
            match_count: Maximum number of matches to return
            min_similarity: Minimum similarity threshold
            query: Original query text (used for mock mode)
            
        Returns:
            List of matching assessments with similarity scores
        """
        # Always use mock data if mock mode is enabled
        if self.use_mock:
            logger.info(f"Mock mode: Using simulated assessment matches")
            return self._get_mock_matches(query)
            
        if not self.initialized or not self.client:
            logger.warning("Using mock match_assessments as Supabase client is not initialized")
            # Return some mock matches
            return self._get_mock_matches(query)
        
        try:
            # If no embedding is provided, just return mock matches
            if embedding is None or len(embedding) == 0:
                logger.warning("No embedding provided, using mock matches")
                return self._get_mock_matches(query)
                
            # Normalize the embedding vector if needed (cosine similarity requires unit vectors)
            # This is just a safety measure in case the embedding isn't already normalized
            magnitude = sum(x*x for x in embedding) ** 0.5
            if magnitude > 0 and abs(magnitude - 1.0) > 0.01:  # If not already normalized
                normalized_embedding = [x/magnitude for x in embedding]
                logger.info("Normalized embedding vector for vector search")
            else:
                normalized_embedding = embedding
                
            # Perform vector search with pgvector - simple approach following documentation
            result = self.client.rpc(
                'match_assessments',
                {
                    'query_embedding': normalized_embedding,
                    'match_threshold': min_similarity,
                    'match_count': match_count
                }
            ).execute()
            
            # Get data field or empty list if not found
            if hasattr(result, 'data'):
                data = result.data or []
            else:
                data = []
            
            # Check if we got any results
            if not data:
                logger.warning("No matches found in vector search, falling back to mock matches")
                return self._get_mock_matches(query)
                
            logger.info(f"Found {len(data)} matches using vector search")
            return data
            
        except Exception as e:
            logger.error(f"Error matching assessments: {e}")
            raise RuntimeError(f"Error matching assessments: {e}")
    
    async def batch_insert_assessments(self, assessments: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Insert multiple assessments in batches.
        
        Args:
            assessments: List of assessment dictionaries to insert
            
        Returns:
            Dictionary with success and error counts
        """
        if not self.initialized or not self.client:
            logger.warning("Using mock batch_insert_assessments as Supabase client is not initialized")
            # Return a mock result
            return {
                "success_count": len(assessments),
                "error_count": 0
            }
        
        try:
            # Process in batches to avoid API limits
            batch_size = 50
            success_count = 0
            error_count = 0
            
            for i in range(0, len(assessments), batch_size):
                batch = assessments[i:i+batch_size]
                
                try:
                    # Insert the batch
                    result = self.client.table(self.assessments_table).insert(batch).execute()
                    
                    if 'error' in result:
                        logger.error(f"Error inserting batch: {result['error']}")
                        error_count += len(batch)
                    else:
                        success_count += len(result.data)
                        
                except Exception as e:
                    logger.error(f"Error inserting batch: {e}")
                    error_count += len(batch)
            
            return {
                "success_count": success_count,
                "error_count": error_count
            }
            
        except Exception as e:
            logger.error(f"Error in batch_insert_assessments: {e}")
            raise RuntimeError(f"Failed to batch insert assessments: {e}")
    
    async def update_assessment_embeddings(self, assessment_id: str, embedding: List[float]) -> bool:
        """
        Update the embedding vector for an assessment.
        
        Args:
            assessment_id: ID of the assessment to update
            embedding: The embedding vector to store
            
        Returns:
            True if the update was successful, False otherwise
        """
        if not self.initialized or not self.client:
            logger.warning("Using mock update_assessment_embeddings as Supabase client is not initialized")
            return True
        
        try:
            # Update just the embedding field
            result = self.client.table(self.assessments_table).update({
                self.embeddings_column: embedding
            }).eq('id', assessment_id).execute()
            
            if 'error' in result:
                raise RuntimeError(f"Error updating assessment embedding: {result['error']}")
            
            # Check if assessment was found and updated
            return result.data and len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating assessment embedding {assessment_id}: {e}")
            raise RuntimeError(f"Failed to update assessment embedding: {e}")

    def _get_mock_matches(self, query=None) -> List[Dict[str, Any]]:
        """Return mock assessment matches for testing."""
        base_assessments = [
            {
                "id": "1",
                "name": "Verbal Reasoning Assessment",
                "description": "Test for verbal reasoning skills and language comprehension. Evaluates ability to understand and analyze written information.",
                "test_types": ["Verbal Reasoning", "Cognitive Ability"],
                "job_levels": ["Professional", "Manager", "Entry Level"],
                "duration_text": "30 minutes",
                "duration_min_minutes": 30,
                "duration_max_minutes": 30,
                "is_untimed": False,
                "is_variable_duration": False,
                "remote_testing": True,
                "languages": ["English", "French", "German"],
                "key_features": ["Online", "Standardized", "Mobile Compatible"]
            },
            {
                "id": "2",
                "name": "Numerical Reasoning Assessment",
                "description": "Test for numerical reasoning skills and data interpretation. Measures ability to analyze numerical data and make logical decisions.",
                "test_types": ["Numerical Reasoning", "Cognitive Ability"],
                "job_levels": ["Professional", "Manager", "Executive"],
                "duration_text": "40 minutes",
                "duration_min_minutes": 40,
                "duration_max_minutes": 40,
                "is_untimed": False,
                "is_variable_duration": False,
                "remote_testing": True,
                "languages": ["English", "Spanish", "French"],
                "key_features": ["Online", "Standardized", "Calculator Provided"]
            },
            {
                "id": "3",
                "name": "Inductive Reasoning Assessment",
                "description": "Test for inductive reasoning skills and pattern recognition. Evaluates ability to identify patterns and apply logical thinking.",
                "test_types": ["Inductive Reasoning", "Cognitive Ability"],
                "job_levels": ["Professional", "Manager"],
                "duration_text": "25 minutes",
                "duration_min_minutes": 25,
                "duration_max_minutes": 25,
                "is_untimed": False,
                "is_variable_duration": False,
                "remote_testing": True,
                "languages": ["English", "French", "Chinese"],
                "key_features": ["Online", "Standardized", "Adaptive"]
            },
            {
                "id": "4",
                "name": "Personality Assessment",
                "description": "Comprehensive personality assessment that measures work-related personality traits and behavioral preferences.",
                "test_types": ["Personality", "Behavioral"],
                "job_levels": ["All Levels"],
                "duration_text": "25 to 35 minutes",
                "duration_min_minutes": 25,
                "duration_max_minutes": 35,
                "is_untimed": False,
                "is_variable_duration": True,
                "remote_testing": True,
                "languages": ["English", "French", "German", "Spanish", "Chinese"],
                "key_features": ["Online", "Normative", "GDPR Compliant"]
            },
            {
                "id": "5",
                "name": "Coding Skills Assessment",
                "description": "Practical coding assessment to evaluate software development skills and problem-solving abilities in real-world scenarios.",
                "test_types": ["Technical", "Coding"],
                "job_levels": ["Professional", "Entry Level"],
                "duration_text": "60 minutes",
                "duration_min_minutes": 60,
                "duration_max_minutes": 60,
                "is_untimed": False,
                "is_variable_duration": False,
                "remote_testing": True,
                "languages": ["English"],
                "key_features": ["Online", "Live Coding", "Multiple Languages"]
            },
            {
                "id": "6",
                "name": "Situational Judgment Test",
                "description": "Assesses decision-making and judgment in workplace scenarios. Evaluates how candidates approach real-world job situations.",
                "test_types": ["Situational Judgment", "Behavioral"],
                "job_levels": ["Manager", "Professional", "Entry Level"],
                "duration_text": "30 minutes",
                "duration_min_minutes": 30,
                "duration_max_minutes": 30,
                "is_untimed": False,
                "is_variable_duration": False,
                "remote_testing": True,
                "languages": ["English", "Spanish", "French"],
                "key_features": ["Online", "Scenario-based", "Video Elements"]
            },
            {
                "id": "7",
                "name": "Leadership Assessment",
                "description": "Evaluates leadership potential and competencies through a combination of cognitive and behavioral measures.",
                "test_types": ["Leadership", "Behavioral", "Cognitive"],
                "job_levels": ["Manager", "Executive"],
                "duration_text": "45 minutes",
                "duration_min_minutes": 45,
                "duration_max_minutes": 45,
                "is_untimed": False,
                "is_variable_duration": False,
                "remote_testing": True,
                "languages": ["English", "French", "German"],
                "key_features": ["Online", "Competency-based", "Benchmarking"]
            }
        ]
        
        # If query is provided, use it to personalize the results
        if query:
            query = query.lower()
            personalized_results = []
            
            # Check for keywords in the query and prioritize matching assessments
            keywords = {
                "coding": ["Coding Skills Assessment"],
                "software": ["Coding Skills Assessment", "Inductive Reasoning Assessment"],
                "developer": ["Coding Skills Assessment", "Inductive Reasoning Assessment"],
                "programming": ["Coding Skills Assessment"],
                "personality": ["Personality Assessment"],
                "behavior": ["Personality Assessment", "Situational Judgment Test"],
                "leadership": ["Leadership Assessment", "Situational Judgment Test"],
                "manager": ["Leadership Assessment", "Numerical Reasoning Assessment"],
                "executive": ["Leadership Assessment", "Numerical Reasoning Assessment"],
                "entry": ["Verbal Reasoning Assessment", "Coding Skills Assessment"],
                "junior": ["Verbal Reasoning Assessment", "Coding Skills Assessment"],
                "technical": ["Coding Skills Assessment", "Numerical Reasoning Assessment"],
                "verbal": ["Verbal Reasoning Assessment"],
                "numerical": ["Numerical Reasoning Assessment"],
                "math": ["Numerical Reasoning Assessment"],
                "reasoning": ["Verbal Reasoning Assessment", "Numerical Reasoning Assessment", "Inductive Reasoning Assessment"]
            }
            
            # Calculate a relevance score for each assessment based on keyword matches
            assessment_scores = {a["name"]: 0 for a in base_assessments}
            
            for keyword, related_assessments in keywords.items():
                if keyword in query:
                    for assessment_name in related_assessments:
                        assessment_scores[assessment_name] = assessment_scores.get(assessment_name, 0) + 1
            
            # Sort assessments by relevance score
            sorted_assessments = sorted(
                base_assessments, 
                key=lambda x: assessment_scores.get(x["name"], 0), 
                reverse=True
            )
            
            # Add similarity scores based on relevance
            for i, assessment in enumerate(sorted_assessments):
                # Create a copy to avoid modifying the original
                result = assessment.copy()
                
                # Calculate a similarity score (higher for more relevant assessments)
                base_similarity = 0.95 - (i * 0.05)  # Starts at 0.95 and decreases by 0.05
                # Ensure score doesn't go below the minimum threshold
                similarity = max(0.6, min(0.98, base_similarity))
                
                result["similarity"] = similarity
                personalized_results.append(result)
            
            return personalized_results
        
        # If no query or not enough matches, return default ordering with made-up similarity scores
        for i, assessment in enumerate(base_assessments):
            assessment["similarity"] = max(0.6, min(0.95, 0.92 - (i * 0.03)))
            
        return base_assessments

    async def update_all_assessment_embeddings(self, assessments: List[dict], embeddings: List[List[float]]) -> Dict[str, int]:
        """
        Update embeddings for multiple assessments in a batch.
        
        Args:
            assessments: List of assessment dictionaries containing at least 'id' field
            embeddings: List of embedding vectors corresponding to assessments
            
        Returns:
            Dictionary with success and error counts
        """
        if not self.initialized or not self.client:
            logger.warning("Using mock update_all_assessment_embeddings as Supabase client is not initialized")
            # Return a mock result
            return {
                "success_count": len(assessments),
                "error_count": 0
            }
        
        if len(assessments) != len(embeddings):
            raise ValueError("Number of assessments must match number of embeddings")
        
        try:
            # Process in batches to avoid API limits
            batch_size = 20
            success_count = 0
            error_count = 0
            
            for i in range(0, len(assessments), batch_size):
                batch_assessments = assessments[i:i+batch_size]
                batch_embeddings = embeddings[i:i+batch_size]
                
                # Create updates
                updates = []
                for j, assessment in enumerate(batch_assessments):
                    if not assessment.get('id'):
                        logger.warning(f"Assessment missing 'id' field: {assessment}")
                        error_count += 1
                        continue
                    
                    # Get the current assessment data
                    try:
                        result = self.client.table(self.assessments_table).select('*').eq('id', assessment['id']).execute()
                        if not result.data or len(result.data) == 0:
                            logger.warning(f"Assessment not found: {assessment['id']}")
                            error_count += 1
                            continue
                        
                        # Preserve existing data and update embedding
                        current_data = result.data[0]
                        current_data[self.embeddings_column] = batch_embeddings[j]
                        updates.append(current_data)
                        
                    except Exception as e:
                        logger.error(f"Error getting current assessment data: {e}")
                        error_count += 1
                        continue
                
                if not updates:
                    continue
                    
                try:
                    # Update the batch
                    result = self.client.table(self.assessments_table).upsert(updates).execute()
                    
                    if 'error' in result:
                        logger.error(f"Error updating embeddings batch: {result['error']}")
                        error_count += len(updates)
                    else:
                        success_count += len(result.data)
                        
                except Exception as e:
                    logger.error(f"Error updating embeddings batch: {e}")
                    error_count += len(updates)
            
            logger.info(f"Updated {success_count} assessment embeddings, {error_count} errors")
            return {
                "success_count": success_count,
                "error_count": error_count
            }
            
        except Exception as e:
            logger.error(f"Error in update_all_assessment_embeddings: {e}")
            raise RuntimeError(f"Failed to update assessment embeddings: {e}")

    def initialize(self) -> bool:
        """Initialize the Supabase client."""
        if self.use_mock:
            logger.info("Mock mode enabled: Skipping Supabase initialization")
            return False
        
        try:
            # Only use the required parameters according to documentation
            self.client = create_client(self.supabase_url, self.service_key)
            
            # Test the connection
            result = self._test_connection()
            if result:
                logger.info("Successfully initialized Supabase client")
                self.initialized = True
                return True
            else:
                logger.warning("Failed to test Supabase connection, falling back to mock implementation")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            logger.info("Falling back to mock implementation")
            return False

# Create a global instance
supabase_service = SupabaseService() 