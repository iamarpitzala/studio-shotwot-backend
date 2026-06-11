import utils.session
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environmental configs
load_dotenv()

# Initialize Firebase on app startup
from services.firebase_service import initialize_firebase
initialize_firebase()

from routers import auth, users, vault, generate

app = FastAPI(
    title="ShotWot Backend POC API",
    description="Backend services facilitating image prompt optimization and generation pipeline.",
    version="1.0.0"
)

# Enable CORS for React frontend integration
# In production, restrict to the actual frontend Firebase Hosting URL.
# Set FRONTEND_URL env var on the backend Cloud Run service after deploying the frontend.
allowed_origins = ["http://localhost:5173"]
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    allowed_origins.append(frontend_url)
# Always allow Firebase Hosting default domain
allowed_origins.append("https://studio-shotwot.web.app")
allowed_origins.append("https://studio-shotwot.firebaseapp.com")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(vault.router)
app.include_router(generate.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the ShotWot POC Backend API"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
