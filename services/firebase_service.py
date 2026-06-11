import os
import firebase_admin
from firebase_admin import credentials

def initialize_firebase():
    """
    Initializes Firebase Admin SDK using Application Default Credentials (ADC)
    or standard service account key credentials.
    """
    if not firebase_admin._apps:
        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        else:
            # Under ADC (gcloud auth application-default login), 
            # firebase-admin automatically resolves credentials
            firebase_admin.initialize_app()
