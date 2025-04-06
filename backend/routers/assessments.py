from fastapi import APIRouter

router = APIRouter()

@router.get("/assessments")
async def get_assessments():
    return {"message": "Assessments endpoint working"}
