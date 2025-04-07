import time
from typing import List, Dict, Any, Optional
import logging
from fastapi import APIRouter, HTTPException, Depends, Query

from backend.core.config import settings
from backend.models.recommendation import RecommendationRequest, RecommendationResponse
from backend.models.assessment import AssessmentResponse
from backend.services.gemini_service import gemini_service
from backend.services.supabase_service import supabase_service, SupabaseService

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/recommendations",
    tags=["recommendations"],
    responses={404: {"description": "Not found"}}
)

@router.post("", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    top_k: int = Query(
        settings.DEFAULT_TOP_K, 
        description="Number of recommendations to return", 
        ge=1, 
        le=20
    )
):
    """
    Get personalized assessment recommendations based on the query.
    
    This endpoint uses semantic search to find the most relevant assessments
    based on the provided query. The recommendations are ordered by relevance.
    """
    start_time = time.time()
    use_mock = settings.USE_MOCK_DATA
    
    query = request.query
    
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    logger.info(f"Processing recommendation request for query: {query}")
    
    # Generate embedding for the query
    try:
        query_embedding = await gemini_service.get_embedding(query)
        if not query_embedding and not use_mock:
            logger.error("Failed to generate embedding for query")
            raise HTTPException(status_code=500, detail="Failed to generate embedding for query")
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating embedding: {str(e)}")
    
    # Perform vector search with Supabase
    try:
        if use_mock or not supabase_service.initialized:
            # If using mock data or Supabase not initialized, use mock matches
            matches = await supabase_service.match_assessments(
                embedding=query_embedding, 
                match_count=top_k * settings.RETRIEVAL_MULTIPLIER,
                min_similarity=settings.MIN_SIMILARITY_THRESHOLD,
                query=query  # Pass the query directly to match_assessments
            )
        else:
            # Perform real vector search
            matches = await perform_vector_search(query_embedding, query, supabase_service)
            
        if not matches:
            logger.warning("No matching assessments found")
            return RecommendationResponse(
                recommendations=[],
                query_embedding=query_embedding,
                processing_time=time.time() - start_time,
                total_assessments=0,
                timestamp=time.time()
            )
    except Exception as e:
        logger.error(f"Error matching assessments: {e}")
        raise HTTPException(status_code=500, detail=f"Error matching assessments: {str(e)}")
    
    # Generate recommendations using LLM
    try:
        if matches and (top_k < len(matches) or settings.ALWAYS_USE_LLM_RERANKING):
            # Only rerank if we have more matches than needed or if reranking is always enabled
            recommendations = await rerank_recommendations(query, matches, top_k)
        else:
            # Just use the top matches as-is
            recommendations = matches[:top_k]
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        # Fall back to using matches directly
        recommendations = matches[:top_k] if matches else []
    
    # Construct response
    processing_time = time.time() - start_time
    logger.info(f"Generated {len(recommendations)} recommendations in {processing_time:.2f}s")
    
    return RecommendationResponse(
        recommendations=recommendations,
        query_embedding=query_embedding,
        processing_time=processing_time,
        total_assessments=len(matches),
        timestamp=time.time()
    )


async def perform_vector_search(query_embedding: List[float], original_query: str, service: SupabaseService) -> List[Dict[str, Any]]:
    """Perform vector search to find matching assessments."""
    try:
        # Get matches from supabase, with the query included for mock mode
        match_results = await service.match_assessments(
            embedding=query_embedding,
            query=original_query
        )
        
        # Return the matches
        return match_results
    except Exception as e:
        error_message = f"Error matching assessments: {str(e)}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)


async def rerank_recommendations(query: str, matches: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    """
    Rerank the matches using the LLM to get more contextually relevant results.
    
    Args:
        query: The original user query
        matches: List of matching assessments with similarity scores
        top_k: Number of recommendations to return
        
    Returns:
        Reranked list of recommendations
    """
    # Prepare context for the LLM
    context_docs = []
    for match in matches:
        # Create a text representation of the assessment
        doc = f"""Assessment: {match.get('name', 'Unknown')}
Description: {match.get('description', 'No description available')}
Test Types: {', '.join(match.get('test_types', []))}
Job Levels: {', '.join(match.get('job_levels', []))}
Duration: {match.get('duration_text', 'Unknown')}
Features: {', '.join(match.get('key_features', []))}
Vector Similarity Score: {match.get('similarity', 0.0)}
"""
        context_docs.append(doc)
    
    # Call the LLM to rerank
    try:
        reranked_indices = await gemini_service.generate_recommendations(query, context_docs, top_k)
        
        # If reranking failed or returned invalid indices, fall back to original order
        if not reranked_indices or not isinstance(reranked_indices, list):
            logger.warning("Reranking failed, falling back to similarity order")
            return matches[:top_k]
        
        # Filter out invalid indices
        valid_indices = [idx for idx in reranked_indices if isinstance(idx, int) and 0 <= idx < len(matches)]
        
        # Use the reranked indices to build the response
        recommendations = []
        for idx in valid_indices[:top_k]:
            recommendations.append(matches[idx])
        
        # If we don't have enough recommendations, fill with the top similarity matches
        if len(recommendations) < top_k:
            used_ids = {r.get('id') for r in recommendations}
            for match in matches:
                if match.get('id') not in used_ids and len(recommendations) < top_k:
                    recommendations.append(match)
        
        return recommendations
    except Exception as e:
        logger.error(f"Error during recommendation reranking: {e}")
        # Fall back to similarity order
        return matches[:top_k]
