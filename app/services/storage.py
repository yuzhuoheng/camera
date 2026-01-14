from minio import Minio
from minio.error import S3Error
from app.core.config import get_settings
import io

settings = get_settings()

class MinioClient:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"Bucket {self.bucket_name} created")
            
            # Ensure policy is set to public read
            import json
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": ["*"]},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"]
                    }
                ]
            }
            self.client.set_bucket_policy(self.bucket_name, json.dumps(policy))
        except S3Error as e:
            print(f"Error checking bucket: {e}")

    def upload_file(self, file_data: bytes, file_name: str, content_type: str) -> str:
        try:
            result = self.client.put_object(
                self.bucket_name,
                file_name,
                io.BytesIO(file_data),
                len(file_data),
                content_type=content_type
            )
            # Return URL
            # Note: This constructs the URL manually or you can use presigned_get_object
            # For public access (if policy allowed):
            protocol = "https" if settings.MINIO_SECURE else "http"
            host = settings.MINIO_PUBLIC_HOST or settings.MINIO_ENDPOINT
            return f"{protocol}://{host}/{self.bucket_name}/{file_name}"
        except S3Error as e:
            print(f"Error uploading file: {e}")
            raise e

    def delete_file(self, file_name: str):
        try:
            self.client.remove_object(self.bucket_name, file_name)
        except S3Error as e:
            print(f"Error deleting file: {e}")
            raise e

minio_client = MinioClient()
