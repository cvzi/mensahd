import datetime
import os
import json
import urllib
import re

import pytz
import requests
from bs4 import BeautifulSoup

from pyopenmensa.feed import LazyBuilder



# Based on https://github.com/mswart/openmensa-parsers/blob/master/magdeburg.py

metaJson = os.path.join(os.path.dirname(__file__), "koeln.json")

metaTemplateFile = os.path.join(os.path.dirname(__file__), "metaTemplate_koeln.xml")

template_metaURL = "%skoeln/meta/%s.xml"
template_todayURL = "%skoeln/today/%s.xml"
template_fullURL = "%skoeln/all/%s.xml"

weekdaysMap = [
    ("Mo", "monday"),
    ("Di", "tuesday"),
    ("Mi", "wednesday"),
    ("Do", "thursday"),
    ("Fr", "friday"),
    ("Sa", "saturday"),
    ("So", "sunday")
    ]

url = r"https://www.max-manager.de/daten-extern/sw-koeln/html/speiseplan-render.php"

roles = ('student', 'employee', 'other')

ingredients = {1: "mit Farbstoff",
            2: "mit Konservierungsstoff",
            3: "mit Antioxidationsmittel",
            4: "mit Geschmacksverstärker",
            5: "geschwefelt",
            6: "geschwärzt",
            7: "gewachst",
            8: "mit Phosphat",
            9: "mit Süßstoff",
            10: "enthält eine Phenylalaninquelle",
            11: "Gluten",
            12: "Krebstiere (Schalen-/Krusten-/Weichtiere)",
            13: "Eier",
            14: "Fisch",
            15: "Erdnüsse",
            16: "Soja",
            17: "Milch",
            18: "Laktose",
            19: "Schalenfrüchte (Nüsse)",
            20: "Sellerie",
            21: "Senf",
            22: "Sesamsamen",
            23: "Schwefeldioxid und Sulfite",
            24: "Lupinen",
            26: "enthält Alkohol",
            27: "enthält Gelatine"}

def parse_url(canteen, locId, day=None):

    if day is None:
        day = datetime.date.today()

    date = day.strftime("%Y-%m-%d")

    r = requests.post(url, data = {'date' : date, 'func': 'make_spl', 'lang': 'de', 'locId': locId})

    content = r.content.decode("utf-8")

    document = BeautifulSoup(content, "html.parser")

    trs = document.find("table", {"class": "speiseplan"}).find_all("tr")

    nextIsMenu = False
    categoryName = ""
    foundAny = False
    for tr in trs:
        td = tr.find("td", {"class": "pk bg-rot"})
        if td:
            nextIsMenu = True
            categoryName = td.text.strip()
            categoryName = categoryName.replace("*","")
            continue

        elif nextIsMenu:
            foundAny = True
            tds = tr.find_all("td")

            artikel = tds[1].find("span", {"class":"artikel"})
            descr = tds[1].find("span", {"class": "descr"})
            
            text = "".join(artikel.findAll(text=True, recursive=False))
            text += " " + "".join(descr.findAll(text=True, recursive=False))
            text = text.replace("*","")

            sup = ",".join([n.text for n in artikel.findAll("sup")])
            sup += "," + ",".join([n.text for n in descr.findAll("sup")])       

            notes = sorted(set([int(x.strip()) for x in sup.split(",") if x.strip()]))
            
            if len(notes):
                notes = [ingredients[i] for i in notes if i in ingredients]
            else:
                notes = None

            prices = [float(x.strip().replace(",",".")) for x in tds[2].text.split("/")]

            canteen.addMeal(date, categoryName, text, notes, prices, roles)


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
            "source_today" : mensa["source_today"].replace("&","&amp;"),
            "source_full" : mensa["source_today"].replace("&","&amp;")
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
        for mensa in self.metaObj["mensen"]:
            self.xmlnames.append(mensa["xml"])
                
        #self.xmlnames = ["spoho", "cafe-himmelsblick", "iwz-deutz", "gummersbach", "kunsthochschule-medien", "muho", "robertkoch", "suedstadt", "unimensa"]     
        
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
        self.handler(canteen, name, today)
        return canteen.toXMLFeed()

    def feed_all(self, name):
        canteen = LazyBuilder()

        date = self.__now()

        # Get this week
        while self.handler(canteen, name, date.date()):
            date += datetime.timedelta(days=1)
            
        # Skip over weekend
        if date.weekday() > 4: 
            date += datetime.timedelta(days=7-date.weekday())
            
            # Get next week
            while self.handler(canteen, name, date.date()):
                date += datetime.timedelta(days=1) 
            
        
        return canteen.toXMLFeed()
    

def getkoeln(baseurl):
    parser = Parser(baseurl, parse_url)
    return parser
        

if __name__ == "__main__":
    print(getkoeln("http://localhost/").feed_today("unimensa"))
