from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import health, assess, verdicts, audit
from .models.loader import model_registry

app = FastAPI(
    title="LoanSense Backend API",
    description="API for LoanSense model serving and database layer",
    version="1.0.0"
)

# CORS config
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Load all models on startup
    print("Initializing model registry...")
    model_registry.load_all()
    print("Model registry initialized.")

# Include routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(assess.router, prefix="/api/v1")
app.include_router(verdicts.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
