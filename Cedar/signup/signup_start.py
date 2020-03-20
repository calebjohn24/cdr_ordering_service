import datetime
import json
import smtplib
import sys
import time
import uuid
from fpdf import FPDF
import plivo
import os
import random
import firebase_admin
from passlib.hash import pbkdf2_sha256
from firebase_admin import credentials
from firebase_admin import db
from flask import Blueprint, render_template, abort, send_file
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
from Cedar.admin.admin_panel import checkLocation, sendEmail, getSquare, checkAdminToken
import stripe

stripe.api_key = "sk_live_sRI03xt3QaCpWZahwnybqnPe007xtcIzKe"


infoFile = open("info.json")
info = dict(json.load(infoFile))
mainLink = info['mainLink']

botNumber = info['number']


signup_start_blueprint = Blueprint(
    'signup_start', __name__, template_folder='templates')


@signup_start_blueprint.route('/signup')
def signupstart():
    return(render_template('Signup/singupstart.html'))


@signup_start_blueprint.route('/signupstart', methods=['POST'])
def collectRestInfo():
    rsp = dict(request.form)
    email = rsp['email']
    email = email.replace('.', '-')
    password = rsp['password']
    restname = rsp['restname']
    phone = rsp['phone']
    restnameDb = restname.replace(' ', '-')
    restnameDb = restnameDb.replace("'", "")
    restnameDb = restnameDb.replace("&", '-')
    restnameDb = restnameDb.lower()
    restnameLegal = rsp['restname-legal']
    sq = rsp['sq']
    state = rsp['state']
    hash = pbkdf2_sha256.hash(password)
    checkRef = db.reference('/restaurants')
    billingRef = db.reference('/billing')
    try:
        if(dict(checkRef.get())[restnameDb] != None):
            restnameDb += '-' + str(random.randint(0, 1000))
    except Exception as e:
        pass
    checkRef.update({
        restnameDb: {
            "admin-info": {
                email: {
                    "password": hash,
                    "time": time.time(),
                    "token": str(uuid.uuid4())
                }
            },
            "sq-token": "token"
        }
    })
    billingRef.update({
        restnameDb: {
            "info": {
                "legalname": restnameLegal,
                "phone": phone,
                "state": rsp['state']
            },
            "trial": True,
            "dispname": str(rsp['restname'])
        }
    })
    session['restnameDb'] = restnameDb
    collect_menu.addEst(restnameDb, str(rsp['restname']))
    return(render_template('Signup/squarecheck.html'))


@signup_start_blueprint.route('/signupgenloc', methods=['GET'])
def genLoc():
    estNameStr = session.get('restnameDb', None)
    tzGl = {}
    locationsPaths = {}
    getSquare(estNameStr, tzGl, locationsPaths)
    print(locationsPaths)
    if(locationsPaths == {}):
        return(render_template('Signup/addlocs.html', estNameStr=estNameStr, locations=locationsPaths))
    else:
        return(render_template('Signup/signup3.html', estNameStr=estNameStr, locations=locationsPaths))


@signup_start_blueprint.route('/genloc2', methods=['POST'])
def genLoc2():
    estNameStr = session.get('restnameDb', None)
    restRef = db.reference('/restaurants/' + estNameStr)
    billingRef = db.reference('/billing/' + estNameStr)
    billingRef.update({"fees":
                       {
                           "all": {
                               "transactions": {
                                   "count": 0,
                                   "fees": 0
                               }
                           }
                       }
                       })
    rsp = dict(request.form)
    print(rsp)
    del rsp['csrf_token']
    testData = db.reference('/restaurants/testraunt/cedar-location-1').get()
    for locKey, locVal in rsp.items():
        restRef = db.reference('/restaurants/' + estNameStr)
        collect_menu.addLoc(estNameStr, locKey, locVal)
        billingRef = db.reference(
            '/billing/' + estNameStr + '/fees/locations/' + locKey)

        restRef.update({
            locKey: testData
        })
        restRef = db.reference('/restaurants/' + estNameStr + '/' + locKey)
        restRef.update({
            "dispname": locVal
        })

        billingRef.update({"fees":
                           {
                               "transactions": {
                                   "count": 0,
                                   "fees": 0
                               }

                           }
                           })

    tzGl = {}
    locationsPaths = {}
    getSquare(estNameStr, tzGl, locationsPaths)
    return(redirect(url_for('signup_start.addKiosksDisp')))


@signup_start_blueprint.route('/signupAddKiosks', methods=['GET'])
def addKiosksDisp():
    print('kiosk')
    return(render_template('Signup/signupKiosks.html'))


@signup_start_blueprint.route('/signupAddKiosksConfirm', methods=['POST'])
def addKiosksStart():
    print('kiosk2')
    estNameStr = session.get('restnameDb', None)
    rsp = dict(request.form)
    numKiosks = int(rsp['numkiosk'])
    billingRef = db.reference('/billing/' + estNameStr + '/kiosks')
    for n in range(numKiosks):
        uid = str(uuid.uuid4())[:8]
        billingRef.update({
            uid: {
                'active': 0,
                'loc': 'inactive'
            }
        })
    return(redirect(url_for('signup_start.pickKiosksDisp', numKiosks=numKiosks)))


@signup_start_blueprint.route('/signupAddKiosksDisp-<numKiosks>', methods=['GET'])
def pickKiosksDisp(numKiosks):
    return(render_template('Signup/kioskSelect.html', numKiosks=int(numKiosks)))


@signup_start_blueprint.route('/kioskSelect', methods=['POST'])
def kioskSelect():
    estNameStr = session.get('restnameDb', None)
    rsp = dict(request.form)
    kioskRef = db.reference('/billing/' + estNameStr + '/kiosks')
    kiosks = dict(kioskRef.get())
    groups = {}
    tablets = {"8": 180.0, "10": 250.0}
    tabletsDisp = {"8": "8 in tablet w/ card reader",
                   "10": "10 inch Tablet w/ Card Reader"}
    cases = {"folio": 0.0, "floor": 20.0}
    casesDisp = {"folio": "folio case", "floor": "floor stand"}
    kioskKeys = list(kiosks.keys())
    groupId = str(uuid.uuid4())[:8]
    kiosksPrce = {}
    kiosksDisp = {}
    for n in range(len(kioskKeys)):
        kioskId = kioskKeys[n]
        kiosktotal = 0
        keyTablet = rsp['tablet-'+str(n)]
        keyCase = rsp['case-'+str(n)]
        kiosktotal += tablets[str(keyTablet)]
        kiosktotal += cases[str(keyCase)]
        dispStr = tabletsDisp[str(keyTablet)] + \
            " and " + casesDisp[str(keyCase)]
        kiosksPrce.update({kioskId: kiosktotal})
        kiosksDisp.update({kioskId: dispStr})
    groups = [{"rem-group": {
        "val": 101010.0,
        "count": 0,
        "kiosks": ["remKiosk"]}
    }]
    kioskTotal = 0
    for keyKiosk, valKiosk in kiosksPrce.items():
        for g in range(len(groups)):
            for key, val in groups[g].items():
                filled = 0
                if(val['val'] == valKiosk):
                    count = groups[g][key]['count']
                    groups[g][key].update({'count': int(count+1)})
                    groups[g][key]['kiosks'].append(keyKiosk)
                    filled = 1
                    kioskTotal += valKiosk
        if(len(groups) - 1 == g and filled == 0):
            newGroupId = str(uuid.uuid4())[:8]
            groups.append({
                newGroupId: {
                    "val": valKiosk,
                    "count": 1,
                    'kiosks': [keyKiosk],
                    "dispName": kiosksDisp[keyKiosk]
                }
            })
            kioskTotal += valKiosk
    groups.pop(0)
    session['groups'] = groups
    session['countKiosk'] = len(kiosksPrce)
    session['kioskTotal'] = kioskTotal
    return(redirect(url_for('signup_start.kioskFinDisp')))


@signup_start_blueprint.route('/kioskFinDisp', methods=['GET'])
def kioskFinDisp():
    groups = session.get('groups', None)
    countKiosk = session.get('countKiosk', None)
    kioskTotal = session.get('kioskTotal', None)
    session['restnameDb'] = session.get('restnameDb', None)
    return(render_template('Signup/kioskFinance.html', groups=groups, countKiosk=countKiosk, kioskTotal=kioskTotal))


@signup_start_blueprint.route('/payment-kiosk', methods=['POST'])
def kioskPay():
    groups = session.get('groups', None)
    countKiosk = session.get('countKiosk', None)
    kioskTotal = session.get('kioskTotal', None)
    estNameStr = session.get('restnameDb', None)
    rsp = dict(request.form)
    if(rsp['type'] == 'upfront'):
        print('-')
        session['kioskFin'] = 'upfront'
    elif(rsp['type'] == '18'):
        session['kioskFin'] = '18'
    elif(rsp['type'] == '24'):
        session['kioskFin'] = '24'
    return(redirect(url_for('signup_start.getBillingInfo')))


@signup_start_blueprint.route('/getBillingInfo', methods=['GET'])
def getBillingInfo():
    return(render_template('Signup/getBilling.html'))


@signup_start_blueprint.route('/getBillingInfox', methods=['POST'])
def getBillingInfoRead():
    groups = session.get('groups', None)
    countKiosk = session.get('countKiosk', None)
    kioskTotal = session.get('kioskTotal', None)
    estNameStr = session.get('restnameDb', None)
    kioskFin = session.get('kioskFin', None)
    rsp = dict(request.form)
    print(rsp)
    restRef = db.reference('/restaurants/' + estNameStr + '/admin-info')
    billingRef = db.reference('/billing/' + estNameStr + '/info')
    billingInfo = billingRef.get()
    emailDict = list(dict(restRef.get()).keys())
    email = emailDict[0].replace('-', '.')

    newCust = stripe.Customer.create(
        description="Standard Acct-"+str(estNameStr),
        name=str(estNameStr),
        email=email,
        phone=billingInfo['phone'],
        address={
            "line1": rsp['line1'],
            "line2": rsp['line2'],
            "city": rsp['city'],
            "state": rsp['state'],
            "postal_code": rsp['zip'],
            "country": "US"
        }
    )
    print(newCust)
    addrStr = rsp['line1'] + ' ' + rsp['line2'] + ' ' + \
        rsp['city'] + ' ' + rsp['state'] + ' ' + rsp['zip']
    addrDict = {
        "line1": rsp['line1'],
        "line2": rsp['line2'],
        "city": rsp['city'],
        "state": rsp['state'],
        "postal_code": rsp['zip'],
        "country": "US"
    }
    if(rsp["shipSame"] == "no"):
        shipAddrStr = rsp['ship-line1'] + ' ' + rsp['ship-line2'] + ' ' + \
            rsp['ship-city'] + ' ' + rsp['ship-state'] + ' ' + rsp['ship-zip']
        shipAddrDict = {
            "line1": rsp['ship-line1'],
            "line2": rsp['ship-line2'],
            "city": rsp['ship-city'],
            "state": rsp['ship-state'],
            "postal_code": rsp['ship-zip'],
            "country": "US"
        }
    else:
        shipAddrStr = addrStr
        shipAddrDict = addrDict
    billingRef.update({
        "stripeId": newCust.id,
        "addr": addrStr,
        "billAddr": addrDict,
        "shipAddr": shipAddrDict,
        "shipAddrStr": shipAddrStr,
        "tax": 10
    })
    billingRef = db.reference('/billing/' + estNameStr)
    billingRef.update({
        "restFee": 0.25,
        "custFee": 0.25,
        "split": 0.5,
        "totalFee": 0.5
    })
    session['custId'] = newCust.id
    return(redirect(url_for('signup_start.checkoutStandard')))


@signup_start_blueprint.route('/checkout-standard', methods=['GET'])
def checkoutStandard():
    groups = session.get('groups', None)
    countKiosk = session.get('countKiosk', None)
    kioskTotal = session.get('kioskTotal', None)
    estNameStr = session.get('restnameDb', None)
    kioskFin = session.get('kioskFin', None)
    print(kioskFin)
    return(render_template('Signup/checkout.html', subscription=kioskFin, countKiosk=countKiosk, groups=groups, kioskTotal=kioskTotal))


@signup_start_blueprint.route('/checkout-standard-confirm', methods=['POST'])
def checkoutStandardconfirm():
    groups = session.get('groups', None)
    countKiosk = session.get('countKiosk', None)
    kioskTotal = session.get('kioskTotal', None)
    estNameStr = session.get('restnameDb', None)
    kioskFin = session.get('kioskFin', None)
    custId = session.get('custId', None)
    rsp = dict(request.form)
    billingRef = db.reference('/billing/' + estNameStr + '/info')
    try:
        card = stripe.Customer.create_source(
            custId,
            source=rsp['stripeToken'],
        )
        billingRef = db.reference('/billing/' + estNameStr + '/info')
        billingRef.update({
            "paymentId": card.id
        })
    except Exception as e:
        print(e, "error")
        return(render_template('Signup/card-declined.html'))
    customer = stripe.Customer.retrieve(custId)
    custId = customer.id
    billingRef = db.reference('/billing/' + estNameStr)
    currDate = datetime.datetime.now()
    delta0 = datetime.timedelta(days=10)
    currDate = currDate + delta0
    delta = datetime.timedelta(days=30)
    nextDate = currDate + delta
    currStr = str(currDate.month) + "-" + \
        str(currDate.day) + "-" + str(currDate.year)
    nextStr = str(nextDate.month) + "-" + \
        str(nextDate.day) + "-" + str(nextDate.year)
    billingRef.update({
        "lastBillTime": float(time.time())+864000.0,
        "billDate": currDate.day,
        "billMonth": currDate.month,
        "billYear": currDate.year,
        "lastBill": currStr,
        "nextBill": nextStr
    })
    billingRef = db.reference('/billing/' + estNameStr + '/fees/all')
    billingRef.update({
        "base": 50
    })
    billingRef = db.reference('/billing/' + estNameStr + '/fees/all/kiosk')
    items = []
    if(kioskFin == '18'):
        for g in groups:
            amt = 0
            for k, v in g.items():
                dictKiosk = {
                    "base": 5,
                    'group': k,
                    "count": v['count'],
                    "fees": ((v['val']/18.0)+5.0),
                    "kiosks": v['kiosks'],
                    'remaining': 18,
                    'term': 18,
                    'installment': "True"
                }
                amt = int((v['val']/18.0) * 100)
                billingRef.push(dictKiosk)
                plans = stripe.Plan.list()
                for p in plans:
                    if(p.amount == amt):
                        items.append(
                            {"plan": p.id, "quantity": int(v['count'])})
                        break
        items.append({"plan": "plan_GgHGo3gFH4zsBA"})
        items.append({"plan": "plan_GgHGgVAJmMlkrQ"})
        items.append({"plan": "plan_GgHGeI5cXGDfEM",
                      "quantity": int(countKiosk)})
        subscription = stripe.Subscription.create(
            customer=custId,
            default_tax_rates=['txr_1G9QLFLYFr9rSSIKx4JornAL'],
            items=items
        )
        print(subscription)
        billingRef = db.reference('/billing/' + estNameStr + '/info')
        billingRef.update({"subId": subscription.id})
        feesRef = db.reference(
            '/billing/' + estNameStr + '/fees/all/transactions')
        items = dict(subscription)['items']
        for i in items:
            print(i.plan.usage_type)
            print(i.id)
            if(i.plan.usage_type == "metered"):
                feesRef.update({"id": str(i.id)})
                break
    elif(kioskFin == '24'):
        for g in groups:
            for k, v in g.items():
                dictKiosk = {
                    "base": 5,
                    'group': k,
                    "count": v['count'],
                    "fees": ((v['val']/24.0) + 5.0),
                    "kiosks": v['kiosks'],
                    'remaining': 24,
                    'term': 24,
                    'installment': "True"
                }
                amt = int((v['val']/24.0) * 100)
                billingRef.push(dictKiosk)
                plans = stripe.Plan.list()
                for p in plans:
                    if(p.amount == amt):
                        items.append(
                            {"plan": p.id, "quantity": int(v['count'])})
                        break
        items.append({"plan": "plan_GgHGo3gFH4zsBA"})
        items.append({"plan": "plan_GgHGgVAJmMlkrQ"})
        items.append({"plan": "plan_GgHGeI5cXGDfEM",
                      "quantity": int(countKiosk)})
        subscription = stripe.Subscription.create(
            customer=custId,
            default_tax_rates=['txr_1G9QLFLYFr9rSSIKx4JornAL'],
            items=items
        )
        print(subscription)
        billingRef = db.reference('/billing/' + estNameStr + '/info')
        billingRef.update({"subId": subscription.id})
        feesRef = db.reference(
            '/billing/' + estNameStr + '/fees/all/transactions')
        items = dict(subscription)['items']
        for i in items:
            print(i.plan.usage_type)
            print(i.id)
            if(i.plan.usage_type == "metered"):
                feesRef.update({"id": str(i.id)})
                break
    else:
        totalTmp = 0
        for g in groups:
            for k, v in g.items():
                dictKiosk = {
                    "base": 5,
                    'group': k,
                    "count": v['count'],
                    "fees": 5,
                    "kiosks": v['kiosks'],
                    'term': 18,
                }
                billingRef.push(dictKiosk)
                amt = int((v['val']) * 100)
                skus = stripe.SKU.list().data
                billingRef.push(dictKiosk)
                for s in skus:
                    if (s.price == amt):
                        totalTmp += (amt*int(v['count']))
                        items.append(
                            {"type": "sku", "parent": s.id, "quantity": int(v['count'])})
                        break
        items.append({
            "type": "tax",
            "amount": int(totalTmp*0.1),
            "description": "WA Sales Tax",
            "parent": null,
        })
        billingRef = db.reference('/billing/' + estNameStr + '/info')
        billingInfo = billingRef.get()
        order = stripe.Order.create(
            currency="usd",
            customer=custId,
            items=items,
            shipping={
                "name": billingInfo['legalname'],
                "address": {
                    "line1": billingInfo['shipAddr']['line1'],
                    "line2": billingInfo['shipAddr']['line2'],
                    "city": billingInfo['shipAddr']['city'],
                    "state": billingInfo['shipAddr']['state'],
                    "country": "US",
                    "postal_code": billingInfo['shipAddr']['postal_code'],
                },
            },
        )
        stripe.Order.pay(
            order.id,
            customer=custId,
            source=card.id
        )

        itemSub = []
        itemSub.append({"plan": "plan_GgHGo3gFH4zsBA"})
        itemSub.append({"plan": "plan_GgHGgVAJmMlkrQ"})
        itemSub.append({"plan": "plan_GgHGeI5cXGDfEM",
                        "quantity": int(countKiosk)})
        subscription = stripe.Subscription.create(
            customer=custId,
            default_tax_rates=['txr_1G9QLFLYFr9rSSIKx4JornAL'],
            items=itemSub
        )
        print(subscription)
        billingRef = db.reference('/billing/' + estNameStr + '/info')
        billingRef.update({"subId": subscription.id})
        feesRef = db.reference(
            '/billing/' + estNameStr + '/fees/all/transactions')
        items = dict(subscription)['items']
        for i in items:
            print(i.plan.usage_type)
            print(i.id)
            if(i.plan.usage_type == "metered"):
                feesRef.update({"id": str(i.id)})
                break

        dictKiosk = {
            "base": 5,
            'group': k,
            "count": v['count'],
            "fees": ((v['val']/18.0)+5.0),
            "kiosks": v['kiosks'],
            'remaining': 18,
            'term': 18,
            'installment': "True"
        }
    os.mkdir('/tmp/' + estNameStr)
    os.mkdir('/tmp/' + estNameStr + "/imgs")
    os.mkdir('/tmp/' + estNameStr + "/invoices")
    os.mkdir('/tmp/' + estNameStr + "/menus")
    return(redirect(url_for('signup_start.confirmSignup')))


@signup_start_blueprint.route('/confirm-signup', methods=['GET'])
def confirmSignup():
    infoFile = open("info.json")
    info = dict(json.load(infoFile))
    mainLink = info['mainLink']
    estNameStr = session.get('restnameDb', None)
    locations = dict(db.reference('/restaurants/' + estNameStr).get())
    del locations['admin-info']
    del locations['sq-token']
    return(render_template("Signup/signup-congrats.html", estNameStr=estNameStr, mainLink=mainLink, locations=locations))


@signup_start_blueprint.route('/view-tos', methods=['GET'])
def tos():
    return(render_template('Signup/tos.html'))


@signup_start_blueprint.route('/view-priv-policy', methods=['GET'])
def priv():
    return(render_template('Signup/privacy.html'))
