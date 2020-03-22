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
from flask import redirect, url_for, send_file
from flask import render_template
from flask_session import Session
from flask_sslify import SSLify
from square.client import Client
from werkzeug.datastructures import ImmutableOrderedMultiDict
from flask import Blueprint, render_template, abort
from Cedar.collect_menu import findMenu, getDispNameEst, getDispNameLoc
from Cedar.admin.admin_panel import getSquare, checkAdminToken, checkLocation
import random

infoFile = open("info.json")
info = json.load(infoFile)
botNumber = info["number"]
mainLink = info['mainLink']

adminSessTime = 3599
client = plivo.RestClient(auth_id='MAYTVHN2E1ZDY4ZDA2YZ',
                          auth_token='ODgzZDA1OTFiMjE2ZTRjY2U4ZTVhYzNiODNjNDll')
cred = credentials.Certificate('CedarChatbot-b443efe11b73.json')
storage_client = storage.Client.from_service_account_json(
    'CedarChatbot-b443efe11b73.json')
bucket = storage_client.get_bucket("cedarchatbot.appspot.com")
sender = 'cedarrestaurantsbot@gmail.com'
emailPass = "cda33d07-f6bd-479e-806f-5d039ae2fa2d"
# smtpObj = smtplib.SMTP_SSL("smtp.gmail.com", 465)
# smtpObj.login(sender, emailPass)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
dayNames = ["MON", "TUE", "WED", "THURS", "FRI", "SAT", "SUN"]

global tzGl
adminSessTime = 3599
global locationsPaths
tzGl = {}
locationsPaths = {}

menu_panel_blueprint = Blueprint('menu', __name__, template_folder='templates')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@menu_panel_blueprint.route('/<estNameStr>/<location>/create-menu', methods=["GET"])
def createMenu(estNameStr, location):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
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
    return(render_template("POS/AdminMini/createMenu.html"))


@menu_panel_blueprint.route('/<estNameStr>/<location>/add-menu', methods=["POST"])
def addMenu(estNameStr, location):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = dict((request.form))
    new_menu = rsp["name"]
    menu_ref = db.reference(
        '/restaurants/' + estNameStr + '/'+location+"/menu")
    menu_ref.update({str(new_menu): {"active": True}})
    return(redirect(url_for("menu.addCat", estNameStr=estNameStr, location=location, menu=new_menu)))


@menu_panel_blueprint.route('/<estNameStr>/<location>/view-menu')
def viewMenu(estNameStr, location):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
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
    menu_ref = db.reference(
        '/restaurants/' + estNameStr + '/' + location + '/menu')
    menu_keys = list((menu_ref.get()).keys())
    return(render_template("POS/AdminMini/dispMenu.html", menus=menu_keys))


@menu_panel_blueprint.route('/<estNameStr>/<location>/edit-menu-<menu>')
def editMenu(estNameStr, location, menu):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
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
    menu_data = db.reference(
        '/restaurants/' + estNameStr + '/' + location + '/menu/'+str(menu)).get()
    try:
        cats = list(dict(menu_data["categories"]).keys())
    except Exception as e:
        cats = []
    return(render_template("POS/AdminMini/menuDetails.html", cats=cats, menu=menu))


@menu_panel_blueprint.route('/<estNameStr>/<location>/rem-cat-<menu>~<category>')
def remCategories(estNameStr, location, menu, category):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
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
    menu_data = db.reference('/restaurants/' + estNameStr + '/' +
                             location + '/menu/'+str(menu)+"/categories/"+category).delete()
    # return(render_template("POS/AdminMini/catDetails.html",items=items,menu=menu,cat=category))
    return(redirect(url_for("menu.viewMenu", estNameStr=estNameStr, location=location)))


@menu_panel_blueprint.route('/<estNameStr>/<location>/view-cat-<menu>~<category>')
def viewCategories(estNameStr, location, menu, category):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
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
    menu_data = dict(db.reference('/restaurants/' + estNameStr +
                                  '/' + location + '/menu/'+str(menu)).get())
    items = []
    try:
        for itx in list(dict(menu_data["categories"][category]).keys()):
            itx2 = str(itx).replace(" ", "-")
            items.append(itx2)
        return(render_template("POS/AdminMini/catDetails.html", items=items, menu=menu, cat=category))
    except Exception as e:
        return(redirect(url_for("viewMenu", estNameStr=estNameStr, location=location)))


@menu_panel_blueprint.route('/<estNameStr>/<location>/remOpt~<menu>~<cat>~<item>~<mods>~<opt>')
def remOpt(estNameStr, location, menu, cat, item, mods, opt):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    opt_ref = db.reference('/restaurants/' + estNameStr + '/' + location +
                           '/menu/'+str(menu)+"/categories/"+cat+"/"+item+"/"+mods+"/info/"+opt)
    opt_ref.delete()
    return(redirect(url_for("menu.viewItem", estNameStr=estNameStr, location=location, menu=menu, cat=cat, item=item)))


@menu_panel_blueprint.route('/<estNameStr>/<location>/addOpt~<menu>~<cat>~<item>~<mods>')
def addOpt(estNameStr, location, menu, cat, item, mods):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
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
    return(render_template("POS/AdminMini/addOpt.html", menu=menu, cat=cat, item=item, mods=mods))


@menu_panel_blueprint.route('/<estNameStr>/<location>/addOptX~<menu>~<cat>~<item>~<mods>', methods=["POST"])
def addOptX(estNameStr, location, menu, cat, item, mods):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    name = str(rsp["name"])
    price = float(rsp["price"])
    opt_ref = db.reference('/restaurants/' + estNameStr + '/' + location +
                           '/menu/'+str(menu)+"/categories/"+cat+"/"+item+"/"+mods+"/info")
    opt_ref.update({name: price})
    return(redirect(url_for("menu.viewItem", estNameStr=estNameStr, location=location, menu=menu, cat=cat, item=item)))


@menu_panel_blueprint.route('/<estNameStr>/<location>/editMax~<menu>~<cat>~<item>~<mods>', methods=["POST"])
def editMax(estNameStr, location, menu, cat, item, mods):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    max = int(rsp["max"])
    opt_ref = db.reference('/restaurants/' + estNameStr + '/' + location +
                           '/menu/'+str(menu)+"/categories/"+cat+"/"+item+"/"+mods)
    opt_ref.update({"max": max})
    return(redirect(url_for("menu.viewItem", estNameStr=estNameStr, location=location, menu=menu, cat=cat, item=item)))


@menu_panel_blueprint.route('/<estNameStr>/<location>/editMin~<menu>~<cat>~<item>~<mods>', methods=["POST"])
def editMin(estNameStr, location, menu, cat, item, mods):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    min = int(rsp["min"])
    opt_ref = db.reference('/restaurants/' + estNameStr + '/' + location +
                           '/menu/'+str(menu)+"/categories/"+cat+"/"+str(item)+"/"+str(mods))
    opt_ref.update({"min": min})
    return(redirect(url_for("menu.viewItem", estNameStr=estNameStr, location=location, menu=menu, cat=cat, item=item)))


@menu_panel_blueprint.route('/<estNameStr>/<location>/editDescrip~<menu>~<cat>~<item>', methods=["POST"])
def editDescrip(estNameStr, location, menu, cat, item):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    descrip = str(rsp["descrip"])
    opt_ref = db.reference('/restaurants/' + estNameStr + '/' +
                           location + '/menu/'+str(menu)+"/categories/"+cat+"/"+str(item))
    opt_ref.update({"descrip": descrip})
    return(redirect(url_for("menu.viewItem", estNameStr=estNameStr, location=location, menu=menu, cat=cat, item=item)))


@menu_panel_blueprint.route('/<estNameStr>/<location>/editExtras~<menu>~<cat>~<item>', methods=["POST"])
def editExtra(estNameStr, location, menu, cat, item):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    extra = str(rsp["extra"])
    opt_ref = db.reference('/restaurants/' + estNameStr + '/' +
                           location + '/menu/'+str(menu)+"/categories/"+cat+"/"+str(item))
    opt_ref.update({"extra-info": extra})
    return(redirect(url_for("menu.viewItem", estNameStr=estNameStr, location=location, menu=menu, cat=cat, item=item)))


@menu_panel_blueprint.route('/<estNameStr>/<location>/editImg~<menu>~<cat>~<item>')
def editImg(estNameStr, location, menu, cat, item):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
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
    return(render_template("POS/AdminMini/editImg.html", menu=menu, cat=cat, item=item))


@menu_panel_blueprint.route('/<estNameStr>/<location>/addModIcon-<menu>~<cat>~<item>~<mod>~<opt>')
def editIcon(estNameStr, location, menu, cat, item, mod, opt):
    return(render_template("POS/AdminMini/addModImg.html", menu=menu, cat=cat, item=item, mod=mod, opt=opt))


@menu_panel_blueprint.route('/<estNameStr>/<location>/addModIcon2-<menu>~<cat>~<item>~<mod>~<opt>', methods=['POST'])
def editIconConfirm(estNameStr, location, menu, cat, item, mod, opt):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    size = str(rsp['size'])
    imgLink = str(rsp['link'])
    remStart = imgLink.find('src=')
    remEnd = imgLink.find('>')
    putLink = "width=" + size + " " + imgLink[remStart:remEnd].replace('"', '')
    print(putLink)
    iconRef = db.reference('/restaurants/' + estNameStr + '/' + location +
                           '/menu/'+str(menu)+"/categories/"+cat+"/"+str(item)+"/"+mod+"/infoimg")
    iconRef.update({opt: putLink})
    return(redirect(url_for("menu.viewItem", estNameStr=estNameStr, location=location, menu=menu, cat=cat, item=item)))


@menu_panel_blueprint.route('/<estNameStr>/<location>/addImgX~<menu>~<cat>~<item>', methods=["POST"])
def editImgX(estNameStr, location, menu, cat, item):
    UPLOAD_FOLDER = '/tmp/' + estNameStr+"/imgs/"
    file = request.files['img']
    filename = secure_filename(file.filename)
    try:
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        upName = "/"+estNameStr+"/imgs/"+file.filename
        blob = bucket.blob(upName)
        fileId = str(uuid.uuid4())
        print(fileId)
        d = estNameStr + "/" + fileId
        d = bucket.blob(d)
        d.upload_from_filename(str(str(
            UPLOAD_FOLDER)+str(file.filename).replace(" ", "_")), content_type='image/jpeg')
        url = str(d.public_url)
        opt_ref = db.reference('/restaurants/' + estNameStr + '/' +
                               location + '/menu/'+str(menu)+"/categories/"+cat+"/"+str(item))
        opt_ref.update({"img": url})
    except Exception as e:
        try:
            os.mkdir(str('/tmp/' + estNameStr + '/'))
        except Exception as e:
            pass
        os.mkdir(str('/tmp/' + estNameStr + '/imgs/'))
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        upName = "/"+estNameStr+"/imgs/"+file.filename
        blob = bucket.blob(upName)
        fileId = str(uuid.uuid4())
        print(fileId)
        d = estNameStr + "/" + fileId
        d = bucket.blob(d)
        d.upload_from_filename(str(str(
            UPLOAD_FOLDER)+str(file.filename).replace(" ", "_")), content_type='image/jpeg')
        url = str(d.public_url)
        opt_ref = db.reference('/restaurants/' + estNameStr + '/' +
                               location + '/menu/'+str(menu)+"/categories/"+cat+"/"+str(item))
        opt_ref.update({"img": url})
    os.remove('/tmp/' + estNameStr + "/imgs/" + filename)
    return(redirect(url_for("menu.viewItem", estNameStr=estNameStr, location=location, menu=menu, cat=cat, item=item)))


@menu_panel_blueprint.route('/<estNameStr>/<location>/addCpn~<menu>~<category>~<item>~<modName>~<modItm>')
def addCpn(estNameStr, location, menu, category, item, modName, modItm):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
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
    return render_template("POS/AdminMini/addCpn.html", menu=menu, cat=category, item=item, modName=modName, modItm=modItm)


@menu_panel_blueprint.route('/<estNameStr>/<location>/addCpn2~<menu>~<category>~<item>~<modName>~<modItm>', methods=["POST"])
def addCpn2(estNameStr, location, menu, category, item, modName, modItm):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    type = rsp["type"]
    name = rsp["name"]
    amount = float(rsp["amount"])
    min = int(rsp["min"])
    limit = int(rsp["lim"])
    discRef = db.reference('/restaurants/' + estNameStr +
                           '/'+location + '/discounts/' + menu)
    discRef.update({
        str(name): {
            'cat': str(category),
            'itm': str(item),
            'mods': [modName, modItm],
            'type': str(type),
            'amt': amount,
            'lim': limit,
            'min': min
        }
    })
    # return str(rsp) +"-"+str(menu)+"-"+str(category)+"-"+str(item)
    return(redirect(url_for("admin_panel.panel", estNameStr=estNameStr, location=location)))


@menu_panel_blueprint.route('/<estNameStr>/<location>/remCpn~<menu>~<cpn>')
def remCpn(estNameStr, location, menu, cpn):
    cpn_ref = db.reference('/restaurants/' + estNameStr +
                           '/' + location + '/discounts/' + menu + '/' + cpn)
    cpn_ref.delete()
    return(redirect(url_for("admin_panel.panel", estNameStr=estNameStr, location=location)))


@menu_panel_blueprint.route('/<estNameStr>/<location>/importMenu', methods=['POST'])
def uploadMenu(estNameStr, location):
    file = request.files['newMenu']
    newMenu = dict(json.load(file))
    menu_ref = db.reference(
        '/restaurants/' + estNameStr + '/' + location + '/menu')
    menu_ref.update(newMenu)
    return(redirect(url_for("menu.viewMenu", estNameStr=estNameStr, location=location)))


@menu_panel_blueprint.route('/<estNameStr>/<location>/exportMenu-<menu>')
def exportMenu(estNameStr, location, menu):
    menu_ref = db.reference('/restaurants/' + estNameStr +
                            '/' + location + '/menu/' + menu)
    menu_dict = {menu: dict(menu_ref.get())}
    print(menu_dict)
    try:
        with open(str('/tmp/' + estNameStr + '/menus/' + location + '-' + menu + '-menu.json'), 'w') as outfile:
            json.dump(menu_dict, outfile)
    except Exception as e:
        try:
            os.mkdir(str('/tmp/' + estNameStr + '/'))
        except Exception as e:
            pass
        os.mkdir(str('/tmp/' + estNameStr + '/menus/'))
        with open(str('/tmp/' + estNameStr + '/menus/' + location + '-' + menu + '-menu.json'), 'w') as outfile:
            json.dump(menu_dict, outfile)
    try:
        return send_file(str('/tmp/' + estNameStr + '/menus/' + location + '-' + menu + '-menu.json'), as_attachment=True, mimetype='application/json', attachment_filename=str(location + '-' + menu + '-menu.json'))
        # os.remove(str(estNameStr + '/menus/' + location + '-' + menu + '-menu.json'))
    except Exception as e:
        print(e)
        return(redirect(url_for("admin_panel.panel", estNameStr=estNameStr, location=location)))


@menu_panel_blueprint.route('/<estNameStr>/<location>/act-menu')
def chooseMenu(estNameStr, location):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
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
    menu_ref = db.reference(
        '/restaurants/' + estNameStr + '/' + location + '/menu')
    menu_keys = list((menu_ref.get()).keys())
    menu_data = menu_ref.get()
    active = []
    inactive = []
    for keys in menu_keys:
        if(menu_data[keys]["active"] == True):
            active.append(keys)
        else:
            inactive.append(keys)
    return(render_template("POS/AdminMini/removeMenu.html", menusActive=active, menusInactive=inactive))


@menu_panel_blueprint.route('/<estNameStr>/<location>/activate-menu-<menu>')
def enableMenu(estNameStr, location, menu):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
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
    menu_ref = db.reference('/restaurants/' + estNameStr +
                            '/' + location + '/menu/'+str(menu))
    menu_ref.update({"active": True})
    return(redirect(url_for("admin_panel.panel", estNameStr=estNameStr, location=location)))


@menu_panel_blueprint.route('/<estNameStr>/<location>/deactivate-menu-<menu>')
def disableMenu(estNameStr, location, menu):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
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
    menu_ref = db.reference('/restaurants/' + estNameStr +
                            '/' + location + '/menu/'+str(menu))
    menu_ref.update({"active": False})
    return(redirect(url_for("admin_panel.panel", estNameStr=estNameStr, location=location)))


@menu_panel_blueprint.route("/<estNameStr>/<location>/remitm~<menu>~<cat>~<item>")
def removeItem(estNameStr, location, menu, cat, item):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    item = str(item).replace("-", " ")
    # #print(item)
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
    item_ref = db.reference('/restaurants/' + estNameStr + '/' + location +
                            '/menu/'+str(menu)+"/categories/"+str(cat)+"/"+str(item))
    item_ref.delete()
    return(redirect(url_for("viewCategories", location=location, menu=menu, category=cat)))


@menu_panel_blueprint.route("/<estNameStr>/<location>/viewitm~<menu>~<cat>~<item>")
def viewItem(estNameStr, location, menu, cat, item):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    # #print(menu,cat,item)
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
    item_ref = db.reference('/restaurants/' + estNameStr + '/' +
                            location + '/menu/'+str(menu)+"/"+str(cat)+"/"+str(item)).get()
    if(item_ref == None):
        item = str(item).replace("-", " ")
        # #print(item)
        itemInfo = db.reference('/restaurants/' + estNameStr + '/' + location +
                                '/menu/'+str(menu)+"/categories/"+str(cat)+"/"+str(item)).get()
        return(render_template("POS/AdminMini/editItem.html", menu=menu, cat=cat, item=item, itemInfo=itemInfo))


@menu_panel_blueprint.route("/<estNameStr>/<location>/addMod-<menu>~<cat>~<item>")
def addMod(estNameStr, location, menu, cat, item):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
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
    return(render_template("POS/AdminMini/addMod2.html", location=location, menu=menu, cat=cat, item=item))


@menu_panel_blueprint.route("/<estNameStr>/<location>/addModX2~<menu>~<cat>~<item>", methods=["POST"])
def addModX(estNameStr, location, menu, cat, item):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    # return(str(rsp))
    name = rsp["name"]
    # try:
    max = int(rsp["max"])
    min = int(rsp["min"])
    item_ref = db.reference('/restaurants/' + estNameStr + '/' + location +
                            '/menu/'+str(menu)+"/categories/"+str(cat)+"/"+str(item)+"/"+str(name))
    item_ref.update({"max": max, "min": min})
    mods = []
    prices = []
    rsp = dict((request.form))
    for keys in range((int((int(len(list(rsp.keys())))-3)/2))):
        prices.append(rsp[str("prce-")+str(keys+1)])
        mods.append(rsp[str("name-")+str(keys+1)])
    for m in range(len(mods)):
        item_ref = db.reference('/restaurants/' + estNameStr + '/' + location + '/menu/'+str(
            menu)+"/categories/"+str(cat)+"/"+str(item)+"/"+str(name)+"/info")
        item_ref.update({str(mods[m]): float(prices[m])})
    '''
    except Exception:
        return(render_template("POS/AdminMini/addMod.html",location=location,menu=menu,cat=cat,item=name))
    '''
    return(redirect(url_for("menu.viewItem", estNameStr=estNameStr, location=location, menu=menu, cat=cat, item=item)))


@menu_panel_blueprint.route("/<estNameStr>/<location>/remMod~<menu>~<cat>~<item>~<mod>")
def remMod(estNameStr, location, menu, cat, item, mod):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
    item_ref = db.reference('/restaurants/' + estNameStr + '/' + location +
                            '/menu/'+str(menu)+"/categories/"+str(cat)+"/"+str(item)+"/"+str(mod))
    item_ref.delete()
    return(redirect(url_for("menu.viewItem", estNameStr=estNameStr, location=location, menu=menu, cat=cat, item=item)))


@menu_panel_blueprint.route("/<estNameStr>/<location>/addItm~<menu>~<cat>")
def addItem(estNameStr, location, menu, cat):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
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
    return(render_template("POS/AdminMini/addItm.html", location=location, menu=menu, cat=cat))


@menu_panel_blueprint.route("/<estNameStr>/<location>/addItmX~<menu>~<cat>", methods=["POST"])
def addItem2(estNameStr, location, menu, cat):
    UPLOAD_FOLDER = '/tmp/' + estNameStr+"/imgs/"
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
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    menu = rsp["menu"]
    name = rsp["name"]
    descrip = rsp["descrip"]
    exinfo = rsp["exinfo"]
    try:
        file = request.files['img']
        if file.filename == '':
            menu_ref = db.reference('/restaurants/' + estNameStr + '/' +
                                    location + '/menu/'+str(menu)+"/categories/"+str(cat))
            menu_ref.update({str(name): {"descrip": str(descrip), "extra-info": str(
                exinfo), "img": "", "uuid": str("a"+str(random.randint(10000, 99999)))}})
            return(render_template("POS/AdminMini/addMod.html", location=location, menu=menu, cat=cat, item=name))
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                upName = "/"+estNameStr+"/imgs/"+file.filename
                blob = bucket.blob(upName)
                fileId = str(uuid.uuid4())
                d = estNameStr + "/" + fileId
                d = bucket.blob(d)
                d.upload_from_filename(
                    str(str(UPLOAD_FOLDER)+"/"+str(file.filename)), content_type='image/jpeg')
                url = str(d.public_url)
                menu_ref = db.reference(
                    '/restaurants/' + estNameStr + '/' + location + '/menu/'+str(menu)+"/categories/"+str(cat))
                menu_ref.update({str(name): {"descrip": str(descrip), "extra-info": str(
                    exinfo), "img": url, "uuid": str("a"+str(random.randint(10000, 99999)))}})
            except Exception as e:
                try:
                    os.mkdir(str('/tmp/' + estNameStr + '/'))
                except Exception as e:
                    pass
                os.mkdir(str('/tmp/' + estNameStr + '/imgs/'))
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                upName = "/"+estNameStr+"/imgs/"+file.filename
                blob = bucket.blob(upName)
                fileId = str(uuid.uuid4())
                d = estNameStr + "/" + fileId
                d = bucket.blob(d)
                d.upload_from_filename(
                    str(str(UPLOAD_FOLDER)+"/"+str(file.filename)), content_type='image/jpeg')
                url = str(d.public_url)
                menu_ref = db.reference(
                    '/restaurants/' + estNameStr + '/' + location + '/menu/'+str(menu)+"/categories/"+str(cat))
                menu_ref.update({str(name): {"descrip": str(descrip), "extra-info": str(
                    exinfo), "img": url, "uuid": str("a"+str(random.randint(10000, 99999)))}})
            os.remove('/tmp/' + estNameStr + "/imgs/" + filename)
        else:
            menu_ref = db.reference('/restaurants/' + estNameStr + '/' +
                                    location + '/menu/'+str(menu)+"/categories/"+str(cat))
            menu_ref.update({str(name): {"descrip": str(descrip), "extra-info": str(
                exinfo), "img": "", "uuid": str("a"+str(random.randint(10000, 99999)))}})
    except Exception:
        menu_ref = db.reference('/restaurants/' + estNameStr + '/' +
                                location + '/menu/'+str(menu)+"/categories/"+str(cat))
        menu_ref.update({str(name): {"descrip": str(descrip), "extra-info": str(exinfo),
                                     "img": "", "uuid": str("a"+str("a"+str(random.randint(10000, 99999))))}})
    return(render_template("POS/AdminMini/addMod.html", location=location, menu=menu, cat=cat, item=name))


@menu_panel_blueprint.route("/<estNameStr>/<location>/addcat~<menu>")
def addCat(estNameStr, location, menu):
    if(checkLocation(estNameStr, location) == 1):
        return(redirect(url_for("find_page.findRestaurant")))
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
    return(render_template("POS/AdminMini/addCat.html", location=location, menu=menu))


@menu_panel_blueprint.route("/<estNameStr>/<location>/addcatSubmit", methods=["POST"])
def addCatX(estNameStr, location):
    UPLOAD_FOLDER = '/tmp/' + estNameStr+"/imgs/"
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
            menu_ref = db.reference(
                '/restaurants/' + estNameStr + '/' + location + '/menu/'+str(menu)+"/categories")
            menu_ref.update({str(cat): {str(name): {"descrip": str(
                descrip), "extra-info": str(exinfo), "img": ""}}})
            return(render_template("POS/AdminMini/addMod.html", location=location, menu=menu, cat=cat, item=name))
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                upName = "/"+estNameStr+"/imgs/"+file.filename
                blob = bucket.blob(upName)
                fileId = str(uuid.uuid4())
                d = estNameStr + "/" + fileId
                d = bucket.blob(d)
                d.upload_from_filename(
                    str(str(UPLOAD_FOLDER)+"/"+str(file.filename)), content_type='image/jpeg')
                url = str(d.public_url)
                menu_ref = db.reference(
                    '/restaurants/' + estNameStr + '/' + location + '/menu/'+str(menu)+"/categories/"+str(cat))
                menu_ref.update({str(name): {"descrip": str(descrip), "extra-info": str(
                    exinfo), "img": url, "uuid": str("a"+str(random.randint(10000, 99999)))}})
            except Exception as e:
                try:
                    os.mkdir(str('/tmp/' + estNameStr + '/'))
                except Exception as e:
                    pass
                os.mkdir(str('/tmp/' + estNameStr + '/imgs/'))
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                upName = "/"+estNameStr+"/imgs/"+file.filename
                blob = bucket.blob(upName)
                fileId = str(uuid.uuid4())
                d = estNameStr + "/" + fileId
                d = bucket.blob(d)
                d.upload_from_filename(
                    str(str(UPLOAD_FOLDER)+"/"+str(file.filename)), content_type='image/jpeg')
                url = str(d.public_url)
                menu_ref = db.reference(
                    '/restaurants/' + estNameStr + '/' + location + '/menu/'+str(menu)+"/categories")
                menu_ref.update({str(cat): {str(name): {"descrip": str(descrip), "extra-info": str(
                    exinfo), "img": url, "uuid": str("a"+str(random.randint(10000, 99999)))}}})
            os.remove('/tmp/' + estNameStr + "/imgs/" + filename)
        else:
            menu_ref = db.reference(
                '/restaurants/' + estNameStr + '/' + location + '/menu/'+str(menu)+"/categories")
            menu_ref.update({str(cat): {str(name): {"descrip": str(descrip), "extra-info": str(
                exinfo), "img": "", "uuid": str("a"+str(random.randint(10000, 99999)))}}})
    except Exception:
        menu_ref = db.reference(
            '/restaurants/' + estNameStr + '/' + location + '/menu/'+str(menu)+"/categories")
        menu_ref.update({str(cat): {str(name): {"descrip": str(descrip), "extra-info": str(
            exinfo), "img": "", "uuid": str("a"+str(random.randint(10000, 99999)))}}})
    return(render_template("POS/AdminMini/addMod.html", location=location, menu=menu, cat=cat, item=name))
