import logging
from sqlalchemy import text, inspect, create_engine
from app.core.database import engine
from app.core.config import get_settings
from app.services.storage import minio_client
import time
from sqlalchemy.exc import ProgrammingError

logger = logging.getLogger(__name__)
settings = get_settings()

def ensure_database_exists():
    """
    Check if the database exists, if not, create it.
    Connects to the default 'postgres' database to perform this check.
    """
    target_db = settings.POSTGRES_DB
    # Construct URL for the default 'postgres' database
    postgres_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/postgres"
    
    try:
        # Create a temporary engine to connect to 'postgres' db
        tmp_engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
        with tmp_engine.connect() as conn:
            # Check if database exists
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{target_db}'"))
            if not result.scalar():
                logger.info(f"Database '{target_db}' does not exist. Creating...")
                conn.execute(text(f"CREATE DATABASE {target_db}"))
                logger.info(f"✅ Database '{target_db}' created successfully.")
            else:
                logger.info(f"✅ Database '{target_db}' already exists.")
    except Exception as e:
        logger.error(f"❌ Failed to ensure database exists: {e}")
        # We don't raise here, let the main connection check fail if it must
        # In some cases (e.g. cloud SQL), we might not have permission to create DB, 
        # but the DB might already exist or be created by other means.

def check_dependencies():
    logger.info("Checking system dependencies...")
    
    # 0. Ensure Database Exists
    ensure_database_exists()
    
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
        required_tables = ["users", "albums", "photos", "shares", "user_quota_logs", "user_invites"]
        
        missing_tables = [t for t in required_tables if t not in existing_tables]
        
        if missing_tables:
            logger.warning(f"⚠️  Missing tables: {', '.join(missing_tables)}. They will be created during startup if not exists.")
        else:
            logger.info(f"✅ Database tables verified: {', '.join(existing_tables)}")
            
            # 2.1 Check Columns for existing tables
            # This is a simple migration-like check to add missing columns
            try:
                for table_name in required_tables:
                    if table_name not in existing_tables:
                        continue
                        
                    inspector_columns = inspector.get_columns(table_name)
                    existing_column_names = [c["name"] for c in inspector_columns]
                    
                    # Define expected columns for each table (simplified, only critical new columns)
                    expected_new_columns = []
                    if table_name == "users":
                        expected_new_columns = [
                            {"name": "storage_used", "type": "BIGINT DEFAULT 0"},
                            {"name": "storage_limit", "type": "BIGINT DEFAULT 524288000"}
                        ]
                    # Add other tables if needed
                    
                    if expected_new_columns:
                        with engine.connect() as conn:
                            for col in expected_new_columns:
                                if col["name"] not in existing_column_names:
                                    logger.warning(f"⚠️  Missing column '{col['name']}' in table '{table_name}'. Adding it...")
                                    try:
                                        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col['name']} {col['type']}"))
                                        conn.commit()
                                        logger.info(f"✅ Column '{col['name']}' added to '{table_name}'.")
                                    except Exception as e:
                                        logger.error(f"❌ Failed to add column '{col['name']}' to '{table_name}': {e}")
            except Exception as e:
                logger.error(f"❌ Failed to check/update table columns: {e}")
            
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
