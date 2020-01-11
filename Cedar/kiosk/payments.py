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
from Cedar import collect_menu
from Cedar.admin.admin_panel import checkLocation, sendEmail, getSquare



payments_blueprint = Blueprint('payments', __name__,template_folder='templates')

mainLink = 'https://033d08d3.ngrok.io/'

@payments_blueprint.route('/<estNameStr>/<location>/pay')
def payQSR(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    orderToken = session.get('orderToken',None)
    pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
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
        subtotal += 0.25
        subtotalStr = "${:0,.2f}".format(subtotal)
        taxRate = float(db.reference('/restaurants/' + estNameStr + '/' + location + '/taxrate').get())
        tax = "${:0,.2f}".format(subtotal * taxRate)
        tax += " (" + str(float(taxRate * 100)) + "%)"
        total = "${:0,.2f}".format(subtotal * (1+taxRate))
        session['total'] = round(subtotal*(1+taxRate),2)
        session['subtotal'] = subtotal
        session['kiosk'] = orderInfo["kiosk"]
        db.reference(pathOrder).update({
            "subtotal":subtotal,
            "total":float(subtotal*(1+taxRate))
        })
        sqTotal = str(int(round(subtotal*(1+taxRate),2) * 100)) + "~" + str(orderToken) +"~"+mainLink+location
        if(orderInfo['kiosk'] == 0):
            return(render_template("Customer/QSR/Payment.html",locName=location.capitalize(),restName=str(estNameStr).capitalize(), cart=str(cart), items=items, subtotal=subtotalStr,tax=tax,total=total,sqTotal=sqTotal))
        else:
            return(render_template("Customer/QSR/Payment-Online.html",locName=location.capitalize(),restName=str(estNameStr).capitalize(), cart=str(cart), items=items, subtotal=subtotalStr,tax=tax,total=total,orderToken=orderToken))
    else:
        cart = dict(orderInfo["ticket"])
        subtotal = orderInfo["subtotal"]
        subtotal += 0.25
        subtotalStr = "${:0,.2f}".format(subtotal)
        taxRate = float(db.reference('/restaurants/' + estNameStr + '/' + location + '/taxrate').get())
        tax = "${:0,.2f}".format(subtotal * taxRate)
        tax += " (" + str(float(taxRate * 100)) + "%)"
        total = "${:0,.2f}".format(subtotal * (1+taxRate))
        cartKeys = list(cart.keys())
        cpnBool = orderInfo["cpn"]
        pathCpn =  db.reference('/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken)
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
        return(render_template("Customer/Sitdown/Payment.html",locName=location.capitalize(),restName=str(estNameStr).capitalize(),
                               items=items, subtotal=subtotalStr,tax=tax,total=total, sqTotal=sqTotal))

@payments_blueprint.route('/<estNameStr>/<location>/payStaff')
def payStaff(estNameStr,location):
    menu = session.get('menu',None)
    orderToken = session.get('orderToken',None)
    tableNum = session.get('table',None)
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu
    pathRequest = '/restaurants/' + estNameStr + '/' + location + "/requests/"
    reqRef = db.reference(pathRequest)
    newReq = reqRef.push({"help":'Payment Assitance'})
    pathRequestkey = '/restaurants/' + estNameStr + '/' + location + "/requests/" + newReq.key + "/info"
    reqRefkey = db.reference(pathRequestkey)
    reqRefkey.set({"table":tableNum,"type":"help","token":orderToken})
    return(render_template('Customer/Sitdown/NoCCpay.html', alert='Staff Will Enter Code To Confirm Payment'))

@payments_blueprint.route('/<estNameStr>/<location>/payStaffConfirm', methods=['POST'])
def payStaffConfirm(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    orderToken = session.get('orderToken',None)
    code = rsp['code']
    loginRef = db.reference('/restaurants/' + estNameStr + '/' + location + "/employee")
    loginData = dict(loginRef.get())
    hashCheck = pbkdf2_sha256.verify(code, loginData['code'])
    if(hashCheck == True):
        pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
        orderRef = db.reference(pathOrder)
        orderRef.update({
            "paid":"PAID"
        })
        if(order['email'] != "no-email"):
            now = datetime.datetime.now(tzGl[location])
            write_str = "Your Meal From "+ estNameStr + " " + location + " @"
            write_str += str(now.hour) + ":" + str(now.minute) + " on " + str(now.month) + "-" + str(now.day) + "-" + str(now.year)
            write_str += "\n \n"
            # TODOX
            cart = dict(order["ticket"])
            subtotal = order["subtotal"]
            subtotalStr = "${:0,.2f}".format(subtotal)
            taxRate = float(db.reference('/restaurants/' + estNameStr + '/' + location + '/taxrate').get())
            tax = "${:0,.2f}".format(subtotal * taxRate)
            tax += " (" + str(float(taxRate * 100)) + "%)"
            total = "${:0,.2f}".format(subtotal * (1+taxRate))
            cartKeys = list(cart.keys())
            for ck in cartKeys:
                ckKeys = list(cart[ck].keys())
                for ckk in ckKeys:
                    dispStr = cart[ck][ckk]["dispStr"] +  "\n"
                    write_str += dispStr
            write_str+= "\n \n"
            write_str += subtotalStr + "\n" + tax + "\n" + total + "\n \n \n"
            write_str += 'Thank You For Dining with us ' + str(order['name']).capitalize() + " !"
            SUBJECT = "Thank You For Dining at "+ estNameStr + " " + location
            message = 'Subject: {}\n\n{}'.format(SUBJECT, write_str)
            # smtpObj.sendmail(sender, [order['email']], message)
            sendEmail(sender, order['email'], message)
        orderRef.delete()
        return(redirect(url_for('startKiosk4',estNameStr=estNameStr, location=location)))
    else:
        return(render_template('Customer/Sitdown/NoCCpay.html', alert='Incorrect Code please try again'))


@payments_blueprint.route('/<estNameStr>/<location>/qsr-payStaff')
def payStaffQSR(estNameStr,location):
    orderToken = session.get('orderToken',None)
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
                    "paid":"NOT PAID",
                    "subtotal":order['subtotal'],
                    "total":order['total'],
                    'table':order['table'],
                    'verify':1}
            }
    })
    return(render_template('Customer/QSR/NoCCpay.html'))


@payments_blueprint.route('/<estNameStr>/<location>/pay-online')
def payOnline(estNameStr,location):
    orderToken = session.get('orderToken',None)
    subtotal = session.get('subtotal',None)
    pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
    orderInfo = dict(db.reference(pathOrder).get())
    sqRef = db.reference(str('/restaurants/' + estNameStr))
    squareToken = dict(sqRef.get())["sq-token"]
    client = Client(
        access_token=squareToken,
        environment='production',
    )
    api_locations = client.locations
    mobile_authorization_api = client.mobile_authorization
    # Call list_locations method to get all locations in this Square account
    result = api_locations.list_locations()
    if result.is_success():
    	# The body property is a list of locations
        locations = result.body['locations']
    	# Iterate over the list
        for locationX in locations:
            # print(location)
            if((dict(locationX.items())["status"]) == "ACTIVE"):
                locationName = (dict(locationX.items())["name"]).replace(" ","-")
                locationId = dict(locationX.items())["id"]
                if(str(location).lower() == str(locationName).lower() ):

                    body = {}
                    body['location_id'] = locationId
                    checkout_api = client.checkout
                    body = {}
                    idX = str(uuid.uuid4())
                    body['idempotency_key'] = idX
                    body['order'] = {}
                    body['order']['reference_id'] = idX
                    body['order']['line_items'] = []
                    body['order']['discounts'] = []
                    body['order']['discounts'].append({})

                    body['order']['line_items'].append({})
                    body['order']['line_items'][0]['name'] = 'Order Fee'
                    body['order']['line_items'][0]['quantity'] = '1'
                    body['order']['line_items'][0]['base_price_money'] = {}
                    body['order']['line_items'][0]['base_price_money']['amount'] = 25
                    body['order']['line_items'][0]['base_price_money']['currency'] = "USD"

                    cart = dict(orderInfo["cart"])
                    subtotal = 0
                    items = []
                    cartKeys = list(cart.keys())
                    for keys in range(1, len(cartKeys)+1):
                        print(keys)
                        dispStr = str(cart[cartKeys[keys-1]]["dispStr"]).split('x')
                        disp2 = list(dispStr[1].split('('))
                        dispX = disp2[0]
                        if(cart[cartKeys[keys-1]]["unitPrice"] > 0):
                            body['order']['line_items'].append({})
                            body['order']['line_items'][keys]['name'] = dispX
                            body['order']['line_items'][keys]['quantity'] = str(cart[cartKeys[keys-1]]["qty"])
                            body['order']['line_items'][keys]['base_price_money'] = {}
                            body['order']['line_items'][keys]['base_price_money']['amount'] = int((cart[cartKeys[keys-1]]["unitPrice"])*100)
                            body['order']['line_items'][keys]['base_price_money']['currency'] = "USD"
                        else:
                            body['order']['discounts'][0]['name'] = dispX
                            body['order']['discounts'][0]['amount_money'] = {"amount":int((cart[cartKeys[keys-1]]["unitPrice"])*-100),"currency":"USD"}
                            body['order']['discounts'][0]['quantity'] =  str(cart[cartKeys[keys-1]]["qty"])
                            # keys -= 1



                    body['order']['taxes'] = []
                    body['order']['taxes'].append({})
                    body['order']['taxes'][0]['name'] = 'Sales Tax'
                    taxRef = db.reference(str('/restaurants/' + estNameStr + '/' + location))
                    taxDict =(dict(taxRef.get())["taxrate"])
                    print(taxDict)
                    tax = str((taxDict * 100))
                    body['order']['taxes'][0]['percentage'] = tax

                    body['ask_for_shipping_address'] = False
                    body['redirect_url'] = mainLink + estNameStr + '/' + location +'/online-confirm~'+orderToken
                    print(body)
                    result = checkout_api.create_checkout(locationId , body)

                    if result.is_success():
                        link = str(result.body["checkout"]["checkout_page_url"])
                        print(link)
                        # print(result.body["checkout"])
                        return redirect(link)
                    elif result.is_error():
                        print(result.errors)
                        print(result)
                        print("")
                        return(redirect(url_for('payments.payQSR',estNameStr=estNameStr,location=location)))


@payments_blueprint.route('/<estNameStr>/<location>/online-confirm~<orderToken>')
def onlineVerify(estNameStr,location,orderToken):
    orderTokenCheck = session.get('orderToken',None)
    if(orderToken == orderTokenCheck):
        pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
        orderRef = db.reference(pathOrder)
        order = dict(orderRef.get())
        if(order['QSR'] == 0):
            qsrOrderPath = '/restaurants/' + estNameStr + '/' + location + '/orderQSR'
            qsrOrderRef = db.reference(qsrOrderPath)
            qsrOrderRef.update({
                orderToken:{
                    "cart":dict(order['cart']),
                    "info":{"name":order["name"],
                            "number":order['phone'],
                            "paid":"PAID",
                            "subtotal":float(order['subtotal']+0.25),
                            "total":order['total'],
                            'table':order['table']}
                    }
            })
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
                subtotalStr = "Subtotal ${:0,.2f}".format(subtotal)
                taxRate = float(db.reference('/restaurants/' + estNameStr + '/' + location + '/taxrate').get())
                tax = "Tax ${:0,.2f}".format(subtotal * taxRate)
                tax += " (" + str(float(taxRate * 100)) + "%)"
                total = "Total ${:0,.2f}".format(subtotal * (1+taxRate))
                write_str+= "\n \n"
                write_str += subtotalStr +"\n"+tax + "\n"+ total +"\n \n \n"
                write_str += 'Thank You For Your Order ' + str(order['name']).capitalize() + " !"
                SUBJECT = "Your Order From "+ estNameStr.capitalize()  + " " + location.capitalize()
                message = 'Subject: {}\n\n{}'.format(SUBJECT, write_str)
                sendEmail(sender, order['email'], mesg)
        return(render_template("Customer/QSR/Payment-Success.html"))
    else:
        return(redirect(url_for('online_menu.istartOnline',estNameStr=estNameStr,location=location)))


@payments_blueprint.route('/<estNameStr>/<location>/applyCpn', methods=["POST"])
def applyCpn(estNameStr,location):
    orderToken = session.get('orderToken',None)
    menu = session.get('menu',None)
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = dict((request.form))
    code = str(rsp["code"]).lower()
    pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
    orderInfo = dict(db.reference(pathOrder).get())
    QSR = orderInfo["QSR"]
    try:
        cpnsPath = '/restaurants/' + estNameStr + '/' + location + "/discounts/"+ menu
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
        pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
        orderInfo = dict(db.reference(pathOrder).get())
        varQSR = (QSR == 0)
        if(varQSR == True):
            cpnBool = orderInfo["cpn"]
            if(cpnBool == 0):
                cart = dict(orderInfo["cart"])
                cartKeys = list(cart.keys())
                for keys in cartKeys:
                    if("discount" == str(cart[keys]["cat"])):
                        pathRem = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken + "/cart/" + keys
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
                pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu
                pathCpn =  db.reference('/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken)
                pathCartitm = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken + "/cart/"
                cartRefItm = db.reference(pathCartitm)
                cartRefItm.push({
                    'cat':'discount',
                    'itm':code,
                    'qty':int(amtUsed),
                    'img':'',
                    'notes':'',
                    'price':discAmt,
                    'dispStr': str(str(amtUsed) + " x " + str(code) + " ( $" + "{:0,.2f}".format(discAmt)) + " )",
                    'mods':[["-",0]],
                    'unitPrice':float(float(discAmt)/float(amtUsed))
                })
                pathCpn.update({"cpn":0})
            return(redirect(url_for('payments.payQSR',estNameStr=estNameStr,location=location)))
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
                            pathRem = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken + "/ticket/" + str(ck) + "/" + str(ckk)
                            pathRemRef = db.reference(pathRem)
                            subtotal -= cart[ck][ckk]['price']
                            pathCpn =  db.reference('/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken)
                            pathCpn.update({"subtotal":subtotal})
                            pathRemRef.delete()
            pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
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
                pathCpn =  db.reference('/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken)
                pathCartitm = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken + "/ticket/"
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
            return(redirect(url_for('payments.payQSR',estNameStr=estNameStr,location=location)))
    except Exception as e:
        print(str(e))
        return(redirect(url_for('payments.payQSR',estNameStr=estNameStr,location=location)))




@payments_blueprint.route('/<estNameStr>/<location>/verify-kiosk', methods=["POST"])
def verifyOrder(estNameStr,location):
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
        packet = {
            "code":token,
            "success": "true"
        }
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
        return jsonify(packet)
    else:
        pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + token
        orderRef = db.reference(pathOrder)
        orderRef.update({
            "paid":"PAID"
        })
        packet = {
            "code":tokenVal,
            "success": "true"
        }
        if(order['email'] != "no-email"):
            now = datetime.datetime.now(tzGl[location])
            write_str = "Your Meal From "+ estNameStr + " " + location + " @"
            write_str += str(now.hour) + ":" + str(now.minute) + " on " + str(now.month) + "-" + str(now.day) + "-" + str(now.year)
            write_str += "\n \n"
            # TODOX
            cart = dict(order["ticket"])
            subtotal = order["subtotal"]
            subtotalStr = "${:0,.2f}".format(subtotal)
            taxRate = float(db.reference('/restaurants/' + estNameStr + '/' + location + '/taxrate').get())
            tax = "${:0,.2f}".format(subtotal * taxRate)
            tax += " (" + str(float(taxRate * 100)) + "%)"
            total = "${:0,.2f}".format(subtotal * (1+taxRate))
            cartKeys = list(cart.keys())
            for ck in cartKeys:
                ckKeys = list(cart[ck].keys())
                for ckk in ckKeys:
                    dispStr = cart[ck][ckk]["dispStr"] +  "\n"
                    write_str += dispStr
            write_str+= "\n \n"
            write_str += subtotalStr + "\n" + tax + "\n" + total + "\n \n \n"
            write_str += 'Thank You For Dining with us ' + str(order['name']).capitalize() + " !"
            SUBJECT = "Thank You For Dining at "+ estNameStr + " " + location
            message = 'Subject: {}\n\n{}'.format(SUBJECT, write_str)
            # smtpObj.sendmail(sender, [order['email']], message)
            sendEmail(sender, order['email'], message)
        orderRef.delete()
        return jsonify(packet)
