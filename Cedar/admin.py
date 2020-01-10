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


admin_blueprint = Blueprint('admin', __name__,template_folder='templates')



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



def checkAdminToken(idToken, username):
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.get()[str(username)]
    if ((idToken == user_ref["token"]) and (time.time() - user_ref["time"] < adminSessTime)):
        return 0
    else:
        return 1




    
@admin_blueprint.route('/<estNameStr>/<location>/admin-login')
def login(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    return render_template("POS/AdminMini/login.html", btn=str("admin"), restName=estNameStr,locName=location)
