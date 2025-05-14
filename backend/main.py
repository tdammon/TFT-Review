from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os
from app.routes import users_router, videos_router, comments_router, events_router
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.auth import AuthMiddleware
from app.db.database import get_db

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(title="TFT Review API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "http://localhost:3000")],
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

# Add error handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 3001))) 