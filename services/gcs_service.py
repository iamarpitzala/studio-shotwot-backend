import os
import datetime
from google.cloud import storage

def get_storage_client():
    return storage.Client()

def upload_to_bucket(bucket_name: str, path: str, data: bytes, content_type: str) -> str:
    client = get_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(path)
    blob.upload_from_string(data, content_type=content_type)
    return path

def download_from_bucket(bucket_name: str, path: str) -> bytes:
    client = get_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(path)
    return blob.download_as_bytes()

def generate_signed_url(bucket_name: str, path: str, expiration_hours: int = 1) -> str:
    client = get_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(path)

    # On Cloud Run, the default SA cannot self-sign blobs using the standard
    # credentials object. Use IAM signBlob via the service account email instead.
    sa_email = os.getenv("SERVICE_ACCOUNT_EMAIL")
    if sa_email:
        from google.auth import impersonated_credentials, transport
        import google.auth

        source_creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        signing_creds = impersonated_credentials.Credentials(
            source_credentials=source_creds,
            target_principal=sa_email,
            target_scopes=["https://www.googleapis.com/auth/devstorage.read_only"],
            lifetime=300,
        )
        url = blob.generate_signed_url(
            expiration=datetime.timedelta(hours=expiration_hours),
            method="GET",
            credentials=signing_creds,
            version="v4",
        )
    else:
        # Local dev: relies on GOOGLE_APPLICATION_CREDENTIALS service account key
        url = blob.generate_signed_url(
            expiration=datetime.timedelta(hours=expiration_hours),
            method="GET",
            version="v4",
        )
    return url
