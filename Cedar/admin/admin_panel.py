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
from google.cloud import storage
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
import Cedar

infoFile = open("info.json")
info = json.load(infoFile)
mainLink = info['mainLink']

storage_client = storage.Client.from_service_account_json(
    'CedarChatbot-b443efe11b73.json')
bucket = storage_client.get_bucket("cedarchatbot.appspot.com")
admin_panel_blueprint = Blueprint(
    'admin_panel', __name__, template_folder='templates')
global tzGl
adminSessTime = 3599
global locationsPaths
tzGl = {}
locationsPaths = {}
sender = 'cedarrestaurantsbot@gmail.com'
emailPass = "cda33d07-f6bd-479e-806f-5d039ae2fa2d"


def sendEmail(sender, rec, msg):
    try:
        sender = 'cedarrestaurantsbot@gmail.com'
        emailPass = "cda33d07-f6bd-479e-806f-5d039ae2fa2d"
        smtpObj = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        smtpObj.login(sender, emailPass)
        smtpObj.sendmail(sender, [rec], msg)
        smtpObj.close()
    except Exception as e:
        try:
            sender = 'cedarrestaurantsbot@gmail.com'
            emailPass = "cda33d07-f6bd-479e-806f-5d039ae2fa2d"
            smtpObj = smtplib.SMTP_SSL("smtp.gmail.com", 465)
            smtpObj.login(sender, emailPass)
            smtpObj.sendmail(sender, [rec], msg)
            smtpObj.close()
        except Exception as e:
            pass


def getSquare(estNameStr, tzGl, locationsPaths):
    sqRef = db.reference(str('/restaurants/' + estNameStr))
    # print(sqRef.get())
    squareToken = dict(sqRef.get())["sq-token"]
    squareClient = Client(
        access_token=squareToken,
        environment='production',
    )
    api_locations = squareClient.locations
    mobile_authorization_api = squareClient.mobile_authorization
    result = api_locations.list_locations()
    if result.is_success():
        # The body property is a list of locations
        locations = result.body['locations']
        # Iterate over the list
        for location in locations:
            if ((dict(location.items())["status"]) == "ACTIVE"):
                # #print((dict(location.items())))
                addrNumber = ""
                street = ""
                for ltrAddr in range(len(dict(location.items())["address"]['address_line_1'])):
                    currentLtr = dict(location.items())[
                        "address"]['address_line_1'][ltrAddr]
                    try:
                        int(currentLtr)
                        addrNumber += currentLtr
                    except Exception as e:
                        street = dict(location.items())["address"]['address_line_1'][
                            ltrAddr + 1:len(dict(location.items())["address"]['address_line_1'])]
                        break

                addrP = str(addrNumber + "," + street + "," + dict(location.items())["address"]['locality'] + "," +
                            dict(location.items())["address"]['administrative_district_level_1'] + "," +
                            dict(location.items())["address"]['postal_code'][:5])
                timez = dict(location.items())["timezone"]
                tz = pytz.timezone(timez)
                locationName = (dict(location.items())[
                                "name"]).replace(" ", "-")
                tzGl.update({locationName: pytz.timezone(timez)})
                locationId = dict(location.items())["id"]
                numb = dict(location.items())['phone_number']
                numb = numb.replace("-", "")
                numb = numb.replace(" ", "")
                numb = numb.replace("+", "")
                locationsPaths.update(
                    {locationName: {
                        "id": locationId, "OCtimes": dict(location.items())["business_hours"]["periods"],
                        "sqEmail": dict(location.items())['business_email'],
                        "sqNumber": numb, "name": locationName}})


def findMenu(estNameStr, location):
    getSquare(estNameStr, tzGl, locationsPaths)
    day = dayNames[int(datetime.datetime.now(tzGl[location]).weekday())]
    curMin = float(datetime.datetime.now(tzGl[location]).minute) / 100.0
    curHr = float(datetime.datetime.now(tzGl[location]).hour)
    curTime = curHr + curMin
    pathTime = '/restaurants/' + estNameStr + '/' + location + "/schedule/" + day

    schedule = db.reference(pathTime).get()
    schedlist = list(schedule)
    start = 24
    sortedHr = [0]
    for scheds in schedlist:
        sortedHr.append(schedule[scheds])

    sortedHr.sort()
    sortedHr.append(24)
    for sh in range(len(sortedHr) - 1):
        if((sortedHr[sh] < curTime < sortedHr[sh + 1]) == True):
            menuKey = sh
            break

    for sh2 in range(len(schedlist)):
        if(sortedHr[menuKey] == schedule[schedlist[sh2]]):
            menu = (schedlist[sh2])
            return(str(menu))


def checkLocation(estNameStr, location):
    try:
        ref = db.reference('/restaurants/' + estNameStr + '/' + location)
        test = dict(ref.get())
        if(test != None):
            return 0
        else:
            return 1
    except Exception as e:
        return 1


def checkAdminToken(estNameStr, idToken, username):
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.get()[str(username)]
    if ((idToken == user_ref["token"]) and (time.time() - user_ref["time"] < adminSessTime)):
        return 0
    else:
        return 1


@admin_panel_blueprint.route('/<estNameStr>/<location>/')
@admin_panel_blueprint.route('/<estNameStr>/<location>/admin-login')
def login(estNameStr, location):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    logo = 'https://storage.googleapis.com/cedarchatbot.appspot.com/' + \
        estNameStr + '/logo.jpg'
    return render_template("POS/AdminMini/login.html", btn=str("admin"), restName=estNameStr, locName=location, logo=logo)


@admin_panel_blueprint.route('/<estNameStr>/<location>/admin', methods=["POST"])
def loginPageCheck(estNameStr, location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    email = str(rsp["emailAddr"])
    pw = str(rsp["pw"])
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    email = str(email).replace(".", "-")
    try:
        user = ref.get()[str(email)]
        if ((pbkdf2_sha256.verify(pw, user["password"])) == True):
            LoginToken = str((uuid.uuid4())) + "-" + str((uuid.uuid4()))
            # ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
            user_ref = ref.child(str(email))
            user_ref.update({
                'token': LoginToken,
                'time': time.time()
            })
            session['user'] = email
            session['token'] = LoginToken
            return redirect(url_for('admin_panel.panel', estNameStr=estNameStr, location=location))
        else:
            return render_template("POS/AdminMini/login2.html", btn=str("admin"), restName=estNameStr, locName=location)
    except Exception as e:
        print(e)
        logo = 'https://storage.googleapis.com/cedarchatbot.appspot.com/' + \
            estNameStr + '/logo.jpg'
        return render_template("POS/AdminMini/login2.html", btn=str("admin"), restName=estNameStr, locName=location, logo=logo)


@admin_panel_blueprint.route('/<estNameStr>/<location>/admin-panel', methods=["GET"])
def panel(estNameStr, location):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
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
        discRef = db.reference(
            '/restaurants/' + estNameStr + '/' + location + '/discounts')
        discDict = dict(discRef.get())
    except Exception as e:
        discDict = {}
    try:
        feedback_ref = db.reference(
            '/restaurants/' + estNameStr + '/' + location + '/feedback')
        feedback = dict(feedback_ref.get())
    except Exception as e:
        feedback = {}
    try:
        comment_ref = db.reference(
            '/restaurants/' + estNameStr + '/' + location + '/comments')
        comments = dict(comment_ref.get())
    except Exception as e:
        comments = {}
    kioskRef = db.reference('/billing/' + estNameStr + '/kiosks')
    kiosks = dict(kioskRef.get())


    logo = 'https://storage.googleapis.com/cedarchatbot.appspot.com/' + \
        estNameStr + '/logo.jpg'
    return render_template("POS/AdminMini/mainAdmin.html",
                           restName=str(estNameStr).capitalize(), feedback=feedback, comments=comments,
                           locName=location.capitalize(),
                           discounts=discDict, logo=logo, kiosks=kiosks)



@admin_panel_blueprint.route('/<estNameStr>/<location>/admin-panel-logloc', methods=["GET"])
def panellog(estNameStr, location):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
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
        logRefLoc = db.reference(
            '/billing/' + estNameStr + '/fees/locations/' + location + '/log')
        logsLoc = dict(logRefLoc.get())
        if(logsLoc == None):
            logsLoc = {}
    except Exception as e:
        print(e)
        logsLoc = {}
    return render_template("POS/AdminMini/logsloc.html",
                           restName=str(estNameStr).capitalize(),
                           locName=location.capitalize(), logsLoc=logsLoc)


@admin_panel_blueprint.route('/<estNameStr>/<location>/admin-panel-log', methods=["GET"])
def panellogloc(estNameStr, location):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
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
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    try:
        logRef = db.reference('/billing/' + estNameStr + '/fees/all/log')
        logs = dict(logRef.get())
        if(logs == None):
            logs = {}
    except Exception as e:
        logs = {}
    return render_template("POS/AdminMini/logsall.html",
                           restName=str(estNameStr).capitalize(),
                           locName=location.capitalize(), logs=logs)



@admin_panel_blueprint.route('/<estNameStr>/<location>/addAdmin', methods=["POST"])
def addAdmin(estNameStr, location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    email = session.get('user', None)
    pw = str(rsp["pw"])
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    email = str(email).replace(".", "-")
    users = list(dict(ref.get()))
    users.remove(email)
    try:
        user = ref.get()[str(email)]
        if ((pbkdf2_sha256.verify(pw, user["password"])) == True):
            return(render_template("POS/AdminMini/addAdmin.html", users=users))
        else:
            return redirect(url_for('admin_panel.panel', estNameStr=estNameStr, location=location))
    except Exception:
        return redirect(url_for('admin_panel.panel', estNameStr=estNameStr, location=location))


@admin_panel_blueprint.route('/<estNameStr>/<location>/confirmAdmin', methods=["POST"])
def confirmAdmin(estNameStr, location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    # email = session.get('user', None)
    email = str(rsp["email"])
    pw = str(rsp["password"])
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    email = str(email).replace(".", "-")
    hash = pbkdf2_sha256.hash(pw)
    ref.update({
        email: {
            "password": hash,
            "time": 0.0,
            "token": "uuid"
        }
    })
    return redirect(url_for('admin_panel.panel', estNameStr=estNameStr, location=location))


@admin_panel_blueprint.route('/<estNameStr>/<location>/editEmployee', methods=["POST"])
def editEmployee(estNameStr, location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    email = session.get('user', None)
    pw = str(rsp["pw"])
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    email = str(email).replace(".", "-")
    try:
        user = ref.get()[str(email)]
        if ((pbkdf2_sha256.verify(pw, user["password"])) == True):
            return(render_template("POS/AdminMini/editEmp.html"))
        else:
            return redirect(url_for('admin_panel.panel', estNameStr=estNameStr, location=location))
    except Exception:
        return redirect(url_for('admin_panel.panel', estNameStr=estNameStr, location=location))


@admin_panel_blueprint.route('/<estNameStr>/<location>/confirmEmpCode', methods=["POST"])
def confirmEmployeeCode(estNameStr, location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    email = session.get('user', None)
    code = rsp["code"]
    hash = pbkdf2_sha256.hash(code)
    ref = db.reference('/restaurants/' + estNameStr +
                       '/' + location + '/employee')
    ref.update({
        'code': hash
    })
    return redirect(url_for('admin_panel.panel', estNameStr=estNameStr, location=location))


@admin_panel_blueprint.route('/<estNameStr>/<location>/editLogo', methods=["POST"])
def editImgX(estNameStr, location):
    UPLOAD_FOLDER = estNameStr + "/imgs/"
    file = request.files['logo']
    filename = secure_filename(file.filename)
    file.save(os.path.join(UPLOAD_FOLDER, 'logo.jpg'))
    upName = "/" + estNameStr + "/imgs/" + 'logo.jpg'
    blob = bucket.blob(upName)
    d = estNameStr + "/logo.jpg"
    d = bucket.blob(d)
    d.upload_from_filename(
        str(str(UPLOAD_FOLDER) + "/" + str('logo.jpg')), content_type='image/jpeg')
    url = str(d.public_url)
    print(url)
    return redirect(url_for('admin_panel.panel', estNameStr=estNameStr, location=location))


@admin_panel_blueprint.route('/<estNameStr>/<location>/remUser~<user>')
def remUser(estNameStr, location, user):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('admin_panel.login', estNameStr=estNameStr, location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('admin_panel.login', estNameStr=estNameStr, location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    if(username != user):
        rem_ref = db.reference(
            '/restaurants/' + estNameStr + '/admin-info/' + user)
        rem_ref.delete()
    return redirect(url_for('admin_panel.panel', estNameStr=estNameStr, location=location))
