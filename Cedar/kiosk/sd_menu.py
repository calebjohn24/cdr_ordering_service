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
from Cedar.collect_menu import findMenu, getDispNameEst, getDispNameLoc
from Cedar.admin import admin_panel
from Cedar.admin.admin_panel import checkLocation, sendEmail, getSquare


sd_menu_blueprint = Blueprint('sd_menu', __name__, template_folder='templates')

infoFile = open("info.json")
info = json.load(infoFile)
mainLink = info['mainLink']


@sd_menu_blueprint.route('/<estNameStr>/<location>/sitdown-startKiosk-<code>', methods=["GET"])
def startKiosk2(estNameStr, location, code):
    testCode = db.reference('/billing/' + estNameStr + '/kiosks/' + code).get()
    if(testCode['active'] == 0):
        return(render_template('Customer/QSR/kioskinactive.html', alert='This Kiosk is Inactive Please Reactivate in the Admin Panel'))
    elif(testCode['active'] == None):
        return(render_template('Customer/QSR/kioskinactive.html', alert="Invalid Kiosk Code Please Reset Kiosk App"))
    else:
        session["kioskCode"] = code
        if(checkLocation(estNameStr, location) == 1):
            return(redirect(url_for("find_page.findRestaurant")))
        logo = 'https://storage.googleapis.com/cedarchatbot.appspot.com/'+estNameStr+'/logo.jpg'
        return(render_template("Customer/Sitdown/startKiosk.html", btn="sitdown-startKiosk", restName=getDispNameEst(estNameStr), locName=getDispNameLoc(estNameStr, location), logo=logo))



@sd_menu_blueprint.route('/<estNameStr>/<location>/sitdown-startKiosk', methods=["POST"])
def startKiosk(estNameStr, location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    phone = rsp["number"]
    name = rsp["name"]
    table = rsp["table"]
    session['table'] = table
    session['name'] = name
    session['phone'] = phone
    path = '/restaurants/' + estNameStr + '/' + location + "/orders/"
    orderToken = str(uuid.uuid4())
    ref = db.reference(path)
    menu = findMenu(estNameStr, location)
    session["menu"] = menu
    newOrd = ref.push({
        "menu": menu,
        "QSR": 1,
        "kiosk": 0,
        "cpn": 1,
        "name": name,
        "phone": phone,
        "table": table,
        "paid": "Not Paid",
        "alert": "null",
        "alertTime": 0,
        "timestamp": time.time(),
        "subtotal": 0.0
    })
    # print(newOrd.key)
    session['orderToken'] = newOrd.key
    msg = "Welcome to " + \
        getDispNameEst(
            estNameStr) + ". You can use this tablet to browse the menu, order food, ask for drink refills, and contact the staff.  Enjoy Your Meal!"
    session["msg"] = msg
    session["startTime"] = time.time()
    session["click"] = "None"
    return(redirect(url_for('sd_menu.sitdownMenu', estNameStr=estNameStr, location=location)))


@sd_menu_blueprint.route('/<estNameStr>/<location>/sitdown-menudisp')
def sitdownMenu(estNameStr, location):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    menu = session.get('menu', None)
    orderToken = session.get('orderToken', None)
    msg = session.get('msg', None)
    click = session.get('click', None)
    pathMenu = '/restaurants/' + estNameStr + '/' + \
        location + "/menu/" + menu + "/categories"
    menuInfo = dict(db.reference(pathMenu).get())
    cartRef = db.reference('/restaurants/' + estNameStr +
                           '/' + location + "/orders/" + orderToken + "/cart")
    try:
        cart = dict(cartRef.get())
    except Exception as e:
        cart = {}
    try:
        tick = db.reference('/restaurants/' + estNameStr + '/' +
                            location + "/orders/" + orderToken + "/ticket").get()
        boolCheck = 0
        if(tick == None):
            boolCheck = 1
    except Exception as e:
        boolCheck = 1
    # print(cart)
    session["msg"] = "None"
    session["click"] = "None"
    return(render_template("Customer/Sitdown/mainKiosk2.html", menu=menuInfo, restName=getDispNameEst(estNameStr), cart=cart, locName=getDispNameLoc(estNameStr, location), msg=msg, click=click, boolCheck=boolCheck))


@sd_menu_blueprint.route('/<estNameStr>/<location>/sitdown-additms~<cat>~<itm>', methods=["POST"])
def kiosk2(estNameStr, location, cat, itm):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    # print((request.form))
    rsp = dict((request.form))
    dispStr = ""
    unitPrice = 0
    notes = rsp['notes']
    qty_str = rsp['qty']
    if(qty_str == ""):
        qty = 1
    else:
        qty = abs(int(qty_str))
    dispStr += str(qty) + " x " + itm + " "
    dict_keys = list(rsp.keys())
    mods = []
    img = ""
    for keys in dict_keys:
        if(keys != "notes" or keys != "qty"):
            try:
                raw_arr = rsp[keys].split("~")
                img = raw_arr[2]
                if(str(raw_arr[0]).lower() != "standard"):
                    dispStr += str(raw_arr[0]).capitalize() + "  "
                mods.append([raw_arr[0], raw_arr[1]])
                unitPrice += float(raw_arr[1])
            except Exception as e:
                pass
    price = float(qty*unitPrice)
    msg = dispStr + " " + notes + " Added To Cart"
    dispStr += "  | Notes: " + notes
    dispStr += "  ($" + "{:0,.2f}".format(price) + ")"
    menu = session.get('menu', None)
    orderToken = session.get('orderToken', None)
    pathCartitm = '/restaurants/' + estNameStr + '/' + \
        location + "/orders/" + orderToken + "/cart/"
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu
    cartRefItm = db.reference(pathCartitm)
    cartRefItm.push({
        'cat': cat,
        'itm': itm,
        'qty': qty,
        'img': img,
        'notes': notes,
        'price': price,
        'dispStr': dispStr,
        'mods': mods,
        'unitPrice': unitPrice
    })
    # print(msg)
    session["msg"] = msg
    session["click"] = "#"+cat+"-btn"
    return(redirect(url_for('sd_menu.sitdownMenu', estNameStr=estNameStr, location=location)))


@sd_menu_blueprint.route('/<estNameStr>/<location>/itmRemove', methods=["POST"])
def kioskRem(estNameStr, location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = dict((request.form))
    remItm = rsp["remove"]
    orderToken = session.get('orderToken', None)
    menu = session.get('menu', None)
    pathCartitm = '/restaurants/' + estNameStr + '/' + \
        location + "/orders/" + orderToken + "/cart/"
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu
    remPath = '/restaurants/' + estNameStr + '/' + \
        location + "/orders/" + orderToken + "/cart/" + remItm
    try:
        remRef = db.reference(remPath)
        remRef.delete()
    except Exception as e:
        pass
    finally:

        cartRefItm = db.reference(pathCartitm)
        menuInfo = db.reference(pathMenu).get()
        cartData = db.reference(pathCartitm).get()
    msg = "None"
    session["msg"] = msg
    session["click"] = "#carttab"
    return(redirect(url_for('sd_menu.sitdownMenu', estNameStr=estNameStr, location=location)))



@sd_menu_blueprint.route('/<estNameStr>/<location>/SDupdate')
def kioskUpdate(estNameStr, location):
    try:
        orderToken = session.get('orderToken', None)
        setPath = '/restaurants/' + estNameStr + \
            '/' + location + "/orders/" + orderToken
        alertTimePath = '/restaurants/' + estNameStr + '/' + \
            location + "/orders/" + orderToken + "/alertTime"
        alertPath = '/restaurants/' + estNameStr + '/' + \
            location + "/orders/" + orderToken + "/alert"
        alert = db.reference(alertPath).get()
        info = {
            "alert": alert,
        }
        return jsonify(info)
    except Exception as e:
        return("200")


@sd_menu_blueprint.route('/<estNameStr>/<location>/cartAdd', methods=["POST"])
def kioskCart(estNameStr, location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    orderToken = session.get('orderToken', None)
    menu = session.get('menu', None)
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu
    pathCart = '/restaurants/' + estNameStr + '/' + \
        location + "/orders/" + orderToken + "/cart/"
    pathTable = '/restaurants/' + estNameStr + '/' + \
        location + "/orders/" + orderToken + "/table/"
    pathRequest = '/restaurants/' + estNameStr + '/' + location + "/requests/"
    tableNum = db.reference(pathTable).get()
    try:
        cartRef = db.reference(pathCart)
        cart = db.reference(pathCart).get()
        reqRef = db.reference(pathRequest)
        newReq = reqRef.push(cart)
        pathRequestkey = '/restaurants/' + estNameStr + '/' + \
            location + "/requests/" + newReq.key + "/info"
        reqRefkey = db.reference(pathRequestkey)
        reqRefkey.update(
            {"table": tableNum, "type": "order", "token": orderToken})
        cartRef.delete()
        msg = "Order Sent To Kitchen"
        session["msg"] = msg
    except Exception:
        msg = "None"
        session["msg"] = msg
    menuInfo = db.reference(pathMenu).get()
    cart = {}
    return(redirect(url_for('sd_menu.sitdownMenu', estNameStr=estNameStr, location=location)))


@sd_menu_blueprint.route('/<estNameStr>/<location>/collect-feedback')
def dispFeedBack(estNameStr, location):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    feedback_ref = db.reference(
        '/restaurants/' + estNameStr + '/' + location + '/feedback')
    feedback = dict(feedback_ref.get())
    return(render_template("Customer/Sitdown/feedback.html", feedback=feedback))


@sd_menu_blueprint.route('/<estNameStr>/<location>/close-alert')
def kioskClear(estNameStr, location):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    orderToken = session.get('orderToken', None)
    alertPath = '/restaurants/' + estNameStr + \
        '/' + location + "/orders/" + orderToken
    clearAlert = db.reference(alertPath).update({"alert": "null"})
    return(redirect(url_for('sd_menu.sitdownMenu', estNameStr=estNameStr, location=location)))


@sd_menu_blueprint.route('/<estNameStr>/<location>/sendReq', methods=["POST"])
def kioskSendReq(estNameStr, location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = dict((request.form))
    del rsp['csrf_token']
    rspKey = list(rsp.keys())[0]
    print(rspKey)
    if(rspKey == "condiments"):
        requestId = "extra condiments-" + rsp["condiments"]
    elif(rspKey == "drinks"):
        requestId = "refill drinks-" + rsp["drinks"]
    elif(rspKey == "napkins"):
        requestId = "more napkins"
    elif(rspKey == "cutlery"):
        requestId = "more cutlery"
    elif(rspKey == "clear"):
        requestId = "clear table"
    elif(rspKey == "issue"):
        requestId = "issue-"+rsp["issue"]
    elif(rspKey == "box"):
        requestId = "box food-"+rsp["box"]
    elif(rspKey == "other"):
        requestId = "other-"+rsp["other"]
    menu = session.get('menu', None)
    orderToken = session.get('orderToken', None)
    tableNum = session.get('table', None)
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu
    pathRequest = '/restaurants/' + estNameStr + '/' + location + "/requests/"
    reqRef = db.reference(pathRequest)
    newReq = reqRef.push({"help": requestId})
    pathRequestkey = '/restaurants/' + estNameStr + '/' + \
        location + "/requests/" + newReq.key + "/info"
    reqRefkey = db.reference(pathRequestkey)
    reqRefkey.set({"table": tableNum, "type": "help", "token": orderToken})
    msg = "Request Sent To Staff"
    session["msg"] = msg
    return(redirect(url_for('sd_menu.sitdownMenu', estNameStr=estNameStr, location=location)))


@sd_menu_blueprint.route('/<estNameStr>/<location>/collect-feedback-ans', methods=['POST'])
def collectFeedback(estNameStr, location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = dict((request.form))
    orderToken = session.get('orderToken', None)
    pathOrder = '/restaurants/' + estNameStr + \
        '/' + location + "/orders/" + orderToken
    if(rsp['email'] != ""):
        userRef = db.reference(pathOrder)
        userRef.update({
            "email": rsp['email']
        })
    else:
        userRef = db.reference(
            '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken)
        userRef.update({
            "email": "no-email"
        })
    orderInfo = dict(db.reference(pathOrder).get())
    tzGl = {}
    locationsPaths = {}
    getSquare(estNameStr, tzGl, locationsPaths)
    now = datetime.datetime.now(tzGl[location])
    feedback_ref = db.reference(
        '/restaurants/' + estNameStr + '/' + location + '/feedback')
    curr_feedback = dict(feedback_ref.get())
    comment_ref = db.reference(
        '/restaurants/' + estNameStr + '/' + location + '/comments/new')
    comments = str(rsp['comment']) + " "
    if(str(rsp['comment']) != ""):
        comment_ref.push({
            "comment": comments,
            "name": orderInfo['name'],
            "timeStamp": str(now.hour) + ":" + str(now.minute) + " " + str(now.month) + "-" + str(now.day) + "-" + str(now.year)
        })
    del rsp['comment']
    newFeedKeys = list(rsp.keys())
    feedKeys = list(curr_feedback.keys())
    timeScale = ['day', 'week', 'month']
    timeScaleVal = [int(datetime.datetime.now(tzGl[location]).weekday()), int(datetime.datetime.now(
        tzGl[location]).isocalendar()[1]), int(datetime.datetime.now(tzGl[location]).month)]
    for tms in range(len(timeScale)):
        for keys in feedKeys:
            currScore = curr_feedback[keys]['info'][timeScale[tms]
                                                    ]['totalScore']
            ansSize = curr_feedback[keys]['info'][timeScale[tms]]['count']
            addScore = curr_feedback[keys]['ans'][rsp[keys]]['score']
            timeKey = "curr" + str(timeScale[tms])
            timeVal = curr_feedback[keys]['info'][timeScale[tms]][timeKey]

            currScore += addScore
            ansSize += 1
            newDispScore = round(float(currScore)/float(ansSize), 2)
            qFeedbackRef = db.reference('/restaurants/' + estNameStr + '/' +
                                        location + '/feedback/' + keys + '/info/' + str(timeScale[tms]))
            if(timeVal == timeScaleVal[tms]):
                qFeedbackRef.update({
                    'count': ansSize,
                    'currentScore': newDispScore,
                    'totalScore': currScore
                })
            else:
                qFeedbackRef.update({
                    timeKey: timeScaleVal[tms],
                    'count': 1,
                    'currentScore': addScore,
                    'totalScore': addScore
                })
    return(redirect(url_for("payments.payQSR", estNameStr=estNameStr, location=location)))
