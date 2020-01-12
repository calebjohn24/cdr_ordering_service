import datetime
import json
import smtplib
import sys
import time
import uuid
import plivo
import os
import firebase_admin
from passlib.hash import pbkdf2_sha256
from firebase_admin import credentials
from firebase_admin import db
from flask import Blueprint, render_template, abort
from google.cloud import storage
import pytz
from flask import Flask, flash, request, session, jsonify
from werkzeug.utils import secure_filename
from flask import redirect, url_for
from flask import render_template
from flask_session import Session
from flask_sslify import SSLify
from square.client import Client
from werkzeug.datastructures import ImmutableOrderedMultiDict
from flask import Blueprint, render_template, abort
from Cedar.admin import admin_panel, menu, pw_reset, feedback, schedule
from Cedar.kiosk import online_menu, payments, qsr_menu, sd_menu
from Cedar.employee import qsr_employee, sd_employee
from Cedar.main_page import find_page


botNumber = '14255992978'
mainLink = 'https://c7de15e9.ngrok.io'
adminSessTime = 3599
client = plivo.RestClient(auth_id='MAYTVHN2E1ZDY4ZDA2YZ', auth_token='ODgzZDA1OTFiMjE2ZTRjY2U4ZTVhYzNiODNjNDll')
cred = credentials.Certificate('CedarChatbot-b443efe11b73.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://cedarchatbot.firebaseio.com/',
    'storageBucket': 'cedarchatbot.appspot.com'
})

ALLOWED_EXTENSIONS = { 'png', 'jpg', 'jpeg'}
storage_client = storage.Client.from_service_account_json('CedarChatbot-b443efe11b73.json')
bucket = storage_client.get_bucket('cedarchatbot.appspot.com')
sender = 'cedarrestaurantsbot@gmail.com'
emailPass = "cda33d07-f6bd-479e-806f-5d039ae2fa2d"
# smtpObj = smtplib.SMTP_SSL("smtp.gmail.com", 465)
# smtpObj.login(sender, emailPass)

dayNames = ["MON", "TUE", "WED", "THURS", "FRI", "SAT", "SUN"]
global locationsPaths
locationsPaths = {}

app = Flask(__name__)
app.register_blueprint(admin_panel.admin_panel_blueprint)
app.register_blueprint(find_page.find_page_blueprint)
app.register_blueprint(menu.menu_panel_blueprint)
app.register_blueprint(pw_reset.pw_reset_blueprint)
app.register_blueprint(feedback.feedback_blueprint)
app.register_blueprint(schedule.schedule_blueprint)
app.register_blueprint(online_menu.online_menu_blueprint)
app.register_blueprint(sd_menu.sd_menu_blueprint)
app.register_blueprint(qsr_menu.qsr_menu_blueprint)
app.register_blueprint(payments.payments_blueprint)
app.register_blueprint(qsr_employee.qsr_employee_blueprint)
app.register_blueprint(sd_employee.sd_employee_blueprint)
sslify = SSLify(app)
scKey = uuid.uuid4()
app.secret_key = scKey


locationsPaths = {}
tzGl = []


# Call the success method to see if the call succeeded
##########Restaurant END END###########


def checkLocation(estNameStr, location):
    try:
        ref = db.reference('/restaurants/'+estNameStr+'/'+location)
        test = dict(ref.get())
        if(test != None):
            return 0
        else:
            return 1
    except Exception as e:
        return 1



def sendCheckmate(estNameStr,location,token):
    print('order sent to checkmate')


####Send Data to Kiosk for Setup####
@app.route('/<estNameStr>/<locationX>/reader/<type>', methods=["POST"])
def GenReaderCode(estNameStr,locationX,type):
    rsp = request.get_json()
    print(rsp)
    code = rsp['code']
    kioskType = ["qsr-startKiosk","sitdown-startKiosk"]
    sqRef = db.reference(str('/restaurants/' + estNameStr))
    squareToken = dict(sqRef.get())["sq-token"]
    loginRef = db.reference('/restaurants/' + estNameStr + '/' + str(locationX) + "/employee")
    loginData = dict(loginRef.get())
    hashCheck = pbkdf2_sha256.verify(code, loginData['code'])
    if(hashCheck == True):
        client = Client(
            access_token=squareToken,
            environment='production',
        )
        api_locations = client.locations
        mobile_authorization_api = client.mobile_authorization
        # Call list_locatio
        result = api_locations.list_locations()
        if result.is_success():
        	# The body property is a list of locations
            locations = result.body['locations']
        	# Iterate over the list
            for location in locations:
                if((dict(location.items())["status"]) == "ACTIVE"):
                    # print(dict(location.items()))
                    locationName = (dict(location.items())["name"]).replace(" ","-")
                    # print(locationName)
                    locationId = dict(location.items())["id"]
                    if(str(locationName).lower() == locationX):
                        body = {}
                        body['location_id'] = locationId
                        result = mobile_authorization_api.create_mobile_authorization_code(body)
                        if result.is_success():
                            code = dict(result.body)['authorization_code']
                            print(code)
                            packet = {
                                "code":code,
                                "link": str(mainLink + locationX + "/" + kioskType[int(type)])
                            }
                            return jsonify(packet)
                        elif result.is_error():
                            packet = {
                                "code":"invlaid location"
                            }
                            return jsonify(packet)
    else:
        packet = {
            "code":"invlaid employee code"
        }
        return jsonify(packet)








if __name__ == '__main__':
    try:
        ##print(locationsPaths.keys())
        app.secret_key = scKey
        sslify = SSLify(app)
        app.config['SESSION_TYPE'] = 'filesystem'
        sess = Session()
        sess.init_app(app)
        app.permanent_session_lifetime = datetime.timedelta(minutes=240)
        app.debug = True
        app.run(host="0.0.0.0",port=5000)
    except KeyboardInterrupt:
        sys.exit()
