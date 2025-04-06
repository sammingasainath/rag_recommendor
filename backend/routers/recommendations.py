from fastapi import APIRouter

router = APIRouter()

@router.get("/recommendations")
async def get_recommendations():
    return {"message": "Recommendations endpoint working"}
