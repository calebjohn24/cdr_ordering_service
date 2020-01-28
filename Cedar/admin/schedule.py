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
from Cedar.admin.admin_panel import getSquare, checkAdminToken, checkLocation, panel
import Cedar

schedule_blueprint = Blueprint('schedule', __name__,template_folder='templates')


dayNames = ["MON", "TUE", "WED", "THURS", "FRI", "SAT", "SUN"]

global tzGl
adminSessTime = 3599
global locationsPaths
tzGl = {}
locationsPaths = {}



@schedule_blueprint.route('/<estNameStr>/<location>/schedule-<day>', methods=["GET"])
def scheduleSet(estNameStr,location,day):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    getSquare(estNameStr, tzGl, locationsPaths)
    print(locationsPaths, tzGl)
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('admin_panel.login',estNameStr=estNameStr,location=location))
    if (checkAdminToken(estNameStr, idToken, username) == 1):
        return redirect(url_for('admin_panel.login',estNameStr=estNameStr,location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    sched_ref = db.reference('/restaurants/' + estNameStr + '/'+location+"/schedule")
    menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu')
    menu_keys = list((menu_ref.get()).keys())
    menu_data = menu_ref.get()
    menuTotals = []
    for keys in menu_keys:
        if(menu_data[keys]["active"] == True):
            menuTotals.append(keys)
    currentSchedule = dict(sched_ref.get()[day])
    schedList = list(currentSchedule.keys())
    timeDict = {"Start-of-Day":'0:00'}
    timeContainers = []
    menus = ["Start-of-Day"]
    menuTimes = [0.0]
    menuTimesStr = ['0:00']
    for s in schedList:
        timeContainers.append(currentSchedule[s])
    timeContainers.sort()
    for tc in range(len(timeContainers)):
        for schedKeys in schedList:
            if(timeContainers[tc] == currentSchedule[schedKeys]):
                sch = str(schedKeys).replace(" ","-")
                menus.append(sch)
                timeStr = "{:.2f}".format(currentSchedule[schedKeys])
                timeStr = str(timeStr).replace(".",":")
                menuTimes.append(currentSchedule[schedKeys])
                menuTimesStr.append(timeStr)
                timeDict.update({sch:timeStr})
    menus.append("End-of-Day")
    menuTimes.append(23.59)
    menuTimesStr.append("23:59")
    timeDict.update({"End-of-Day":"23:59"})
    return(render_template("POS/AdminMini/listSchedule.html",day=day,menuTotals=menuTotals,timeDict=timeDict,menuTimes=menuTimes,menus=menus,menuTimesStr=menuTimesStr))

@schedule_blueprint.route('/<estNameStr>/<location>/remTs~<day>~<menu>')
def remTimeSlot(estNameStr,location,day,menu):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    menu = str(menu).replace("-"," ")
    menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/schedule/'+str(day)+"/"+str(menu))
    menu_ref.delete()
    return(redirect(url_for("schedule.scheduleSet",estNameStr=estNameStr,location=location,day=day)))

@schedule_blueprint.route('/<estNameStr>/<location>/schedMenu~<day>~<menu>~<timeVal>', methods=["POST"])
def editTimeSlot(estNameStr,location,day,menu,timeVal):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    new_menu = str(rsp["menu"])
    del_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/schedule/'+str(day)+"/"+menu)
    del_ref.delete()
    menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/schedule/'+str(day))
    menu_ref.update({new_menu:float(timeVal)})
    return(redirect(url_for("schedule.scheduleSet",estNameStr=estNameStr,location=location,day=day)))

@schedule_blueprint.route('/<estNameStr>/<location>/editMenuTime~<day>~<menu>', methods=["POST"])
def editMenuSlot(estNameStr,location,day,menu):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    hour = float(rsp["hour"])
    minute = (float(rsp["minute"])/100)
    newTime = hour+minute
    menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/schedule/'+str(day))
    menu_ref.update({menu:newTime})
    return(redirect(url_for("schedule.scheduleSet",estNameStr=estNameStr,location=location,day=day)))

@schedule_blueprint.route('/<estNameStr>/<location>/addTs~<day>', methods=["POST"])
def addTimeSlot(estNameStr,location,day):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    hour = float(rsp["hour"])
    minute = (float(rsp["minute"])/100)
    menu = str(rsp["menu"])
    newTime = hour+minute
    menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/schedule/'+str(day))
    menu_ref.update({menu:newTime})
    return(redirect(url_for("schedule.scheduleSet",estNameStr=estNameStr,location=location,day=day)))
