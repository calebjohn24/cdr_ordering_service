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
from Cedar.collect_menu import findMenu
from Cedar.admin.admin_panel import checkLocation, sendEmail, getSquare


online_menu_blueprint = Blueprint('online_menu', __name__,template_folder='templates')

infoFile = open("info.json")
info = json.load(infoFile)
mainLink = info['mainLink']

@online_menu_blueprint.route('/<estNameStr>/<location>/order', methods=["GET"])
def startKiosk5(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    logo = 'https://storage.googleapis.com/cedarchatbot.appspot.com/'+estNameStr+'/logo.jpg'
    return(render_template("Customer/QSR/startKiosk.html",btn="startOnline",restName=estNameStr,locName=location,logo=logo))


@online_menu_blueprint.route('/<estNameStr>/<location>/startOnline', methods=["POST"])
def startOnline(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    phone = rsp["number"]
    name = rsp["name"]
    togo = rsp["togo"]
    table = "Online Order"
    session['table'] = ""
    session['name'] = name
    session['phone'] = phone
    path = '/restaurants/' + estNameStr + '/' + location + "/orders/"
    orderToken = str(uuid.uuid4())
    ref = db.reference(path)
    newOrd = ref.push({
        "togo":togo,
        "QSR":0,
        "cpn":1,
        "kiosk":1,
        "name":name,
        "phone":phone,
        "table":table,
        "alert":"null",
        "alertTime":0,
        "timestamp":time.time(),
        "subtotal":0.0
        })
    #print(newOrd.key)
    session['orderToken'] = newOrd.key
    menu = findMenu(estNameStr,location)
    print(menu)
    session["menu"] = menu
    ##print(menu)
    return(redirect(url_for('qsr_menu.qsrMenu',estNameStr=estNameStr,location=location)))
