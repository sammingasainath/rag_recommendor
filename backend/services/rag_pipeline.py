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
            query_embedding = gemini_service.get_embedding(request.query)
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
                query_embedding=query_embedding, 
                match_threshold=match_threshold,
                match_count=match_count,
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
            llm_recommendations = gemini_service.generate_recommendations(
                query=request.query,
                contexts=matches,
                top_k=request.top_k
            )
            
            logger.debug(f"Generated {len(llm_recommendations)} recommendations")
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            raise RuntimeError(f"Failed to generate recommendations: {e}")
        
        # Step 5: Convert to AssessmentResponse objects
        recommendations = []
        
        # Create a dictionary of matches for quick lookup by name
        matches_by_name = {match["name"]: match for match in matches}
        
        for rec in llm_recommendations:
            name = rec.get("name")
            
            if name in matches_by_name:
                match = matches_by_name[name]
                
                assessment = AssessmentResponse(
                    name=name,
                    url=match.get("url"),
                    description=match.get("description"),
                    explanation=rec.get("explanation", ""),
                    similarity_score=match.get("similarity", 0.0),
                    relevance_score=rec.get("relevance_score", 0.0) / 10.0,  # Normalize to 0-1 range
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
            else:
                logger.warning(f"Recommendation for '{name}' not found in retrieved matches")
        
        processing_time = time.time() - start_time
        logger.info(f"Processed query in {processing_time:.2f}s, found {len(recommendations)} recommendations")
        
        # Create and return the response
        return RecommendationResponse(
            recommendations=recommendations,
            query_embedding=query_embedding,
            processing_time=processing_time,
            total_assessments=len(matches)
        )

# Create a global instance
rag_pipeline = RAGPipeline()
