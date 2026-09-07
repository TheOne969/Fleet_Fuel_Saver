from fastapi import APIRouter
router = APIRouter(prefix="/fleet", tags=["fleet"])
@router.get("/")
def get_fleet():
    return []

