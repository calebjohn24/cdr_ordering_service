# -*- coding: UTF-8 -*-
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from google.cloud import storage
import uuid
import time
import datetime
import pytz
estNameStr = 'testraunt'
location = 'cedar-location-1'
tz = pytz.timezone("America/Los_Angeles")
#print(datetime.datetime.now(tz).weekday())
day = "TUE"
# Use a service account
cred = credentials.Certificate('/Users/caleb/Documents/GitHub/CedarFlask/CedarChatbot-b443efe11b73.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://cedarchatbot.firebaseio.com/',
    'storageBucket': 'cedarchatbot.appspot.com'
})
storage_client = storage.Client.from_service_account_json(
        'CedarChatbot-b443efe11b73.json')
bucket = storage_client.get_bucket("cedarchatbot.appspot.com")
upName = estNameStr + "/" + "manifestt.json"
blob = bucket.blob(upName)
blob.upload_from_filename("manifest.json")
