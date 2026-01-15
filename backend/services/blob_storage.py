import os
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER", "interviews")

def upload_video_to_blob(file_content: bytes, session_id: str) -> str:
    """Uploads video bytes to Azure Blob and returns the secure URL/Path."""
    try:
        blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        
        # Create container if not exists
        if not container_client.exists():
            container_client.create_container()
            
        blob_name = f"{session_id}/full_interview.webm"
        blob_client = container_client.get_blob_client(blob_name)
        
        # Increase timeout to 1 hour (3600s) and reduce concurrency for stability
        blob_client.upload_blob(
            file_content, 
            overwrite=True, 
            timeout=3600, 
            max_concurrency=1,
            connection_timeout=3600
        )
        
        return blob_client.url
    except Exception as e:
        print(f"Azure Upload Error: {e}")
        raise e

def generate_sas_url(blob_url: str) -> str:
    """Generates a read-only SAS URL for the blob."""
    if not blob_url: return None
    try:
        blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
        blob_name = blob_url.split(f"{CONTAINER_NAME}/")[-1]
        
        sas_token = generate_blob_sas(
            account_name=blob_service_client.account_name,
            container_name=CONTAINER_NAME,
            blob_name=blob_name,
            account_key=blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=1)
        )
        return f"{blob_url}?{sas_token}"
    except Exception as e:
        print(f"SAS Generation Error: {e}")
        return blob_url # Fallback

def upload_audio_to_blob(audio_bytes: bytes, filename: str) -> str:
    """
    Uploads audio bytes to Azure Blob and returns a public SAS URL.
    Used for D-ID avatar video generation.
    """
    try:
        blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        
        # Create container if not exists
        if not container_client.exists():
            container_client.create_container()
            
        blob_name = f"avatar_audio/{filename}"
        blob_client = container_client.get_blob_client(blob_name)
        
        blob_client.upload_blob(
            audio_bytes, 
            overwrite=True,
            content_type="audio/mpeg"
        )
        
        # Generate SAS URL for public access
        sas_url = generate_sas_url(blob_client.url)
        return sas_url
        
    except Exception as e:
        print(f"Audio Upload Error: {e}")
        return None

