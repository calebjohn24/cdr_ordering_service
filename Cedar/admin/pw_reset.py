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
from Cedar.admin.admin_panel import getSquare, checkAdminToken, checkLocation


mainLink = 'https://033d08d3.ngrok.io/'
pw_reset_blueprint = Blueprint('pw_reset', __name__,template_folder='templates')
global tzGl
adminSessTime = 3599
global locationsPaths
tzGl = {}
locationsPaths = {}
sender = 'cedarrestaurantsbot@gmail.com'
emailPass = "cda33d07-f6bd-479e-806f-5d039ae2fa2d"
smtpObj = smtplib.SMTP_SSL("smtp.gmail.com", 465)
smtpObj.login(sender, emailPass)


@pw_reset_blueprint.route('/<estNameStr>/<location>/reset-link~<token>~<user>', methods=["GET"])
def pwResetLink(estNameStr,location,token,user):
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        token_check = dict(ref.get())[user]['token']
        if(token == token_check):
            return render_template("POS/AdminMini/changepw.html", token=token, user=user)
        else:
            return(redirect(url_for("login",estNameStr=estNameStr,location=location)))
    except Exception as e:
        return(redirect(url_for("login",estNameStr=estNameStr,location=location)))


@pw_reset_blueprint.route('/<estNameStr>/<location>/pw-reset-confirm~<token>~<user>', methods=["POST"])
def pwResetCheck(estNameStr,location,token,user):
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        token_check = dict(ref.get())[user]['token']
        if(token == token_check):
            request.parameter_storage_class = ImmutableOrderedMultiDict
            rsp = dict((request.form))
            pw = rsp['password']
            hash = pbkdf2_sha256.hash(pw)
            LoginToken = str((uuid.uuid4())) + "-" + str((uuid.uuid4()))
            userRef = db.reference('/restaurants/' + estNameStr + '/admin-info/' + user)
            userRef.update({
                'token': LoginToken,
                'time': time.time(),
                'password':hash
            })
            return render_template("POS/AdminMini/alertpw.html")
        else:
            return(redirect(url_for("login",estNameStr=estNameStr,location=location)))
    except Exception as e:
        return(redirect(url_for("login",estNameStr=estNameStr,location=location)))


@pw_reset_blueprint.route('/<estNameStr>/<location>/forgot-password', methods=["GET"])
def pwReset(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    return render_template("POS/AdminMini/forgot-password.html", btn=str("admin"), restName=estNameStr)


@pw_reset_blueprint.route('/<estNameStr>/<location>/forgot-password', methods=["POST"])
def pwResetConfirm(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = dict((request.form))
    email = str(rsp['email']).replace(".","-")
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info/' + email)
    user = ref.get()
    if(user != None):
        write_str = mainLink + estNameStr+"/"+location+ "/reset-link~" + user['token'] + "~" + email
        SUBJECT = "Password Reset for " + str(estNameStr).capitalize() + " "+ location.capitalize()  + " Admin Account"
        message = 'Subject: {}\n\n{}'.format(SUBJECT, write_str)
        smtpObj.sendmail(sender, [str(rsp['email'])], message)
        alert = "Password Reset Email From cedarrestaurantsbot@gmail.com Sent"
        type="success"
    else:
        alert = "Invalid Email Please Go Back and Re-Enter Your Email or Create a New Account"
        type = "danger"
    return render_template("POS/AdminMini/pwsent.html", alert=alert, type=type)
