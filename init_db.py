import logging
from app.core.database import engine, Base
from app.models import models  # Import models to ensure they are registered with Base
from app.core.deps_check import check_dependencies

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def init_db():
    logger.info("Initializing database...")
    
    # 1. Create Tables
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        raise e

    # 2. Verify Dependencies and Tables
    try:
        check_dependencies()
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        raise e

    logger.info("Database initialization completed.")

if __name__ == "__main__":
    init_db()
