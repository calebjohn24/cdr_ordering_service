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
from Cedar.admin import admin_panel
from Cedar.admin.admin_panel import checkLocation, sendEmail, getSquare
from Cedar import collect_menu
from Cedar.admin.billing import updateTransactionFees
from Cedar.collect_menu import findMenu, getDispNameEst, getDispNameLoc, updateEst, updateLoc

infoFile = open("info.json")
info = json.load(infoFile)
mainLink = info['mainLink']

kioskApi_blueprint = Blueprint('kioskApi', __name__,template_folder='templates')

sender = 'cedarrestaurantsbot@gmail.com'
emailPass = "cda33d07-f6bd-479e-806f-5d039ae2fa2d"



@kioskApi_blueprint.before_request
def check_csrf():
    print(request.path)


@kioskApi_blueprint.route('/<estNameStr>/<locationX>/kiosksetup/<type>', methods=["POST"])
def GenReaderCode(estNameStr,locationX,type):
    locationX = str(locationX).lower()
    rsp = request.get_json()
    print(rsp, locationX)
    code = rsp['code']
    kioskRef = db.reference('/billing/' + estNameStr.lower() + '/kiosks/' + code)
    try:
        check = kioskRef.get()
        print(check, "check")
        if(check == None):
            packet = {
                "success":"no",
                "code":"Invlaid Kiosk code"
            }
            return jsonify(packet)
        elif(check['active'] == 1):
            print(check)
            packet = {
                "success":"no",
                "code":"Kiosk Already In Use. Please Deauthorize In The Admin Panel"
            }
            return jsonify(packet)
        else:
            kioskType = ["qsr-startKiosk","sitdown-startKiosk"]
            sqRef = db.reference(str('/restaurants/' + estNameStr))
            squareToken = dict(sqRef.get())["sq-token"]
            print(squareToken)
            client = Client(
                access_token=squareToken,
                environment='production',
            )
            api_locations = client.locations
            mobile_authorization_api = client.mobile_authorization
            # Call list_locatio
            result = api_locations.list_locations()
            if result.is_success():
            	# The body property is a list of locations
                locations = result.body['locations']
            	# Iterate over the list
                for location in locations:
                    if((dict(location.items())["status"]) == "ACTIVE"):
                        # print(dict(location.items()))
                        locationName = (dict(location.items())["name"]).replace(" ","-")
                        # print(locationName)
                        locationId = dict(location.items())["id"]
                        if(str(locationName).lower() == locationX):
                            body = {}
                            body['location_id'] = locationId
                            result = mobile_authorization_api.create_mobile_authorization_code(body)
                            if result.is_success():
                                code = dict(result.body)['authorization_code']
                                print(code)
                                kioskRef = db.reference('/billing/' + estNameStr + '/kiosks')
                                kioskRef.update({str(rsp['code']):
                                    {"active":1,
                                     "loc":locationX}})
                                packet = {
                                    "success":"yes",
                                    "code":code ,
                                    "link": str(mainLink+estNameStr+'/'+ locationX + "/" + str(kioskType[int(type)]) + "-" + str(rsp['code']))
                                }
                                return jsonify(packet)
                            elif result.is_error():
                                print('err')
                                packet = {
                                    "success":"no",
                                    "code":"invlaid location"
                                }
                                return jsonify(packet)
    except Exception as e:
        print(e)
        print(2)
        packet = {
            "success":"no",
            "code":"Invlaid Kiosk code"
        }
        return jsonify(packet)


@kioskApi_blueprint.route('/<estNameStr>/<location>/verify-kiosk-payment~<kioskCode>', methods=["POST"])
def verifyOrder(estNameStr, location, kioskCode):
    tzGl = {}
    locationsPaths = {}
    getSquare(estNameStr, tzGl, locationsPaths)
    rsp = request.get_json()
    print(rsp)
    token = rsp['tokenVal']
    pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + token
    orderRef = db.reference(pathOrder)
    order = dict(orderRef.get())
    if(order['QSR'] == 0):
        qsrOrderPath = '/restaurants/' + estNameStr + '/' + location + '/orderQSR'
        qsrOrderRef = db.reference(qsrOrderPath)
        qsrOrderRef.update({
            token: {
                "cart": dict(order['cart']),
                "info": {"name": order["name"],
                         "number": order['phone'],
                         "paid": "PAID",
                         "subtotal": order['subtotal'],
                         "total": order['total'],
                         'table': order['table']}
            }
        })
        now = datetime.datetime.now(tzGl[location])
        month = str(now.month)
        logRef = str(now.month) + '-' + str(now.year)[:2]
        checkmate = db.reference(
            '/restaurants/' + estNameStr + '/' + location + '/checkmate').get()
        if(checkmate == 0):
            sendCheckmate(estNameStr, location, token)
        tzGl = {}
        locationsPaths = {}
        billingRef = db.reference('/billing/' + estNameStr)
        billingInfo = dict(billingRef.get())
        getSquare(estNameStr, tzGl, locationsPaths)
        now = datetime.datetime.now(tzGl[location])
        write_str = "Your Order From " + getDispNameEst(estNameStr) + " " + \
            getDispNameLoc(estNameStr,location) + " on "
        timeStamp = str(now.month) + "-" + str(now.day) + "-" + \
            str(now.year) + " @ " + str(now.strftime("%H:%M"))
        write_str += timeStamp
        write_str += "\n \n"
        cart = dict(order["cart"])
        subtotal = 0
        items = []
        cartKeys = list(cart.keys())
        startTime = session.get('startTime', None)
        duration = time.time() - startTime
        logOrd = {
            "info": {
                "location": location,
                "menu": order['menu'],
                "time": timeStamp,
                "duartion": duration,
                "name": order['name'],
                "phone": order['phone'],
                "payment": "square-cc",
                "type": "QSR",
                "email": order['email'],
                "subtotal": 0,
                "feescustomer": billingInfo['custFee'],
                "feesrestaurant": billingInfo['restFee'],
                "feestotal": billingInfo['totalFee'],
                "taxes": 0,
                "total": 0
            },
            "order": [],
            "orderDict": []
        }
        for keys in cartKeys:
            subtotal += cart[keys]["price"]
            dispStr = cart[keys]["dispStr"]
            logOrd['order'].append(dispStr)
            logOrd['orderDict'].append(cart[keys])
            write_str += dispStr + "\n"
        logOrd['info'].update({"subtotal": subtotal, "feescustomer": billingInfo['custFee'],
                               "feesrestaurant": billingInfo['restFee'], "feestotal": billingInfo['totalFee']})
        subtotal += billingInfo['custFee']
        logOrd['info'].update({"subtotal": float(subtotal)})
        subtotalStr = "${:0,.2f}".format(subtotal)
        taxRate = float(db.reference('/restaurants/' +
                                     estNameStr + '/' + location + '/taxrate').get())
        tax = "${:0,.2f}".format(subtotal * taxRate)
        tax += " (" + str(float(taxRate * 100)) + "%)"
        logOrd['info'].update({"taxes": float(subtotal * taxRate)})
        total = "${:0,.2f}".format(subtotal * (1 + taxRate))
        logOrd['info'].update({"total": float(subtotal * (1 + taxRate))})
        logRef = db.reference('/billing/' + estNameStr + '/fees/all/log')
        logRef.push(logOrd)
        logRef = db.reference('/billing/' + estNameStr +
                              '/fees/locations/' + location + '/log')
        logRef.push(logOrd)
        sendSQpos2(estNameStr, location, token)
        if(order['email'] != "no-email"):
            write_str += "\n \n"
            write_str += "Order Fee " + \
                "${:0,.2f}".format(billingInfo['custFee']) + "\n"
            write_str += "Subtotal " + subtotalStr + "\n" + \
                "Tax " + tax + "\n" + "Total " + total + "\n \n \n"
            write_str += 'Thank You For Your Order ' + \
                str(order['name']).capitalize() + " !"
            SUBJECT = "Your Order From " + getDispNameEst(estNameStr) + " " + \
                getDispNameLoc(estNameStr,location)
            message = 'Subject: {}\n\n{}'.format(SUBJECT, write_str)
            sendEmail(sender, order['email'], message)
        kioskCode = session.get('kioskCode', None)
        testCode = db.reference(
            '/billing/' + estNameStr + '/kiosks/' + kioskCode).get()
        if(testCode['active'] == 1):
            packet = {
                "code": token,
                "success": "true"
            }
        else:
            packet = {
                "code": token,
                "success": "kiosk deactivated"
            }
        updateTransactionFees(billingInfo['totalFee'], estNameStr, location)
        orderRef.delete()
        return jsonify(packet)
    else:
        pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + token
        orderRef = db.reference(pathOrder)
        orderRef.update({
            "paid": "PAID"
        })

        now = datetime.datetime.now(tzGl[location])
        write_str = "Your Meal From " + getDispNameEst(estNameStr) + " " + \
            getDispNameLoc(estNameStr, location) + " on "
        timeStamp = str(now.month) + "-" + str(now.day) + "-" + \
            str(now.year) + " @ " + str(now.strftime("%H:%M"))
        write_str += timeStamp
        write_str += "\n \n"
        cart = dict(order["ticket"])
        subtotal = order["subtotal"]
        billingRef = db.reference('/billing/' + estNameStr)
        billingInfo = dict(billingRef.get())
        subtotal += billingInfo['custFee']
        subtotalStr = "${:0,.2f}".format(subtotal)
        taxRate = float(db.reference('/restaurants/' +
                                     estNameStr + '/' + location + '/taxrate').get())
        tax = "${:0,.2f}".format(subtotal * taxRate)
        tax += " (" + str(float(taxRate * 100)) + "%)"
        total = "${:0,.2f}".format(subtotal * (1 + taxRate))
        startTime = session.get('startTime', None)
        duration = time.time() - startTime
        logOrd = {
            "info": {
                "location": location,
                "menu": order['menu'],
                "time": timeStamp,
                "duartion": duration,
                "name": order['name'],
                "phone": order['phone'],
                "payment": "square-cc",
                "type": "Sitdown",
                "email": order['email'],
                "subtotal": float(subtotal - billingInfo['custFee']),
                "feescustomer": billingInfo['custFee'],
                "feesrestaurant": billingInfo['restFee'],
                "feestotal": billingInfo['totalFee'],
                "taxes": float(subtotal) * float(taxRate),
                "total": float(subtotal * (1 + taxRate))
            },
            "order": [],
            "orderDict": []
        }
        cartKeys = list(cart.keys())
        for ck in cartKeys:
            ckKeys = list(cart[ck].keys())
            for ckk in ckKeys:
                dispStr = cart[ck][ckk]["dispStr"] + "\n"
                write_str += dispStr
                logOrd['order'].append(cart[ck][ckk]["dispStr"])
                logOrd['orderDict'].append(cart[ck][ckk])
        logRef = db.reference('/billing/' + estNameStr + '/fees/all/log')
        logRef.push(logOrd)
        logRef = db.reference('/billing/' + estNameStr +
                              '/fees/locations/' + location + '/log')
        logRef.push(logOrd)
        if(order['email'] != "no-email"):
            write_str += "\n \n"
            write_str += "Order Fee " + \
                "${:0,.2f}".format(billingInfo['custFee'])
            write_str += "\n"
            write_str += "Subtotal: " +subtotalStr + "\n" + "Sales Tax: "+tax + "\n" + "Total: " +total + "\n \n \n"
            write_str += 'Thank You For Dining with us ' + \
                str(order['name']).capitalize() + " !"
            SUBJECT = "Thank You For Dining at " + getDispNameEst(estNameStr)+ " " + \
                getDispNameLoc(estNameStr, location)
            message = 'Subject: {}\n\n{}'.format(SUBJECT, write_str)
            sendEmail(sender, order['email'], message)
        orderRef.delete()
        kioskCode = session.get('kioskCode', None)
        testCode = db.reference(
            '/billing/' + estNameStr + '/kiosks/' + kioskCode).get()
        if(testCode['active'] == 1):
            packet = {
                "code": token,
                "success": "true"
            }
        else:
            packet = {
                "code": token,
                "success": "kiosk deactivated"
            }
        updateTransactionFees(billingInfo['totalFee'], estNameStr, location)
        return jsonify(packet)




@kioskApi_blueprint.route('/signup-card', methods=['POST'])
def cardAdded():
    rsp = request.json
    print(rsp)
    return("200")