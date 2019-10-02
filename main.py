import calendar
import datetime
import json
import random
import smtplib
import time
import uuid
import requests
import pandas as pd
import plivo
import pygsheets
import pyrebase
import pytz
from square.client import Client
import dateparser
from flask import Flask, request, session
from flask import redirect, url_for
from flask import render_template
from flask_session import Session
from flask_sslify import SSLify
from fpdf import FPDF
from werkzeug.datastructures import ImmutableOrderedMultiDict
from firebase import firebase
import sys
dbid = "d1ab1a95-ddb5-4ee4-83db-9179d37f8e78"
infoFile = open("info.json")
info = json.load(infoFile)
uid = info['uid']
gc = pygsheets.authorize(service_file='static/CedarChatbot-70ec2d781527.json')
email = "cedarchatbot@appspot.gserviceaccount.com"
estName = info['uid']
estNameStr = info['name']
botNumber = info["number"]
gsheetsLink = info["gsheets"]
adminSessTime = 3599
client = plivo.RestClient(auth_id='MAYTVHN2E1ZDY4ZDA2YZ', auth_token='ODgzZDA1OTFiMjE2ZTRjY2U4ZTVhYzNiODNjNDll')
mainLink = ""
authentication = firebase.FirebaseAuthentication('if7swrlQM4k9cBvm0dmWqO3QsI5zjbcdbstSgq1W', 'cajohn0205@gmail.com',
                                                 extra={'id': dbid})

database = firebase.FirebaseApplication("https://cedarchatbot.firebaseio.com/", authentication=authentication)
data = (database.get("restaurants/" + uid, "/"))
squareToken = database.get("/tokens/",estNameStr.upper())
items = []
config = {
    "apiKey": "AIzaSyB2it4zPzPdn_bW9OAglTHUtclidAw307o",
    "authDomain": "cedarchatbot.firebaseapp.com",
    "databaseURL": "https://cedarchatbot.firebaseio.com",
    "storageBucket": "cedarchatbot.appspot.com",
}
pyreBase= pyrebase.initialize_app(config)
auth = pyreBase.auth()
storage = pyreBase.storage()
promoPass = "promo-" + str(estName)
addPass = "add-" + str(estName)
remPass = "remove-" + str(estName)
sh = gc.open('TestRaunt')
webLink = "sms:+" + botNumber + "?body=order"
sender = 'receipts@cedarrobots.com'
emailPass = "Cedar2421!"
smtpObj = smtplib.SMTP_SSL("smtp.zoho.com", 465)
smtpObj.login(sender, emailPass)
squareClient = Client(
    access_token=squareToken,
    environment='production',
)
dayNames = ["MON","TUE","WED","THURS","FRI","SAT","SUN"]
global locationsPaths
locationsPaths = {}
app = Flask(__name__)
sslify = SSLify(app)
app.secret_key = 'fe71b83d-9f64-46c2-b083-3a9d29d02f5d'

api_locations = squareClient.locations
mobile_authorization_api = squareClient.mobile_authorization
result = api_locations.list_locations()
locationsPaths = {}
# Call the success method to see if the call succeeded
def getSquare():
    if result.is_success():
    	# The body property is a list of locations
        locations = result.body['locations']
    	# Iterate over the list
        for location in locations:
            if((dict(location.items())["status"]) == "ACTIVE"):
                # print((dict(location.items())))
                addrNumber = ""
                street = ""
                for ltrAddr in range(len(dict(location.items())["address"]['address_line_1'])):
                    currentLtr = dict(location.items())["address"]['address_line_1'][ltrAddr]
                    try:
                        int(currentLtr)
                        addrNumber += currentLtr
                    except Exception as e:
                        street = dict(location.items())["address"]['address_line_1'][ltrAddr+1:len(dict(location.items())["address"]['address_line_1'])]
                        break

                addrP = str(addrNumber+ ","+ street+","+dict(location.items())["address"]['locality'] + "," + dict(location.items())["address"]['administrative_district_level_1'] + "," + dict(location.items())["address"]['postal_code'][:5])
                timez = dict(location.items())["timezone"]
                tz = pytz.timezone(timez)
                locationName = (dict(location.items())["name"]).replace(" ","-")
                locationId = dict(location.items())["id"]
                numb = dict(location.items())['phone_number']
                numb = numb.replace("-","")
                numb = numb.replace(" ","")
                numb = numb.replace("+","")
                locationsPaths.update(
                     {locationName:{
                    "id":locationId,"OCtimes":dict(location.items())["business_hours"]["periods"],
                    "sqEmail": dict(location.items())['business_email'],
                    "sqNumber": numb,"name":locationName}} )


def checkLocation(location,custFlag):
    try:
        locationsPaths[location]
        return [0,0]
    except Exception as e:
        if(custFlag == 0):
            return [1,"pickLocation"]
        elif(custFlag == 1):
            return [1,"MobileStart"]
        elif(custFlag == 1):
            return [1, "EmployeeLocation"]

def checkAdminToken(location):
    if((idToken == database.get("restaurants/" + uid+"/"+location+"/", "LoginToken")) and (time.time() - database.get("restaurants/" + uid+"/"+location+"/", "LoginTime") < adminSessTime)):
        return 0
    else:
        return 1


def getReply(msg, number):
    authentication = firebase.FirebaseAuthentication('if7swrlQM4k9cBvm0dmWqO3QsI5zjbcdbstSgq1W',
                                                     'cajohn0205@gmail.com', extra={'id': dbid})
    database = firebase.FirebaseApplication("https://cedarchatbot.firebaseio.com/", authentication=authentication)
    SMSTimes = database.get("restaurants/" + uid + "/", "SMSTime")
    closeTimeHr = int(SMSTimes["end"][0:2])
    closeTimeMin = int(SMSTimes["end"][3:5])
    openTimeHr = int(SMSTimes["start"][0:2])
    openTimeMin = int(SMSTimes["start"][3:5])
    closeCheck = float(closeTimeHr) + float(closeTimeMin/100.0)
    openCheck = float(openTimeHr) + float(openTimeMin/100.0)
    currentHour = float(datetime.datetime.now(tz).strftime("%H"))
    currentMin = float(datetime.datetime.now(tz).strftime("%M"))/100.0
    currentTime = currentHour + currentMin
    if(openCheck <= currentTime <= closeCheck):
        msg = msg.lower()
        msg.replace("\n", "")
        msg.replace(".", "")
        msg.replace(" ", "")
        msg = ''.join(msg.split())

        if (msg == "order" or msg == "ordew" or msg == "ord" or msg == "ordet" or msg == "oderr" or msg == "ordee" or (
                "ord" in msg)):
            reply = "Hi welcome to "+estNameStr+"! click the link below to order \n" + str(mainLink)+"/smsinit/"+str(number)
            return reply
        else:
            return ("no msg")
    else:
        return ("no msg")


@app.route('/<location>/admin',methods=["POST","GET"])
def login(location):
    if(checkLocation(location,0)[0] == 1):
        return(redirect(url_for(checkLocation(location,0)[1])))
    return render_template("login.html", btn=str("admin2"), restName=estNameStr)


@app.route('/<location>/admin2', methods=["POST"])
def loginPageCheck(location):
    if(checkLocation(location,0)[0] == 1):
        return(redirect(url_for(checkLocation(location,0)[1])))
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    email = str(rsp["email"])
    pw = str(rsp["pw"])
    try:
        user = auth.sign_in_with_email_and_password(str(rsp["email"]), pw)
        # print(user['localId'])
        authentication = firebase.FirebaseAuthentication('if7swrlQM4k9cBvm0dmWqO3QsI5zjbcdbstSgq1W',
                                                         'cajohn0205@gmail.com', extra={'id': dbid})
        fireapp = firebase.FirebaseApplication('https://cedarchatbot.firebaseio.com/', authentication=authentication)
        testDB = (fireapp.get("/restaurants/", user["localId"]))
        if (str(user["localId"]) == str(uid) and testDB != None):
            print("found")
            database = firebase.FirebaseApplication("https://cedarchatbot.firebaseio.com/",
                                                    authentication=authentication)

            LoginToken = str((uuid.uuid4())) +"-"+str((uuid.uuid4()))
            database.put("/restaurants/" + estName + "/"+location+"/", "LoginToken",LoginToken)
            database.put("/restaurants/" + estName + "/"+location+"/", "LoginTime",time.time())
            session['fbToken'] = user['idToken']
            session['token'] = LoginToken
            return redirect(url_for('.panel', location=location))
        else:
            authentication = firebase.FirebaseAuthentication('if7swrlQM4k9cBvm0dmWqO3QsI5zjbcdbstSgq1W',
                                                             'cajohn0205@gmail.com', extra={'id': dbid})
            print("incorrect password")
            database = firebase.FirebaseApplication("https://cedarchatbot.firebaseio.com/",
                                                    authentication=authentication)
            return render_template("login2.html", btn=str(estNameStr), restName=estNameStr)
    except Exception:
        print("exec")
        authentication = firebase.FirebaseAuthentication('if7swrlQM4k9cBvm0dmWqO3QsI5zjbcdbstSgq1W',
                                                         'cajohn0205@gmail.com', extra={'id': dbid})
        database = firebase.FirebaseApplication("https://cedarchatbot.firebaseio.com/",
                                                authentication=authentication)
        return render_template("login2.html", btn=str("admin"), restName=estNameStr)


@app.route('/<location>/adminpanel', methods=["GET"])
def panel(location):
    idToken = session.get('token', None)
    fbToken = session.get('fbToken', None)
    authentication = firebase.FirebaseAuthentication('if7swrlQM4k9cBvm0dmWqO3QsI5zjbcdbstSgq1W',
                                                     'cajohn0205@gmail.com', extra={'id': dbid})
    database = firebase.FirebaseApplication("https://cedarchatbot.firebaseio.com/",
                                            authentication=authentication)
    if((idToken == database.get("restaurants/" + uid+"/"+location+"/", "LoginToken")) and (time.time() - database.get("restaurants/" + uid+"/"+location+"/", "LoginTime") < adminSessTime)):
        return render_template("panel.html",
                               gcard=location+"/giftcard",
                               addCpn=location+"/addCoupon",
                               remCpn=location+"/removeCoupon",
                               editMenu=location+"/editMenu",
                               createMenu=location+"/createMenu",
                               importMenu=location+"/importMenu",
                               outStck=location+"/changestock",
                               promo=location+"/promoSuite",
                               spreadSheet=gsheetsLink)
    else:
        return redirect(url_for('.login', location=location))


@app.route('/<location>/createMenu', methods=["POST"])
def meun1(location):
    idToken = session.get('token', None)
    fbToken = session.get('fbToken', None)
    authentication = firebase.FirebaseAuthentication('if7swrlQM4k9cBvm0dmWqO3QsI5zjbcdbstSgq1W',
                                                     'cajohn0205@gmail.com', extra={'id': dbid})
    database = firebase.FirebaseApplication("https://cedarchatbot.firebaseio.com/",
                                            authentication=authentication)
    if((idToken == database.get("restaurants/" + uid+"/"+location+"/", "LoginToken")) and (time.time() - database.get("restaurants/" + uid+"/"+location+"/", "LoginTime") < adminSessTime)):
        return render_template("createMenu1.html",
                               next=location+"/createMenu2",
                               back=location+"/adminpanel")
    else:
        return redirect(url_for('.login', location=location))

@app.route('/<location>/createMenu', methods=["POST"])
def createMenu(location):
    idToken = session.get('token', None)
    fbToken = session.get('fbToken', None)
    authentication = firebase.FirebaseAuthentication('if7swrlQM4k9cBvm0dmWqO3QsI5zjbcdbstSgq1W',
                                                     'cajohn0205@gmail.com', extra={'id': dbid})
    database = firebase.FirebaseApplication("https://cedarchatbot.firebaseio.com/",
                                            authentication=authentication)
    if(checkAdminToken(location) == 1):
        return redirect(url_for('.login', location=location))
    return render_template("createMenu1.html",
                           next=location+"/createMenu2",
                           back=location+"/adminpanel")

@app.route('/<location>/createMenu2', methods=["POST"])
def createMenu2(location):
    idToken = session.get('token', None)
    fbToken = session.get('fbToken', None)
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    menuName = rsp["Name"]
    menuDays = rsp["Days"]
    authentication = firebase.FirebaseAuthentication('if7swrlQM4k9cBvm0dmWqO3QsI5zjbcdbstSgq1W',
                                                     'cajohn0205@gmail.com', extra={'id': dbid})
    database = firebase.FirebaseApplication("https://cedarchatbot.firebaseio.com/",
                                            authentication=authentication)
    if(checkAdminToken(location) == 1):
        return redirect(url_for('.login', location=location))
    return render_template("createMenu1.html",
                           next=location+"/createMenu3",
                           back=location+"/adminpanel")







@app.route('/admin', methods=["GET"])
def pickLocation():
    authentication = firebase.FirebaseAuthentication('if7swrlQM4k9cBvm0dmWqO3QsI5zjbcdbstSgq1W',
                                                     'cajohn0205@gmail.com', extra={'id': dbid})
    database = firebase.FirebaseApplication("https://cedarchatbot.firebaseio.com/",
                                            authentication=authentication)
    getSquare()
    locs = []
    for lc in locationsPaths:
        locs.append(locationsPaths[lc]["name"])
    return (render_template("pickLocation.html", btn="uid", locs=locs,len=len(locs)))

@app.route('/uid', methods=["POST"])
def pickLocation2():
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    locationPick = rsp["location"]
    authentication = firebase.FirebaseAuthentication('if7swrlQM4k9cBvm0dmWqO3QsI5zjbcdbstSgq1W',
                                                     'cajohn0205@gmail.com', extra={'id': dbid})
    database = firebase.FirebaseApplication("https://cedarchatbot.firebaseio.com/",
                                            authentication=authentication)
    return redirect(url_for('.login', location=locationPick))

@app.route('/sms')
def inbound_sms():
    # Sender's phone number
    from_number = request.values.get('From')
    # Receiver's phone number - Plivo number
    to_number = request.values.get('To')
    # The text which was received
    text = request.values.get('Text')
    print('Message received - From: %s, To: %s, Text: %s' % (from_number, to_number, text))
    resp = getReply(text, from_number)
    print(str(resp))
    if (resp != "no msg"):
        client.messages.create(
            src=botNumber,
            dst=from_number,
            text=resp
        )
    return '200'


if __name__ == '__main__':
    try:
        getSquare()
        print(locationsPaths)
        app.secret_key = 'fe71b83d-9f64-46c2-b083-3a9d29d02f5d'
        sslify = SSLify(app)
        app.config['SESSION_TYPE'] = 'filesystem'
        sess = Session()
        sess.init_app(app)
        app.permanent_session_lifetime = datetime.timedelta(minutes=200)
        #app.debug = True
        app.run(host="0.0.0.0", port=8888)
    except KeyboardInterrupt:
        sys.exit()
