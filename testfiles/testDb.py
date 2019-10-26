import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import uuid
import time
import datetime
import pytz
estNameStr = 'testraunt'
location = 'cedar-location-1'
tz = pytz.timezone("America/Los_Angeles")
#print(datetime.datetime.now(tz).weekday())
day = "TUE"
# Use a service account
cred = credentials.Certificate('/Users/caleb/Documents/GitHub/CedarFlask/CedarChatbot-b443efe11b73.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://cedarchatbot.firebaseio.com/'
})

curMin = float(datetime.datetime.now(tz).minute) / 100.0
curHr = float(datetime.datetime.now(tz).hour)
curTime = curHr + curMin
#print(curTime)
#print(day)
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
    if((sortedHr[sh] <= curTime <= sortedHr[sh+1])== True):
        menuKey = sh
        break


for sh2 in range(len(schedlist)):
    if(sortedHr[menuKey] == schedule[schedlist[sh2]]):
        menu = (schedlist[sh2])
        break

print(menu)

pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu
menuInfo = db.reference(pathMenu).get()
#print(menuInfo)
categories = list(menuInfo["categories"])
baseItms = []
descrips = []
exInfo = []
modsArr = []
for itms in categories:
    #print(list(menuInfo["categories"][itms]))
    currArr = []
    currArr2 = []
    currArr3 = []
    currArr4 = []
    currArr5 = []
    for ll in range(len(list(menuInfo["categories"][itms]))):
        itmArr = []
        itx = (list(menuInfo["categories"][itms])[ll])
        itx2 = itx.replace(" ","-")
        currArr2.append([itx,itx2])
        descrip = (menuInfo["categories"][itms][itx]["descrip"])
        exinfo = (menuInfo["categories"][itms][itx]["extra-info"])
        currArr4.append(exinfo)
        currArr3.append(descrip)
        modNames = (list(menuInfo["categories"][itms][itx])[2:])
        for mods in modNames:
            max = int(menuInfo["categories"][itms][itx][mods]["max"]) - int(menuInfo["categories"][itms][itx][mods]["min"])
            modArr = [mods,menuInfo["categories"][itms][itx][mods]["min"],max]
            opt = list(menuInfo["categories"][itms][itx][mods]["info"])
            modArr2 = []
            for oo in opt:
                modArr2.append([oo,menuInfo["categories"][itms][itx][mods]["info"][oo]])
            modArr.append(modArr2)
        currArr5.append(modArr)
        modArr = []
        itmArr = []
    baseItms.append(currArr2)
    descrips.append(currArr3)
    exInfo.append(currArr4)
    modsArr.append([currArr5])
    currArr2 = []
    currArr3 = []
    currArr4 = []
    currArr5 = []


prinArr = [ [[["sizes",1,0,[['standard',6.55]]],["sides",1,0,[["bacon fries",1],["fries",0]]]] , [["sizes", 1,0,[["standard",6]]], ["toppings",0,2,[["bacon",1],["cheese",1]]]]], [ [["sizes",1,0,[["11 in", 9],["17 in", 11.25]]],["toppings", 0,2,[["extra cheese", 0.56],["extra pepperoni", 1]]]] ] ]

print(baseItms)
print(categories)
print(descrips)
print(exInfo)
print(modsArr)
print(prinArr)

print(" ")
print("\n")
