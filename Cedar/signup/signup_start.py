import datetime
import json
import smtplib
import sys
import time
import uuid
from fpdf import FPDF
import plivo
import os
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
info = json.load(infoFile)
mainLink = info['mainLink']

botNumber = info['number']



signup_start_blueprint = Blueprint('signup_start', __name__, template_folder='templates')




@signup_start_blueprint.route('/signup')
def signupstart():
    return(render_template('Signup/singupstart.html'))



@signup_start_blueprint.route('/signupstart', methods=['POST'])
def collectRestInfo():
    rsp = dict(request.form)
    return(rsp,200)
