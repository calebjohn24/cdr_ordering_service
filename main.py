import datetime
import json
import smtplib
import sys
import time
import uuid
import plivo
import pygsheets
import firebase_admin
from passlib.hash import pbkdf2_sha256
from firebase_admin import credentials
from firebase_admin import db
from google.cloud import storage
import pytz
from flask import Flask, request, session, jsonify
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
adminSessTime = 3599
client = plivo.RestClient(auth_id='MAYTVHN2E1ZDY4ZDA2YZ', auth_token='ODgzZDA1OTFiMjE2ZTRjY2U4ZTVhYzNiODNjNDll')
cred = credentials.Certificate('CedarChatbot-b443efe11b73.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://cedarchatbot.firebaseio.com/',
    'storageBucket': 'cedarchatbot.appspot.com'
})
storage_client = storage.Client.from_service_account_json(
        'CedarChatbot-b443efe11b73.json')
bucket = storage_client.get_bucket("cedarchatbot.appspot.com")

sqRef = db.reference(str('/restaurants/' + estNameStr))
#print(sqRef.get())
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
app = Flask(__name__)
sslify = SSLify(app)
scKey = uuid.uuid4()
app.secret_key = scKey

api_locations = squareClient.locations
mobile_authorization_api = squareClient.mobile_authorization
result = api_locations.list_locations()
locationsPaths = {}
tzGl = []


# Call the success method to see if the call succeeded
##########Restaurant END END###########
def getSquare():
    if result.is_success():
        # The body property is a list of locations
        locations = result.body['locations']
        # Iterate over the list
        for location in locations:
            if ((dict(location.items())["status"]) == "ACTIVE"):
                # print((dict(location.items())))
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





@app.route('/<location>/menu', methods=["GET"])
def login(location):
    return render_template("POS/AdminMini/login.html", btn=str("menu-build"), restName=estNameStr,locName=location)

@app.route('/<location>/forgot-password', methods=["GET"])
def pwReset():
    return render_template("POS/AdminMini/forgot-password.html", btn=str("menu-build"), restName=estNameStr)



@app.route('/<location>/menu-build', methods=["POST"])
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
            user_ref = ref.child(str(email))
            user_ref.update({
                'token': LoginToken,
                'time': time.time()
            })
            session['user'] = email
            session['token'] = LoginToken
            return redirect(url_for('panel',location=location))
        else:
            return render_template("POS/AdminMini/login2.html", btn=str("menu-build"), restName=estNameStr, locName=location)
    except Exception as e:
        #print(e)
        return render_template("POS/AdminMini/login2.html", btn=str("menu-build"), restName=estNameStr, locName=location)


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
    getSquare()
    LocName = list(locationsPaths.keys())
    return render_template("POS/AdminMini/mainAdmin.html",
                           restName=str(estNameStr).capitalize(),
                           locName=str(location).capitalize())



@app.route('/admin-location/<location>')
def locPanel(location):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        doc = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login', location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    #print(checkLocation(location,1))
    if(checkLocation(location,1)[0] == 1):
        return redirect(url_for('.login', location=location))
    getSquare()
    LocName = list(locationsPaths.keys())
    return render_template("POS/Admin/locationAdmin.html",
                            restName=estNameStr,
                            LocName=LocName,
                            lenLocName=len(LocName),
                            currentLoc=location)


@app.route('/<location>/createMenu', methods=["POST"])
def meun1(location):
    idToken = session.get('token', None)
    fbToken = session.get('fbToken', None)
    authentication = firebase.FirebaseAuthentication('if7swrlQM4k9cBvm0dmWqO3QsI5zjbcdbstSgq1W',
                                                     'cajohn0205@gmail.com', extra={'id': dbid})
    database = firebase.FirebaseApplication("https://cedarchatbot.firebaseio.com/",
                                            authentication=authentication)
    if ((idToken == database.get("restaurants/" + uid + "/" + location + "/", "LoginToken")) and (
            time.time() - database.get("restaurants/" + uid + "/" + location + "/", "LoginTime") < adminSessTime)):
        return render_template("createMenu1.html",
                               next=location + "/createMenu2",
                               back=location + "/adminpanel")
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
    if (checkAdminToken(location) == 1):
        return redirect(url_for('.login', location=location))
    return render_template("createMenu1.html",
                           next=location + "/createMenu2",
                           back=location + "/adminpanel")


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
    if (checkAdminToken(location) == 1):
        return redirect(url_for('.login', location=location))
    return render_template("createMenu1.html",
                           next=location + "/createMenu3",
                           back=location + "/adminpanel")


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
    return (render_template("pickLocation.html", btn="uid", locs=locs, len=len(locs)))


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


##########CUSTOMER END###########

def getReply(msg, number):
    doc_ref = db.collection('restaurants').document('info')
    doc = doc_ref.get().to_dict()
    smsopen = doc["smsopen"]
    smsclosed  = doc["smsclosed"]
    closeTimeHr = int(smsclosed[0:2])
    closeTimeMin = int(smsclosed[3:5])
    openTimeHr = int(smsopen[0:2])
    openTimeMin = int(smsopen[3:5])
    closeCheck = float(closeTimeHr) + float(closeTimeMin / 100.0)
    openCheck = float(openTimeHr) + float(openTimeMin / 100.0)
    currentHour = float(datetime.datetime.now(tzGl[0]).strftime("%H"))
    currentMin = float(datetime.datetime.now(tzGl[0]).strftime("%M")) / 100.0
    currentTime = currentHour + currentMin
    if (openCheck <= currentTime <= closeCheck):
        msg = msg.lower()
        msg.replace("\n", "")
        msg.replace(".", "")
        msg.replace(" ", "")
        msg = ''.join(msg.split())

        if (msg == "order" or msg == "ordew" or msg == "ord" or msg == "ordet" or msg == "oderr" or msg == "ordee" or (
                "ord" in msg)):
            reply = "Hi welcome to " + estNameStr + "! click the link below to order \n" + str(
                mainLink) + "/smsinit/" + str(number)
            return reply
        else:
            return ("no msg")
    else:
        return ("no msg")

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
    #print(str(resp))
    if (resp != "no msg"):
        client.messages.create(
            src=botNumber,
            dst=from_number,
            text=resp
        )
    return '200'

###Kiosk###

def genMenuData(location,menu):
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu
    menuInfo = db.reference(pathMenu).get()
    #print(menuInfo)
    categories = list(menuInfo["categories"])
    baseItms = []
    descrips = []
    exInfo = []
    imgLink = []
    for itms in categories:
        #print(list(menuInfo["categories"][itms]))
        currArr2 = []
        currArr3 = []
        currArr4 = []
        currArr5 = []
        for ll in range(len(list(menuInfo["categories"][itms]))):
            itmArr = []
            itx = (list(menuInfo["categories"][itms])[ll])
            itx2 = itx.replace(" ","-")
            currArr2.append([itx2,itx])
            descrip = (menuInfo["categories"][itms][itx]["descrip"])
            exinfo = (menuInfo["categories"][itms][itx]["extra-info"])
            img = (menuInfo["categories"][itms][itx]["img"])
            mN = (list(menuInfo["categories"][itms][itx]))
            mN.remove("img")
            mN.remove("descrip")
            mN.remove("extra-info")
            currArr3.append(descrip)
            currArr4.append(exinfo)
            currArr5.append(img)
            for mods in mN:
                print(mods)
                max = int(menuInfo["categories"][itms][itx][mods]["max"]) - int(menuInfo["categories"][itms][itx][mods]["min"])
                min = int(menuInfo["categories"][itms][itx][mods]["min"])
                opt = list(menuInfo["categories"][itms][itx][mods]["info"])
        baseItms.append(currArr2)
        descrips.append(currArr3)
        exInfo.append(currArr4)
        imgLink.append(currArr5)
        currArr2 = []
        currArr3 = []
        currArr4 = []
        currArr5 = []

    modsName = []
    modsItm = []
    for itms in categories:
        catArr = []
        catArr2 = []
        for mx in list(menuInfo["categories"][itms]):
            tmpArr = []
            mNX = list(menuInfo["categories"][itms][mx])
            mNX.remove("img")
            mNX.remove("descrip")
            mNX.remove("extra-info")
            for tt in mNX:
                max = int(menuInfo["categories"][itms][mx][tt]["max"]) - int(menuInfo["categories"][itms][mx][tt]["min"])
                min = menuInfo["categories"][itms][mx][tt]["min"]
                tmpArr.append([tt,min,max])
            catArr.append(tmpArr)
        modsName.append(catArr)


    for itms2 in categories:
        catArr = []
        for mx2 in list(menuInfo["categories"][itms2]):
            tmpArr = []
            mNX2 = list(menuInfo["categories"][itms2][mx2])
            mNX2.remove("img")
            mNX2.remove("descrip")
            mNX2.remove("extra-info")
            for tt2 in mNX2:
                tmpArr2 = []
                for hnn in list(menuInfo["categories"][itms2][mx2][tt2]["info"]):
                    tmpArr2.append([hnn,menuInfo["categories"][itms2][mx2][tt2]["info"][hnn]])
                tmpArr.append(tmpArr2)
            catArr.append(tmpArr)
        modsItm.append(catArr)
    '''
    print(baseItms[0][0][0])
    print(categories[0])
    print(descrips[0][0])
    print(exInfo[0][0])
    print(modsName[0][0][0][0])
    print(modsItm[0][0][0][0][1])
    '''
    itmArr = [baseItms,categories,descrips,exInfo,modsName,modsItm,imgLink]
    return itmArr

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
            break

    menuItems = []
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu
    menuInfo = db.reference(pathMenu).get()
    categories = list(menuInfo["categories"])
    for itms in categories:
        #print(list(menuInfo["categories"][itms]))
        currArr = [itms]
        for ll in range(len(list(menuInfo["categories"][itms]))):
            itmArr = []
            itx = (list(menuInfo["categories"][itms])[ll])
            descrip = (menuInfo["categories"][itms][itx]["descrip"])
            exinfo = (menuInfo["categories"][itms][itx]["extra-info"])
            itmArr.append(itx)
            itmArr.append(descrip)
            itmArr.append(exinfo)
            modNames = (list(menuInfo["categories"][itms][itx])[2:])
            for mods in modNames:
                modArr = [mods,menuInfo["categories"][itms][itx][mods]["min"],menuInfo["categories"][itms][itx][mods]["max"]]
                opt = list(menuInfo["categories"][itms][itx][mods]["info"])
                for oo in opt:
                    modArr.append([oo,menuInfo["categories"][itms][itx][mods]["info"][oo]])
                itmArr.append(modArr)
                modArr = []
            currArr.append(itmArr)
            itmArr = []
        menuItems.append(currArr)
    return(menuItems)

@app.route('/<location>/sitdown-startKiosk', methods=["GET"])
def startKiosk2(location):
    return(render_template("Customer/Sitdown/startKiosk.html",btn="startKiosk",restName=estNameStr,locName=location))


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
        "name":name,
        "phone":phone,
        "table":table,
        "alert":"null",
        "alertTime":0,
        "timestamp":time.time(),
        "subtotal":0.0
        })
    print(newOrd.key)
    session['orderToken'] = newOrd.key
    #menu = findMenu(location)
    menu = "lunch"
    session["menu"] = menu
    #print(menu)
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu
    menuInfo = db.reference(pathMenu).get()
    menuData = genMenuData(location,menu)
    baseItms = menuData[0]
    cats = menuData[1]
    descrips = menuData[2]
    exInfo = menuData[3]
    modsName = menuData[4]
    modsItm = menuData[5]
    imgData = menuData[6]
    baseitmCart = ["Add Items to Your Cart"]
    modsCart = [" "]
    notesCart = [" "]
    qtysCart = [" "]
    imgCart = [" "]
    cartKeys = ["-ig"]
    return(render_template("Customer/Sitdown/mainKiosk.html",
                           cats=cats,baseItms=baseItms,descrips=descrips,exInfo=exInfo,imgData=imgData,
                           modsName=modsName,modsItm=modsItm,btn=str("sitdown-additms"),restName=str(estNameStr.capitalize()),
                           baseitmCart=baseitmCart,modsCart=modsCart,notesCart=notesCart,qtysCart=qtysCart,imgCart=imgCart,
                           cartKeys=cartKeys,btn2="itmRemove",btn3="sendReq"))


@app.route('/<location>/sitdown-additms', methods=["POST"])
def kiosk2(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    #print((request.form))
    rsp = dict((request.form))
    #print(rsp)
    itmKeys = list(rsp.keys())
    cat = ""
    itm = ""
    mods = []
    img = ""
    notes = ""
    qty = 1
    price = 0.0
    unitPrice = 0.0
    for itx in itmKeys:
        if((itx[:3]) == "mod"):
            try:
                spt = list(str(rsp[itx]).split("~"))
                unitPrice += float(spt[1])
                mods.append(spt)
            except:
                pass
        elif((itx) == "itm"):
            cat = list(str(rsp[itx]).split("~"))[0]
            itm = list(str(rsp[itx]).split("~"))[1]
            img = list(str(rsp[itx]).split("~"))[2]
        if(itx == "notes"):
            notes = rsp[itx]
        if(itx == "qty"):
            if(rsp[itx] == ""):
                qty = 1
            else:
                qty = int(rsp[itx])

    price = unitPrice*qty
    price = round(price,2)
    unitPrice = round(unitPrice,2)
    #print(price,itm,cat,unitPrice,qty,mods,notes)
    menu = session.get('menu', None)
    orderToken = session.get('orderToken',None)
    #print(orderToken)
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
        'unitPrice':unitPrice
    })
    menuInfo = db.reference(pathMenu).get()
    menuData = genMenuData(location,menu)
    baseItms = menuData[0]
    cats = menuData[1]
    descrips = menuData[2]
    exInfo = menuData[3]
    modsName = menuData[4]
    modsItm = menuData[5]
    imgData  = menuData[6]
    cartData = db.reference(pathCartitm).get()
    #print(cartData)
    cartKeys = list(cartData.keys())
    baseitmCart = []
    modsCart = []
    notesCart = []
    qtysCart = []
    imgCart = []
    for cc in range(len(cartKeys)):
        baseitmCart.append(cartData[cartKeys[cc]]["itm"])
        notesCart.append(cartData[cartKeys[cc]]["notes"])
        qtysCart.append(cartData[cartKeys[cc]]["qty"])
        imgCart.append(cartData[cartKeys[cc]]["img"])
        modStr = ""
        for mds in range(len(cartData[cartKeys[cc]]["mods"])):
            modStr += cartData[cartKeys[cc]]["mods"][mds][0]
            modStr += " - "
        modsCart.append(modStr)
        modStr = ""

    return(render_template("Customer/Sitdown/mainKiosk.html",location=location,
                           cats=cats,baseItms=baseItms,descrips=descrips,exInfo=exInfo,imgData=imgData,
                           modsName=modsName,modsItm=modsItm,btn="sitdown-additms",restName=str(estNameStr.capitalize()),
                           baseitmCart=baseitmCart,modsCart=modsCart,notesCart=notesCart,qtysCart=qtysCart,imgCart=imgCart,
                           cartKeys=cartKeys,btn2="itmRemove",btn3="cartAdd"))


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
    cartRefItm = db.reference(pathCartitm)
    menuInfo = db.reference(pathMenu).get()
    menuData = genMenuData(location,menu)
    baseItms = menuData[0]
    cats = menuData[1]
    descrips = menuData[2]
    exInfo = menuData[3]
    modsName = menuData[4]
    modsItm = menuData[5]
    imgData = menuData[6]
    cartData = db.reference(pathCartitm).get()
    #print(cartData)

    try:
        cartKeys = list(cartData.keys())
        baseitmCart = []
        modsCart = []
        notesCart = []
        qtysCart = []
        imgCart = []
        for cc in range(len(cartKeys)):
            baseitmCart.append(cartData[cartKeys[cc]]["itm"])
            notesCart.append(cartData[cartKeys[cc]]["notes"])
            qtysCart.append(cartData[cartKeys[cc]]["qty"])
            imgCart.append(cartData[cartKeys[cc]]["img"])
            modStr = ""
            for mds in range(len(cartData[cartKeys[cc]]["mods"])):
                modStr += cartData[cartKeys[cc]]["mods"][mds][0]
                modStr += " - "
            modsCart.append(modStr)
            modStr = ""
        #print("INFO--",baseitmCart,modsCart,notesCart,notesCart,qtysCart)
    except:
        baseitmCart = ["Add Items to Your Cart"]
        modsCart = [" "]
        notesCart = [" "]
        qtysCart = [" "]
        cartKeys = ["-ig"]
        imgCart = [" "]
    testData = "testAlert"
    return(render_template("Customer/Sitdown/mainKiosk.html",location=location,
                           cats=cats,baseItms=baseItms,descrips=descrips,exInfo=exInfo,imgData=imgData,
                           modsName=modsName,modsItm=modsItm,btn="sitdown-additms",restName=str(estNameStr.capitalize()),
                           baseitmCart=baseitmCart,modsCart=modsCart,notesCart=notesCart,qtysCart=qtysCart,imgCart=imgCart,
                           cartKeys=cartKeys,btn2="itmRemove",btn3="cartAdd"))



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
    menuInfo = db.reference(pathMenu).get()
    menuData = genMenuData(location,menu)
    try:
        cartRef = db.reference(pathCart)
        cart = db.reference(pathCart).get()
        reqRef = db.reference(pathRequest)
        newReq = reqRef.push(cart)
        pathRequestkey = '/restaurants/' + estNameStr + '/' + str(location) + "/requests/" + newReq.key + "/info"
        reqRefkey = db.reference(pathRequestkey)
        reqRefkey.set({"table":tableNum,"type":"order","token":orderToken})
        cartRef.delete()
        print(cart)
    except Exception:
        pass
    baseItms = menuData[0]
    cats = menuData[1]
    descrips = menuData[2]
    exInfo = menuData[3]
    modsName = menuData[4]
    modsItm = menuData[5]
    imgData = menuData[6]
    baseitmCart = ["Add Items to Your Cart"]
    modsCart = [" "]
    notesCart = [" "]
    qtysCart = [" "]
    cartKeys = ["-ig"]
    imgCart = [" "]
    return(render_template("Customer/Sitdown/mainKiosk.html",location=location,
                           cats=cats,baseItms=baseItms,descrips=descrips,exInfo=exInfo,imgData=imgData,
                           modsName=modsName,modsItm=modsItm,btn=str("sitdown-additms"),restName=str(estNameStr.capitalize()),
                           baseitmCart=baseitmCart,modsCart=modsCart,notesCart=notesCart,qtysCart=qtysCart,imgCart=imgCart,
                           cartKeys=cartKeys,btn2="itmRemove"))

@app.route('/<location>/close-alert')
def kioskClear(location):
    orderToken = session.get('orderToken',None)
    alertPath = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken
    clearAlert = db.reference(alertPath).update({"alert":"null"})
    orderToken = session.get('orderToken',None)
    menu = session.get('menu',None)
    pathCartitm = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken +"/cart/"
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu
    cartRefItm = db.reference(pathCartitm)
    menuInfo = db.reference(pathMenu).get()
    menuData = genMenuData(location,menu)
    baseItms = menuData[0]
    cats = menuData[1]
    descrips = menuData[2]
    exInfo = menuData[3]
    modsName = menuData[4]
    modsItm = menuData[5]
    imgData = menuData[6]
    cartData = db.reference(pathCartitm).get()
    try:
        cartKeys = list(cartData.keys())
        baseitmCart = []
        modsCart = []
        notesCart = []
        qtysCart = []
        imgCart = []
        for cc in range(len(cartKeys)):
            baseitmCart.append(cartData[cartKeys[cc]]["itm"])
            notesCart.append(cartData[cartKeys[cc]]["notes"])
            qtysCart.append(cartData[cartKeys[cc]]["qty"])
            imgCart.append(cartData[cartKeys[cc]]["img"])
            modStr = ""
            for mds in range(len(cartData[cartKeys[cc]]["mods"])):
                modStr += cartData[cartKeys[cc]]["mods"][mds][0]
                modStr += " - "
            modsCart.append(modStr)
            modStr = ""
        #print("INFO--",baseitmCart,modsCart,notesCart,notesCart,qtysCart)
    except:
        baseitmCart = ["Add Items to Your Cart"]
        modsCart = [" "]
        notesCart = [" "]
        qtysCart = [" "]
        cartKeys = ["-ig"]
        imgCart = [" "]
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
    pathCartitm = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/" + orderToken +"/cart/"
    cartRefItm = db.reference(pathCartitm)
    menuInfo = db.reference(pathMenu).get()
    menuData = genMenuData(location,menu)
    baseItms = menuData[0]
    cats = menuData[1]
    descrips = menuData[2]
    exInfo = menuData[3]
    modsName = menuData[4]
    modsItm = menuData[5]
    imgData = menuData[6]
    cartData = db.reference(pathCartitm).get()
    print(cartData)
    try:
        cartKeys = list(cartData.keys())
        baseitmCart = []
        modsCart = []
        notesCart = []
        qtysCart = []
        imgCart = []
        for cc in range(len(cartKeys)):
            baseitmCart.append(cartData[cartKeys[cc]]["itm"])
            notesCart.append(cartData[cartKeys[cc]]["notes"])
            qtysCart.append(cartData[cartKeys[cc]]["qty"])
            imgCart.append(cartData[cartKeys[cc]]["img"])
            modStr = ""
            for mds in range(len(cartData[cartKeys[cc]]["mods"])):
                modStr += cartData[cartKeys[cc]]["mods"][mds][0]
                modStr += " "
            modsCart.append(modStr)
            modStr = ""
        print(baseitmCart,modsCart,notesCart,notesCart,qtysCart)
    except:
        baseitmCart = ["Add Items to Your Cart"]
        modsCart = [" "]
        notesCart = [" "]
        qtysCart = [" "]
        cartKeys = ["-ig"]
    return(render_template("Customer/Sitdown/mainKiosk.html",location=location,
                           cats=cats,baseItms=baseItms,descrips=descrips,exInfo=exInfo,imgData=imgData,
                           modsName=modsName,modsItm=modsItm,btn=str("sitdown-additms"),restName=str(estNameStr.capitalize()),
                           baseitmCart=baseitmCart,modsCart=modsCart,notesCart=notesCart,qtysCart=qtysCart,imgCart=imgCart,
                           cartKeys=cartKeys,btn2="itmRemove",btn3="cartAdd"))


##########Employee###########
@app.route('/<location>/view')
def EmployeePanel(location):
    try:
        ordPath = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/"
        ordsRef = db.reference(ordPath)
        ordsGet = dict(ordsRef.get())
        tokens = list(ordsGet)
        subTotals = []
        tableTotals = []
        ticketDisp = []
        for tt in tokens:
            subTotals.append(round(float(ordsGet[tt]["subtotal"]),2))
            tableTotals.append(ordsGet[tt]["table"])
            try:
                tickList = []
                ticket = dict(ordsGet[tt]["ticket"])
                for tickItms in list(ticket.keys()):
                    tickItmX = []
                    for tts in list(ordsGet[tt]["ticket"][tickItms].keys()):

                        modStr = ""
                        modStr += str(ordsGet[tt]["ticket"][tickItms][tts]["qty"])
                        modStr += "x $"
                        modStr += str(ordsGet[tt]["ticket"][tickItms][tts]["unitPrice"])
                        modStr += " "
                        modStr += ordsGet[tt]["ticket"][tickItms][tts]["itm"]
                        modStr += "-"
                        modStr += ordsGet[tt]["ticket"][tickItms][tts]["notes"]
                        modStr += "-"
                        for mds in range(len(ordsGet[tt]["ticket"][tickItms][tts]["mods"])):
                            modStr += ordsGet[tt]["ticket"][tickItms][tts]["mods"][mds][0]
                            modStr += " - "
                        modStr += "||$"
                        modStr += str(ordsGet[tt]["ticket"][tickItms][tts]["price"])
                        tickItmX.append(modStr)
                        modStr = ""
                    tickList.append(tickItmX)
                ticketDisp.append(tickList)
            except Exception as e:
                ticketDisp.append([["No Items"]])
    except Exception as e:
        subtotals = []
        tokens = []
        tableTotals = []
        ticketDisp = []
    try:
        pathRequest = '/restaurants/' + estNameStr + '/' + str(location) + "/requests/"
        reqRef = db.reference(pathRequest)
        reqData = reqRef.get()
        reqKeys = list(reqData.keys())
        reqTypes = []
        requests = []
        tables = []
        for rr in reqKeys:
            reqTypes.append(reqData[rr]["info"]["type"])
            tables.append(reqData[rr]["info"]["table"])
            if(reqData[rr]["info"]["type"] == "help"):
                requests.append([reqData[rr]["help"]])
            else:
                totalAdd = 0
                cartData = reqData[rr]
                cartKeys = list(cartData.keys())
                cartKeys.remove("info")
                # return(str(cartKeys))
                req = []
                for cc in range(len(cartKeys)):
                    modStr = ""
                    modStr += str(cartData[cartKeys[cc]]["qty"])
                    modStr += "x "
                    modStr += cartData[cartKeys[cc]]["itm"]
                    modStr += "-"
                    modStr += cartData[cartKeys[cc]]["notes"]
                    modStr += "-"
                    for mds in range(len(cartData[cartKeys[cc]]["mods"])):
                        modStr += cartData[cartKeys[cc]]["mods"][mds][0]
                        modStr += " - "
                    req.append(modStr)
                    modStr = ""
                requests.append(req)
    except Exception as e:
        reqKeys = []
        reqTypes = []
        requests = []
        tables = []
    return(render_template("POS/StaffSitdown/View.html",location=str(location).capitalize(),restName=str(estNameStr.capitalize()),ticketDisp=ticketDisp,tickets=tokens,subTotals=subTotals,
    tableTotals=tableTotals,success="view-success",reject="view-reject",warning="view-warning",reqKeys=reqKeys,type=reqTypes,tables=tables,requests=requests))

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









if __name__ == '__main__':
    try:
        getSquare()
        #print(locationsPaths.keys())
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
