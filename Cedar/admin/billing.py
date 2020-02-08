import datetime
import json
import smtplib
import sys
import time
import uuid
from fpdf import FPDF
import plivo
import os
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
from Cedar.collect_menu import getDispNameEst, getDispNameLoc
from Cedar.admin.admin_panel import checkLocation, sendEmail, getSquare, checkAdminToken
import stripe


stripe.api_key = "sk_live_sRI03xt3QaCpWZahwnybqnPe007xtcIzKe"
billing_blueprint = Blueprint('billing', __name__, template_folder='templates')

infoFile = open("info.json")
info = json.load(infoFile)
mainLink = info['mainLink']

sender = 'cedarrestaurantsbot@gmail.com'
emailPass = "cda33d07-f6bd-479e-806f-5d039ae2fa2d"


def updateTransactionFees(amt, estNameStr, location):
    feesRef = db.reference('/billing/' + estNameStr + '/fees/all/transactions')
    fees = dict(feesRef.get())
    feeId = fees['id']
    newCount = fees['count'] + 1
    newFees = fees['fees'] + amt
    feesRef.update({"count": newCount, "fees": newFees})
    feesRef = db.reference('/billing/' + estNameStr +
                           '/fees/locations/' + location + '/fees/transactions')
    fees = dict(feesRef.get())
    newCount = fees['count'] + 1
    newFees = fees['fees'] + amt
    feesRef.update({"count": newCount, "fees": newFees})
    stripe.SubscriptionItem.create_usage_record(
        feeId,
        quantity=1,
        timestamp=int(time.time()),
        action='increment'
    )


@billing_blueprint.route('/<estNameStr>/<location>/billing-detail', methods=['POST', 'GET'])
def billDetails(estNameStr, location):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    tzGl = {}
    locationsPaths = {}
    getSquare(estNameStr, tzGl, locationsPaths)
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('admin_panel.login', estNameStr=estNameStr, location=location))
    if (checkAdminToken(estNameStr, idToken, username) == 1):
        return redirect(url_for('admin_panel.login', estNameStr=estNameStr, location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    try:
        billingRef = db.reference('/billing/' + estNameStr)
        billing = dict(billingRef.get())
        if(billing == None):
            billing = {}
            total = 0
        else:
            total = 0
            baseFee = billing['fees']['all']['base']
            orderFees = billing['fees']['all']['transactions']['fees']

            kioskKeys = list(dict(billing['fees']['all']['kiosk']).keys())
            kioskFees = 0
            for keys in kioskKeys:
                kioskFees += float(billing['fees']['all']['kiosk'][keys]['fees'] * float(
                    billing['fees']['all']['kiosk'][keys]['count']))
            total = baseFee + orderFees + kioskFees
    except Exception as e:
        total = 0
        billing = {}
    infoRef = db.reference('/billing/' + estNameStr + '/info')
    info = dict(infoRef.get())
    taxRate = float(info['tax'])/100.0
    pmId = info['paymentId']
    pm = stripe.PaymentMethod.retrieve(
        pmId
    )
    cardBrand = str(pm.card.brand).capitalize()
    cardLast4 = pm.card.last4
    return(render_template("POS/AdminMini/billing.html", restName=getDispNameEst(estNameStr), billing=billing, total=total, taxRate=taxRate, cardBrand=cardBrand, cardLast4=cardLast4))


@billing_blueprint.route('/<estNameStr>/<location>/changeCard', methods=['POST'])
def changeCard(estNameStr, location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    infoRef = db.reference('/billing/' + estNameStr + '/info')
    info = dict(infoRef.get())
    custId = info['stripeId']
    oldPm = info['paymentId']
    try:
        card = stripe.Customer.create_source(
            custId,
            source=rsp['stripeToken'],
        )
        infoRef = db.reference('/billing/' + estNameStr + '/info')
        infoRef.update({
            "paymentId": card.id
        })
        stripe.Customer.delete_source(
            custId,
            oldPm,
        )
    except Exception as e:
        print(e)
        return(render_template('POS/AdminMini/card-declined.html'))
    return(redirect(url_for('billing.billDetails', estNameStr=estNameStr, location=location)))


@billing_blueprint.route('/<estNameStr>/<location>/change-split', methods=['POST'])
def splitChange(estNameStr, location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    splitPct = float(rsp['split'])
    billingRef = db.reference('/billing/' + estNameStr)
    billing = dict(billingRef.get())
    totalFee = billing['totalFee']
    custFee = round(float(totalFee * splitPct), 2)
    splitPctRest = 1.0 - splitPct
    restFee = round(float(totalFee * splitPctRest), 2)
    billingRef.update(
        {'split': splitPct, 'custFee': custFee, 'restFee': restFee})
    return(redirect(url_for('billing.billDetails', estNameStr=estNameStr, location=location)))


@billing_blueprint.route('/<estNameStr>/<location>/donwloadinvoice-<key>')
def genInvoice(estNameStr, location, key):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    tzGl = {}
    locationsPaths = {}
    getSquare(estNameStr, tzGl, locationsPaths)
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('admin_panel.login', estNameStr=estNameStr, location=location))
    if (checkAdminToken(estNameStr, idToken, username) == 1):
        return redirect(url_for('admin_panel.login', estNameStr=estNameStr, location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    billingRef = db.reference(
        '/billing/' + estNameStr + '/bills/' + str(key))
    billing = dict(billingRef.get())

    infoRef = db.reference('/billing/' + estNameStr + '/info')
    info = dict(infoRef.get())
    base = billing['base']
    date = billing['date']
    pdf = FPDF()
    pdf.add_page()

    font_name = "Helvetica"
    pdf.image(name=str('CedarRoboticsLogo.jpg'), h=30)

    text = 'Cedar Robotics LLC'
    pdf.set_font(font_name, size=16, style="B")
    w = pdf.get_string_width(text)
    pdf.cell(w, 15, txt=text, align="L")

    pdf.set_font(font_name, size=24, style="B")
    text = "Invoice"
    pdf.multi_cell(0, 20, txt=text, align="R")

    text = 'UBI #604 313 861'
    pdf.set_font(font_name, size=10, style="I")
    w = pdf.get_string_width(text)
    pdf.cell(w, 15, txt=text, align="L")

    text = "ID #CDR" + str(key)
    w = pdf.get_string_width(text)
    pdf.set_font(font_name, size=10, style="B")
    pdf.multi_cell(0, 15, txt=text, align="R")

    text = 'cedarrestaurants.com' + "     " + '17203269719'
    pdf.set_font(font_name, size=12)
    w = pdf.get_string_width(text)
    pdf.cell(w, 15, txt=text, align="L")

    text = "Date: " + str(date)
    w = pdf.get_string_width(text)
    pdf.set_font(font_name, size=12, style="B")
    pdf.multi_cell(0, 15, txt=text, align="R")

    text = "Bill To: "
    pdf.set_font(font_name, size=12, style="B")
    w = pdf.get_string_width(text)
    pdf.cell(w, 15, txt=text, align="L")

    text = info['legalname'] + \
        ' (' + str(estNameStr.capitalize()).replace('-', ' ') + ')'
    pdf.set_font(font_name, size=14)
    pdf.multi_cell(200, 15, txt=text, align="L")

    text = "Billing Address: "
    pdf.set_font(font_name, size=10, style="B")
    w = pdf.get_string_width(text)
    pdf.cell(w, 15, txt=text, align="L")

    text = str(info['addr'])
    pdf.set_font(font_name, size=10)
    pdf.multi_cell(200, 15, txt=text, align="L")

    text = ''
    pdf.set_font(font_name, size=10)
    pdf.multi_cell(200, 15, txt=text, align="L")

    text = "Item"
    testStr = 'Quantity       Unit Price       Total Price'
    testWidth = pdf.get_string_width(testStr)
    wI = pdf.get_string_width(text)
    pdf.set_font(font_name, size=12, style="B")
    allWidth = (170 - testWidth) + wI
    pdf.cell(allWidth, 15, txt=text, align="L")

    text = "Quantity"
    wQ = pdf.get_string_width(text)
    pdf.set_font(font_name, size=12, style="B")
    pdf.cell((wQ), 15, txt=text, align="R")

    space = "       "
    wS = pdf.get_string_width(space)
    pdf.set_font(font_name, size=12, style="B")
    pdf.cell((wS), 15, txt=space, align="R")

    allWidthQ = allWidth + wQ + wS

    text = "Unit Price"
    wU = pdf.get_string_width(text)
    pdf.set_font(font_name, size=12, style="B")
    pdf.cell(wU, 15, txt=text, align="R")

    space = "       "
    wS = pdf.get_string_width(space)
    pdf.set_font(font_name, size=12, style="B")
    pdf.cell((wS), 15, txt=space, align="R")

    text = "Total Price"
    wT = pdf.get_string_width(text)
    pdf.set_font(font_name, size=12, style="B")
    pdf.cell(wT, 15, txt=text, align="R")

    text = ''
    pdf.set_font(font_name, size=10)
    pdf.multi_cell(200, 15, txt=text, align="L")

    text = "Server Fee"
    w = pdf.get_string_width(text)
    pdf.set_font(font_name, size=12)
    pdf.cell(allWidth - 1, 15, txt=text, align="L")

    text = "1"
    w = pdf.get_string_width(text)
    pdf.set_font(font_name, size=12)
    pdf.cell((wQ), 15, txt=text, align="C")

    space = "       "
    wS = pdf.get_string_width(space)
    pdf.set_font(font_name, size=12, style="B")
    pdf.cell((wS), 15, txt=space, align="R")

    text = '${:.2f}'.format((base))
    w = pdf.get_string_width(text)
    pdf.set_font(font_name, size=12)
    pdf.cell((wU), 15, txt=text, align="C")

    space = "       "
    wS = pdf.get_string_width(space)
    pdf.set_font(font_name, size=12, style="B")
    pdf.cell((wS), 15, txt=space, align="R")

    text = '${:.2f}'.format((base))
    w = pdf.get_string_width(text)
    pdf.set_font(font_name, size=12)
    pdf.cell((wT), 15, txt=text, align="C")

    text = ''
    pdf.set_font(font_name, size=10)
    pdf.multi_cell(200, 15, txt=text, align="L")

    transactionFees = billing['transaction']['amt']
    totalVal = base
    totalVal += billing['transaction']['amt']
    transactionCount = billing['transaction']['count']
    if(billing['transaction']['count'] != 0):
        transactionUnit = float(
            billing['transaction']['amt'] / float(billing['transaction']['count']))
    else:
        transactionUnit = 0.5
    text = "Transaction Fee"
    w = pdf.get_string_width(text)
    pdf.set_font(font_name, size=12)
    pdf.cell(allWidth - 1, 15, txt=text, align="L")

    text = str(billing['transaction']['count'])
    w = pdf.get_string_width(text)
    pdf.set_font(font_name, size=12)
    pdf.cell((wQ), 15, txt=text, align="C")

    space = "       "
    wS = pdf.get_string_width(space)
    pdf.set_font(font_name, size=12, style="B")
    pdf.cell((wS), 15, txt=space, align="R")

    text = '${:.2f}'.format((transactionUnit))
    w = pdf.get_string_width(text)
    pdf.set_font(font_name, size=12)
    pdf.cell((wU), 15, txt=text, align="C")

    space = "       "
    wS = pdf.get_string_width(space)
    pdf.set_font(font_name, size=12, style="B")
    pdf.cell((wS), 15, txt=space, align="R")

    text = '${:.2f}'.format((transactionFees))
    w = pdf.get_string_width(text)
    pdf.set_font(font_name, size=12)
    pdf.cell((wT), 15, txt=text, align="C")
    text = ''
    pdf.set_font(font_name, size=10)
    pdf.multi_cell(200, 15, txt=text, align="L")
    kiosks = dict(billing['kiosks']['ids'])
    for kioskKeys in kiosks:
        if(kiosks[kioskKeys]['hardware'] != 0):
            text = "Kiosk Hardware Installment (Group id " + \
                kiosks[kioskKeys]['group'] + ")"
            w = pdf.get_string_width(text)
            pdf.set_font(font_name, size=12)
            pdf.cell(allWidth - 1, 15, txt=text, align="L")

            text = str(kiosks[kioskKeys]['count'])
            w = pdf.get_string_width(text)
            pdf.set_font(font_name, size=12)
            pdf.cell((wQ), 15, txt=text, align="C")

            space = "       "
            wS = pdf.get_string_width(space)
            pdf.set_font(font_name, size=12, style="B")
            pdf.cell((wS), 15, txt=space, align="R")

            text = '${:.2f}'.format((kiosks[kioskKeys]['hardware']))
            w = pdf.get_string_width(text)
            pdf.set_font(font_name, size=12)
            pdf.cell((wU), 15, txt=text, align="C")

            space = "       "
            wS = pdf.get_string_width(space)
            pdf.set_font(font_name, size=12, style="B")
            pdf.cell((wS), 15, txt=space, align="R")

            text = '${:.2f}'.format(
                (kiosks[kioskKeys]['hardware'] * kiosks[kioskKeys]['count']))
            totalVal += float(kiosks[kioskKeys]['hardware']
                              * kiosks[kioskKeys]['count'])
            w = pdf.get_string_width(text)
            pdf.set_font(font_name, size=12)
            pdf.cell((wT), 15, txt=text, align="C")

            text = ''
            pdf.set_font(font_name, size=10)
            pdf.multi_cell(200, 15, txt=text, align="L")

        text = "Kiosk Software Fee (Group id " + \
            kiosks[kioskKeys]['group'] + ")"
        w = pdf.get_string_width(text)
        pdf.set_font(font_name, size=12)
        pdf.cell(allWidth - 1, 15, txt=text, align="L")

        text = str(kiosks[kioskKeys]['count'])
        w = pdf.get_string_width(text)
        pdf.set_font(font_name, size=12)
        pdf.cell((wQ), 15, txt=text, align="C")

        space = "       "
        wS = pdf.get_string_width(space)
        pdf.set_font(font_name, size=12, style="B")
        pdf.cell((wS), 15, txt=space, align="R")

        text = '${:.2f}'.format((kiosks[kioskKeys]['software']))
        w = pdf.get_string_width(text)
        pdf.set_font(font_name, size=12)
        pdf.cell((wU), 15, txt=text, align="C")

        space = "       "
        wS = pdf.get_string_width(space)
        pdf.set_font(font_name, size=12, style="B")
        pdf.cell((wS), 15, txt=space, align="R")

        text = '${:.2f}'.format(
            (kiosks[kioskKeys]['software'] * kiosks[kioskKeys]['count']))
        totalVal += (kiosks[kioskKeys]['software']
                     * kiosks[kioskKeys]['count'])
        w = pdf.get_string_width(text)
        pdf.set_font(font_name, size=12)
        pdf.cell((wT), 15, txt=text, align="C")

        text = ''
        pdf.set_font(font_name, size=10)
        pdf.multi_cell(200, 15, txt=text, align="L")

    text = ''
    pdf.set_font(font_name, size=10, style="B")
    pdf.multi_cell(200, 5, txt=text, align="L")

    subtotal = totalVal
    taxRate = float(info['tax'])/100.0
    tax = totalVal * taxRate
    total = subtotal + tax

    text = 'Subtotal: ' + '${:.2f}'.format(subtotal)
    pdf.set_font(font_name, size=12, style="B")
    pdf.multi_cell(200, 15, txt=text, align="L")

    text = 'Sales Tax (' + \
        '{:.2f}'.format(info['tax']) + '%): ' + '${:.2f}'.format(tax)
    pdf.set_font(font_name, size=12, style="B")
    pdf.multi_cell(200, 15, txt=text, align="L")

    text = 'Total: ' + '${:.2f}'.format(total)
    pdf.set_font(font_name, size=12, style="B")
    pdf.multi_cell(200, 15, txt=text, align="L")

    try:
        tmp_filename = '/tmp/' + estNameStr + "/invoices/" + str(date) + "-invoice.pdf"
        pdf.output(tmp_filename)
    except Exception as e:
        try:
            os.mkdir('/tmp/' + estNameStr + '/')
            os.mkdir('/tmp/' + estNameStr + '/invoices/')
            tmp_filename = '/tmp/' + estNameStr + "/invoices/" + str(date) + "-invoice.pdf"
            pdf.output(tmp_filename)
        except Exception as e:
            os.mkdir('/tmp/' + estNameStr + '/invoices/')
            tmp_filename = '/tmp/' + estNameStr + "/invoices/" + str(date) + "-invoice.pdf"
            pdf.output(tmp_filename)
    # return('ok', 200)
    return send_file(tmp_filename, attachment_filename=str(str(date) + "-cedar-invoice.pdf"), as_attachment=True, mimetype='application/pdf')
