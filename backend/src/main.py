from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from .infrastructure.config import settings
from .presentation.routes import main_router

app = FastAPI(title="Predictor Model Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(main_router)

@app.get("/")
async def root():
    return {"message": "Backend listo para FastAPI con hot reload."}

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "healthy"}
  
@app.get("/hello/{name}", status_code=status.HTTP_200_OK)
async def name(name: str):
    return {"message": f"Hello {name}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
