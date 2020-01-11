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
from Cedar.admin.admin_panel import getSquare, checkAdminToken, checkLocation, panel
import Cedar

feedback_blueprint = Blueprint('feedback', __name__,template_folder='templates')




@feedback_blueprint.route('/<estNameStr>/<location>/rem-new-comment~<comment>')
def remNewComment(estNameStr,location,comment):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login',estNameStr=estNameStr,location=location))
    finally:
        if (checkAdminToken(estNameStr, idToken, username) == 1):
            return redirect(url_for('.login',estNameStr=estNameStr,location=location))
        item_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/comments/new/'+str(comment))
        item_ref.delete()
        return(redirect(url_for("admin_panel.panel",estNameStr=estNameStr,location=location)))

@feedback_blueprint.route('/<estNameStr>/<location>/rem-saved-comment~<comment>')
def remSavedComment(estNameStr,location,comment):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login',estNameStr=estNameStr,location=location))
    finally:
        if (checkAdminToken(estNameStr, idToken, username) == 1):
            return redirect(url_for('.login',estNameStr=estNameStr,location=location))
        item_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/comments/saved/'+str(comment))
        item_ref.delete()
        return(redirect(url_for("admin_panel.panel",estNameStr=estNameStr,location=location)))

@feedback_blueprint.route('/<estNameStr>/<location>/save-comment~<comment>')
def saveComment(estNameStr,location,comment):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login',estNameStr=estNameStr,location=location))
    finally:
        if (checkAdminToken(estNameStr, idToken, username) == 1):
            return redirect(url_for('.login',estNameStr=estNameStr,location=location))
        commRef = db.reference('/restaurants/' + estNameStr + '/' +location+ '/comments/new/'+str(comment))
        commentData = dict(commRef.get())
        commRef.delete()
        savedRef = db.reference('/restaurants/' + estNameStr + '/' +location+ '/comments/saved')
        savedRef.update({
            comment:commentData
        })
        return(redirect(url_for("admin_panel.panel",estNameStr=estNameStr,location=location)))

@feedback_blueprint.route('/<estNameStr>/<location>/rem-feedback~<question>')
def remQuestion(estNameStr,location,question):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login',estNameStr=estNameStr,location=location))
    finally:
        if (checkAdminToken(estNameStr, idToken, username) == 1):
            return redirect(url_for('.login',estNameStr=estNameStr,location=location))
        item_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/feedback/'+str(question))
        item_ref.delete()
        return(redirect(url_for("panel",estNameStr=estNameStr,location=location)))

@feedback_blueprint.route('/<estNameStr>/<location>/add-feedback')
def addQuestion(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login',estNameStr=estNameStr,location=location))
    finally:
        if (checkAdminToken(estNameStr, idToken, username) == 1):
            return redirect(url_for('.login',estNameStr=estNameStr,location=location))
        return(render_template("POS/AdminMini/addFeedback.html",estNameStr=estNameStr,location=location))

@feedback_blueprint.route('/<estNameStr>/<location>/add-feedback-confirm', methods=['POST'])
def addQuestionConfirm(estNameStr,location):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login',estNameStr=estNameStr,location=location))
    finally:
        if (checkAdminToken(estNameStr, idToken, username) == 1):
            return redirect(url_for('.login',estNameStr=estNameStr,location=location))

        request.parameter_storage_class = ImmutableOrderedMultiDict
        rsp = dict((request.form))
        print(rsp)
        qName = rsp['q-name']
        qId = str(uuid.uuid4()).replace("-","")
        qDict = {qId:
            {'ans':{},
             'info':{
                 "name":qName,
                 "maxScore":int(rsp['max']),
                 "day":{
                     "currday":int(datetime.datetime.now().weekday()),
                     "count":0,
                     "currentScore":0.0,
                     "totalScore":0
                 },
                 "week":{
                     "currweek":int(datetime.datetime.now().isocalendar()[1]),
                     "count":0,
                     "currentScore":0.0,
                     "totalScore":0
                 },
                 "month":{
                     "currmonth":int(datetime.datetime.now().month),
                     "count":0,
                     "currentScore":0.0,
                     "totalScore":0
                 }
             }
             }}
        del rsp['q-name']
        del rsp['max']
        for k in range(0,int(len(rsp)/2)):
            nameKey = 'name-' + str(k+1)
            scoreKey = 'prce-' + str(k+1)
            print(rsp[nameKey])
            ansKey = str(uuid.uuid4()).replace("-","")
            ansDict = {ansKey:{
                "name":rsp[nameKey],
                "score":int(rsp[scoreKey])
            }}
            qDict[qId]['ans'].update(ansDict)

        qRef = db.reference('/restaurants/' + estNameStr + '/' +location+ '/feedback')
        qRef.update(qDict)
        return(redirect(url_for("panel",estNameStr=estNameStr,location=location)))
