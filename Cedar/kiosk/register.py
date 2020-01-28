import datetime
import json
import smtplib
import sys
import time
import uuid
import plivo
from flask_wtf.csrf import CSRFProtect, CSRFError
import os
import firebase_admin
from passlib.hash import pbkdf2_sha256
from flask_wtf import csrf
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
from Cedar.collect_menu import findMenu, getDispNameEst, getDispNameLoc
from werkzeug.datastructures import ImmutableOrderedMultiDict
from flask import Blueprint, render_template, abort
import Cedar




infoFile = open("info.json")
info = json.load(infoFile)
mainLink = info['mainLink']
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


@register_kiosk_blueprint.route('/<estNameStr>/<location>/deactivate-kiosk-<kioskCode>')
def deactivateKiosk(estNameStr, location, kioskCode):
    kioskRef = db.reference('/billing/' + estNameStr + '/kiosks')
    kioskRef.update({str(kioskCode):
        {"active":0,
         "loc":location}})
    return redirect(url_for('admin_panel.panel',estNameStr=estNameStr,location=location))
