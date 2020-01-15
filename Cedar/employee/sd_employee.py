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



sd_employee_blueprint = Blueprint('sd_employee', __name__,template_folder='templates')

infoFile = open("info.json")
info = json.load(infoFile)
mainLink = info['mainLink']

@sd_employee_blueprint.route('/<estNameStr>/<location>/employee-login')
def EmployeeLogin(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    return(render_template("POS/StaffSitdown/login.html"))

@sd_employee_blueprint.route('/<estNameStr>/<location>/employee-login2')
def EmployeeLogin2(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    return(render_template("POS/StaffSitdown/login2.html"))

@sd_employee_blueprint.route('/<estNameStr>/<location>/employee-login', methods=['POST'])
def EmployeeLoginCheck(estNameStr,location):
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
        return(redirect(url_for("sd_employee.EmployeePanel",estNameStr=estNameStr,location=location)))
    else:
        return(redirect(url_for("sd_employee.EmployeeLogin2",estNameStr=estNameStr,location=location)))

@sd_employee_blueprint.route('/<estNameStr>/<location>/view')
def EmployeePanel(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    token = session.get('token',None)
    loginRef = db.reference('/restaurants/' + estNameStr + '/' + location + "/employee")
    loginData = dict(loginRef.get())
    try:
        if(((token == loginData["token"]) and (time.time() - loginData["time"] <= 3600))):
            pass
        else:
            return(redirect(url_for("sd_employee.EmployeeLogin",estNameStr=estNameStr,location=location)))
    except Exception as e:
        print(e)
        return(redirect(url_for("sd_employee.EmployeeLogin2",estNameStr=estNameStr,location=location)))
    try:
        ordPath = '/restaurants/' + estNameStr + '/' + location + "/orders"
        ordsRef = db.reference(ordPath)
        ordsGet = dict(ordsRef.get())
        tokens = list(ordsGet)
        for tt in tokens:
            if(int(ordsGet[tt]["QSR"]) == 0):
                print(ordsGet[tt])
                del ordsGet[tt]
        print(ordsGet)
    except Exception as e:
        print(e)
        ordsGet = {}
    try:
        pathRequest = '/restaurants/' + estNameStr + '/' + location + "/requests/"
        reqRef = db.reference(pathRequest)
        reqData = dict(reqRef.get())
    except Exception as e:
        reqData = {}
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
    return(render_template("POS/StaffSitdown/View.html", location=location.capitalize(), restName=str(estNameStr.capitalize()), menu=menu, activeItems=activeItems, inactiveItems=inactiveItems, reqData=reqData, orders=ordsGet))


@sd_employee_blueprint.route('/<estNameStr>/<location>/activate-item~<cat>~<item>~<menu>')
def activateItem(estNameStr,location,cat,item,menu):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories/"+ cat + "/" + item
    descrip = dict(db.reference(pathMenu).get())["tmp"]
    db.reference(pathMenu).update({"descrip":descrip})
    pathDel = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories/"+ cat + "/" + item +"/tmp"
    db.reference(pathDel).delete()
    return(redirect(url_for("sd_employee.EmployeePanel",estNameStr=estNameStr,location=location)))

@sd_employee_blueprint.route('/<estNameStr>/<location>/deactivate-item~<cat>~<item>~<menu>')
def deactivateItem(estNameStr,location,cat,item,menu):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories/"+ cat + "/" + item
    descrip = dict(db.reference(pathMenu).get())["descrip"]
    db.reference(pathMenu).update({"tmp":descrip})
    db.reference(pathMenu).update({"descrip":"INACTIVE"})
    return(redirect(url_for("sd_employee.EmployeePanel",estNameStr=estNameStr,location=location)))

@sd_employee_blueprint.route('/<estNameStr>/<location>/view-success', methods=["POST"])
def EmployeeSuccess(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    reqToken = rsp["req"]
    pathRequest = '/restaurants/' + estNameStr + '/' + location + "/requests/" + reqToken
    reqRef = db.reference(pathRequest)
    reqData = dict(reqRef.get())
    orderToken = reqData["info"]["token"]
    if(reqData["info"]["type"] == "order"):
        pathTicket = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken +"/ticket"
        pathTotal = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
        del reqData["info"]
        tickRef = db.reference(pathTicket)
        cartData = reqData
        cartKeys = list(cartData.keys())
        # return(str(cartKeys))
        addTotal = 0
        req = []
        for ccx in range(len(cartKeys)):
            addTotal += float(cartData[cartKeys[ccx]]["price"])
        tickRef.push(reqData)
        currTotal = float(dict(db.reference(pathTotal).get())["subtotal"])
        tickTotal = db.reference(pathTotal).update({"subtotal":float(currTotal+addTotal)})
    reqRef.delete()
    return(redirect(url_for("sd_employee.EmployeePanel",estNameStr=estNameStr,location=location)))

@sd_employee_blueprint.route('/<estNameStr>/<location>/view-warning', methods=["POST"])
def EmployeeWarn(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    reqToken = rsp["req"]
    alert = rsp["reason"]
    pathRequest = '/restaurants/' + estNameStr + '/' + location + "/requests/" + reqToken
    reqRef = db.reference(pathRequest)
    reqData = dict(reqRef.get())
    orderToken = reqData["info"]["token"]
    pathRequest = '/restaurants/' + estNameStr + '/' + location + "/requests/" + reqToken
    pathUser = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
    reqRef = db.reference(pathRequest)
    reqData = dict(reqRef.get())
    orderToken = reqData["info"]["token"]
    if(reqData["info"]["type"] == "order"):
        pathTicket = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken +"/ticket"
        pathTotal = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
        del reqData["info"]
        tickRef = db.reference(pathTicket)
        cartData = reqData
        cartKeys = list(cartData.keys())
        # return(str(cartKeys))
        addTotal = 0
        req = []
        for ccx in range(len(cartKeys)):
            addTotal += float(cartData[cartKeys[ccx]]["price"])
        tickRef.push(reqData)
        currTotal = float(dict(db.reference(pathTotal).get())["subtotal"])
        tickTotal = db.reference(pathTotal).update({"subtotal":float(currTotal+addTotal)})
    AlertSend = db.reference(pathUser).update({"alert":str("Warning: "+alert)})
    AlertTime = db.reference(pathUser).update({"alertTime":time.time()})
    reqRef.delete()
    return(redirect(url_for("sd_employee.EmployeePanel",estNameStr=estNameStr,location=location)))


@sd_employee_blueprint.route('/<estNameStr>/<location>/view-reject', methods=["POST"])
def EmployeeReject(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    reqToken = rsp["req"]
    alert = rsp["reason"]
    pathRequest = '/restaurants/' + estNameStr + '/' + location + "/requests/" + reqToken
    reqRef = db.reference(pathRequest)
    reqData = dict(reqRef.get())
    orderToken = reqData["info"]["token"]
    pathUser = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
    AlertSend = db.reference(pathUser).update({"alert":str("Request Issue: "+alert)})
    AlertTime = db.reference(pathUser).update({"alertTime":time.time()})
    reqRef.delete()
    return(redirect(url_for("sd_employee.EmployeePanel",estNameStr=estNameStr,location=location)))


@sd_employee_blueprint.route('/<estNameStr>/<location>/view-editBill', methods=["POST"])
def EditBill(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    orderToken = rsp["req"]
    amt = float(rsp["amt"])
    itm = str(rsp["itm"])
    pathUserX = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
    pathUser = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken + "/ticket"
    cartRefItm = db.reference(pathUser)
    subtotal = float(db.reference(pathUserX).get()["subtotal"])
    subtotal += amt
    db.reference(pathUserX).update({"subtotal":subtotal})
    cartRefItm.push({str(uuid.uuid4()):{
        'cat':"",
        'img':"",
        'itm':itm,
        'qty':1,
        'notes':"added by staff",
        'dispStr':"Staff Correction: "+ itm + "  ($" + "{:0,.2f}".format(amt) + ")",
        'price':amt,
        'mods':[["",str(amt)]],
        'unitPrice':amt
    }})
    return(redirect(url_for("sd_employee.EmployeePanel",estNameStr=estNameStr,location=location)))


@sd_employee_blueprint.route('/<estNameStr>/<location>/view-clearTicket', methods=["POST"])
def RemBill(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    orderToken = rsp["req"]
    pathUserX = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
    remRef = db.reference(pathUserX)
    remRef.delete()
    return(redirect(url_for("sd_employee.EmployeePanel",estNameStr=estNameStr,location=location)))
