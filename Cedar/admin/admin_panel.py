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
import Cedar


admin_panel_blueprint = Blueprint('admin_panel', __name__,template_folder='templates')
global tzGl
adminSessTime = 3599
global locationsPaths
tzGl = {}
locationsPaths = {}
sender = 'cedarrestaurantsbot@gmail.com'
emailPass = "cda33d07-f6bd-479e-806f-5d039ae2fa2d"

def sendEmail(sender, rec, msg):
    try:
        smtpObj.sendmail(sender, [rec], msg)
    except Exception as e:
        sender = 'cedarrestaurantsbot@gmail.com'
        emailPass = "cda33d07-f6bd-479e-806f-5d039ae2fa2d"
        smtpObj = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        smtpObj.login(sender, emailPass)
        sendEmail(sender, rec, msg)


def getSquare(estNameStr):
    sqRef = db.reference(str('/restaurants/' + estNameStr))
    ##print(sqRef.get())
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
                    currentLtr = dict(location.items())["address"]['address_line_1'][ltrAddr]
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
                locationName = (dict(location.items())["name"]).replace(" ", "-")
                tzGl.update({locationName:pytz.timezone(timez)})
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



def checkLocation(estNameStr, location):
    try:
        ref = db.reference('/restaurants/'+estNameStr+'/'+location)
        test = dict(ref.get())
        if(test != None):
            return 0
        else:
            return 1
    except Exception as e:
        return 1



def checkAdminToken(estNameStr,idToken, username):
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.get()[str(username)]
    if ((idToken == user_ref["token"]) and (time.time() - user_ref["time"] < adminSessTime)):
        return 0
    else:
        return 1




@admin_panel_blueprint.route('/<estNameStr>/<location>/admin-login')
def login(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    return render_template("POS/AdminMini/login.html", btn=str("admin"), restName=estNameStr,locName=location)


@admin_panel_blueprint.route('/<estNameStr>/<location>/admin', methods=["POST"])
def loginPageCheck(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    email = str(rsp["emailAddr"])
    pw = str(rsp["pw"])
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    email = str(email).replace(".","-")
    print(pw,email)
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
            return redirect(url_for('admin_panel.panel',estNameStr=estNameStr,location=location))
        else:
            return render_template("POS/AdminMini/login2.html", btn=str("admin"), restName=estNameStr, locName=location)
    except Exception as e:
        print(e)
        return render_template("POS/AdminMini/login2.html", btn=str("admin"), restName=estNameStr, locName=location)



@admin_panel_blueprint.route('/<estNameStr>/<location>/admin-panel', methods=["GET"])
def panel(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    getSquare(estNameStr)
    print(tzGl)
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login',estNameStr=estNameStr,location=location))
    if (checkAdminToken(estNameStr, idToken, username) == 1):
        return redirect(url_for('.login',estNameStr=estNameStr,location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    discRef = db.reference('/restaurants/' + estNameStr + '/'+ location + '/discounts')
    discDict = dict(discRef.get())
    discMenus = list(discDict.keys())
    discItms = []
    discTypes = []
    discAmts = []
    discLimMin = []
    discNames = []
    discMenu = []
    for menus in discMenus:
        cpns = list(dict(discDict[menus]).keys())
        for disc in cpns:
            discMenu.append(menus)
            discNames.append(disc)
            discItms.append(str(discDict[menus][disc]["mods"][1]) + " " + str(discDict[menus][disc]["itm"]))
            discTypes.append(discDict[menus][disc]["type"])
            discAmts.append(str(discDict[menus][disc]["amt"]))
            limStr = str("lim:") + str(discDict[menus][disc]["lim"]) + str(" min:") + str(discDict[menus][disc]["min"])
            discLimMin.append(limStr)
    feedback_ref = db.reference('/restaurants/' + estNameStr + '/'+ location + '/feedback')
    feedback = dict(feedback_ref.get())
    comment_ref = db.reference('/restaurants/' + estNameStr + '/'+ location + '/comments')
    comments = dict(comment_ref.get())
    return render_template("POS/AdminMini/mainAdmin.html",
                           restName=str(estNameStr).capitalize(), feedback=feedback,comments=comments,
                           locName=location.capitalize(),
                           discNames=discNames,discItms=discItms,
                           discTypes=discTypes,discMenu=discMenu,
                           discAmts=discAmts,discLimMin=discLimMin)


@admin_panel_blueprint.route('/<estNameStr>/<location>/addAdmin', methods=["POST"])
def addAdmin(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    email = session.get('user', None)
    pw = str(rsp["pw"])
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    email = str(email).replace(".","-")
    users = list(dict(ref.get()))
    users.remove(email)
    try:
        user = ref.get()[str(email)]
        if ((pbkdf2_sha256.verify(pw, user["password"])) == True):
            return(render_template("POS/AdminMini/addAdmin.html",users=users))
        else:
            return redirect(url_for('panel',estNameStr=estNameStr,location=location))
    except Exception:
        return redirect(url_for('panel',estNameStr=estNameStr,location=location))

@admin_panel_blueprint.route('/<estNameStr>/<location>/confirmAdmin', methods=["POST"])
def confirmAdmin(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    # email = session.get('user', None)
    email = str(rsp["email"])
    pw = str(rsp["password"])
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    email = str(email).replace(".","-")
    hash = pbkdf2_sha256.hash(pw)
    ref.update({
        email: {
            "password":hash,
            "time":0.0,
            "token":"uuid"
        }
    })
    return redirect(url_for('panel',estNameStr=estNameStr,location=location))

@admin_panel_blueprint.route('/<estNameStr>/<location>/editEmployee', methods=["POST"])
def editEmployee(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    email = session.get('user', None)
    pw = str(rsp["pw"])
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    email = str(email).replace(".","-")
    try:
        user = ref.get()[str(email)]
        if ((pbkdf2_sha256.verify(pw, user["password"])) == True):
            return(render_template("POS/AdminMini/editEmp.html"))
        else:
            return redirect(url_for('panel',estNameStr=estNameStr,location=location))
    except Exception:
        return redirect(url_for('panel',estNameStr=estNameStr,location=location))

@admin_panel_blueprint.route('/<estNameStr>/<location>/confirmEmpCode', methods=["POST"])
def confirmEmployeeCode(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    email = session.get('user', None)
    code = rsp["code"]
    hash = pbkdf2_sha256.hash(code)
    ref = db.reference('/restaurants/' + estNameStr + '/' + location + '/employee')
    ref.update({
        'code': hash
    })
    return redirect(url_for('panel',estNameStr=estNameStr,location=location))

@admin_panel_blueprint.route('/<estNameStr>/<location>/remUser~<user>')
def remUser(estNameStr,location,user):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login',estNameStr=estNameStr,location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login',estNameStr=estNameStr,location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    if(username != user):
        rem_ref = db.reference('/restaurants/' + estNameStr + '/admin-info/' + user)
        rem_ref.delete()
    return redirect(url_for('panel',estNameStr=estNameStr,location=location))
