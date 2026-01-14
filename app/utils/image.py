import io
from PIL import Image

def create_thumbnail(file_data: bytes, max_size: tuple[int, int] = (300, 300), quality: int = 85) -> bytes:
    """
    Generate a thumbnail from image bytes.
    
    :param file_data: Original image bytes
    :param max_size: Tuple of (width, height) for maximum thumbnail size
    :param quality: JPEG quality (1-100)
    :return: Thumbnail image bytes (JPEG format)
    """
    try:
        # Open image from bytes
        with Image.open(io.BytesIO(file_data)) as img:
            # Convert to RGB if necessary (e.g. for PNGs with transparency)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Create thumbnail (modifies image in place, preserves aspect ratio)
            img.thumbnail(max_size)
            
            # Save to bytes
            thumb_io = io.BytesIO()
            img.save(thumb_io, format='JPEG', quality=quality)
            return thumb_io.getvalue()
    except Exception as e:
        print(f"Error creating thumbnail: {e}")
        # If thumbnail generation fails, return original data (fallback) 
        # or raise error depending on requirements. 
        # Here we return None to indicate failure or handle upstream.
        raise e
