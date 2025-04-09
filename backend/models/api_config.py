from typing import List, Optional
from pydantic import BaseModel, Field

class StandardAssessmentRecommendation(BaseModel):
    """Standard assessment recommendation response model as per API Configuration Documentation."""
    url: str = Field(..., description="Valid URL to the assessment resource")
    adaptive_support: str = Field(..., description="Either 'Yes' or 'No' indicating if the assessment supports adaptive testing")
    description: str = Field(..., description="Detailed description of the assessment")
    duration: int = Field(..., description="Duration of the assessment in minutes")
    remote_support: str = Field(..., description="Either 'Yes' or 'No' indicating if the assessment can be taken remotely")
    test_type: List[str] = Field(..., description="Categories or types of the assessment")
    
    class Config:
        schema_extra = {
            "example": {
                "url": "https://www.shl.com/solutions/products/product-catalog/view/python-new/",
                "adaptive_support": "No",
                "description": "Multi-choice test that measures the knowledge of Python programming, databases, modules and library.",
                "duration": 11,
                "remote_support": "Yes",
                "test_type": ["Knowledge & Skills"]
            }
        }

class StandardRecommendationResponse(BaseModel):
    """Standard recommendation response model as per API Configuration Documentation."""
    recommended_assessments: List[StandardAssessmentRecommendation] = Field(..., description="List of recommended assessments")
    
    class Config:
        schema_extra = {
            "example": {
                "recommended_assessments": [
                    {
                        "url": "https://www.shl.com/solutions/products/product-catalog/view/python-new/",
                        "adaptive_support": "No",
                        "description": "Multi-choice test that measures the knowledge of Python programming, databases, modules and library.",
                        "duration": 11,
                        "remote_support": "Yes",
                        "test_type": ["Knowledge & Skills"]
                    },
                    {
                        "url": "https://www.shl.com/solutions/products/product-catalog/view/technology-professional-8-0-job-focused-assessment/",
                        "adaptive_support": "No",
                        "description": "The Technology Job Focused Assessment assesses key behavioral attributes required for success in fast-paced, rapidly changing technology environments.",
                        "duration": 16,
                        "remote_support": "Yes",
                        "test_type": ["Competencies", "Personality & Behaviour"]
                    }
                ]
            }
        }

class StandardRecommendationRequest(BaseModel):
    """Standard recommendation request model as per API Configuration Documentation."""
    query: str = Field(..., description="Job description or natural language query")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "Looking for programming assessments for Java developers"
            }
        }

class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str = Field("healthy", description="Status of the API")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy"
            }
        } 