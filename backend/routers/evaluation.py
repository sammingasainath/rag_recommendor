import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Body

from backend.models.evaluation import QueryGroundTruth, EvaluationResult, EvaluationSummary
from backend.services.evaluation_service import evaluation_service

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/evaluation",
    tags=["evaluation"],
    responses={404: {"description": "Not found"}}
)

@router.post("/ground-truth", response_model=Dict[str, str])
async def save_ground_truth(
    ground_truth_data: List[QueryGroundTruth]
):
    """
    Save ground truth data for evaluation.
    
    This endpoint allows saving a list of queries with their relevant assessments
    that will be used for evaluating the recommendation system.
    """
    try:
        evaluation_service.save_ground_truth(ground_truth_data)
        return {"message": f"Successfully saved {len(ground_truth_data)} ground truth queries"}
    except Exception as e:
        logger.error(f"Error saving ground truth data: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving ground truth data: {str(e)}")

@router.get("/ground-truth", response_model=List[QueryGroundTruth])
async def get_ground_truth():
    """
    Get ground truth data used for evaluation.
    
    This endpoint returns all ground truth queries and their relevant assessments.
    """
    try:
        return list(evaluation_service.ground_truth_data.values())
    except Exception as e:
        logger.error(f"Error retrieving ground truth data: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving ground truth data: {str(e)}")

@router.post("/run", response_model=EvaluationSummary)
async def run_evaluation(
    k: int = Query(10, description="Number of recommendations to evaluate (K)")
):
    """
    Run evaluation against all ground truth queries.
    
    This endpoint evaluates the recommendation system against all ground truth queries
    and returns metrics like Mean Recall@K and MAP@K.
    """
    try:
        results = await evaluation_service.evaluate_all(k)
        if not results:
            raise HTTPException(status_code=404, detail="No evaluation results produced. Check if ground truth data exists.")
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running evaluation: {e}")
        raise HTTPException(status_code=500, detail=f"Error running evaluation: {str(e)}")

@router.get("/history", response_model=List[Dict[str, Any]])
async def get_evaluation_history():
    """
    Get history of evaluation runs.
    
    This endpoint returns a list of all previous evaluation runs.
    """
    try:
        return evaluation_service.get_saved_evaluations()
    except Exception as e:
        logger.error(f"Error retrieving evaluation history: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving evaluation history: {str(e)}")

@router.post("/query", response_model=EvaluationResult)
async def evaluate_query(
    query_id: str = Body(..., embed=True),
    k: int = Query(10, description="Number of recommendations to evaluate (K)")
):
    """
    Evaluate a single query.
    
    This endpoint evaluates the recommendation system for a single query
    and returns detailed metrics.
    """
    try:
        result = await evaluation_service.evaluate_query(query_id, k)
        if not result:
            raise HTTPException(status_code=404, detail=f"Query ID '{query_id}' not found in ground truth data")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error evaluating query: {e}")
        raise HTTPException(status_code=500, detail=f"Error evaluating query: {str(e)}") 