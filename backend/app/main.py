from fastapi import FastAPI, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.routes import router
from app.auth.exceptions import AuthError, InvalidTokenError, InsufficientPermissionsError
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

origins = [
    "http://localhost:5173",
    "https://main.d12abg5dtejald.amplifyapp.com/",
    "https://develop.d12abg5dtejald.amplifyapp.com/",
]

app = FastAPI(title="Predictor Model Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers for authentication errors
@app.exception_handler(InvalidTokenError)
async def invalid_token_handler(request: Request, exc: InvalidTokenError):
    """Handle invalid token errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError):
    """Handle general authentication errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(InsufficientPermissionsError)
async def insufficient_permissions_handler(request: Request, exc: InsufficientPermissionsError):
    """Handle insufficient permissions errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.get("/")
async def root():
    return {"message": "Backend listo para FastAPI con hot reload."}

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "healthy"}
  

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
