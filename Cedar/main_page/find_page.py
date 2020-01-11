import datetime
import json
import smtplib
import sys
import time
import uuid
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
from Cedar.admin.admin_panel import checkLocation


find_page_blueprint = Blueprint('find_page', __name__,template_folder='templates')

@find_page_blueprint.route('/find-restaurant')
def findRestaurant():
    restaurantsDict = dict(db.reference('/restaurants').get())
    restaurants = list(restaurantsDict.keys())
    return(render_template("Global/findrestaurant.html", restaurants=restaurants))


@find_page_blueprint.route('/restname~<restaurant>')
def findRestaurantLocation(restaurant):
    restaurantsDict = dict(db.reference('/restaurants/' + restaurant).get())
    del restaurantsDict['admin-info']
    del restaurantsDict['sq-token']
    locations = list(restaurantsDict.keys())
    return(render_template("Global/findrestaurantloc.html",restaurant=restaurant,locations=locations))

@find_page_blueprint.route('/pickscreen-<restaurant>~<location>')
def pickScreen(restaurant, location):
    return(render_template("Global/pickScreen.html",restaurant=restaurant,location=location))
