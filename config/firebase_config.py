import os
import firebase_admin
import pyrebase
from firebase_admin import credentials, firestore, auth, storage
from dotenv import load_dotenv

load_dotenv()

# Firebase Admin SDK variables
FIREBASE_CREDENTIALS_PATH = os.getenv('FIREBASE_CREDENTIALS_PATH')
FIREBASE_STORAGE_BUCKET = os.getenv('FIREBASE_STORAGE_BUCKET')

# Pyrebase variables
FIREBASE_API_KEY = os.getenv('FIREBASE_API_KEY')
FIREBASE_AUTH_DOMAIN = os.getenv('FIREBASE_AUTH_DOMAIN')
FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID')
FIREBASE_MESSAGING_SENDER_ID = os.getenv('FIREBASE_MESSAGING_SENDER_ID')
FIREBASE_APP_ID = os.getenv('FIREBASE_APP_ID')

# Initialize Firebase Admin SDK
def init_firebase_admin():
    try:
        default_app = firebase_admin.get_app()
        db = firestore.client()
        bucket = storage.bucket(app=default_app, name=FIREBASE_STORAGE_BUCKET)
    except ValueError:
        # The app doesn't exist yet, so initialize it
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        bucket = storage.bucket(app=firebase_admin.get_app(), name=FIREBASE_STORAGE_BUCKET)
    
    return db, bucket

# Initialize Pyrebase
def init_pyrebase():
    firebase_config = {
        "apiKey": FIREBASE_API_KEY,
        "authDomain": FIREBASE_AUTH_DOMAIN,
        "projectId": FIREBASE_PROJECT_ID,
        "storageBucket": FIREBASE_STORAGE_BUCKET,
        "messagingSenderId": FIREBASE_MESSAGING_SENDER_ID,
        "appId": FIREBASE_APP_ID,
        "databaseURL": ""
    }
    
    firebase = pyrebase.initialize_app(firebase_config)
    auth_instance = firebase.auth()
    
    return auth_instance