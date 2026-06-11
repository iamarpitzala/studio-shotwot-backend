from fastapi import APIRouter, Depends, HTTPException, Header
from google.cloud import firestore
from models.user import UserRegisterRequest
from services.firestore_service import db
from firebase_admin import auth as firebase_auth

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", status_code=201)
async def register_user(
    request: UserRegisterRequest,
    authorization: str = Header(...)
):
    """
    Decodes the Firebase JWT token from the headers, verifies it,
    and initializes a profile document for the user in Firestore.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token formatting")
    
    token = authorization.split("Bearer ")[1]
    
    try:
        decoded = firebase_auth.verify_id_token(token)
        uid = decoded["uid"]
        email = decoded.get("email")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")
    
    user_ref = db.collection("users").document(uid)
    user_snap = user_ref.get()
    
    if user_snap.exists:
        # User already exists, return current profile details
        return user_snap.to_dict()
        
    user_doc = {
        "email": email,
        "companyName": request.companyName,
        "industry": request.industry,
        "companySize": request.companySize,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "plan": "free",
        "generationsUsed": 0,
        "generationsLimit": 10
    }
    
    user_ref.set(user_doc)
    
    # Return document values with updated timestamps locally if needed
    user_doc["uid"] = uid
    return user_doc
