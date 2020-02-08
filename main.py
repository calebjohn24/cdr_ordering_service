import datetime
import json
import smtplib
import sys
import time
import uuid
import os
from fpdf import FPDF
import firebase_admin
from passlib.hash import pbkdf2_sha256
from firebase_admin import credentials
from firebase_admin import db
from flask import Blueprint, render_template, abort
from google.cloud import storage
import pytz
from flask import Flask, flash, request, session, jsonify
from flask_compress import Compress
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.utils import secure_filename
from flask import redirect, url_for
from flask import render_template, send_file
from flask_session import Session
from flask_sslify import SSLify
from square.client import Client
from werkzeug.datastructures import ImmutableOrderedMultiDict
from flask import Blueprint, render_template, abort
from Cedar.admin import admin_panel, menu, pw_reset, feedback, schedule, billing
from Cedar.admin.admin_panel import getSquare, sendEmail
from Cedar.admin.billing import updateTransactionFees
from Cedar.kiosk import online_menu, payments, qsr_menu, sd_menu, register
from Cedar.employee import qsr_employee, sd_employee
from Cedar.main_page import find_page
from Cedar.signup import signup_start, squareoauth
from Cedar.kioskApi import kioskApi
import atexit
from werkzeug.local import Local, LocalManager
from apscheduler.schedulers.background import BackgroundScheduler
import stripe


stripe.api_key = "sk_live_sRI03xt3QaCpWZahwnybqnPe007xtcIzKe"


infoFile = open("info.json")
info = json.load(infoFile)
mainLink = info['mainLink']

botNumber = info['number']
adminSessTime = 3599


cred = credentials.Certificate('CedarChatbot-b443efe11b73.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://cedarchatbot.firebaseio.com/',
    'storageBucket': 'cedarchatbot.appspot.com'
})


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
storage_client = storage.Client.from_service_account_json(
    'CedarChatbot-b443efe11b73.json')
bucket = storage_client.get_bucket('cedarchatbot.appspot.com')
sender = 'cedarrestaurantsbot@gmail.com'
emailPass = "cda33d07-f6bd-479e-806f-5d039ae2fa2d"
dayNames = ["MON", "TUE", "WED", "THURS", "FRI", "SAT", "SUN"]
global locationsPaths
locationsPaths = {}


def checkBilling():
    timeInterval = 2592000
    restDict = dict(db.reference('/billing/').get())
    restaurants = list(dict(db.reference('/billing/').get()).keys())
    for estNameStr in restaurants:
        print("billing checked " + estNameStr)
        billingRef = db.reference('/billing/' + estNameStr)
        billInfo = dict(billingRef.get())
        lastBillTime = dict(billingRef.get())['lastBillTime']
        if(time.time() - lastBillTime >= timeInterval):
            try:
                billingRef = db.reference('/billing/' + estNameStr)
                dictBill = {}
                base = billInfo['fees']['all']['base']
                dictBill.update({"base": base})
                startDate = billInfo['lastBill']
                endDate = billInfo['nextBill']
                dictBill.update({"startdate": startDate})
                dictBill.update({"date": endDate})
                tax = billInfo['info']['tax']
                dictBill.update({"tax": tax})
                dictBill.update({"paid": "no"})
                kioskDict = {'kiosks':
                 {"ids": {}}
                }
                billingRef = db.reference('/billing/' + estNameStr)
                billInfo = dict(billingRef.get())
                for kioskKey, kioskVal in dict(billInfo['fees']['all']['kiosk']).items():
                    print(kioskKey)
                    print(dict(kioskVal).keys())
                    kioskTmpDict = {kioskKey: {"count": kioskVal['count'],
                                            "software": kioskVal['base'],
                                            "group": kioskVal['group']}
                                            }
                    if(kioskVal['fees'] != 5):
                        kioskTmpDict[kioskKey].update({
                            "term": kioskVal['term'],
                            "remaining": kioskVal['remaining'],
                            'hardware': (kioskVal['fees'] - kioskVal['base'])

                        })
                        if(kioskVal['remaining'] > 1):
                            changeRef = db.reference(
                                '/billing/' + estNameStr + '/fees/all/kiosk/' + kioskKey)
                            changeRef.update({
                                "remaining": int(kioskVal['remaining']-1)
                            })
                        else:
                            changeRef = db.reference(
                                '/billing/' + estNameStr + '/fees/all/kiosk/' + kioskKey)
                            changeRef.update({
                                "remaining": 0,
                                'fees':5
                            })
                            changeRef = db.reference(
                                '/billing/' + estNameStr + '/fees/all/kiosk/' + kioskKey + '/installment')
                            changeRef.delete()


                    elif(kioskVal['fees'] != 5):
                        kioskTmpDict[kioskKey].update({
                            "hardware": 0
                        })
                    kioskDict['kiosks']['ids'].update(kioskTmpDict)
                print(kioskDict)
                dictBill.update(kioskDict)
                transactionCount = billInfo['fees']['all']['transactions']['count']
                transactionFees = billInfo['fees']['all']['transactions']['fees']
                dictBill.update({
                    'transaction': {
                        'amt': transactionFees,
                        'count': transactionCount
                    }
                })
                newBillRef = db.reference('/billing/' + estNameStr + '/bills')
                newBillRef.push(dictBill)

                changeRef = db.reference(
                    '/billing/' + estNameStr + '/fees/all/transactions')
                changeRef.update({
                    "count": 0,
                    "fees": 0
                })
                locations = db.reference(
                    '/billing/' + estNameStr + '/fees/locations').get()
                for l,v in locations.items():
                    changeRef =  db.reference(
                    '/billing/' + estNameStr + '/fees/locations/' + str(l) + '/fees/transactions')
                    changeRef.update({
                        'count':0,
                        'fees':0
                    })
                currDate = datetime.datetime.now()
                delta = datetime.timedelta(days=30)
                nextDate = currDate + delta
                currStr = str(currDate.month) + "-" + \
                    str(currDate.day) + "-" + str(currDate.year)
                nextStr = str(nextDate.month) + "-" + \
                    str(nextDate.day) + "-" + str(nextDate.year)
                billingRef.update({
                    "lastBillTime": float(time.time()),
                    "billDate": currDate.day,
                    "billMonth": currDate.month,
                    "billYear": currDate.year,
                    "lastBill": currStr,
                    "nextBill": nextStr
                })
                SUBJECT = 'Your Cedar Invoice Is Ready'
                write_str = "View your Cedar billing panel to view this month's invoice"
                message = 'Subject: {}\n\n{}'.format(SUBJECT, write_str)
                emails = list(dict(db.reference('/restaurants/' + estNameStr + '/admin-info').get()).keys())
                for e in emails:
                    sendEmail(sender, str(e).replace('-','.'), message)
                print('done ' + estNameStr)
            except Exception as e:
                print(e, ' error')


sched = BackgroundScheduler(daemon=True)
sched.add_job(checkBilling, 'interval', minutes=30)
sched.start()

app = Flask(__name__)

app.register_blueprint(admin_panel.admin_panel_blueprint)
app.register_blueprint(find_page.find_page_blueprint)
app.register_blueprint(menu.menu_panel_blueprint)
app.register_blueprint(pw_reset.pw_reset_blueprint)

app.register_blueprint(feedback.feedback_blueprint)
app.register_blueprint(schedule.schedule_blueprint)
app.register_blueprint(online_menu.online_menu_blueprint)
app.register_blueprint(sd_menu.sd_menu_blueprint)
app.register_blueprint(qsr_menu.qsr_menu_blueprint)
app.register_blueprint(payments.payments_blueprint)
app.register_blueprint(qsr_employee.qsr_employee_blueprint)
app.register_blueprint(sd_employee.sd_employee_blueprint)
app.register_blueprint(register.register_kiosk_blueprint)
app.register_blueprint(billing.billing_blueprint)
app.register_blueprint(signup_start.signup_start_blueprint)
app.register_blueprint(squareoauth.oauth_api_blueprint)
app.register_blueprint(kioskApi.kioskApi_blueprint)

scKey = str(uuid.uuid4())
app.secret_key = scKey
Compress(app)
csrf = CSRFProtect(app)
csrf.exempt(kioskApi.kioskApi_blueprint)


@app.before_request
def before_request():
    if request.url.startswith('http://'):
        url = request.url.replace('http://', 'https://', 1)
        code = 301
        return redirect(url, code=code)


@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('find_page.findRestaurant'))


@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    print(e)
    referrer = request.headers.get("Referer")
    return(redirect(referrer), 302)


if __name__ == '__main__':
    try:
        app.secret_key = scKey
        sslify = SSLify(app, permanent=True)
        app.config['SESSION_TYPE'] = 'filesystem'
        sess = Session()
        sess.init_app(app)
        csrf.exempt(kioskApi.kioskApi_blueprint)
        csrf.init_app(app)
        csrf.exempt(kioskApi.kioskApi_blueprint)
        sess.permanent = True
        '''
        app.config.update(
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
        )
        '''
        app.jinja_env.cache = {}
        app.run(host='0.0.0.0', port=5000, debug=True)
    except KeyboardInterrupt:
        sys.exit()
