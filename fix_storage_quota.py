from sqlalchemy.orm import Session
from sqlalchemy import func, update
import sys
import logging

# Add project root to sys.path
import os
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.models import User, Photo

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def recalculate_storage_usage():
    """
    Recalculate storage_used for all users based on their existing photos.
    This fixes inconsistencies caused by the album deletion bug.
    """
    db: Session = SessionLocal()
    try:
        logger.info("Starting storage usage recalculation...")
        
        # 1. Get all users
        users = db.query(User).all()
        logger.info(f"Found {len(users)} users to process.")
        
        updated_count = 0
        
        for user in users:
            # 2. Calculate actual storage used by summing up photo sizes
            # Note: We only count photos where this user is the OWNER.
            # In our model, Photo.owner_id is the billable user.
            actual_usage = db.query(func.sum(Photo.size)).filter(
                Photo.owner_id == user.id
            ).scalar() or 0
            
            # 3. Check if update is needed
            # Ensure storage_used is not None (default 0)
            current_usage = user.storage_used or 0
            
            if current_usage != actual_usage:
                logger.info(f"User {user.id}: Correcting {current_usage} -> {actual_usage} bytes")
                
                # 4. Update user record
                user.storage_used = actual_usage
                updated_count += 1
            else:
                logger.debug(f"User {user.id}: Quota correct ({current_usage} bytes)")
        
        # 5. Commit changes
        if updated_count > 0:
            db.commit()
            logger.info(f"Successfully corrected storage usage for {updated_count} users.")
        else:
            logger.info("All users have correct storage usage. No changes needed.")
            
    except Exception as e:
        logger.error(f"An error occurred during recalculation: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    recalculate_storage_usage()
