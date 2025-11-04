from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
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
