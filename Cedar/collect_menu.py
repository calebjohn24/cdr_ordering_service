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
global tzGl
adminSessTime = 3599
global locationsPaths
tzGl = {}
locationsPaths = {}
dayNames = ["MON", "TUE", "WED", "THURS", "FRI", "SAT", "SUN"]


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
    # print(result)
    if result.is_success():
        # The body property is a list of locations
        locations = result.body['locations']
        for location in locations:
            if((location['status']) == 'ACTIVE'):
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
                locationName = locationName.lower()
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
    return(locationsPaths)


def findMenu(estNameStr, location):
    tzGl = {}
    locationsPaths = {}
    getSquare(estNameStr, tzGl, locationsPaths)
    print(tzGl)
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


def getDispNameEst(estNameStr):
    dispnameEst = db.reference(
        '/billing/' + estNameStr + '/dispname').get()
    return str(dispnameEst)


def getDispNameLoc(estNameStr, location):
    dispnameEst = db.reference(
        '/restaurants/' + estNameStr + '/'+location + '/dispname').get()
    return str(dispnameEst)


def updateEst(estNameStr, new):
    nameRef = db.reference('/billing/' + estNameStr)
    nameRef.update({"dispname": new})
    print("updated")
    return


def updateLoc(estNameStr, location, new):
    nameRef = db.reference('/restaurants/' + estNameStr + '/' + location)
    nameRef.update({"dispname": new})
    return


def addEst(estNameStr, dispname):
    dispnameEst = db.reference('/billing/' + estNameStr)
    dispnameEst.update({
        "dispname": dispname
    })
    print("added")
    with open('data.txt', 'w') as outfile:
        json.dump(info, outfile)
    return


def addLoc(estNameStr, location, dispname):
    dispnameEst = db.reference(
        '/billing/' + estNameStr + '/dispname').get()
    restaurants.update({
        estNameStr: {
            "dispname": dispnameEst
        }
    })
    print("added")
    return
