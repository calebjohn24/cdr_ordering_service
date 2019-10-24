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
        print(itms)
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



print(menuItems)
print(len(menuItems))
print(" ")
print("\n")
