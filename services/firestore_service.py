from firebase_admin import firestore
from .firebase_service import initialize_firebase

# Ensure Firebase is initialized before accessing Firestore
initialize_firebase()

db = firestore.client()
