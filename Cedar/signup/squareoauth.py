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
from flask import Flask, flash, session, jsonify
from werkzeug.utils import secure_filename
from flask import redirect, url_for, request
from flask import render_template
from flask_session import Session
from flask_sslify import SSLify
from square.client import Client
from werkzeug.datastructures import ImmutableOrderedMultiDict
from flask import Blueprint, render_template, abort
from bottle import get, static_file, run, response
import squareconnect
from squareconnect.apis.o_auth_api import OAuthApi
from squareconnect.models.obtain_token_request import ObtainTokenRequest


application_id = 'sq0idp-taGpJk5rPAp_ragT6WZW4w'
application_secret = 'sq0csp-oW3f74ovaUjZfC6Y_wVNrNQFg6sZVS7D12LfvWTl8Iw'

oauth_api = OAuthApi()

oauth_api_blueprint = Blueprint(
    'squareoauth', __name__, template_folder='templates')


@oauth_api_blueprint.route('/sqacct-check-rd')
def redirectSq():
    return(redirect('https://connect.squareup.com/oauth2/authorize?client_id='+application_id+'&scope=ORDERS_WRITE%20PAYMENTS_WRITE%20PAYMENTS_WRITE_IN_PERSON%20MERCHANT_PROFILE_READ'))


@oauth_api_blueprint.route('/callback', methods=['GET'])
def callback():
    authorization_code = request.args.get('code', None)
    if authorization_code:

        oauth_request_body = ObtainTokenRequest()
        oauth_request_body.client_id = application_id
        oauth_request_body.client_secret = application_secret
        oauth_request_body.code = authorization_code
        oauth_request_body.grant_type = 'authorization_code'
        response = oauth_api.obtain_token(oauth_request_body)

        if response.access_token:

            token = response.access_token
            return(render_template('Signup/dispsqcode.html', token=token))

        else:
            return(render_template('Signup/squarecheck.html'))

    else:
        return(render_template('Signup/squarecheck.html'))


@oauth_api_blueprint.route('/add-sqToken/<restnameDb>', methods=['POST'])
def addToken(restnameDb):
    rsp = dict(request.form)
    token = str(rsp['token']).replace(' ', '')
    ref = db.reference('/restaurants/' + restnameDb)
    ref.update({"sq-token": token})
    session['restnameDb'] = restnameDb
    return (redirect(url_for('signup_start.genLoc')))
