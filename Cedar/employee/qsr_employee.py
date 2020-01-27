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



qsr_employee_blueprint = Blueprint('qsr_employee', __name__,template_folder='templates')
sender = 'cedarrestaurantsbot@gmail.com'
emailPass = "cda33d07-f6bd-479e-806f-5d039ae2fa2d"
infoFile = open("info.json")
info = json.load(infoFile)
mainLink = info['mainLink']




@qsr_employee_blueprint.route('/<estNameStr>/<location>/qsr-employee-login')
def EmployeeLoginQSR(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    return(render_template("POS/StaffQSR/login.html"))

@qsr_employee_blueprint.route('/<estNameStr>/<location>/qsr-employee-login2')
def EmployeeLogin2QSR(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    return(render_template("POS/StaffQSR/login2.html"))

@qsr_employee_blueprint.route('/<estNameStr>/<location>/qsr-employee-login', methods=['POST'])
def EmployeeLoginCheckQSR(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    code = rsp['code']
    loginRef = db.reference('/restaurants/' + estNameStr + '/' + location + "/employee")
    loginData = dict(loginRef.get())
    hashCheck = pbkdf2_sha256.verify(code, loginData['code'])
    if(hashCheck == True):
        token = str(uuid.uuid4())
        loginRef.update({
            "token":token,
            "time":time.time()
        })
        session["token"] = token
        return(redirect(url_for("qsr_employee.EmployeePanelQSR",estNameStr=estNameStr,location=location)))
    else:
        return(redirect(url_for("qsr_employee.EmployeeLogin2QSR",estNameStr=estNameStr,location=location)))

@qsr_employee_blueprint.route('/<estNameStr>/<location>/qsr-view')
def EmployeePanelQSR(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    token = session.get('token',None)
    loginRef = db.reference('/restaurants/' + estNameStr + '/' + location + "/employee/")
    loginData = dict(loginRef.get())
    try:
        if(((token == loginData["token"]) and (time.time() - loginData["time"] <= 3600))):
            pass
        else:
            return(redirect(url_for("qsr_employee.EmployeeLoginQSR",estNameStr=estNameStr,location=location)))
    except Exception as e:
        return(redirect(url_for("EmployeeLogin2QSR",estNameStr=estNameStr,location=location)))
    try:
        ordPath = '/restaurants/' + estNameStr + '/' + location + "/orderQSR"
        ordsRef = db.reference(ordPath)
        ordsGet = dict(ordsRef.get())
    except Exception as e:
        ordsGet = {}
    menu = findMenu(estNameStr,location)
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories"
    menuInfo = dict(db.reference(pathMenu).get())
    categories = list(menuInfo.keys())
    activeItems = []
    inactiveItems = []
    for cats in categories:
        itms = list(dict(menuInfo[cats]).keys())
        for itm in itms:
            if(menuInfo[cats][itm]["descrip"] != "INACTIVE"):
                appItem = str(cats) + "~" + str(itm)
                activeItems.append(appItem)
            else:
                appItem = str(cats) + "~" + str(itm)
                inactiveItems.append(appItem)
    return(render_template("POS/StaffQSR/View.html", location=getDispNameLoc(estNameStr,location), restName=getDispNameEst(estNameStr), menu=menu, activeItems=activeItems, inactiveItems=inactiveItems, orders=ordsGet))


@qsr_employee_blueprint.route('/<estNameStr>/<location>/qsr-activate-item~<cat>~<item>~<menu>')
def activateItemQSR(estNameStr,location,cat,item,menu):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories/"+ cat + "/" + item
    descrip = dict(db.reference(pathMenu).get())["tmp"]
    db.reference(pathMenu).update({"descrip":descrip})
    pathDel = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories/"+ cat + "/" + item +"/tmp"
    db.reference(pathDel).delete()
    return(redirect(url_for("qsr_employee.EmployeePanelQSR",estNameStr=estNameStr,location=location)))

@qsr_employee_blueprint.route('/<estNameStr>/<location>/qsr-deactivate-item~<cat>~<item>~<menu>')
def deactivateItemQSR(estNameStr,location,cat,item,menu):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories/"+ cat + "/" + item
    descrip = dict(db.reference(pathMenu).get())["descrip"]
    db.reference(pathMenu).update({"tmp":descrip})
    db.reference(pathMenu).update({"descrip":"INACTIVE"})
    return(redirect(url_for("qsr_employee.EmployeePanelQSR",estNameStr=estNameStr,location=location)))

@qsr_employee_blueprint.route('/<estNameStr>/<location>/qsr-view-success', methods=["POST"])
def EmployeeSuccessQSR(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    reqToken = rsp["req"]
    pathRequest = '/restaurants/' + estNameStr + '/' + location + "/orderQSR/" + reqToken
    reqRef = db.reference(pathRequest)
    reqRef.delete()
    return(redirect(url_for("qsr_employee.EmployeePanelQSR",estNameStr=estNameStr,location=location)))

@qsr_employee_blueprint.route('/<estNameStr>/<location>/qsr-sendOrder', methods=["POST"])
def sendOrderQsr(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    token = rsp["token"]
    pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + token
    orderRef = db.reference(pathOrder)
    order = dict(orderRef.get())
    qsrOrderPath = '/restaurants/' + estNameStr + '/' + location + '/orderQSR'
    qsrOrderRef = db.reference(qsrOrderPath)
    qsrOrderRef.update({
        token:{
            "cart":dict(order['cart']),
            "info":{"name":order["name"],
                    "number":order['phone'],
                    "paid":"PAID",
                    "subtotal":order['subtotal'],
                    "total":order['total'],
                    'table':order['table']}
            }
    })

    checkmate = db.reference('/restaurants/' + estNameStr + '/' + location + '/checkmate').get()
    if(checkmate == 0):
        sendCheckmate(estNameStr,location, token)

    if(order['email'] != "no-email"):
        tzGl = {}
        locationsPaths = {}
        getSquare(estNameStr, tzGl, locationsPaths)
        now = datetime.datetime.now(tzGl[location])
        write_str = "Your Order From "+ estNameStr.capitalize()  + " " + location.capitalize() + " @"
        write_str += str(now.strftime("%H:%M ")) + " on " + str(now.month) + "-" + str(now.day) + "-" + str(now.year)
        write_str += "\n \n"
        cart = dict(order["cart"])
        subtotal = 0
        items = []
        cartKeys = list(cart.keys())
        for keys in cartKeys:
            subtotal += cart[keys]["price"]
            dispStr = cart[keys]["dispStr"]
            write_str += dispStr + "\n"
        subtotal += 0.25
        subtotalStr = "${:0,.2f}".format(subtotal)
        taxRate = float(db.reference('/restaurants/' + estNameStr + '/' + location + '/taxrate').get())
        tax = "${:0,.2f}".format(subtotal * taxRate)
        tax += " (" + str(float(taxRate * 100)) + "%)"
        total = "${:0,.2f}".format(subtotal * (1+taxRate))
        write_str+= "\n \n"
        write_str += subtotalStr +"\n"+tax + "\n"+ total +"\n \n \n"
        write_str += 'Thank You For Your Order ' + str(order['name']).capitalize() + " !"
        SUBJECT = "Your Order From "+ estNameStr.capitalize()  + " " + location.capitalize()
        message = 'Subject: {}\n\n{}'.format(SUBJECT, write_str)
        # smtpObj.sendmail(sender, [order['email']], message)
        sendEmail(sender, order['email'], message)
    return(redirect(url_for("qsr_employee.EmployeePanelQSR",estNameStr=estNameStr,location=location)))
