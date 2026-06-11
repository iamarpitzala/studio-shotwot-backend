from fastapi import Header, HTTPException, Depends
from firebase_admin import auth as firebase_auth
from services.firestore_service import db  # Ensures Firebase is initialized

async def verify_token(authorization: str = Header(...)) -> str:
    """
    FastAPI dependency that extracts the ID token from the Authorization header,
    verifies it via Firebase Admin SDK, and returns the unique Firebase UID (userId).
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format. Must be 'Bearer {token}'")
    
    token = authorization.split("Bearer ")[1]
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token["uid"]
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {str(e)}")
