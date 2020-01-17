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
from Cedar.admin.admin_panel import checkLocation, sendEmail, getSquare


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
