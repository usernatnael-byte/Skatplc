import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

def init_firebase():
    """Firebaseን ከ Environment Variable ወይም ከሎካል ፋይል የማስጀመር ሃላፊነት ያለው ክፍል"""
    if not firebase_admin._apps:
        firebase_credentials_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
        
        if firebase_credentials_json:
            # ሬንደር ላይ (Environment Variable) ሲገባ
            cred_dict = json.loads(firebase_credentials_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        else:
            # በሎካል ኮምፒዩተርዎ (Localhost) ለመፈተን ከፈለጉ
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)

# ፋየርቤዝን ማስጀመር
init_firebase()

# የ Firestore ክላየንት (Client) ዕቃ - መረጃዎችን ለመጻፍ እና ለማንበብ ይጠቅማል
db = firestore.client()
