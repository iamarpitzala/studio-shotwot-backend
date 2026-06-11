from fastapi import APIRouter, Depends, HTTPException
from middleware.auth_middleware import verify_token
from services.firestore_service import db

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me")
async def get_me(userId: str = Depends(verify_token)):
    """
    Returns current user details and generation usage statistics.
    """
    user_ref = db.collection("users").document(userId)
    user_snap = user_ref.get()
    
    if not user_snap.exists:
        raise HTTPException(status_code=404, detail="User profile not registered")
        
    return user_snap.to_dict()
