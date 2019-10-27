# -*- coding: UTF-8 -*-
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

menu = "lunch"

pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu
menuInfo = db.reference(pathMenu).get()
#print(menuInfo)
categories = list(menuInfo["categories"])
baseItms = []
descrips = []
exInfo = []


for itms in categories:
    #print(list(menuInfo["categories"][itms]))
    currArr2 = []
    currArr3 = []
    currArr4 = []
    for ll in range(len(list(menuInfo["categories"][itms]))):
        itmArr = []
        itx = (list(menuInfo["categories"][itms])[ll])
        itx2 = itx.replace(" ","-")
        currArr2.append([itx,itx2])
        descrip = (menuInfo["categories"][itms][itx]["descrip"])
        exinfo = (menuInfo["categories"][itms][itx]["extra-info"])
        mN = (list(menuInfo["categories"][itms][itx])[2:])
        currArr3.append(descrip)
        currArr4.append(exinfo)
        #print(mN)
        for mods in mN:
            max = int(menuInfo["categories"][itms][itx][mods]["max"]) - int(menuInfo["categories"][itms][itx][mods]["min"])
            min = int(menuInfo["categories"][itms][itx][mods]["min"])
            opt = list(menuInfo["categories"][itms][itx][mods]["info"])
    baseItms.append(currArr2)
    descrips.append(currArr3)
    exInfo.append(currArr4)
    currArr2 = []
    currArr3 = []
    currArr4 = []

modsName = []
modsItm = []
for itms in categories:
    catArr = []
    catArr2 = []
    for mx in list(menuInfo["categories"][itms]):
        tmpArr = []
        for tt in list(menuInfo["categories"][itms][mx])[2:]:
            max = int(menuInfo["categories"][itms][mx][tt]["max"]) - int(menuInfo["categories"][itms][mx][tt]["min"])
            min = menuInfo["categories"][itms][mx][tt]["min"]
            tmpArr.append([tt,min,max])
        catArr.append(tmpArr)
    modsName.append(catArr)


for itms2 in categories:
    catArr = []
    for mx2 in list(menuInfo["categories"][itms2]):
        #print(mx)
        print("\n")
        tmpArr = []
        for tt2 in list(menuInfo["categories"][itms2][mx2])[2:]:
            tmpArr2 = []
            for hnn in list(menuInfo["categories"][itms2][mx2][tt2]["info"]):
                print([hnn,menuInfo["categories"][itms2][mx2][tt2]["info"][hnn]])
                tmpArr2.append([hnn,menuInfo["categories"][itms2][mx2][tt2]["info"][hnn]])
            tmpArr.append(tmpArr2)
        catArr.append(tmpArr)
    modsItm.append(catArr)







#prinArr = [ [ [ ["sizes", 1, 0, [['standard', 6.55]]], ["sides" , 1 , 0,[ ["bacon fries",1], ["fries",0] ] ] ] , [["sizes", 1,0,[["standard",6]]], ["toppings",0,2,[["bacon",1],["cheese",1]]]]], [ [["sizes",1,0,[["11 in", 8.9],["17 in", 11.5]]]]]]

#mods =    [ [ [ ['sizes', 1, 0, [['standard', 6.55]]], ['toppings', 0, 3, [['avaocado', 0.85], ['bacon', 0.65], ['cheese', 0.15] ] ] ] ], [[['sizes', 1, 0, [['11 in', 8.9], ['17 in', 11.5]]]]]]

print("\n")
print(baseItms)
print(categories)
print(descrips)
print(exInfo)
print(modsName[0][0][0][0])
print(modsItm[0][0][0])





print(" ")
print("\n")
