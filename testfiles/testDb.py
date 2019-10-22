import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import uuid
import time

# Use a service account
cred = credentials.Certificate('/Users/caleb/Documents/GitHub/CedarFlask/CedarChatbot-b443efe11b73.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://cedarchatbot.firebaseio.com/'
})
ref = db.reference('/restaurants/testraunt/menu')
print(ref.get())
print(type(ref.get()))
