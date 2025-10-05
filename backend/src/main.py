from fastapi import FastAPI, status

# Create FastAPI app instance
app = FastAPI(title="Predictor Model Backend", version="0.1.0")

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
