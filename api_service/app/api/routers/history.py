from fastapi import APIRouter
router = APIRouter(prefix="/history", tags=["history"])
@router.get("/")
def get_history():
    return []

