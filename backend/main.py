import logging
from fastapi import FastAPI, Request, Body
from fastapi.middleware.cors import CORSMiddleware
import time
import uvicorn
from typing import Dict, Any

from backend.core.config import settings
from backend.routers import recommendations, assessments, evaluation
from backend.models.api_config import HealthCheckResponse, StandardRecommendationResponse, StandardRecommendationRequest
from backend.models.recommendation import RecommendationRequest
from backend.services.gemini_service import gemini_service
from backend.services.supabase_service import supabase_service
from backend.models.api_config import StandardAssessmentRecommendation

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Define tags for Swagger documentation with preferred order
tags_metadata = [
    {
        "name": "API Configuration",
        "description": "API Endpoints as per API Configuration Documentation given in the mail",
    },
    {
        "name": "recommendations",
        "description": "Recommendation endpoints for the original application",
        "display_name": "Advanced APIs - Recommendations"
    },
    {
        "name": "assessments",
        "description": "Assessment management endpoints",
        "display_name": "Advanced APIs - Assessments"
    },
    {
        "name": "evaluation",
        "description": "Evaluation and metrics endpoints",
        "display_name": "Advanced APIs - Evaluation"
    },
]

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    openapi_tags=tags_metadata,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    return response

# Include routers
app.include_router(recommendations.router, prefix="/api", tags=["recommendations"])
app.include_router(assessments.router, prefix="/api", tags=["assessments"])
app.include_router(evaluation.router, prefix="/api", tags=["evaluation"])

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.APP_VERSION}

# API Configuration Documentation Endpoints

@app.get("/health", response_model=HealthCheckResponse, tags=["API Configuration"])
async def standard_health_check():
    """
    Health check endpoint as per API Configuration Documentation.
    
    Returns a simple status check to verify the API is running.
    """
    return HealthCheckResponse(status="healthy")

@app.post("/recommend", response_model=StandardRecommendationResponse, tags=["API Configuration"])
async def standard_recommend(request_data: StandardRecommendationRequest):
    """
    Assessment recommendation endpoint as per API Configuration Documentation.
    
    Accepts a job description or Natural language query and returns recommended 
    relevant assessments (At most 10, minimum 1) based on the input.
    
    Request body format:
    ```json
    {
      "query": "JD/query in string"
    }
    ```
    """
    # Extract the query from the request body
    query = request_data.query
    if not query:
        return StandardRecommendationResponse(recommended_assessments=[])
    
    # Create a RecommendationRequest object
    request = RecommendationRequest(query=query)
    
    # Process the request using the existing recommendation logic
    try:
        # Use the existing recommendations endpoint functionality
        recommendation_response = await recommendations.get_recommendations(request, top_k=10)
        
        # Transform the response to match the standard format
        standard_assessments = []
        
        for assessment in recommendation_response.recommendations:
            # Convert duration to integer minutes
            duration_minutes = 0
            if assessment.duration_max_minutes is not None:
                duration_minutes = assessment.duration_max_minutes
            elif assessment.duration_min_minutes is not None:
                duration_minutes = assessment.duration_min_minutes
            elif assessment.duration_text and assessment.duration_text.isdigit():
                duration_minutes = int(assessment.duration_text)
            
            # Format URL with SHL domain if needed
            url = assessment.url
            if url and not url.startswith(('http://', 'https://')):
                url = f"https://www.shl.com{url}"
            
            standard_assessment = StandardAssessmentRecommendation(
                url=url or "https://www.shl.com",
                adaptive_support="Yes" if assessment.adaptive_irt else "No",
                description=assessment.description or "No description available",
                duration=duration_minutes,
                remote_support="Yes" if assessment.remote_testing else "No",
                test_type=assessment.test_types
            )
            standard_assessments.append(standard_assessment)
        
        return StandardRecommendationResponse(
            recommended_assessments=standard_assessments
        )
    except Exception as e:
        logger.error(f"Error processing recommendation: {e}")
        # Return empty list in case of error to maintain API contract
        return StandardRecommendationResponse(recommended_assessments=[])

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    ) 