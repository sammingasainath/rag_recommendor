import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse

from backend.models.assessment import AssessmentResponse, AssessmentCreate, AssessmentUpdate
from backend.services.supabase_service import supabase_service
from backend.services.gemini_service import gemini_service
from backend.utils.data_parser import parse_csv_file

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/assessments", response_model=List[AssessmentResponse])
async def get_assessments(
    job_level: Optional[str] = Query(None, description="Filter by job level"),
    test_type: Optional[str] = Query(None, description="Filter by test type"),
    remote: Optional[bool] = Query(None, description="Filter by remote testing availability"),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records to return")
):
    """Get a list of assessments with optional filtering."""
    try:
        filters = {}
        
        if job_level:
            filters["job_level"] = job_level
        
        if test_type:
            filters["test_type"] = test_type
            
        if remote is not None:
            filters["remote_testing"] = remote
        
        assessments = await supabase_service.get_assessments(
            filters=filters,
            skip=skip,
            limit=limit
        )
        
        return assessments
        
    except Exception as e:
        logger.error(f"Error retrieving assessments: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve assessments: {str(e)}")

@router.get("/assessments/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(assessment_id: str):
    """Get a single assessment by ID."""
    try:
        assessment = await supabase_service.get_assessment(assessment_id)
        
        if not assessment:
            raise HTTPException(status_code=404, detail=f"Assessment with ID {assessment_id} not found")
            
        return assessment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving assessment {assessment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve assessment: {str(e)}")

@router.post("/assessments", response_model=AssessmentResponse, status_code=201)
async def create_assessment(assessment: AssessmentCreate, background_tasks: BackgroundTasks):
    """Create a new assessment."""
    try:
        # Generate embedding in the background if text is provided
        if assessment.description:
            try:
                embedding = gemini_service.get_embedding(assessment.description)
                assessment_dict = assessment.model_dump()
                assessment_dict["embedding"] = embedding
            except Exception as e:
                logger.warning(f"Failed to generate embedding: {str(e)}")
                assessment_dict = assessment.model_dump()
        else:
            assessment_dict = assessment.model_dump()
        
        # Create the assessment
        created_assessment = await supabase_service.create_assessment(assessment_dict)
        
        if not created_assessment:
            raise HTTPException(status_code=500, detail="Failed to create assessment")
            
        return created_assessment
        
    except Exception as e:
        logger.error(f"Error creating assessment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create assessment: {str(e)}")

@router.put("/assessments/{assessment_id}", response_model=AssessmentResponse)
async def update_assessment(assessment_id: str, assessment: AssessmentUpdate):
    """Update an existing assessment."""
    try:
        # Check if assessment exists
        existing = await supabase_service.get_assessment(assessment_id)
        
        if not existing:
            raise HTTPException(status_code=404, detail=f"Assessment with ID {assessment_id} not found")
        
        # Generate new embedding if description has changed
        if assessment.description and assessment.description != existing.description:
            try:
                embedding = gemini_service.get_embedding(assessment.description)
                assessment_dict = assessment.model_dump(exclude_unset=True)
                assessment_dict["embedding"] = embedding
            except Exception as e:
                logger.warning(f"Failed to update embedding: {str(e)}")
                assessment_dict = assessment.model_dump(exclude_unset=True)
        else:
            assessment_dict = assessment.model_dump(exclude_unset=True)
        
        # Update the assessment
        updated_assessment = await supabase_service.update_assessment(assessment_id, assessment_dict)
        
        if not updated_assessment:
            raise HTTPException(status_code=500, detail="Failed to update assessment")
            
        return updated_assessment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating assessment {assessment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update assessment: {str(e)}")

@router.delete("/assessments/{assessment_id}", status_code=200)
async def delete_assessment(assessment_id: str):
    """Delete an assessment."""
    try:
        # Check if assessment exists
        existing = await supabase_service.get_assessment(assessment_id)
        
        if not existing:
            raise HTTPException(status_code=404, detail=f"Assessment with ID {assessment_id} not found")
        
        # Delete the assessment
        success = await supabase_service.delete_assessment(assessment_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete assessment")
            
        return {"message": f"Assessment with ID {assessment_id} was deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting assessment {assessment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete assessment: {str(e)}")

@router.post("/assessments/upload", status_code=201)
async def upload_assessments(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    generate_embeddings: bool = Form(True)
):
    """Upload assessments from a CSV file."""
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
        # Save the file temporarily
        temp_file_path = f"temp_{file.filename}"
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(await file.read())
        
        # Parse the CSV file
        assessments = parse_csv_file(temp_file_path)
        
        if generate_embeddings:
            # Generate embeddings for each assessment
            for assessment in assessments:
                if "description" in assessment and assessment["description"]:
                    try:
                        assessment["embedding"] = gemini_service.get_embedding(assessment["description"])
                    except Exception as e:
                        logger.warning(f"Failed to generate embedding: {str(e)}")
        
        # Batch insert assessments
        result = await supabase_service.batch_insert_assessments(assessments)
        
        return {
            "message": f"Successfully processed {len(assessments)} assessments",
            "success_count": result.get("success_count", 0),
            "error_count": result.get("error_count", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading assessments: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload assessments: {str(e)}")
