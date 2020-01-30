import datetime
import json
import smtplib
import sys
import time
import uuid
from fpdf import FPDF
import plivo
import os
import random
import firebase_admin
from passlib.hash import pbkdf2_sha256
from firebase_admin import credentials
from firebase_admin import db
from flask import Blueprint, render_template, abort, send_file
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
import stripe


stripe.api_key = "sk_test_Sr1g0u9XZ2txPiq8XENOQjCd00pjjrscNp"


infoFile = open("info.json")
info = dict(json.load(infoFile))
mainLink = info['mainLink']

botNumber = info['number']


signup_start_blueprint = Blueprint(
    'signup_start', __name__, template_folder='templates')


@signup_start_blueprint.route('/signup')
def signupstart():
    return(render_template('Signup/singupstart.html'))


@signup_start_blueprint.route('/signupstart', methods=['POST'])
def collectRestInfo():
    rsp = dict(request.form)
    email = rsp['email']
    email = email.replace('.', '-')
    password = rsp['password']
    restname = rsp['restname']
    phone = rsp['phone']
    restnameDb = restname.replace(' ', '-')
    restnameDb = restnameDb.replace("'", "")
    restnameDb = restnameDb.replace("&", '-')
    restnameDb = restnameDb.lower()
    restnameLegal = rsp['restname-legal']
    sq = rsp['sq']
    state = rsp['state']
    hash = pbkdf2_sha256.hash(password)
    checkRef = db.reference('/restaurants')
    billingRef = db.reference('/billing')
    try:
        if(dict(checkRef.get())[restnameDb] != None):
            restnameDb += '-' + str(random.randint(0, 1000))
    except Exception as e:
        pass
    checkRef.update({
        restnameDb: {
            "admin-info": {
                email: {
                    "password": hash,
                    "time": time.time(),
                    "token": str(uuid.uuid4())
                }
            },
            "sq-token": "token"
        }
    })
    billingRef.update({
        restnameDb: {
            "info": {
                "legalname": restnameLegal,
                "phone": phone,
                "state": rsp['state']
            },
            "trial": True,
            "dispname": str(rsp['restname'])
        }
    })
    session['restnameDb'] = restnameDb
    collect_menu.addEst(restnameDb, str(rsp['restname']))
    return(render_template('Signup/squarecheck.html'))


@signup_start_blueprint.route('/signupgenloc', methods=['GET'])
def genLoc():
    estNameStr = session.get('restnameDb', None)
    tzGl = {}
    locationsPaths = {}
    getSquare(estNameStr, tzGl, locationsPaths)
    print(locationsPaths)
    if(locationsPaths == {}):
        return(render_template('Signup/addlocs.html', estNameStr=estNameStr, locations=locationsPaths))
    else:
        return(render_template('Signup/signup3.html', estNameStr=estNameStr, locations=locationsPaths))


@signup_start_blueprint.route('/genloc2', methods=['POST'])
def genLoc2():
    estNameStr = session.get('restnameDb', None)
    restRef = db.reference('/restaurants/' + estNameStr)
    billingRef = db.reference('/billing/' + estNameStr)
    billingRef.update({"fees":
                       {
                           "all": {
                               "transactions": {
                                   "count": 0,
                                   "fees": 0
                               }
                           }
                       }
                       })
    rsp = dict(request.form)
    print(rsp)
    del rsp['csrf_token']
    testData = db.reference('/restaurants/testraunt/cedar-location-1').get()
    for locKey, locVal in rsp.items():
        restRef = db.reference('/restaurants/' + estNameStr)
        collect_menu.addLoc(estNameStr, locKey, locVal)
        billingRef = db.reference(
            '/billing/' + estNameStr + '/fees/locations/' + locKey)

        restRef.update({
            locKey:testData
        })
        restRef = db.reference('/restaurants/' + estNameStr + '/' + locKey)
        restRef.update({
            "dispname":locVal
        })

        billingRef.update({"fees":
                           {
                               "transactions": {
                                   "count": 0,
                                   "fees": 0
                               }

                           }
                           })

    tzGl = {}
    locationsPaths = {}
    getSquare(estNameStr, tzGl, locationsPaths)
    return ("done", 200)
