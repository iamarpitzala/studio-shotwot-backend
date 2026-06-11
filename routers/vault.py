import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from google.cloud import firestore
from middleware.auth_middleware import verify_token
from services.firestore_service import db
from services.gcs_service import upload_to_bucket, generate_signed_url, get_storage_client
from models.vault import VaultAssetResponse

router = APIRouter(prefix="/vault", tags=["vault"])

@router.post("/upload", response_model=VaultAssetResponse)
async def upload_asset(
    file: UploadFile = File(...),
    category: str = Form(...),
    userId: str = Depends(verify_token)
):
    """
    Validates the asset size and format, uploads it to GCS, and saves metadata in Firestore.
    """
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, and WebP formats are supported")
    
    max_size = 20 * 1024 * 1024  # 20MB limit
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(status_code=400, detail="File exceeds 20MB limit")
        
    bucket_name = os.getenv("GCS_VAULT_BUCKET")
    if not bucket_name:
         raise HTTPException(status_code=500, detail="GCS_VAULT_BUCKET environment variable is not set")
         
    file_extension = file.filename.split(".")[-1].lower() if "." in file.filename else "jpg"
    asset_id = str(uuid.uuid4())
    gcs_path = f"{userId}/references/{asset_id}.{file_extension}"
    
    # Upload directly from bytes
    upload_to_bucket(bucket_name, gcs_path, contents, file.content_type)
    
    asset_doc = {
        "userId": userId,
        "category": category,
        "filename": file.filename,
        "gcsPath": gcs_path,
        "uploadedAt": firestore.SERVER_TIMESTAMP,
        "sizeBytes": len(contents),
        "tags": []
    }
    
    db.collection("vault_assets").document(asset_id).set(asset_doc)
    
    # Return fresh metadata
    return {
        "assetId": asset_id,
        "category": category,
        "filename": file.filename,
        "uploadedAt": firestore.SERVER_TIMESTAMP  # Firestore updates this, Pydantic will serialize
    }

@router.get("/assets", response_model=List[VaultAssetResponse])
async def list_assets(userId: str = Depends(verify_token)):
    """
    Lists user's vault assets, generating short-lived signed URLs on-the-fly.
    """
    bucket_name = os.getenv("GCS_VAULT_BUCKET")
    if not bucket_name:
         raise HTTPException(status_code=500, detail="GCS_VAULT_BUCKET environment variable is not set")
         
    assets_ref = db.collection("vault_assets").where("userId", "==", userId)
    docs = assets_ref.stream()
    
    result = []
    for doc in docs:
        data = doc.to_dict()
        signed_url = generate_signed_url(bucket_name, data["gcsPath"], expiration_hours=1)
        
        result.append({
            "assetId": doc.id,
            "category": data["category"],
            "filename": data["filename"],
            "signedUrl": signed_url,
            "uploadedAt": data["uploadedAt"]
        })
        
    return result

@router.delete("/assets/{asset_id}")
async def delete_asset(asset_id: str, userId: str = Depends(verify_token)):
    """
    Deletes vault asset metadata and removes the object from Google Cloud Storage.
    """
    asset_ref = db.collection("vault_assets").document(asset_id)
    asset_snap = asset_ref.get()
    
    if not asset_snap.exists:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    data = asset_snap.to_dict()
    if data["userId"] != userId:
        raise HTTPException(status_code=403, detail="Not authorized to delete this asset")
        
    # Delete from GCS
    bucket_name = os.getenv("GCS_VAULT_BUCKET")
    try:
        storage_client = get_storage_client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(data["gcsPath"])
        blob.delete()
    except Exception as e:
        # Log error or continue to delete record if bucket is empty/already deleted
        pass
        
    asset_ref.delete()
    return {"message": "Asset deleted successfully", "assetId": asset_id}
