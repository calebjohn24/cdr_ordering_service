import datetime
import json
import smtplib
import sys
import time
import uuid
import plivo
import pygsheets
import os
import firebase_admin
from passlib.hash import pbkdf2_sha256
from firebase_admin import credentials
from firebase_admin import db
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

infoFile = open("info.json")
info = json.load(infoFile)
uid = info['uid']
#gc = pygsheets.authorize(service_file='static/CedarChatbot-70ec2d781527.json')
email = "cedarchatbot@appspot.gserviceaccount.com"
estName = info['uid']
estNameStr = str(info['name'])
botNumber = info["number"]
gsheetsLink = info["gsheets"]
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

sqRef = db.reference(str('/restaurants/' + estNameStr))
##print(sqRef.get())
squareToken = sqRef.get()["sq-token"]
promoPass = "promo-" + str(estName)
addPass = "add-" + str(estName)
remPass = "remove-" + str(estName)
#sh = gc.open('TestRaunt')
webLink = "sms:+" + botNumber + "?body=order"
sender = 'receipts@cedarrobots.com'
emailPass = "Cedar2421!"
smtpObj = smtplib.SMTP_SSL("smtp.zoho.com", 465)
smtpObj.login(sender, emailPass)
squareClient = Client(
    access_token=squareToken,
    environment='production',
)
dayNames = ["MON", "TUE", "WED", "THURS", "FRI", "SAT", "SUN"]
global locationsPaths
locationsPaths = {}
UPLOAD_FOLDER = estNameStr+"/imgs/"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app = Flask(__name__)
sslify = SSLify(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
scKey = uuid.uuid4()
app.secret_key = scKey

api_locations = squareClient.locations
mobile_authorization_api = squareClient.mobile_authorization
result = api_locations.list_locations()
locationsPaths = {}
tzGl = []


# Call the success method to see if the call succeeded
##########Restaurant END END###########
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def getSquare():
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
                tzGl.append(pytz.timezone(timez))
                locationName = (dict(location.items())["name"]).replace(" ", "-")
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


def checkLocation(location, custFlag):
    try:
        locationsPaths[location]
        return [0,0]
    except Exception as e:
        if (custFlag == 0):
            return [1, "pickLocation"]
        elif (custFlag == 1):
            return [1, "MobileStart"]
        elif (custFlag == 1):
            return [1, "EmployeeLocation"]


def checkAdminToken(idToken, username):
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.get()[str(username)]
    if ((idToken == user_ref["token"]) and (time.time() - user_ref["time"] < adminSessTime)):
        return 0
    else:
        return 1





@app.route('/<location>/admin-login', methods=["GET"])
def login(location):
    return render_template("POS/AdminMini/login.html", btn=str("admin"), restName=estNameStr,locName=location)

@app.route('/<location>/forgot-password', methods=["GET"])
def pwReset():
    return render_template("POS/AdminMini/forgot-password.html", btn=str("admin"), restName=estNameStr)

@app.route('/<location>/admin', methods=["POST"])
def loginPageCheck(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    email = str(rsp["emailAddr"])
    pw = str(rsp["pw"])
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    email = str(email).replace(".","-")
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
            return redirect(url_for('panel',location=location))
        else:
            return render_template("POS/AdminMini/login2.html", btn=str("admin"), restName=estNameStr, locName=location)
    except Exception as e:
        ##print(e)
        return render_template("POS/AdminMini/login2.html", btn=str("admin"), restName=estNameStr, locName=location)


@app.route('/<location>/admin-panel', methods=["GET"])
def panel(location):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    getSquare()
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
                           locName=str(location).capitalize(),
                           discNames=discNames,discItms=discItms,
                           discTypes=discTypes,discMenu=discMenu,
                           discAmts=discAmts,discLimMin=discLimMin)

@app.route('/<location>/addAdmin', methods=["POST"])
def addAdmin(location):
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
            return redirect(url_for('panel',location=location))
    except Exception:
        return redirect(url_for('panel',location=location))

@app.route('/<location>/confirmAdmin', methods=["POST"])
def confirmAdmin(location):
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
    return redirect(url_for('panel',location=location))

@app.route('/<location>/editEmployee', methods=["POST"])
def editEmployee(location):
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
            return redirect(url_for('panel',location=location))
    except Exception:
        return redirect(url_for('panel',location=location))

@app.route('/<location>/confirmEmpCode', methods=["POST"])
def confirmEmployeeCode(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    email = session.get('user', None)
    code = rsp["code"]
    hash = pbkdf2_sha256.hash(code)
    ref = db.reference('/restaurants/' + estNameStr + '/' + str(location) + '/employee')
    ref.update({
        'code': hash
    })
    return redirect(url_for('panel',location=location))

@app.route('/<location>/remUser~<user>')
def remUser(location,user):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    if(username != user):
        rem_ref = db.reference('/restaurants/' + estNameStr + '/admin-info/' + user)
        rem_ref.delete()
    return redirect(url_for('panel',location=location))

@app.route('/<location>/schedule-<day>', methods=["GET"])
def scheduleSet(location,day):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
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

@app.route('/<location>/remTs~<day>~<menu>')
def remTimeSlot(location,day,menu):
    menu = str(menu).replace("-"," ")
    menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/schedule/'+str(day)+"/"+str(menu))
    menu_ref.delete()
    return(redirect(url_for("scheduleSet",location=location,day=day)))

@app.route('/<location>/schedMenu~<day>~<menu>~<timeVal>', methods=["POST"])
def editTimeSlot(location,day,menu,timeVal):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    new_menu = str(rsp["menu"])
    del_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/schedule/'+str(day)+"/"+menu)
    del_ref.delete()
    menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/schedule/'+str(day))
    menu_ref.update({new_menu:float(timeVal)})
    return(redirect(url_for("scheduleSet",location=location,day=day)))

@app.route('/<location>/editMenuTime~<day>~<menu>', methods=["POST"])
def editMenuSlot(location,day,menu):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    hour = float(rsp["hour"])
    minute = (float(rsp["minute"])/100)
    newTime = hour+minute
    menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/schedule/'+str(day))
    menu_ref.update({menu:newTime})
    return(redirect(url_for("scheduleSet",location=location,day=day)))

@app.route('/<location>/addTs~<day>', methods=["POST"])
def addTimeSlot(location,day):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    hour = float(rsp["hour"])
    minute = (float(rsp["minute"])/100)
    menu = str(rsp["menu"])
    newTime = hour+minute
    menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/schedule/'+str(day))
    menu_ref.update({menu:newTime})
    return(redirect(url_for("scheduleSet",location=location,day=day)))

@app.route('/<location>/create-menu', methods=["GET"])
def createMenu(location):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    return(render_template("POS/AdminMini/createMenu.html"))

@app.route('/<location>/add-menu', methods=["POST"])
def addMenu(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = dict((request.form))
    new_menu = rsp["name"]
    menu_ref = db.reference('/restaurants/' + estNameStr + '/'+location+"/menu")
    menu_ref.update({str(new_menu):{"active":False}})
    return(redirect(url_for("viewMenu",location=location)))

@app.route('/<location>/view-menu')
def viewMenu(location):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu')
    menu_keys = list((menu_ref.get()).keys())
    return(render_template("POS/AdminMini/dispMenu.html",menus=menu_keys))

@app.route('/<location>/edit-menu-<menu>')
def editMenu(location,menu):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    menu_data = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)).get()
    try:
        cats = list(dict(menu_data["categories"]).keys())
    except Exception as e:
        cats = []
    return(render_template("POS/AdminMini/menuDetails.html",cats=cats,menu=menu))


@app.route('/<location>/rem-cat-<menu>~<category>')
def remCategories(location,menu,category):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    menu_data = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories/"+category).delete()
    # return(render_template("POS/AdminMini/catDetails.html",items=items,menu=menu,cat=category))
    return(redirect(url_for("viewMenu",location=location)))

@app.route('/<location>/view-cat-<menu>~<category>')
def viewCategories(location,menu,category):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    menu_data = dict(db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)).get())
    items = []
    try:
        for itx in list(dict(menu_data["categories"][category]).keys()):
            itx2 = str(itx).replace(" ","-")
            items.append(itx2)
        return(render_template("POS/AdminMini/catDetails.html",items=items,menu=menu,cat=category))
    except Exception as e:
        return(redirect(url_for("viewMenu",location=location)))

@app.route('/<location>/remOpt~<menu>~<cat>~<item>~<mods>~<opt>')
def remOpt(location,menu,cat,item,mods,opt):
    opt_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories/"+cat+"/"+item+"/"+mods+"/info/"+opt)
    opt_ref.delete()
    return(redirect(url_for("viewItem",location=location,menu=menu,cat=cat,item=item)))

@app.route('/<location>/addOpt~<menu>~<cat>~<item>~<mods>')
def addOpt(location,menu,cat,item,mods):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    return(render_template("POS/AdminMini/addOpt.html",menu=menu,cat=cat,item=item,mods=mods))


@app.route('/<location>/addOptX~<menu>~<cat>~<item>~<mods>', methods=["POST"])
def addOptX(location,menu,cat,item,mods):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    name = str(rsp["name"])
    price = float(rsp["price"])
    opt_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories/"+cat+"/"+item+"/"+mods+"/info")
    opt_ref.update({name:price})
    return(redirect(url_for("viewItem",location=location,menu=menu,cat=cat,item=item)))

@app.route('/<location>/editMax~<menu>~<cat>~<item>~<mods>', methods=["POST"])
def editMax(location,menu,cat,item,mods):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    max = int(rsp["max"])
    opt_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories/"+cat+"/"+item+"/"+mods)
    opt_ref.update({"max":max})
    return(redirect(url_for("viewItem",location=location,menu=menu,cat=cat,item=item)))

@app.route('/<location>/editMin~<menu>~<cat>~<item>~<mods>', methods=["POST"])
def editMin(location,menu,cat,item,mods):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    min = int(rsp["min"])
    opt_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories/"+cat+"/"+str(item)+"/"+str(mods))
    opt_ref.update({"min":min})
    return(redirect(url_for("viewItem",location=location,menu=menu,cat=cat,item=item)))

@app.route('/<location>/editDescrip~<menu>~<cat>~<item>', methods=["POST"])
def editDescrip(location,menu,cat,item):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    descrip = str(rsp["descrip"])
    opt_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories/"+cat+"/"+str(item))
    opt_ref.update({"descrip":descrip})
    return(redirect(url_for("viewItem",location=location,menu=menu,cat=cat,item=item)))

@app.route('/<location>/editExtras~<menu>~<cat>~<item>', methods=["POST"])
def editExtra(location,menu,cat,item):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    extra = str(rsp["extra"])
    opt_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories/"+cat+"/"+str(item))
    opt_ref.update({"extra-info": extra})
    return(redirect(url_for("viewItem",location=location,menu=menu,cat=cat,item=item)))

@app.route('/<location>/editImg~<menu>~<cat>~<item>')
def editImg(location,menu,cat,item):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    return(render_template("POS/AdminMini/editImg.html",menu=menu,cat=cat,item=item))

@app.route('/<location>/addImgX~<menu>~<cat>~<item>', methods=["POST"])
def editImgX(location,menu,cat,item):
    file = request.files['img']
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    old_img_ref = dict(db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories/"+cat+"/"+str(item)).get())
    old_img = str(old_img_ref["img"]).split(str(estNameStr)+str("/"))
    imgUUID = str(estNameStr)+str("/")+str(old_img[1])
    bucket.delete_blob(imgUUID)
    upName = "/"+estNameStr+"/imgs/"+file.filename
    blob = bucket.blob(upName)
    fileId = str(uuid.uuid4())
    d = estNameStr + "/" + fileId
    d = bucket.blob(d)
    d.upload_from_filename(str(str(UPLOAD_FOLDER)+"/"+str(file.filename)),content_type='image/jpeg')
    url = str(d.public_url)
    opt_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories/"+cat+"/"+str(item))
    opt_ref.update({"img":url})
    os.remove(estNameStr + "/imgs/" + filename)
    return(redirect(url_for("viewItem",location=location,menu=menu,cat=cat,item=item)))

@app.route('/<location>/addCpn~<menu>~<category>~<item>~<modName>~<modItm>')
def addCpn(location,menu,category,item,modName,modItm):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    return render_template("POS/AdminMini/addCpn.html",menu=menu,cat=category,item=item,modName=modName,modItm=modItm)

@app.route('/<location>/addCpn2~<menu>~<category>~<item>~<modName>~<modItm>', methods=["POST"])
def addCpn2(location,menu,category,item,modName,modItm):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    type = rsp["type"]
    name = rsp["name"]
    amount = float(rsp["amount"])
    min = int(rsp["min"])
    limit = int(rsp["lim"])
    discRef = db.reference('/restaurants/' + estNameStr +'/'+location + '/discounts/'+ menu)
    discRef.update({
        str(name):{
        'cat': str(category),
        'itm':str(item),
        'mods':[modName,modItm],
        'type':str(type),
        'amt':amount,
        'lim':limit,
        'min':min
        }
    })
    # return str(rsp) +"-"+str(menu)+"-"+str(category)+"-"+str(item)
    return(redirect(url_for("panel",location=location)))


@app.route('/<location>/act-menu')
def chooseMenu(location):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu')
    menu_keys = list((menu_ref.get()).keys())
    menu_data = menu_ref.get()
    active = []
    inactive = []
    for keys in menu_keys:
        if(menu_data[keys]["active"] == True):
            active.append(keys)
        else:
            inactive.append(keys)
    return(render_template("POS/AdminMini/removeMenu.html",menusActive=active,menusInactive=inactive))



@app.route('/<location>/activate-menu-<menu>')
def enableMenu(location,menu):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu))
    menu_ref.update({"active":True})
    return(redirect(url_for("panel",location=location)))

@app.route('/<location>/deactivate-menu-<menu>')
def disableMenu(location,menu):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu))
    menu_ref.update({"active":False})
    return(redirect(url_for("panel",location=location)))

@app.route("/<location>/remitm~<menu>~<cat>~<item>")
def removeItem(location,menu,cat,item):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    item = str(item).replace("-"," ")
    # #print(item)
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    item_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories/"+str(cat)+"/"+str(item))
    item_ref.delete()
    return(redirect(url_for("viewCategories",location=location,menu=menu,category=cat)))

@app.route("/<location>/viewitm~<menu>~<cat>~<item>")
def viewItem(location,menu,cat,item):
    # #print(menu,cat,item)
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    item_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/"+str(cat)+"/"+str(item)).get()
    if(item_ref == None):
        item = str(item).replace("-"," ")
        # #print(item)
        item_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories/"+str(cat)+"/"+str(item)).get()
    descrip = item_ref["descrip"]
    extra_info = item_ref["extra-info"]
    img = item_ref["img"]
    mods = []
    for item_keys in list(item_ref.keys()):
        if(str(item_keys) != "descrip" and str(item_keys) != "extra-info" and str(item_keys) != "img" and str(item_keys) != "uuid"):
            tmp_arr = [item_keys, item_ref[item_keys]["max"],item_ref[item_keys]["min"]]
            tmp_arr2 = []
            for info_keys in list(dict(item_ref[item_keys]["info"]).keys()):
                tmp_arr2.append([info_keys,item_ref[item_keys]["info"][info_keys]])
            tmp_arr.append(tmp_arr2)
            mods.append(tmp_arr)
            tmp_arr = []
    # return(str(mods))
    return(render_template("POS/AdminMini/editItem.html",mods=mods,img=img,extra_info=extra_info,descrip=descrip,menu=menu,cat=cat,item=item))

@app.route("/<location>/addMod-<menu>~<cat>~<item>")
def addMod(location,menu,cat,item):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    return(render_template("POS/AdminMini/addMod2.html",location=location,menu=menu,cat=cat,item=item))

@app.route("/<location>/addModX2~<menu>~<cat>~<item>", methods=["POST"])
def addModX(location,menu,cat,item):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    # return(str(rsp))
    name = rsp["name"]
    # try:
    max = int(rsp["max"])
    min = int(rsp["min"])
    item_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories/"+str(cat)+"/"+str(item)+"/"+str(name))
    item_ref.update({"max":max,"min":min})
    mods = []
    prices = []
    rsp = dict((request.form))
    for keys in range((int((int(len(list(rsp.keys())))-3)/2))):
        prices.append(rsp[str("prce-")+str(keys+1)])
        mods.append(rsp[str("name-")+str(keys+1)])
    for m in range(len(mods)):
        item_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories/"+str(cat)+"/"+str(item)+"/"+str(name)+"/info")
        item_ref.update({str(mods[m]):float(prices[m])})
    '''
    except Exception:
        return(render_template("POS/AdminMini/addMod.html",location=location,menu=menu,cat=cat,item=name))
    '''
    return(redirect(url_for("viewItem",location=location,menu=menu,cat=cat,item=item)))

@app.route("/<location>/remMod~<menu>~<cat>~<item>~<mod>")
def remMod(location,menu,cat,item,mod):
    item_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories/"+str(cat)+"/"+str(item)+"/"+str(mod))
    item_ref.delete()
    return(redirect(url_for("viewItem",location=location,menu=menu,cat=cat,item=item)))

@app.route("/<location>/addItm~<menu>~<cat>")
def addItem(location,menu,cat):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    return(render_template("POS/AdminMini/addItm.html",location=location,menu=menu,cat=cat))

@app.route("/<location>/addItmX~<menu>~<cat>" , methods=["POST","GET"])
def addItem2(location,menu,cat):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    menu = rsp["menu"]
    name = rsp["name"]
    descrip = rsp["descrip"]
    exinfo = rsp["exinfo"]
    try:
        file = request.files['img']
        if file.filename == '':
            menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories/"+str(cat))
            menu_ref.update({str(name):{ "descrip":str(descrip), "extra-info":str(exinfo),"img":""}})
            return(render_template("POS/AdminMini/addMod.html",location=location,menu=menu,cat=cat,item=name))
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            upName = "/"+estNameStr+"/imgs/"+file.filename
            blob = bucket.blob(upName)
            fileId = str(uuid.uuid4())
            d = estNameStr + "/" + fileId
            d = bucket.blob(d)
            d.upload_from_filename(str(str(UPLOAD_FOLDER)+"/"+str(file.filename)),content_type='image/jpeg')
            url = str(d.public_url)
            menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories/"+str(cat))
            menu_ref.update({str(name):{ "descrip":str(descrip), "extra-info":str(exinfo),"img":url, "uuid":str("a"+str(random.randint(10000,99999)))}})
            os.remove(estNameStr + "/imgs/" + filename)
        else:
            menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories/"+str(cat))
            menu_ref.update({str(name):{ "descrip":str(descrip), "extra-info":str(exinfo),"img":"", "uuid":str("a"+str(random.randint(10000,99999)))}})
    except Exception:
        menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories/"+str(cat))
        menu_ref.update({str(name):{ "descrip":str(descrip), "extra-info":str(exinfo),"img":"", "uuid":str("a"+str("a"+str(random.randint(10000,99999))))}})
    return(render_template("POS/AdminMini/addMod.html",location=location,menu=menu,cat=cat,item=name))

@app.route("/<location>/addcat~<menu>")
def addCat(location,menu):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    return(render_template("POS/AdminMini/addCat.html",location=location,menu=menu))


@app.route("/<location>/addcatSubmit", methods=["POST","GET"])
def addCatX(location):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    cat = str(rsp["cat"]).replace(" ", "-")
    menu = rsp["menu"]
    name = rsp["name"]
    descrip = rsp["descrip"]
    exinfo = rsp["exinfo"]
    try:
        file = request.files['img']
        if file.filename == '':
            menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories")
            menu_ref.update({str(cat):{str(name):{ "descrip":str(descrip), "extra-info":str(exinfo),"img":""}}})
            return(render_template("POS/AdminMini/addMod.html",location=location,menu=menu,cat=cat,item=name))
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            upName = "/"+estNameStr+"/imgs/"+file.filename
            blob = bucket.blob(upName)
            fileId = str(uuid.uuid4())
            d = estNameStr + "/" + fileId
            d = bucket.blob(d)
            d.upload_from_filename(str(str(UPLOAD_FOLDER)+"/"+str(file.filename)),content_type='image/jpeg')
            url = str(d.public_url)
            menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories")
            menu_ref.update({str(cat):{str(name):{ "descrip":str(descrip), "extra-info":str(exinfo),"img":url, "uuid":str("a"+str(random.randint(10000,99999))) }}})
            os.remove(estNameStr + "/imgs/" + filename)
        else:
            menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories")
            menu_ref.update({str(cat):{str(name):{ "descrip":str(descrip), "extra-info":str(exinfo),"img":"", "uuid":str("a"+str(random.randint(10000,99999))) }}})
    except Exception:
        menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu/'+str(menu)+"/categories")
        menu_ref.update({str(cat):{str(name):{ "descrip":str(descrip), "extra-info":str(exinfo),"img":"", "uuid":str("a"+str(random.randint(10000,99999)))}}})
    return(render_template("POS/AdminMini/addMod.html",location=location,menu=menu,cat=cat,item=name))
    # return(redirect(url_for("viewItem",location=location,menu=menu,cat=cat,item=name)))

@app.route('/<location>/rem-new-comment~<comment>')
def remNewComment(location,comment):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    finally:
        if (checkAdminToken(idToken, username) == 1):
            return redirect(url_for('.login', location=location))
        item_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/comments/new/'+str(comment))
        item_ref.delete()
        return(redirect(url_for("panel",location=location)))

@app.route('/<location>/rem-saved-comment~<comment>')
def remSavedComment(location,comment):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    finally:
        if (checkAdminToken(idToken, username) == 1):
            return redirect(url_for('.login', location=location))
        item_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/comments/saved/'+str(comment))
        item_ref.delete()
        return(redirect(url_for("panel",location=location)))

@app.route('/<location>/save-comment~<comment>')
def saveComment(location,comment):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    finally:
        if (checkAdminToken(idToken, username) == 1):
            return redirect(url_for('.login', location=location))
        commRef = db.reference('/restaurants/' + estNameStr + '/' +location+ '/comments/new/'+str(comment))
        commentData = dict(commRef.get())
        commRef.delete()
        savedRef = db.reference('/restaurants/' + estNameStr + '/' +location+ '/comments/saved')
        savedRef.update({
            comment:commentData
        })
        return(redirect(url_for("panel",location=location)))

@app.route('/<location>/rem-feedback~<question>')
def remQuestion(location,question):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    finally:
        if (checkAdminToken(idToken, username) == 1):
            return redirect(url_for('.login', location=location))
        item_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/feedback/'+str(question))
        item_ref.delete()
        return(redirect(url_for("panel",location=location)))

@app.route('/<location>/add-feedback')
def addQuestion(location):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    finally:
        if (checkAdminToken(idToken, username) == 1):
            return redirect(url_for('.login', location=location))
        return(render_template("POS/AdminMini/addFeedback.html",location=location))

@app.route('/<location>/add-feedback-confirm', methods=['POST'])
def addQuestionConfirm(location):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    finally:
        if (checkAdminToken(idToken, username) == 1):
            return redirect(url_for('.login', location=location))

        request.parameter_storage_class = ImmutableOrderedMultiDict
        rsp = dict((request.form))
        print(rsp)
        qName = rsp['q-name']
        qId = str(uuid.uuid4()).replace("-","")
        qDict = {qId:
            {'ans':{},
             'info':{
                 "name":qName,
                 "maxScore":int(rsp['max']),
                 "day":{
                     "currday":int(datetime.datetime.now().weekday()),
                     "count":0,
                     "currentScore":0.0,
                     "totalScore":0
                 },
                 "week":{
                     "currweek":int(datetime.datetime.now().isocalendar()[1]),
                     "count":0,
                     "currentScore":0.0,
                     "totalScore":0
                 },
                 "month":{
                     "currmonth":int(datetime.datetime.now().month),
                     "count":0,
                     "currentScore":0.0,
                     "totalScore":0
                 }
             }
             }}
        del rsp['q-name']
        del rsp['max']
        for k in range(0,int(len(rsp)/2)):
            nameKey = 'name-' + str(k+1)
            scoreKey = 'prce-' + str(k+1)
            print(rsp[nameKey])
            ansKey = str(uuid.uuid4()).replace("-","")
            ansDict = {ansKey:{
                "name":rsp[nameKey],
                "score":int(rsp[scoreKey])
            }}
            qDict[qId]['ans'].update(ansDict)

        qRef = db.reference('/restaurants/' + estNameStr + '/' +location+ '/feedback')
        qRef.update(qDict)
        return(redirect(url_for("panel",location=location)))

##########CUSTOMER END###########


###Kiosk###

def findMenu(location):
    day = dayNames[int(datetime.datetime.now(tzGl[0]).weekday())]
    curMin = float(datetime.datetime.now(tzGl[0]).minute) / 100.0
    curHr = float(datetime.datetime.now(tzGl[0]).hour)
    curTime = curHr + curMin
    pathTime = '/restaurants/' + estNameStr + '/' + str(location) + "/schedule/" + day

    schedule = db.reference(pathTime).get()
    schedlist = list(schedule)
    start = 24
    sortedHr = [0]
    for scheds in schedlist:
        sortedHr.append(schedule[scheds])

    sortedHr.sort()
    sortedHr.append(24)
    for sh in range(len(sortedHr) - 1):
        if((sortedHr[sh]< curTime < sortedHr[sh+1])== True):
            menuKey = sh
            break

    for sh2 in range(len(schedlist)):
        if(sortedHr[menuKey] == schedule[schedlist[sh2]]):
            menu = (schedlist[sh2])
            return(str(menu))


@app.route('/<location>/sitdown-startKiosk', methods=["GET"])
def startKiosk2(location):
    return(render_template("Customer/Sitdown/startKiosk.html",btn="sitdown-startKiosk",restName=estNameStr,locName=location))

@app.route('/<location>/qsr-startKiosk', methods=["GET"])
def startKiosk4(location):
    return(render_template("Customer/QSR/startKiosk.html",btn="qsr-startKiosk",restName=estNameStr,locName=location))

@app.route('/<location>/order', methods=["GET"])
def startKiosk5(location):
    return(render_template("Customer/QSR/startKiosk.html",btn="startOnline",restName=estNameStr,locName=location))

@app.route('/<location>/startOnline', methods=["POST"])
def startOnline(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    phone = rsp["number"]
    name = rsp["name"]
    togo = rsp["togo"]
    table = ""
    session['table'] = ""
    session['name'] = name
    session['phone'] = phone
    path = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/"
    orderToken = str(uuid.uuid4())
    ref = db.reference(path)
    newOrd = ref.push({
        "togo":togo,
        "QSR":0,
        "cpn":1,
        "kiosk":1,
        "name":name,
        "phone":phone,
        "table":table,
        "alert":"null",
        "alertTime":0,
        "timestamp":time.time(),
        "subtotal":0.0
        })
    #print(newOrd.key)
    session['orderToken'] = newOrd.key
    menu = findMenu(location)
    # menu = "lunch"
    session["menu"] = menu
    ##print(menu)
    return(redirect(url_for('qsrMenu', location=location)))



@app.route('/<location>/qsr-startKiosk', methods=["POST"])
def startKioskQsr(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    phone = rsp["number"]
    name = rsp["name"]
    togo = rsp["togo"]
    print(togo)
    if(togo == "here"):
        table = rsp["table"]
        print(table)
    else:
        table = "togo"
    session['table'] = table
    session['name'] = name
    session['phone'] = phone
    path = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/"
    orderToken = str(uuid.uuid4())
    ref = db.reference(path)
    newOrd = ref.push({
        "togo":togo,
        "QSR":0,
        "cpn":1,
        "kiosk":0,
        "name":name,
        "phone":phone,
        "table":table,
        "alert":"null",
        "alertTime":0,
        "timestamp":time.time(),
        "subtotal":0.0
        })
    #print(newOrd.key)
    session['orderToken'] = newOrd.key
    menu = findMenu(location)
    # menu = "lunch"
    session["menu"] = menu
    ##print(menu)
    return(redirect(url_for('qsrMenu', location=location)))


@app.route('/<location>/sitdown-startKiosk', methods=["POST"])
def startKiosk(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    phone = rsp["number"]
    name = rsp["name"]
    table = rsp["table"]
    session['table'] = table
    session['name'] = name
    session['phone'] = phone
    path = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/"
    orderToken = str(uuid.uuid4())
    ref = db.reference(path)
    newOrd = ref.push({
        "QSR":1,
        "kiosk":0,
        "cpn":1,
        "name":name,
        "phone":phone,
        "table":table,
        "paid":"Not Paid",
        "alert":"null",
        "alertTime":0,
        "timestamp":time.time(),
        "subtotal":0.0
        })
    #print(newOrd.key)
    session['orderToken'] = newOrd.key
    menu = findMenu(location)
    # menu = "lunch"
    session["menu"] = menu
    return(redirect(url_for('sitdownMenu', location=location)))


@app.route('/<location>/testmenu')
def dummyMenuRender(location):
    menu = "breakfast"
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu + "/categories"
    menuInfo = dict(db.reference(pathMenu).get())
    cart = {}
    return(render_template("Customer/QSR/mainKiosk2.html", menu=menuInfo, restName=estNameStr.capitalize(), locName=location.capitalize(), cart=cart ))


@app.route('/<location>/sitdown-menudisp')
def sitdownMenu(location):
    menu = session.get('menu', None)
    orderToken = session.get('orderToken',None)
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu + "/categories"
    menuInfo = dict(db.reference(pathMenu).get())
    cartRef = db.reference('/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken + "/cart")
    try:
        cart = dict(cartRef.get())
    except Exception as e:
        cart = {}
    print(cart)
    return(render_template("Customer/Sitdown/mainKiosk2.html", menu=menuInfo, restName=estNameStr.capitalize(), cart=cart, locName=location.capitalize()))

@app.route('/<location>/qsr-menudisp')
def qsrMenu(location):
    menu = session.get('menu', None)
    orderToken = session.get('orderToken',None)
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu + "/categories"
    menuInfo = dict(db.reference(pathMenu).get())
    cartRef = db.reference('/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken + "/cart")
    try:
        cart = dict(cartRef.get())
    except Exception as e:
        cart = {}
    print(cart)
    return(render_template("Customer/QSR/mainKiosk2.html", menu=menuInfo, restName=estNameStr.capitalize(), cart=cart, locName=location.capitalize()))

@app.route('/<location>/qsr-additms~<cat>~<itm>', methods=["POST"])
def kiosk2QSR(location,cat,itm):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    ##print((request.form))
    rsp = dict((request.form))
    dispStr = ""
    unitPrice = 0
    notes = rsp['notes']
    qty_str = rsp['qty']
    if(qty_str == ""):
        qty = 1
    else:
        qty = int(qty_str)
    dispStr += str(qty) + " x " + itm + " "
    dict_keys = list(rsp.keys())
    mods = []
    img = ""
    for keys in dict_keys:
        if(keys != "notes" or keys != "qty"):
            try:
                raw_arr = rsp[keys].split("~")
                img = raw_arr[2]
                dispStr += str(raw_arr[0]).capitalize() + " "
                mods.append([raw_arr[0],raw_arr[1]])
                unitPrice += float(raw_arr[1])
            except Exception as e:
                pass
    price = float(qty*unitPrice)
    dispStr += "  |Notes: " +notes + "  ($" + "{:0,.2f}".format(price) + ")"
    menu = session.get('menu', None)
    orderToken = session.get('orderToken',None)
    ##print(orderToken)
    pathCartitm = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken + "/cart/"
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu
    cartRefItm = db.reference(pathCartitm)
    cartRefItm.push({
        'cat':cat,
        'itm':itm,
        'qty':qty,
        'img':img,
        'notes':notes,
        'price':price,
        'mods':mods,
        'unitPrice':unitPrice,
        'dispStr':dispStr
    })
    return(redirect(url_for('qsrMenu', location=location)))


@app.route('/<location>/sitdown-additms~<cat>~<itm>', methods=["POST"])
def kiosk2(location, cat, itm):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    ##print((request.form))
    rsp = dict((request.form))
    dispStr = ""
    unitPrice = 0
    notes = rsp['notes']
    qty_str = rsp['qty']
    if(qty_str == ""):
        qty = 1
    else:
        qty = int(qty_str)
    dispStr += str(qty) + " x " + itm + " "
    dict_keys = list(rsp.keys())
    mods = []
    img = ""
    for keys in dict_keys:
        if(keys != "notes" or keys != "qty"):
            try:
                raw_arr = rsp[keys].split("~")
                img = raw_arr[2]
                dispStr += str(raw_arr[0]).capitalize() + " "
                mods.append([raw_arr[0],raw_arr[1]])
                unitPrice += float(raw_arr[1])
            except Exception as e:
                pass
    price = float(qty*unitPrice)
    dispStr += "  |Notes: " +notes + "  ($" + "{:0,.2f}".format(price) + ")"
    menu = session.get('menu', None)
    orderToken = session.get('orderToken',None)
    ##print(orderToken)
    pathCartitm = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken + "/cart/"
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu
    cartRefItm = db.reference(pathCartitm)
    cartRefItm.push({
        'cat':cat,
        'itm':itm,
        'qty':qty,
        'img':img,
        'notes':notes,
        'price':price,
        'dispStr':dispStr,
        'mods':mods,
        'unitPrice':unitPrice
    })
    return(redirect(url_for('sitdownMenu', location=location)))


@app.route('/<location>/qsr-itmRemove', methods=["POST"])
def kioskRemQSR(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = dict((request.form))
    remItm = rsp["remove"]
    orderToken = session.get('orderToken',None)
    menu = session.get('menu',None)
    pathCartitm = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken +"/cart/"
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu
    remPath = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken +"/cart/" + remItm
    try:
        remRef = db.reference(remPath)
        remRef.delete()
    except Exception as e:
        pass
    cartRefItm = db.reference(pathCartitm)
    menuInfo = db.reference(pathMenu).get()
    cartData = db.reference(pathCartitm).get()
    return(redirect(url_for('qsrMenu', location=location)))


@app.route('/<location>/itmRemove', methods=["POST"])
def kioskRem(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = dict((request.form))
    remItm = rsp["remove"]
    orderToken = session.get('orderToken',None)
    menu = session.get('menu',None)
    pathCartitm = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken +"/cart/"
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu
    remPath = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken +"/cart/" + remItm
    try:
        remRef = db.reference(remPath)
        remRef.delete()
    except Exception as e:
        pass
    finally:
        cartRefItm = db.reference(pathCartitm)
        menuInfo = db.reference(pathMenu).get()
        cartData = db.reference(pathCartitm).get()
    return(redirect(url_for('sitdownMenu', location=location)))





@app.route('/<location>/SDupdate')
def kioskUpdate(location):
    try:
        orderToken = session.get('orderToken',None)
        setPath = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken
        alertTimePath = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken + "/alertTime"
        alertPath = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken + "/alert"
        alert = db.reference(alertPath).get()
        info = {
               "alert" : alert,
            }
        return jsonify(info)
    except Exception as e:
        return("200")


@app.route('/<location>/cartAdd', methods=["POST"])
def kioskCart(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    orderToken = session.get('orderToken',None)
    menu = session.get('menu',None)
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu
    pathCart = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken +"/cart/"
    pathTable = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken +"/table/"
    pathRequest = '/restaurants/' + estNameStr + '/' + str(location) + "/requests/"
    tableNum = db.reference(pathTable).get()
    try:
        cartRef = db.reference(pathCart)
        cart = db.reference(pathCart).get()
        reqRef = db.reference(pathRequest)
        newReq = reqRef.push(cart)
        pathRequestkey = '/restaurants/' + estNameStr + '/' + str(location) + "/requests/" + newReq.key + "/info"
        reqRefkey = db.reference(pathRequestkey)
        reqRefkey.update({"table":tableNum,"type":"order","token":orderToken})
        cartRef.delete()
        # #print(cart)
    except Exception:
        pass
    menuInfo = db.reference(pathMenu).get()
    cart = {}

    return(redirect(url_for('sitdownMenu', location=location)))

@app.route('/<location>/cartAdd-QSR', methods=["POST"])
def kioskCartQSR(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    orderToken = session.get('orderToken',None)
    menu = session.get('menu',None)
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu
    pathCart = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken +"/cart/"
    pathTable = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken +"/table/"
    pathRequest = '/restaurants/' + estNameStr + '/' + str(location) + "/requests/"
    tableNum = db.reference(pathTable).get()
    menuInfo = db.reference(pathMenu).get()
    try:
        cartRef = db.reference(pathCart)
        cart = db.reference(pathCart).get()
        test = str(list(cart.keys()))
        pathOrder = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken
        orderInfo = dict(db.reference(pathOrder).get())
        cpnBool = orderInfo["cpn"]
        if(cpnBool == 0):
            cart = dict(orderInfo["cart"])
            cartKeys = list(cart.keys())
            for keys in cartKeys:
                if("discount" == str(cart[keys]["cat"])):
                    pathRem = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken + "/cart/" + keys
                    pathRemRef = db.reference(pathRem)
                    pathRemRef.delete()
        return(redirect(url_for("payQSR",location=location)))
    except Exception:
        return(redirect(url_for("qsrMenu",location=location)))


@app.route('/<location>/collect-feedback')
def dispFeedBack(location):
    feedback_ref = db.reference('/restaurants/' + estNameStr + '/'+ location + '/feedback')
    feedback = dict(feedback_ref.get())
    return(render_template("Customer/Sitdown/feedback.html",feedback=feedback))


@app.route('/<location>/collect-feedback-ans', methods=['POST'])
def collectFeedback(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = dict((request.form))
    orderToken = session.get('orderToken',None)
    pathOrder = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken
    orderInfo = dict(db.reference(pathOrder).get())
    now = datetime.datetime.now(tzGl[0])
    feedback_ref = db.reference('/restaurants/' + estNameStr + '/'+ location + '/feedback')
    curr_feedback = dict(feedback_ref.get())
    comment_ref = db.reference('/restaurants/' + estNameStr + '/'+ location + '/comments/new')
    comments = str(rsp['comment']) + " "
    comment_ref.push({
        "comment":comments,
        "name":orderInfo['name'],
        "timeStamp":str(now.hour) + ":" + str(now.minute) + " " + str(now.month) + "-" + str(now.day) + "-" + str(now.year)
    })
    del rsp['comment']
    newFeedKeys = list(rsp.keys())
    feedKeys = list(curr_feedback.keys())
    timeScale = ['day','week','month']
    timeScaleVal = [int(datetime.datetime.now(tzGl[0]).weekday()),int(datetime.datetime.now(tzGl[0]).isocalendar()[1]),int(datetime.datetime.now(tzGl[0]).month)]
    for tms in range(len(timeScale)):
        for keys in feedKeys:
            currScore = curr_feedback[keys]['info'][timeScale[tms]]['totalScore']
            ansSize = curr_feedback[keys]['info'][timeScale[tms]]['count']
            addScore = curr_feedback[keys]['ans'][rsp[keys]]['score']
            timeKey = "curr" + str(timeScale[tms])
            timeVal = curr_feedback[keys]['info'][timeScale[tms]][timeKey]

            currScore += addScore
            ansSize += 1
            newDispScore = round(float(currScore)/float(ansSize),2)
            qFeedbackRef = db.reference('/restaurants/' + estNameStr + '/'+ location + '/feedback/' + keys + '/info/' + str(timeScale[tms]))
            if(timeVal == timeScaleVal[tms]):
                qFeedbackRef.update({
                    'count':ansSize,
                    'currentScore': newDispScore,
                    'totalScore':currScore
                })
            else:
                qFeedbackRef.update({
                    timeKey:timeScaleVal[tms],
                    'count':1,
                    'currentScore': addScore,
                    'totalScore':addScore
                })
    return(redirect(url_for("payQSR",location=location)))

@app.route('/<location>/pay')
def payQSR(location):
    orderToken = session.get('orderToken',None)
    pathOrder = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken
    orderInfo = dict(db.reference(pathOrder).get())
    QSR = orderInfo["QSR"]
    orderInfo = dict(db.reference(pathOrder).get())
    QSR = orderInfo["QSR"]
    if(QSR == 0):
        cart = dict(orderInfo["cart"])
        subtotal = 0
        items = []
        cartKeys = list(cart.keys())
        for keys in cartKeys:
            subtotal += cart[keys]["price"]
            dispStr = cart[keys]["dispStr"]
            items.append(dispStr)
        subtotalStr = "${:0,.2f}".format(subtotal)
        taxRate = float(db.reference('/restaurants/' + estNameStr + '/' + str(location) + '/taxrate').get())
        tax = "${:0,.2f}".format(subtotal * taxRate)
        tax += " (" + str(float(taxRate * 100)) + "%)"
        total = "${:0,.2f}".format(subtotal * (1+taxRate))
        session['total'] = round(subtotal*(1+taxRate),2)
        session['kiosk'] = orderInfo["kiosk"]
        db.reference(pathOrder).update({
            "subtotal":subtotal,
            "total":float(subtotal*(1+taxRate))
        })
        sqTotal = str(int(round(subtotal*(1+taxRate),2) * 100)) + "~" + str(orderToken) +"~"+mainLink+location
        return(render_template("Customer/QSR/Payment.html",locName=str(location).capitalize(),restName=str(estNameStr).capitalize(), cart=str(cart), items=items, subtotal=subtotalStr,tax=tax,total=total,sqTotal=sqTotal))
    else:
        cart = dict(orderInfo["ticket"])
        subtotal = orderInfo["subtotal"]
        subtotalStr = "${:0,.2f}".format(subtotal)
        taxRate = float(db.reference('/restaurants/' + estNameStr + '/' + str(location) + '/taxrate').get())
        tax = "${:0,.2f}".format(subtotal * taxRate)
        tax += " (" + str(float(taxRate * 100)) + "%)"
        total = "${:0,.2f}".format(subtotal * (1+taxRate))
        cartKeys = list(cart.keys())
        cpnBool = orderInfo["cpn"]
        pathCpn =  db.reference('/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken)
        # pathCpn.update({"cpn":1})
        items = []
        for ck in cartKeys:
            ckKeys = list(cart[ck].keys())
            for ckk in ckKeys:
                dispStr = cart[ck][ckk]["itm"]
                dispStr += " "
                for mds in range(len(cart[ck][ckk]["mods"])):
                    dispStr += cart[ck][ckk]["mods"][mds][0]
                dispStr += " "
                dispStr += str("$" + "{:0,.2f}".format(float(cart[ck][ckk]["unitPrice"])))
                dispStr += " x "
                dispStr += str(cart[ck][ckk]["qty"])
                dispStr += " " + str(cart[ck][ckk]["notes"])
                dispStr += " || $"
                dispStr += "{:0,.2f}".format(float(cart[ck][ckk]["price"]))
                items.append(dispStr)
                session['total'] = round(subtotal*(1+taxRate),2)
                session['kiosk'] = orderInfo["kiosk"]
        sqTotal = str(int(round(subtotal*(1+taxRate),2) * 100)) + "~" + str(orderToken)+"~"+mainLink+location
        return(render_template("Customer/Sitdown/Payment.html",locName=str(location).capitalize(),restName=str(estNameStr).capitalize(),
                               items=items, subtotal=subtotalStr,tax=tax,total=total, sqTotal=sqTotal))


@app.route('/<location>/applyCpn', methods=["POST"])
def applyCpn(location):
    orderToken = session.get('orderToken',None)
    menu = session.get('menu',None)
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = dict((request.form))
    code = str(rsp["code"]).lower()
    pathOrder = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken
    orderInfo = dict(db.reference(pathOrder).get())
    QSR = orderInfo["QSR"]
    try:
        cpnsPath = '/restaurants/' + estNameStr + '/' + str(location) + "/discounts/"+ menu
        cpns = dict(db.reference(cpnsPath).get())
        disc = cpns[code]
        discCat = disc["cat"]
        discItm = disc["itm"]
        lim = disc["lim"]
        min = disc["min"]
        type = disc["type"]
        amt = float(disc["amt"])
        modName = disc["mods"][0]
        modItm = disc["mods"][1]
        QSR = int(orderInfo["QSR"])
        pathOrder = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken
        orderInfo = dict(db.reference(pathOrder).get())
        varQSR = (QSR == 0)
        if(varQSR == True):
            cpnBool = orderInfo["cpn"]
            if(cpnBool == 0):
                cart = dict(orderInfo["cart"])
                cartKeys = list(cart.keys())
                for keys in cartKeys:
                    if("discount" == str(cart[keys]["cat"])):
                        pathRem = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken + "/cart/" + keys
                        pathRemRef = db.reference(pathRem)
                        pathRemRef.delete()
            cart = dict(orderInfo["cart"])
            amtUsed = 0
            discAmt = 0
            cartKeys = list(cart.keys())
            for keys in cartKeys:
                if(discCat == str(cart[keys]["cat"]) and discItm == str(cart[keys]["itm"])):
                    # TODO
                    for mod in range(len(cart[keys]["mods"])):
                        md = cart[keys]["mods"][mod][0]
                        print(md, modItm)
                        if(modItm == md):
                            for q in range(int(cart[keys]["qty"])):
                                if(amtUsed < lim):
                                    if(type == "money"):
                                        discAmt -= amt
                                    else:
                                        discAmt -= (cart[keys]["unitPrice"]*float(amt/100))
                                    amtUsed += 1
                                else:
                                    break
            print(amtUsed, min, discAmt)
            if(amtUsed >= min):
                #print("discApplied")
                pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu
                pathCpn =  db.reference('/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken)
                pathCartitm = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken + "/cart/"
                cartRefItm = db.reference(pathCartitm)
                cartRefItm.push({
                    'cat':'discount',
                    'itm':code,
                    'qty':int(amtUsed),
                    'img':'',
                    'notes':'',
                    'price':discAmt,
                    'dispStr': str(str(amtUsed) + " x " + str(code) + " $" + "{:0,.2f}".format(discAmt)),
                    'mods':[["-",0]],
                    'unitPrice':float(float(discAmt)/float(amtUsed))
                })
                pathCpn.update({"cpn":0})
            return(redirect(url_for('payQSR',location=location)))
        else:
            cart = dict(orderInfo["ticket"])
            subtotal = orderInfo["subtotal"]
            subtotalStr = "${:0,.2f}".format(subtotal)
            tax = "${:0,.2f}".format(subtotal *0.1)
            total = "${:0,.2f}".format(subtotal *1.1)
            amtUsed = 0
            discAmt = 0
            cartKeys = list(cart.keys())
            cpnBool = orderInfo["cpn"]
            print(cpnBool)
            if(cpnBool == 0):
                for ck in cartKeys:
                    ckKeys = list(cart[ck].keys())
                    for ckk in ckKeys:
                        if(cart[ck][ckk]["cat"] == "discount"):
                            pathRem = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken + "/ticket/" + str(ck) + "/" + str(ckk)
                            pathRemRef = db.reference(pathRem)
                            subtotal -= cart[ck][ckk]['price']
                            pathCpn =  db.reference('/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken)
                            pathCpn.update({"subtotal":subtotal})
                            pathRemRef.delete()
            pathOrder = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken
            orderInfo = dict(db.reference(pathOrder).get())
            cart = dict(orderInfo["ticket"])
            subtotal = orderInfo["subtotal"]
            subtotalStr = "${:0,.2f}".format(subtotal)
            tax = "${:0,.2f}".format(subtotal *0.1)
            total = "${:0,.2f}".format(subtotal *1.1)
            amtUsed = 0
            discAmt = 0
            cartKeys = list(cart.keys())
            for ckx in cartKeys:
                ckxKeys = list(cart[ckx].keys())
                for ckkx in ckxKeys:
                    if((discCat == str(cart[ckx][ckkx]["cat"])) and (discItm == str(cart[ckx][ckkx]["itm"]))):
                        for mod in range(len(cart[ckx][ckkx]["mods"])):
                            md = cart[ckx][ckkx]["mods"][mod][0]
                            if(modItm == md):
                                for q in range(int(cart[ckx][ckkx]["qty"])):
                                    if(amtUsed < lim):
                                        if(type == "money"):
                                            discAmt -= amt
                                        else:
                                            discAmt -= (cart[ckx][ckkx]["unitPrice"]*float(amt/100))
                                        amtUsed += 1

                                    else:
                                        break
            if(amtUsed >= min):
                #print("discApplied")
                subtotal += discAmt
                pathCpn =  db.reference('/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken)
                pathCartitm = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken + "/ticket/"
                cartRefItm = db.reference(pathCartitm)
                postToken = str(uuid.uuid4()).replace("-","a")
                cartRefItm.push({
                    postToken:{
                    'cat':'discount',
                    'itm':code,
                    'qty':int(amtUsed),
                    'img':'',
                    'notes':'',
                    'price':discAmt,
                    'mods':[[" ",0]],
                    'unitPrice':float(float(discAmt)/float(amtUsed))
                    }
                })
                pathCpn.update({"cpn":0,
                                "subtotal":subtotal})
            return(redirect(url_for('payQSR',location=location)))
    except Exception as e:
        print(str(e))
        return(redirect(url_for('payQSR',location=location)))


@app.route('/<location>/close-alert')
def kioskClear(location):
    orderToken = session.get('orderToken',None)
    alertPath = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken
    clearAlert = db.reference(alertPath).update({"alert":"null"})

    return(render_template("Customer/Sitdown/mainKiosk.html",location=location,
                           cats=cats,baseItms=baseItms,descrips=descrips,exInfo=exInfo,imgData=imgData,
                           modsName=modsName,modsItm=modsItm,btn=str("sitdown-additms"),restName=str(estNameStr.capitalize()),
                           baseitmCart=baseitmCart,modsCart=modsCart,notesCart=notesCart,qtysCart=qtysCart,imgCart=imgCart,
                           cartKeys=cartKeys,btn2="itmRemove",btn3="cartAdd"))


@app.route('/<location>/sendReq', methods=["POST"])
def kioskSendReq(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    orderToken = session.get('orderToken',None)
    menu = session.get('menu',None)
    tableNum = session.get('table',None)
    rspKey = list(rsp.keys())[0]
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
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu
    pathRequest = '/restaurants/' + estNameStr + '/' + str(location) + "/requests/"
    reqRef = db.reference(pathRequest)
    newReq = reqRef.push({"help":requestId})
    pathRequestkey = '/restaurants/' + estNameStr + '/' + str(location) + "/requests/" + newReq.key + "/info"
    reqRefkey = db.reference(pathRequestkey)
    reqRefkey.set({"table":tableNum,"type":"help","token":orderToken})
    return(redirect(url_for("sitdownMenu", location=location)))


##########Employee###########
@app.route('/<location>/qsr-employee-login')
def EmployeeLoginQSR(location):
    return(render_template("POS/StaffQSR/login.html"))

@app.route('/<location>/qsr-employee-login2')
def EmployeeLogin2QSR(location):
    return(render_template("POS/StaffSitdown/login2.html"))

@app.route('/<location>/qsr-employee-login', methods=['POST'])
def EmployeeLoginCheckQSR(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    code = rsp['code']
    loginRef = db.reference('/restaurants/' + estNameStr + '/' + str(location) + "/employee")
    loginData = dict(loginRef.get())
    hashCheck = pbkdf2_sha256.verify(code, loginData['code'])
    if(hashCheck == True):
        token = str(uuid.uuid4())
        loginRef.update({
            "token":token,
            "time":time.time()
        })
        session["token"] = token
        return(redirect(url_for("EmployeePanelQSR",location=location)))
    else:
        return(redirect(url_for("EmployeeLogin2",location=location)))

@app.route('/<location>/qsr-view')
def EmployeePanelQSR(location):
    token = session.get('token',None)
    loginRef = db.reference('/restaurants/' + estNameStr + '/' + str(location) + "/employee/")
    loginData = dict(loginRef.get())
    try:
        if(((token == loginData["token"]) and (time.time() - loginData["time"] <= 3600))):
            pass
        else:
            return(redirect(url_for("EmployeeLoginQSR",location=location)))
    except Exception as e:
        return(redirect(url_for("EmployeeLogin2QSR",location=location)))
    try:
        ordPath = '/restaurants/' + estNameStr + '/' + str(location) + "/orderQSR"
        ordsRef = db.reference(ordPath)
        ordsGet = dict(ordsRef.get())
    except Exception as e:
        ordsGet = {}
    menu = findMenu(location)
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu + "/categories"
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
    return(render_template("POS/StaffQSR/View.html", location=str(location).capitalize(), restName=str(estNameStr.capitalize()), menu=menu, activeItems=activeItems, inactiveItems=inactiveItems, orders=ordsGet))


@app.route('/<location>/qsr-activate-item~<cat>~<item>~<menu>')
def activateItemQSR(location,cat,item,menu):
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu + "/categories/"+ cat + "/" + item
    descrip = dict(db.reference(pathMenu).get())["tmp"]
    db.reference(pathMenu).update({"descrip":descrip})
    pathDel = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu + "/categories/"+ cat + "/" + item +"/tmp"
    db.reference(pathDel).delete()
    return(redirect(url_for("EmployeePanelQSR",location=location)))

@app.route('/<location>/qsr-deactivate-item~<cat>~<item>~<menu>')
def deactivateItemQSR(location,cat,item,menu):
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu + "/categories/"+ cat + "/" + item
    descrip = dict(db.reference(pathMenu).get())["descrip"]
    db.reference(pathMenu).update({"tmp":descrip})
    db.reference(pathMenu).update({"descrip":"INACTIVE"})
    return(redirect(url_for("EmployeePanelQSR",location=location)))

@app.route('/<location>/qsr-view-success', methods=["POST"])
def EmployeeSuccessQSR(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    reqToken = rsp["req"]
    pathRequest = '/restaurants/' + estNameStr + '/' + str(location) + "/orderQSR/" + reqToken
    reqRef = db.reference(pathRequest)
    reqRef.delete()
    return(redirect(url_for("EmployeePanelQSR",location=location)))


@app.route('/<location>/employee-login')
def EmployeeLogin(location):
    return(render_template("POS/StaffSitdown/login.html"))

@app.route('/<location>/employee-login2')
def EmployeeLogin2(location):
    return(render_template("POS/StaffSitdown/login2.html"))

@app.route('/<location>/employee-login', methods=['POST'])
def EmployeeLoginCheck(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    code = rsp['code']
    loginRef = db.reference('/restaurants/' + estNameStr + '/' + str(location) + "/employee")
    loginData = dict(loginRef.get())
    hashCheck = pbkdf2_sha256.verify(code, loginData['code'])
    if(hashCheck == True):
        token = str(uuid.uuid4())
        loginRef.update({
            "token":token,
            "time":time.time()
        })
        session["token"] = token
        return(redirect(url_for("EmployeePanel",location=location)))
    else:
        return(redirect(url_for("EmployeeLogin2",location=location)))

@app.route('/<location>/view')
def EmployeePanel(location):
    token = session.get('token',None)
    loginRef = db.reference('/restaurants/' + estNameStr + '/' + str(location) + "/employee/")
    loginData = dict(loginRef.get())
    try:
        if(((token == loginData["token"]) and (time.time() - loginData["time"] <= 3600))):
            pass
        else:
            return(redirect(url_for("EmployeeLogin",location=location)))
    except Exception as e:
        return(redirect(url_for("EmployeeLogin2",location=location)))
    try:
        ordPath = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/"
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
        pathRequest = '/restaurants/' + estNameStr + '/' + str(location) + "/requests/"
        reqRef = db.reference(pathRequest)
        reqData = dict(reqRef.get())
    except Exception as e:
        reqData = {}
    menu = findMenu(location)
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu + "/categories"
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
    print(tokens)
    return(render_template("POS/StaffSitdown/View.html", location=str(location).capitalize(), restName=str(estNameStr.capitalize()), menu=menu, activeItems=activeItems, inactiveItems=inactiveItems, reqData=reqData, orders=ordsGet))


@app.route('/<location>/activate-item~<cat>~<item>~<menu>')
def activateItem(location,cat,item,menu):
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu + "/categories/"+ cat + "/" + item
    descrip = dict(db.reference(pathMenu).get())["tmp"]
    db.reference(pathMenu).update({"descrip":descrip})
    pathDel = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu + "/categories/"+ cat + "/" + item +"/tmp"
    db.reference(pathDel).delete()
    return(redirect(url_for("EmployeePanel",location=location)))

@app.route('/<location>/deactivate-item~<cat>~<item>~<menu>')
def deactivateItem(location,cat,item,menu):
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu + "/categories/"+ cat + "/" + item
    descrip = dict(db.reference(pathMenu).get())["descrip"]
    db.reference(pathMenu).update({"tmp":descrip})
    db.reference(pathMenu).update({"descrip":"INACTIVE"})
    return(redirect(url_for("EmployeePanel",location=location)))

@app.route('/<location>/view-success', methods=["POST"])
def EmployeeSuccess(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    reqToken = rsp["req"]
    pathRequest = '/restaurants/' + estNameStr + '/' + str(location) + "/requests/" + reqToken
    reqRef = db.reference(pathRequest)
    reqData = dict(reqRef.get())
    orderToken = reqData["info"]["token"]
    if(reqData["info"]["type"] == "order"):
        pathTicket = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken +"/ticket"
        pathTotal = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken
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
    return(redirect(url_for("EmployeePanel",location=location)))

@app.route('/<location>/view-warning', methods=["POST"])
def EmployeeWarn(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    reqToken = rsp["req"]
    alert = rsp["reason"]
    pathRequest = '/restaurants/' + estNameStr + '/' + str(location) + "/requests/" + reqToken
    reqRef = db.reference(pathRequest)
    reqData = dict(reqRef.get())
    orderToken = reqData["info"]["token"]
    pathRequest = '/restaurants/' + estNameStr + '/' + str(location) + "/requests/" + reqToken
    pathUser = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken
    reqRef = db.reference(pathRequest)
    reqData = dict(reqRef.get())
    orderToken = reqData["info"]["token"]
    if(reqData["info"]["type"] == "order"):
        pathTicket = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken +"/ticket"
        pathTotal = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken
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
    return(redirect(url_for("EmployeePanel",location=location)))

@app.route('/<location>/view-reject', methods=["POST"])
def EmployeeReject(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    reqToken = rsp["req"]
    alert = rsp["reason"]
    pathRequest = '/restaurants/' + estNameStr + '/' + str(location) + "/requests/" + reqToken
    reqRef = db.reference(pathRequest)
    reqData = dict(reqRef.get())
    orderToken = reqData["info"]["token"]
    pathUser = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken
    AlertSend = db.reference(pathUser).update({"alert":str("Request Cancelled: "+alert)})
    AlertTime = db.reference(pathUser).update({"alertTime":time.time()})
    reqRef.delete()
    return(redirect(url_for("EmployeePanel",location=location)))


@app.route('/<location>/view-editBill', methods=["POST"])
def EditBill(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    orderToken = rsp["req"]
    amt = float(rsp["amt"])
    itm = str(rsp["itm"])
    pathUserX = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken
    pathUser = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken + "/ticket"
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
    return(redirect(url_for("EmployeePanel",location=location)))


@app.route('/<location>/view-clearTicket', methods=["POST"])
def RemBill(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    orderToken = rsp["req"]
    pathUserX = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken
    remRef = db.reference(pathUserX)
    remRef.delete()
    return(redirect(url_for("EmployeePanel",location=location)))

####SQUARE####
@app.route('/<location>/verify-kiosk', methods=["POST"])
def verifyOrder(location):
    rsp = request.get_json()
    print(rsp)
    token = rsp['tokenVal']
    pathOrder = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + token
    orderRef = db.reference(pathOrder)
    order = dict(orderRef.get())
    if(order['QSR'] == 0):
        qsrOrderPath = '/restaurants/' + estNameStr + '/' + str(location) + '/orderQSR'
        qsrOrderRef = db.reference(qsrOrderPath)
        qsrOrderRef.update({
            token:{
                "cart":dict(order['cart']),
                "info":{"name":order["name"],
                        "number":order['phone'],
                        "paid":"PAID",
                        "subtotal":order['subtotal'],
                        "total":order['total']}
                }
        })
        packet = {
            "code":token,
            "success": "true"
        }
        return jsonify(packet)
    else:
        orderRef.update({
            "paid":"PAID"
        })
        packet = {
            "code":tokenVal,
            "success": "true"
        }
        return jsonify(packet)


@app.route('/reader/<locationX>/<type>', methods=["POST"])
def GenReaderCode(locationX,type):
    rsp = request.get_json()
    print(rsp)
    code = rsp['code']
    kioskType = ["qsr-startKiosk","sitdown-startKiosk"]
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
        getSquare()
        ##print(locationsPaths.keys())
        app.secret_key = scKey
        sslify = SSLify(app)
        app.config['SESSION_TYPE'] = 'filesystem'
        sess = Session()
        sess.init_app(app)
        app.permanent_session_lifetime = datetime.timedelta(minutes=200)
        app.debug = True
        app.run(host="0.0.0.0",port=5000)
    except KeyboardInterrupt:
        sys.exit()
