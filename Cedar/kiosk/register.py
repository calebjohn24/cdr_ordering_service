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
from google.cloud import storage
from firebase_admin import db
from flask import Blueprint,  render_template, abort
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
import Cedar

storage_client = storage.Client.from_service_account_json('CedarChatbot-b443efe11b73.json')
bucket = storage_client.get_bucket("cedarchatbot.appspot.com")
register_kiosk_blueprint = Blueprint('register', __name__,template_folder='templates')
global tzGl
adminSessTime = 3599
global locationsPaths
tzGl = {}
locationsPaths = {}
sender = 'cedarrestaurantsbot@gmail.com'
emailPass = "cda33d07-f6bd-479e-806f-5d039ae2fa2d"




@register_kiosk_blueprint.route('/<estNameStr>/<locationX>/reader/<type>', methods=["POST"])
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
                                "code":code ,
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
