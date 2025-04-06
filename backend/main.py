from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from routers import assessments, recommendations

app = FastAPI(
    title=settings.APP_NAME,
    description="SHL Assessment Recommendation Engine API",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(assessments.router, prefix="/api/v1", tags=["assessments"])
app.include_router(recommendations.router, prefix="/api/v1", tags=["recommendations"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to SHL Assessment Recommendation Engine API",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    ) 