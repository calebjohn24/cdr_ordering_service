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
from Cedar.admin import admin_panel, menu, pw_reset, feedback, schedule
from Cedar.kiosk import online_menu, payments, qsr_menu, sd_menu
from Cedar.main_page import find_page

infoFile = open("info.json")
info = json.load(infoFile)
botNumber = info["number"]
mainLink = info['mainLink']
adminSessTime = 3599
client = plivo.RestClient(auth_id='MAYTVHN2E1ZDY4ZDA2YZ', auth_token='ODgzZDA1OTFiMjE2ZTRjY2U4ZTVhYzNiODNjNDll')
cred = credentials.Certificate('CedarChatbot-b443efe11b73.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://cedarchatbot.firebaseio.com/',
    'storageBucket': 'cedarchatbot.appspot.com'
})
storage_client = storage.Client.from_service_account_json('CedarChatbot-b443efe11b73.json')
bucket = storage_client.get_bucket("cedarchatbot.appspot.com")
sender = 'cedarrestaurantsbot@gmail.com'
emailPass = "cda33d07-f6bd-479e-806f-5d039ae2fa2d"
smtpObj = smtplib.SMTP_SSL("smtp.gmail.com", 465)
smtpObj.login(sender, emailPass)

dayNames = ["MON", "TUE", "WED", "THURS", "FRI", "SAT", "SUN"]
global locationsPaths
locationsPaths = {}

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
sslify = SSLify(app)
scKey = uuid.uuid4()
app.secret_key = scKey


locationsPaths = {}
tzGl = []


# Call the success method to see if the call succeeded
##########Restaurant END END###########


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



def sendCheckmate(estNameStr,location,token):
    print('order sent to checkmate')





##########CUSTOMER END###########


###Kiosk###



##########Employee###########
@app.route('/<estNameStr>/<location>/qsr-employee-login')
def EmployeeLoginQSR(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    return(render_template("POS/StaffQSR/login.html"))

@app.route('/<estNameStr>/<location>/qsr-employee-login2')
def EmployeeLogin2QSR(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    return(render_template("POS/StaffSitdown/login2.html"))

@app.route('/<estNameStr>/<location>/qsr-employee-login', methods=['POST'])
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
        return(redirect(url_for("EmployeePanelQSR",estNameStr=estNameStr,location=location)))
    else:
        return(redirect(url_for("EmployeeLogin2",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/qsr-view')
def EmployeePanelQSR(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    token = session.get('token',None)
    loginRef = db.reference('/restaurants/' + estNameStr + '/' + location + "/employee/")
    loginData = dict(loginRef.get())
    try:
        if(((token == loginData["token"]) and (time.time() - loginData["time"] <= 3600))):
            pass
        else:
            return(redirect(url_for("EmployeeLoginQSR",estNameStr=estNameStr,location=location)))
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
    return(render_template("POS/StaffQSR/View.html", location=location.capitalize(), restName=str(estNameStr.capitalize()), menu=menu, activeItems=activeItems, inactiveItems=inactiveItems, orders=ordsGet))


@app.route('/<estNameStr>/<location>/qsr-activate-item~<cat>~<item>~<menu>')
def activateItemQSR(estNameStr,location,cat,item,menu):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories/"+ cat + "/" + item
    descrip = dict(db.reference(pathMenu).get())["tmp"]
    db.reference(pathMenu).update({"descrip":descrip})
    pathDel = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories/"+ cat + "/" + item +"/tmp"
    db.reference(pathDel).delete()
    return(redirect(url_for("EmployeePanelQSR",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/qsr-deactivate-item~<cat>~<item>~<menu>')
def deactivateItemQSR(estNameStr,location,cat,item,menu):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories/"+ cat + "/" + item
    descrip = dict(db.reference(pathMenu).get())["descrip"]
    db.reference(pathMenu).update({"tmp":descrip})
    db.reference(pathMenu).update({"descrip":"INACTIVE"})
    return(redirect(url_for("EmployeePanelQSR",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/qsr-view-success', methods=["POST"])
def EmployeeSuccessQSR(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    reqToken = rsp["req"]
    pathRequest = '/restaurants/' + estNameStr + '/' + location + "/orderQSR/" + reqToken
    reqRef = db.reference(pathRequest)
    reqRef.delete()
    return(redirect(url_for("EmployeePanelQSR",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/qsr-sendOrder', methods=["POST"])
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
        getSquare(estNameStr)
        now = datetime.datetime.now(tzGl[location])
        write_str = "Your Order From "+ estNameStr.capitalize()  + " " + location.capitalize() + " @"
        write_str += str(now.hour) + ":" + str(now.minute) + " on " + str(now.month) + "-" + str(now.day) + "-" + str(now.year)
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
        sendEmail(sender, order['email'], mesg)
    return(redirect(url_for("EmployeePanelQSR",estNameStr=estNameStr,location=location)))


@app.route('/<estNameStr>/<location>/employee-login')
def EmployeeLogin(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    return(render_template("POS/StaffSitdown/login.html"))

@app.route('/<estNameStr>/<location>/employee-login2')
def EmployeeLogin2(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    return(render_template("POS/StaffSitdown/login2.html"))

@app.route('/<estNameStr>/<location>/employee-login', methods=['POST'])
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
        return(redirect(url_for("EmployeePanel",estNameStr=estNameStr,location=location)))
    else:
        return(redirect(url_for("EmployeeLogin2",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/view')
def EmployeePanel(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    token = session.get('token',None)
    loginRef = db.reference('/restaurants/' + estNameStr + '/' + location + "/employee/")
    loginData = dict(loginRef.get())
    try:
        if(((token == loginData["token"]) and (time.time() - loginData["time"] <= 3600))):
            pass
        else:
            return(redirect(url_for("EmployeeLogin",estNameStr=estNameStr,location=location)))
    except Exception as e:
        return(redirect(url_for("EmployeeLogin2",estNameStr=estNameStr,location=location)))
    try:
        ordPath = '/restaurants/' + estNameStr + '/' + location + "/orders/"
        ordsRef = db.reference(ordPath)
        ordsGet = dict(ordsRef.get())
        tokens = list(ordsGet)
        for tt in tokens:
            if(int(ordsGet[tt]["QSR"]) == 0):
                print(ordsGet[tt])
                del ordsGet[tt]
    except Exception as e:
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


@app.route('/<estNameStr>/<location>/activate-item~<cat>~<item>~<menu>')
def activateItem(estNameStr,location,cat,item,menu):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories/"+ cat + "/" + item
    descrip = dict(db.reference(pathMenu).get())["tmp"]
    db.reference(pathMenu).update({"descrip":descrip})
    pathDel = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories/"+ cat + "/" + item +"/tmp"
    db.reference(pathDel).delete()
    return(redirect(url_for("EmployeePanel",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/deactivate-item~<cat>~<item>~<menu>')
def deactivateItem(estNameStr,location,cat,item,menu):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories/"+ cat + "/" + item
    descrip = dict(db.reference(pathMenu).get())["descrip"]
    db.reference(pathMenu).update({"tmp":descrip})
    db.reference(pathMenu).update({"descrip":"INACTIVE"})
    return(redirect(url_for("EmployeePanel",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/view-success', methods=["POST"])
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
    return(redirect(url_for("EmployeePanel",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/view-warning', methods=["POST"])
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
    return(redirect(url_for("EmployeePanel",estNameStr=estNameStr,location=location)))


@app.route('/<estNameStr>/<location>/view-reject', methods=["POST"])
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
    AlertSend = db.reference(pathUser).update({"alert":str("Request Cancelled: "+alert)})
    AlertTime = db.reference(pathUser).update({"alertTime":time.time()})
    reqRef.delete()
    return(redirect(url_for("EmployeePanel",estNameStr=estNameStr,location=location)))


@app.route('/<estNameStr>/<location>/view-editBill', methods=["POST"])
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
    return(redirect(url_for("EmployeePanel",estNameStr=estNameStr,location=location)))


@app.route('/<estNameStr>/<location>/view-clearTicket', methods=["POST"])
def RemBill(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    orderToken = rsp["req"]
    pathUserX = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
    remRef = db.reference(pathUserX)
    remRef.delete()
    return(redirect(url_for("EmployeePanel",estNameStr=estNameStr,location=location)))

####SQUARE####

@app.route('/<estNameStr>/<locationX>/reader/<type>', methods=["POST"])
def GenReaderCode(estNameStr,locationX,type):
    rsp = request.get_json()
    print(rsp)
    code = rsp['code']
    kioskType = ["qsr-startKiosk","sitdown-startKiosk"]
    sqRef = db.reference(str('/restaurants/' + estNameStr))
    squareToken = dict(sqRef.get())["sq-token"]
    loginRef = db.reference('/restaurants/' + estNameStr + '/' + str(locationX) + "/employee")
    loginData = dict(loginRef.get())
    hashCheck = pbkdf2_sha256.verify(code, loginData['code'])
    if(hashCheck == True):
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
                            packet = {
                                "code":code,
                                "link": str(mainLink + locationX + "/" + kioskType[int(type)])
                            }
                            return jsonify(packet)
                        elif result.is_error():
                            packet = {
                                "code":"invlaid location"
                            }
                            return jsonify(packet)
    else:
        packet = {
            "code":"invlaid employee code"
        }
        return jsonify(packet)








if __name__ == '__main__':
    try:
        ##print(locationsPaths.keys())
        app.secret_key = scKey
        sslify = SSLify(app)
        app.config['SESSION_TYPE'] = 'filesystem'
        sess = Session()
        sess.init_app(app)
        app.permanent_session_lifetime = datetime.timedelta(minutes=240)
        app.debug = True
        app.run(host="0.0.0.0",port=5000)
    except KeyboardInterrupt:
        sys.exit()
