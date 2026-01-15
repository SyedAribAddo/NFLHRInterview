from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
import os
from datetime import datetime, timedelta

CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER")
ACCOUNT_KEY = os.getenv("AZURE_BLOB_KEY")
ACCOUNT_NAME = "nflsalesinterviewdemo" # Extracted from connection string or env, better to parse or separate env

def get_blob_service_client():
    return BlobServiceClient.from_connection_string(CONNECTION_STRING)

def upload_video(file_content: bytes, session_id: str, question_id: int, extension: str = "webm") -> str:
    """Uploads video bytes to Azure Blob and returns the blob name."""
    blob_service_client = get_blob_service_client()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    blob_name = f"{session_id}/q{question_id}/{timestamp}.{extension}"
    
    blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)
    blob_client.upload_blob(file_content, overwrite=True)
    
    return blob_name

def generate_sas_url(blob_name: str, expiry_hours: int = 1) -> str:
    """Generates a temporary SAS URL for the blob."""
    sas_token = generate_blob_sas(
        account_name=ACCOUNT_NAME,
        container_name=CONTAINER_NAME,
        blob_name=blob_name,
        account_key=ACCOUNT_KEY,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
    )
    return f"https://{ACCOUNT_NAME}.blob.core.windows.net/{CONTAINER_NAME}/{blob_name}?{sas_token}"
