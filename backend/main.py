from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os
from app.routes import users_router, videos_router, comments_router, events_router, auth_router, tft_router
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.auth import AuthMiddleware
from app.db.database import get_db
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.routers.health import router as health_router

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(title="TFT Review API")

# Configure CORS
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add auth middleware
app.add_middleware(AuthMiddleware)

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to TFT Review API"}

# Test database connection
@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    try:
        # Execute a simple query with proper text() wrapper
        result = db.execute(text("SELECT 1"))
        return {"message": "Database connection successful", "result": result.scalar()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add routers
app.include_router(videos_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(comments_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(tft_router, prefix="/api/v1")
app.include_router(health_router)

# Add error handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

# Mount static files directory AFTER router registration
static_dir = Path(__file__).parent / "app" / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3001, reload=True) 