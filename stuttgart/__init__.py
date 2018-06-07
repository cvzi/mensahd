import datetime
import os
import json
import urllib
import re

import pytz
import requests
from bs4 import BeautifulSoup

from pyopenmensa.feed import LazyBuilder


metaJson = os.path.join(os.path.dirname(__file__), "stuttgart.json")

metaTemplateFile = os.path.join(os.path.dirname(__file__), "metaTemplate_stuttgart.xml")

template_metaURL = "%sstuttgart/meta/%s.xml"
template_todayURL = "%sstuttgart/today/%s.xml"
template_fullURL = "%sstuttgart/all/%s.xml"

weekdaysMap = [
    ("Mo", "monday"),
    ("Di", "tuesday"),
    ("Mi", "wednesday"),
    ("Do", "thursday"),
    ("Fr", "friday"),
    ("Sa", "saturday"),
    ("So", "sunday")
    ]

url = r"https://sws2.maxmanager.xyz/inc/ajax-php_konnektor.inc.php"
sourceUrl = r"https://www.studierendenwerk-stuttgart.de/essen/speiseplan/"
roles = ('student', 'employee', 'other')
price_pattern = re.compile('\d+,\d\d')

ingredients = {
    "Ei" : "Ei",
    "En" : "Erdnuss",
    "Fi" : "Fisch",
    "GlW" : "Weizen",
    "GlD" : "Dinkel",
    "GlKW" : "Khorasan-Weizen",
    "GlR" : "Roggen",
    "GlG" : "Gerste",
    "GlH" : "Hafer",
    "Kr" : "Krebstiere Krusten- und Schalentiere",
    "La" : "Milch und Laktose",
    "Lu" : "Lupine",
    "NuM" : "Mandeln",
    "NuH" : "Haselnüsse",
    "NuW" : "Walnüsse",
    "NuC" : "Cashewnüsse",
    "NuPe" : "Pecannüsse",
    "NuPa" : "Paranüsse",
    "NuPi" : "Pistazien",
    "NuMa" : "Macadamianüsse",
    "Se" : "Sesam",
    "Sf" : "Senf",
    "Sl" : "Sellerie",
    "So" : "Soja",
    "Sw" : "Schwefeldioxid SO2 und Sulfite",
    "Wt" : "Weichtiere",
    "1" : "mit Konservierungsstoffen",
    "2" : "mit Farbstoffen",
    "3" : "mit Antioxidationsmitteln",
    "4" : "mit Geschmacksverstärkern",
    "5" : "geschwefelt",
    "6" : "gewachst",
    "7" : "mit Phosphaten",
    "8" : "mit Süßungsmitteln",
    "9" : "enthält eine Phenylalaninquelle",
    "10" : "geschwärzt",
    "11" : "mit Alkohol"
    }

def parse_url(canteen, locId, day=None):

    if day is None:
        day = datetime.date.today()

    date = day.strftime("%Y-%m-%d")

    headers = {
        'Host': 'sws2.maxmanager.xyz',
        'X-Requested-With' : 'XMLHttpRequest',
        'Referer' :   'https://sws2.maxmanager.xyz/',
        'User-Agent': 'Mozilla/5.0',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Accept-Language': 'de-De,de'
        }
          
    startThisWeek = day - datetime.timedelta(days=day.weekday())
    startNextWeek = startThisWeek + datetime.timedelta(days=7)

    startThisWeek = startThisWeek.strftime("%Y-%m-%d")
    startNextWeek = startNextWeek.strftime("%Y-%m-%d")

    data = "func=make_spl&locId=%s&date=%s&lang=de&startThisWeek=%s&startNextWeek=%s" % (locId, date, startThisWeek, startNextWeek)

    r = requests.post(url, data = data, headers = headers)

    content = r.content.decode("utf-8")

    document = BeautifulSoup(content, "html.parser")


    divs = document.find("div", {"class": "container-fluid"}).find_all("div", {"class", "row"})

    nextIsMenu = False
    categoryName = ""
    foundAny = False
    for div in divs:

        
        isCat = div.find("div", {"class": "gruppenname"})
        if isCat:
            categoryName = isCat.text.strip()
            categoryName = categoryName.replace("*","").strip()
            categoryName = categoryName[0] + categoryName[1:].lower() 
            if categoryName in ("Hinweis","Information"):
                nextIsMenu = False
            else:
                nextIsMenu = True
            continue

        elif nextIsMenu:

            mealName = div.find("div", {"class" : "visible-xs-block"}).text.strip()

            
            if mealName.lower() == "geschlossen":
                nextIsMenu = False
                continue

            notes = div["lang"].split(",")
            
            if len(notes):
                notes = [ingredients[i] for i in notes if i in ingredients]
            else:
                notes = None


            pricesText = div.find("div", {"class" : "preise-xs"}).text.strip()

            prices = [float(x.replace(",",".")) for x in price_pattern.findall(pricesText)]

            canteen.addMeal(date, categoryName, mealName, notes, prices, roles)
            foundAny = True

    if foundAny:
        return True

    canteen.setDayClosed(date)
    return False



def _generateCanteenMeta(obj, name,  baseurl):
    """Generate an openmensa XML meta feed from the static json file using an XML template"""
    template = open(metaTemplateFile).read()

    for mensa in obj["mensen"]:
        if not mensa["xml"]:
            continue
        
        if name != mensa["xml"]:
            continue
        
        shortname = name
        
        data = {
            "name" : mensa["name"],
            "adress" : "%s %s %s %s" % (mensa["name"],mensa["strasse"],mensa["plz"],mensa["ort"]),
            "city" : mensa["ort"],
            "phone" : mensa["phone"],
            "latitude" : mensa["latitude"],
            "longitude" : mensa["longitude"],
            "feed_today" : template_todayURL % (baseurl, urllib.parse.quote(shortname)),
            "feed_full" : template_fullURL % (baseurl, urllib.parse.quote(shortname)),
            "source_today" : sourceUrl,
            "source_full" : sourceUrl
            }
        openingTimes = {}
        infokurz = mensa["infokurz"]
        pattern = re.compile("([A-Z][a-z])( - ([A-Z][a-z]))? (\d{1,2})\.(\d{2}) - (\d{1,2})\.(\d{2}) Uhr")
        m = re.findall(pattern, infokurz)
        for result in m:
            fromDay,_,toDay,fromTimeH,fromTimeM,toTimeH,toTimeM = result
            openingTimes[fromDay] = "%s:%s-%s:%s" % (fromTimeH,fromTimeM,toTimeH,toTimeM)
            if toDay:
                select = False
                for short,long in weekdaysMap:
                    if short == fromDay:
                        select = True
                    elif select:
                        openingTimes[short] = "%s:%s-%s:%s" % (fromTimeH,fromTimeM,toTimeH,toTimeM)
                    if short == toDay:
                        select = False

            for short,long in weekdaysMap:
                if short in openingTimes:
                    data[long] = 'open="%s"' % openingTimes[short]
                else:
                    data[long] = 'closed="true"'
            
        
        xml = template.format(**data)
        return xml

    return '<openmensa xmlns="http://openmensa.org/open-mensa-v2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.1" xsi:schemaLocation="http://openmensa.org/open-mensa-v2 http://openmensa.org/open-mensa-v2.xsd"/>'


class Parser:
    def __init__(self, baseurl, handler):
        self.baseurl = baseurl
        self.metaObj = json.load(open(metaJson))
        
        self.xmlnames = []
        self.xml2locId = {}
        for mensa in self.metaObj["mensen"]:
            self.xmlnames.append(mensa["xml"])
            self.xml2locId[mensa["xml"]] = mensa["locId"]
                
        self.handler = handler

    def __now(self):
        berlin = pytz.timezone('Europe/Berlin')
        now = datetime.datetime.now(berlin)
        return now
        
    def json(self):
        tmp = {}
        for name in self.xmlnames:
            tmp[name] = template_metaURL % (self.baseurl, name)
        return json.dumps(tmp, indent=2)
    
    def meta(self, name):
        return _generateCanteenMeta(self.metaObj, name, self.baseurl)
    
    def feed_today(self, name):
        today = self.__now().date()
        canteen = LazyBuilder()
        
        self.handler(canteen, self.xml2locId[name], today)
        return canteen.toXMLFeed()

    def feed_all(self, name):
        canteen = LazyBuilder()

        date = self.__now()

        # Get this week
        lastWeekday = -1
        while self.handler(canteen, self.xml2locId[name], date.date()):
            date += datetime.timedelta(days=1)
            if lastWeekday > date.weekday():
                break
            lastWeekday = date.weekday()
            
        # Skip over weekend
        if date.weekday() > 4: 
            date += datetime.timedelta(days=7-date.weekday())
            
            # Get next week
            lastWeekday = -1
            while self.handler(canteen, self.xml2locId[name], date.date()):
                date += datetime.timedelta(days=1) 
                if lastWeekday > date.weekday():
                    break
                lastWeekday = date.weekday()
        
        return canteen.toXMLFeed()
    

def getstuttgart(baseurl):
    parser = Parser(baseurl, parse_url)
    return parser
        

if __name__ == "__main__":
    print(getstuttgart("http://localhost/").feed_today("mitteMusikhochschule"))
    #print(getstuttgart("http://localhost/").feed_all("mitteMusikhochschule"))
    #print(getstuttgart("http://localhost/").meta("mitteMusikhochschule"))

    
