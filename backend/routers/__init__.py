"""
Routers package initialization.
"""

# API Routers for SHL Assessment Recommendation Engine 
from .recommendations import router as recommendations_router
from .assessments import router as assessments_router
from .evaluation import router as evaluation_router

__all__ = ["recommendations_router", "assessments_router", "evaluation_router"] 