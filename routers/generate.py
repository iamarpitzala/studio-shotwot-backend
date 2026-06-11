import os
import uuid
import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from google.cloud import firestore
from middleware.auth_middleware import verify_token
from services.firestore_service import db
from services.gcs_service import download_from_bucket, upload_to_bucket, generate_signed_url
from services.vertex_service import optimize_prompt_with_gemini, generate_image_with_gemini_2_5
from models.generation import GenerationRequest, GenerationResponse

router = APIRouter(prefix="/generate", tags=["generate"])

async def run_generation_pipeline(
    generation_id: str,
    user_id: str,
    brief: str,
    asset_gcs_path: str,
    aspect_ratio: str
):
    """
    Background worker pipeline executing optimization and generation.
    """
    try:
        # Update status to processing
        db.collection("generations").document(generation_id).update({
            "status": "processing"
        })
        
        # Download reference image from Vault bucket
        vault_bucket = os.getenv("GCS_VAULT_BUCKET")
        image_bytes = download_from_bucket(vault_bucket, asset_gcs_path)
        
        # Optimize the prompt with Gemini 1.5 Pro
        optimized_prompt = optimize_prompt_with_gemini(brief)
        
        # Update record with optimized prompt
        db.collection("generations").document(generation_id).update({
            "optimizedPrompt": optimized_prompt
        })
        
        # Generate target image with Gemini 2.5 Flash Image Model
        output_bytes = generate_image_with_gemini_2_5(optimized_prompt, image_bytes, aspect_ratio)
        
        # Upload output image to GCS Output Bucket
        output_bucket = os.getenv("GCS_OUTPUT_BUCKET")
        output_gcs_path = f"{user_id}/{generation_id}.png"
        upload_to_bucket(output_bucket, output_gcs_path, output_bytes, "image/png")
        
        # Generate signed URL
        signed_url = generate_signed_url(output_bucket, output_gcs_path, expiration_hours=24)
        
        # Mark generation complete
        db.collection("generations").document(generation_id).update({
            "status": "complete",
            "outputGcsPath": output_gcs_path,
            "outputSignedUrl": signed_url,
            "signedUrlExpiry": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
            "completedAt": firestore.SERVER_TIMESTAMP
        })
        
    except Exception as e:
        # Error handling - mark record as failed
        db.collection("generations").document(generation_id).update({
            "status": "failed",
            "errorMessage": str(e),
            "completedAt": firestore.SERVER_TIMESTAMP
        })
        
        # Refund credit to user
        db.collection("users").document(user_id).update({
            "generationsUsed": firestore.Increment(-1)
        })
        print(f"Generation pipeline failure [{generation_id}]: {str(e)}")


@router.post("", response_model=GenerationResponse)
async def create_generation(
    request: GenerationRequest,
    userId: str = Depends(verify_token),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Submits a generation request. Assesses quota validation, deducts credits,
    registers the job document, and kicks off background tasks.
    """
    user_ref = db.collection("users").document(userId)
    user_snap = user_ref.get()
    
    if not user_snap.exists:
        raise HTTPException(status_code=404, detail="User profile not registered")
        
    user_data = user_snap.to_dict()
    if user_data["generationsUsed"] >= user_data["generationsLimit"]:
        raise HTTPException(status_code=429, detail="Generation limit reached. Upgrade to continue.")
        
    # Validate reference asset ownership
    asset_snap = db.collection("vault_assets").document(request.referenceAssetId).get()
    if not asset_snap.exists:
        raise HTTPException(status_code=404, detail="Reference asset not found")
        
    asset_data = asset_snap.to_dict()
    if asset_data["userId"] != userId:
        raise HTTPException(status_code=403, detail="Reference asset does not belong to this user")
        
    generation_id = str(uuid.uuid4())
    generation_doc = {
        "userId": userId,
        "status": "pending",
        "brief": request.brief,
        "referenceAssetId": request.referenceAssetId,
        "aspectRatio": request.aspectRatio,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "retryCount": 0
    }
    
    db.collection("generations").document(generation_id).set(generation_doc)
    
    # Increment usage counter immediately
    user_ref.update({
        "generationsUsed": firestore.Increment(1)
    })
    
    # Kickoff pipeline
    background_tasks.add_task(
        run_generation_pipeline,
        generation_id=generation_id,
        user_id=userId,
        brief=request.brief,
        asset_gcs_path=asset_data["gcsPath"],
        aspect_ratio=request.aspectRatio
    )
    
    return {
        "generationId": generation_id,
        "status": "pending",
        "brief": request.brief,
        "createdAt": datetime.datetime.utcnow()
    }


@router.get("/history")
async def get_generation_history(userId: str = Depends(verify_token)):
    """
    Returns all generation histories associated with this user.
    """
    output_bucket = os.getenv("GCS_OUTPUT_BUCKET")
    if not output_bucket:
         raise HTTPException(status_code=500, detail="GCS_OUTPUT_BUCKET not set")
         
    generations_ref = db.collection("generations")\
        .where("userId", "==", userId)\
        .order_by("createdAt", direction=firestore.Query.DESCENDING)\
        .limit(20)
        
    docs = generations_ref.stream()
    results = []
    
    for doc in docs:
        data = doc.to_dict()
        entry = {
            "generationId": doc.id,
            "status": data["status"],
            "brief": data["brief"],
            "aspectRatio": data.get("aspectRatio"),
            "createdAt": data["createdAt"]
        }
        
        if data["status"] == "complete" and data.get("outputGcsPath"):
            # Fresh URL valid for 1 hour
            entry["outputUrl"] = generate_signed_url(output_bucket, data["outputGcsPath"], expiration_hours=1)
        results.append(entry)
        
    return results


@router.get("/{generation_id}", response_model=GenerationResponse)
async def get_generation_status(generation_id: str, userId: str = Depends(verify_token)):
    """
    Fetches status for a single generation. Regenerates signed URL if expired.
    """
    doc_snap = db.collection("generations").document(generation_id).get()
    if not doc_snap.exists:
        raise HTTPException(status_code=404, detail="Generation not found")
        
    data = doc_snap.to_dict()
    if data["userId"] != userId:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    response = {
        "generationId": generation_id,
        "status": data["status"],
        "brief": data["brief"],
        "createdAt": data["createdAt"]
    }
    
    if data["status"] == "complete":
        # Check signed URL expiry
        expiry = data.get("signedUrlExpiry")
        now = datetime.datetime.utcnow()
        output_bucket = os.getenv("GCS_OUTPUT_BUCKET")
        
        # Firestore returns datetime objects timezone aware or naive depending on serialization
        # Remove TZ info from comparison if needed
        if expiry:
            if expiry.tzinfo is not None:
                expiry = expiry.replace(tzinfo=None)
                
            if expiry < now:
                # Regenerate and update
                fresh_url = generate_signed_url(output_bucket, data["outputGcsPath"], expiration_hours=24)
                db.collection("generations").document(generation_id).update({
                    "outputSignedUrl": fresh_url,
                    "signedUrlExpiry": now + datetime.timedelta(hours=24)
                })
                response["outputUrl"] = fresh_url
            else:
                response["outputUrl"] = data["outputSignedUrl"]
        else:
             response["outputUrl"] = data.get("outputSignedUrl")
             
        response["optimizedPrompt"] = data.get("optimizedPrompt")
        
    elif data["status"] == "failed":
        response["error"] = data.get("errorMessage", "Generation pipeline failure")
        
    return response
