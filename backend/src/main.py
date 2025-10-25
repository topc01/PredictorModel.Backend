import os
import logging
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from src.routes import router
from src.s3_client import get_s3_client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Get CORS origins from environment or use defaults
cors_origins_env = os.getenv("CORS_ORIGINS", "")
origins = [origin.strip() for origin in cors_origins_env.split(",")] if cors_origins_env else [
    "http://localhost:5173",
    "https://main.d12abg5dtejald.amplifyapp.com",
    "https://develop.d12abg5dtejald.amplifyapp.com",
]

app = FastAPI(title="Predictor Model Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting up backend application...")
    
    # Initialize S3 client
    try:
        s3_client = get_s3_client()
        logger.info("S3 client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize S3 client: {str(e)}")
        logger.warning("Application will continue without S3 integration")
    
    # Log configuration
    logger.info(f"AWS Region: {os.getenv('AWS_REGION', 'Not set')}")
    logger.info(f"S3 Files Bucket: {os.getenv('S3_FILES_BUCKET', 'Not set')}")
    logger.info(f"S3 Data Bucket: {os.getenv('S3_DATA_BUCKET', 'Not set')}")
    logger.info(f"CORS Origins: {origins}")

@app.get("/")
async def root():
    return {
        "message": "Predictor Model Backend API",
        "version": "0.1.0",
        "status": "running"
    }

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "healthy"}
  
@app.get("/hello/{name}", status_code=status.HTTP_200_OK)
async def name(name: str):
    return {"message": f"Hello {name}"}

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
