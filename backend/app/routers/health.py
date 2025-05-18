from fastapi import APIRouter

router = APIRouter(
    prefix="/api/v1",
    tags=["health"]
)

@router.get("/health")
async def health_check():
    """
    Simple health check endpoint to verify the API is running.
    Returns a 200 OK response when the API is operational.
    """
    return {"status": "ok", "message": "Service is healthy"} 