"""
Google Cloud Storage integration for PDF uploads
"""

from google.cloud import storage
from google.oauth2 import service_account
import os
import uuid
from typing import Optional
import logging
from dotenv import load_dotenv
from datetime import timedelta
logger = logging.getLogger(__name__)

load_dotenv(dotenv_path=".env")
# GCS Configuration
BUCKET_NAME = "automateprint"
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Initialize GCS client
try:
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
    storage_client = storage.Client(credentials=credentials, project=credentials.project_id)
    bucket = storage_client.bucket(BUCKET_NAME)
    logger.info(f"✅ GCS client initialized for bucket: {BUCKET_NAME}")
except Exception as e:
    logger.error(f"❌ GCS initialization failed: {e}")
    bucket = None


def upload_pdf_to_gcs(file_content: bytes, filename: str, order_id: str) -> Optional[str]:
    """
    Upload PDF to Google Cloud Storage
    
    Args:
        file_content: PDF file bytes
        filename: Original filename
        order_id: Order ID for organizing files
    
    Returns:
        Public URL of uploaded file or None on failure
    """
    if not bucket:
        logger.error("GCS bucket not initialized")
        return None
    
    try:
        # Generate unique blob name
        file_extension = filename.split('.')[-1] if '.' in filename else 'pdf'
        blob_name = f"orders/{order_id}/{uuid.uuid4().hex}.{file_extension}"
        
        # Upload file
        blob = bucket.blob(blob_name)
        blob.upload_from_string(file_content, content_type='application/pdf')
        
        file_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=1),
            method="GET",
        )
        
        logger.info(f"✅ File uploaded: {blob_name}")
        
        return file_url
        
    except Exception as e:
        logger.error(f"❌ GCS upload failed: {e}")
        return None


def delete_file_from_gcs(file_url: str) -> bool:
    """
    Delete file from GCS
    
    Args:
        file_url: Public URL of the file
    
    Returns:
        True if deleted successfully
    """
    if not bucket:
        return False
    
    try:
        # Extract blob name from URL
        blob_name = file_url.split(f"{BUCKET_NAME}/")[-1]
        blob = bucket.blob(blob_name)
        blob.delete()
        
        logger.info(f"✅ File deleted: {blob_name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ GCS delete failed: {e}")
        return False