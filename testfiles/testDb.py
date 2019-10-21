import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import uuid
import time

# Use a service account
cred = credentials.Certificate('/Users/caleb/Documents/GitHub/CedarFlask/CedarChatbot-b443efe11b73.json')
firebase_admin.initialize_app(cred)

db = firestore.client()
#write

key = uuid.uuid4()
doc_ref = db.collection('restaurants').document('testraunt').collection('info').document("admininfo").collection("admininfo").document("cajohn0205@gmail.com")

doc_ref.update({
    'time': time.time(),
    'token':str(key)

})


#read

#doc_ref = db.collection('restaurants').document('orders').collection('orders').document(str(key))

try:
    doc = doc_ref.get().to_dict()
    print(doc)
except Exception:
    print(u'No such document!')
