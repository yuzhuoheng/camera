from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import get_settings
from app.routers import auth, albums, photos, shares
from app.core.database import engine, Base
from app.models import models
from app.core.deps_check import check_dependencies
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    try:
        check_dependencies()
        # Create database tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created.")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise e
    
    yield
    # Shutdown logic (if any)

settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Include Routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(albums.router, prefix=f"{settings.API_V1_STR}/albums", tags=["albums"])
app.include_router(photos.router, prefix=f"{settings.API_V1_STR}/photos", tags=["photos"])
app.include_router(shares.router, prefix=f"{settings.API_V1_STR}/shares", tags=["shares"])

@app.get("/")
def root():
    return {"message": "Welcome to Camera Server API"}
