import time
import logging
from typing import List, Dict, Any, Optional

from backend.services.supabase_service import supabase_service
from backend.services.gemini_service import gemini_service
from backend.models.recommendation import RecommendationRequest, RecommendationResponse, AssessmentResponse
from backend.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class RAGPipeline:
    """Retrieval-Augmented Generation pipeline for assessment recommendations."""
    
    @staticmethod
    async def process_query(request: RecommendationRequest) -> RecommendationResponse:
        """Process a recommendation request using RAG pipeline.
        
        Args:
            request: The recommendation request object.
            
        Returns:
            A recommendation response object with the recommended assessments.
            
        Raises:
            ValueError: If the request is invalid or missing required fields.
            RuntimeError: If the pipeline fails to process the request.
        """
        if not request.query:
            raise ValueError("Query cannot be empty")
        
        start_time = time.time()
        logger.info(f"Processing query: {request.query}")
        
        # Step 1: Get query embedding
        try:
            query_embedding = await gemini_service.get_embedding(request.query)
            logger.debug(f"Generated embedding with dimension {len(query_embedding)}")
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise RuntimeError(f"Failed to generate query embedding: {e}")
        
        # Step 2: Prepare filters for vector search
        filters = {}
        
        if request.filters:
            if request.filters.job_levels and len(request.filters.job_levels) > 0:
                filters["filter_job_levels"] = request.filters.job_levels
            
            if request.filters.max_duration_minutes:
                filters["filter_max_duration"] = request.filters.max_duration_minutes
                
            if request.filters.test_types and len(request.filters.test_types) > 0:
                filters["filter_test_types"] = request.filters.test_types
                
            if request.filters.languages and len(request.filters.languages) > 0:
                filters["filter_languages"] = request.filters.languages
                
            if request.filters.remote_testing is not None:
                filters["filter_remote_testing"] = request.filters.remote_testing
        
        # Calculate number of candidates to retrieve (more than we need for re-ranking)
        match_count = request.top_k * settings.RETRIEVAL_MULTIPLIER
        match_threshold = request.filters.min_similarity if request.filters and request.filters.min_similarity else settings.MIN_SIMILARITY_THRESHOLD
        
        logger.debug(f"Vector search parameters: match_count={match_count}, match_threshold={match_threshold}, filters={filters}")
        
        # Step 3: Retrieve candidates via vector similarity search
        try:
            matches = await supabase_service.match_assessments(
                embedding=query_embedding, 
                match_count=match_count,
                min_similarity=match_threshold,
                query=request.query,
                **filters
            )
            
            logger.debug(f"Retrieved {len(matches)} candidate assessments")
            
            if not matches:
                logger.warning("No matching assessments found")
                return RecommendationResponse(
                    recommendations=[],
                    query_embedding=query_embedding,
                    processing_time=time.time() - start_time,
                    total_assessments=0
                )
        except Exception as e:
            logger.error(f"Failed to retrieve candidate assessments: {e}")
            raise RuntimeError(f"Failed to retrieve candidate assessments: {e}")
        
        # Step 4: Generate recommendations using LLM
        try:
            # This function returns a list of indices corresponding to the matches list
            recommended_indices = await gemini_service.generate_recommendations(
                query=request.query,
                context_docs=matches,
                top_k=request.top_k
            )
            
            logger.debug(f"Generated {len(recommended_indices)} recommendation indices")
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            raise RuntimeError(f"Failed to generate recommendations: {e}")
        
        # Step 5: Convert to AssessmentResponse objects
        recommendations = []
        
        # Process each recommended index to get the corresponding match
        for idx in recommended_indices:
            # Validate index is within range
            if not isinstance(idx, int):
                logger.warning(f"Skipping non-integer index: {idx}")
                continue
                
            if idx < 0 or idx >= len(matches):
                logger.warning(f"Skipping out-of-range index: {idx} (valid range: 0-{len(matches)-1})")
                continue
                
            # Get the match from the matches list using the index
            match = matches[idx]
            
            # Create explanations based on similarity score
            explanation = f"This assessment has a semantic relevance of {match.get('similarity', 0.0):.2f} to your query about '{request.query}'"
            
            # Create the assessment response object
            assessment = AssessmentResponse(
                id=match.get("id"),  # Include the ID field
                name=match.get("name"),
                url=match.get("url"),
                description=match.get("description"),
                explanation=explanation,  # Use generated explanation
                similarity_score=match.get("similarity", 0.0),
                relevance_score=match.get("similarity", 0.0),  # Use similarity as relevance for now
                remote_testing=match.get("remote_testing", False),
                adaptive_irt=match.get("adaptive_irt", False),
                test_types=match.get("test_types", []),
                job_levels=match.get("job_levels", []),
                duration_text=match.get("duration_text", ""),
                duration_min_minutes=match.get("duration_min_minutes"),
                duration_max_minutes=match.get("duration_max_minutes"),
                is_untimed=match.get("is_untimed", False),
                is_variable_duration=match.get("is_variable_duration", False),
                languages=match.get("languages", []),
                key_features=match.get("key_features", [])
            )
            
            recommendations.append(assessment)
        
        processing_time = time.time() - start_time
        logger.info(f"Processed query in {processing_time:.2f}s, found {len(recommendations)} recommendations")
        
        # Create and return the response
        return RecommendationResponse(
            recommendations=recommendations,
            query_embedding=query_embedding,
            processing_time=processing_time,
            total_assessments=len(matches)
        )
        
    @staticmethod
    async def get_recommendations(query: str, top_k: int = 10) -> List[AssessmentResponse]:
        """Get assessment recommendations for a query.
        
        This is a convenience method for the evaluation service to use.
        
        Args:
            query: The natural language query.
            top_k: The number of recommendations to return.
            
        Returns:
            A list of assessment responses.
        """
        try:
            logger.info(f"Getting recommendations for evaluation: {query}")
            
            # Create a recommendation request
            request = RecommendationRequest(
                query=query,
                top_k=top_k
            )
            
            # Process the query
            response = await RAGPipeline.process_query(request)
            
            # Return the recommendations
            return response.recommendations
        except Exception as e:
            logger.error(f"Failed to get recommendations for evaluation: {e}")
            # Return an empty list rather than raising an exception
            # This allows the evaluation service to continue with other queries
            return []

# Create a global instance
rag_pipeline = RAGPipeline()
