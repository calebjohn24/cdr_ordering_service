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
cred = credentials.Certificate('/Users/caleb/Documents/GitHub/CedarFlask/CREDS')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://cedarchatbot.firebaseio.com/',
    'storageBucket': 'cedarchatbot.appspot.com'
})
storage_client = storage.Client.from_service_account_json('CREDS')
bucket = storage_client.get_bucket("cedarchatbot.appspot.com")
d = estNameStr + "/" + "coffee.jpg"
d = bucket.blob(d)
d.upload_from_filename(str('testfiles/coffee.jpg'),content_type='image/jpeg')
url = str(d.public_url)
url = url.replace("googleapis","cloud.google")
print(url)
