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
from Cedar import collect_menu
from Cedar.admin.admin_panel import checkLocation, sendEmail, getSquare, checkAdminToken


billing_blueprint = Blueprint('billing', __name__, template_folder='templates')

infoFile = open("info.json")
info = json.load(infoFile)
mainLink = info['mainLink']

sender = 'cedarrestaurantsbot@gmail.com'
emailPass = "cda33d07-f6bd-479e-806f-5d039ae2fa2d"

def updateTransactionFees(amt,estNameStr,location):
    feesRef = db.reference('/billing/' + estNameStr + '/fees/all/transactions')
    fees = dict(feesRef.get())
    newCount = fees['count'] + 1
    newFees = fees['fees'] + amt
    feesRef.update({"count":newCount, "fees":newFees})
    feesRef = db.reference('/billing/' + estNameStr + '/fees/locations/'+location+'/transactions')
    fees = dict(feesRef.get())
    newCount = fees['count'] + 1
    newFees = fees['fees'] + amt
    feesRef.update({"count":newCount, "fees":newFees})



@billing_blueprint.route('/<estNameStr>/<location>/billing-detail', methods=['POST','GET'])
def billDetails(estNameStr, location):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    tzGl = {}
    locationsPaths = {}
    getSquare(estNameStr, tzGl, locationsPaths)
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('admin_panel.login', estNameStr=estNameStr, location=location))
    if (checkAdminToken(estNameStr, idToken, username) == 1):
        return redirect(url_for('admin_panel.login', estNameStr=estNameStr, location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    try:
        billingRef = db.reference('/billing/' + estNameStr)
        billing = dict(billingRef.get())
        if(billing == None):
            billing = {}
            total = 0
        else:
            total = 0
            baseFee = billing['fees']['all']['base']
            print(baseFee)
            orderFees = billing['fees']['all']['transactions']['fees']
            print(orderFees)
            kioskKeys = list(dict(billing['fees']['all']['kiosk']).keys())
            print(kioskKeys)
            kioskFees = 0
            for keys in kioskKeys:
                kioskFees += float(billing['fees']['all']['kiosk'][keys]['fees'] * float(billing['fees']['all']['kiosk'][keys]['count']))
            total = baseFee + orderFees + kioskFees
    except Exception as e:
        total = 0
        billing = {}
    return(render_template("POS/AdminMini/billing.html", restName=estNameStr.capitalize() ,billing=billing, total=total))




@billing_blueprint.route('/<estNameStr>/<location>/change-split', methods=['POST'])
def splitChange(estNameStr, location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    splitPct = float(rsp['split'])
    billingRef = db.reference('/billing/' + estNameStr)
    billing = dict(billingRef.get())
    totalFee = billing['totalFee']
    custFee = round(float(totalFee*splitPct),2)
    splitPctRest = 1.0 - splitPct
    restFee = round(float(totalFee*splitPctRest),2)
    billingRef.update({'split':splitPct, 'custFee':custFee, 'restFee':restFee})
    return(redirect(url_for('billing.billDetails', estNameStr=estNameStr, location=location)))
