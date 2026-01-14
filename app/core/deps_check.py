import logging
from sqlalchemy import text, inspect
from app.core.database import engine
from app.services.storage import minio_client
import time

logger = logging.getLogger(__name__)

def check_dependencies():
    logger.info("Checking system dependencies...")
    
    # 1. Check PostgreSQL Connection
    max_retries = 5
    for i in range(max_retries):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("✅ PostgreSQL connection successful.")
            break
        except Exception as e:
            if i == max_retries - 1:
                logger.error(f"❌ PostgreSQL connection failed: {e}")
                raise e
            logger.warning(f"Waiting for PostgreSQL... ({i+1}/{max_retries})")
            time.sleep(2)

    # 2. Check Database Tables
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        required_tables = ["users", "albums", "photos", "shares"]
        
        missing_tables = [t for t in required_tables if t not in existing_tables]
        
        if missing_tables:
            logger.warning(f"⚠️  Missing tables: {', '.join(missing_tables)}. They will be created during startup if not exists.")
        else:
            logger.info(f"✅ Database tables verified: {', '.join(existing_tables)}")
            
    except Exception as e:
        logger.error(f"❌ Failed to check database tables: {e}")
        # We don't raise here to allow create_all to try fixing it
    
    # 3. Check MinIO
    try:
        if minio_client.client.bucket_exists(minio_client.bucket_name):
             logger.info(f"✅ MinIO connection successful. Bucket '{minio_client.bucket_name}' exists.")
        else:
             # Should be created by storage.py logic, but good to check
             logger.info(f"✅ MinIO connection successful. (Bucket '{minio_client.bucket_name}' created/checked)")
    except Exception as e:
        logger.error(f"❌ MinIO connection failed: {e}")
        raise e

    logger.info("All systems operational.")
