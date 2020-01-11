import datetime
import os
import json
import urllib
import re
import logging

import pytz
import requests
from bs4 import BeautifulSoup

from pyopenmensa.feed import LazyBuilder


metaJson = os.path.join(os.path.dirname(__file__), "stuttgart.json")

metaTemplateFile = os.path.join(os.path.dirname(
    __file__), "metaTemplate_stuttgart.xml")

template_metaURL = "%sstuttgart/meta/%s.xml"
template_feedURL = "%sstuttgart/feed/%s.xml"

url = r"https://sws.maxmanager.xyz/extern/"
sourceUrl = r"https://www.studierendenwerk-stuttgart.de/essen/speiseplan/"
roles = ('student', 'employee', 'other')
weight = 'Preis je %sg'

weekdaysMap = [
    ("Mo", "monday"),
    ("Di", "tuesday"),
    ("Mi", "wednesday"),
    ("Do", "thursday"),
    ("Fr", "friday"),
    ("Sa", "saturday"),
    ("So", "sunday")
]

ingredients = {
    "Ei": "Ei",
    "En": "Erdnuss",
    "Fi": "Fisch",
    "GlW": "Weizen",
    "GlD": "Dinkel",
    "GlKW": "Khorasan-Weizen",
    "GlR": "Roggen",
    "GlG": "Gerste",
    "GlH": "Hafer",
    "Kr": "Krebstiere Krusten- und Schalentiere",
    "La": "Milch und Laktose",
    "Lu": "Lupine",
    "NuM": "Mandeln",
    "NuH": "Haselnüsse",
    "NuW": "Walnüsse",
    "NuC": "Cashewnüsse",
    "NuPe": "Pecannüsse",
    "NuPa": "Paranüsse",
    "NuPi": "Pistazien",
    "NuMa": "Macadamianüsse",
    "Se": "Sesam",
    "Sf": "Senf",
    "Sl": "Sellerie",
    "So": "Soja",
    "Sw": "Schwefeldioxid SO2 und Sulfite",
    "Wt": "Weichtiere",
    "1": "mit Konservierungsstoffen",
    "2": "mit Farbstoffen",
    "3": "mit Antioxidationsmitteln",
    "4": "mit Geschmacksverstärkern",
    "5": "geschwefelt",
    "6": "gewachst",
    "7": "mit Phosphaten",
    "8": "mit Süßungsmitteln",
    "9": "enthält eine Phenylalaninquelle",
    "10": "geschwärzt",
    "11": "mit Alkohol",
    "R": "Rind",
    "RS": "Rind/Schwein",
    "S": "Schwein",
    "G": "Geflügel",
    "MSC": "MSC-zertifizierter Fisch (MSC-C-51632)",
    "B": "100% Bio nach EG-Öko-Verordnung (DE-ÖKO-006)",
    "VG": "vegan",
    "F": "Fitness",
    "V": "vegetarisch",
    "P": "Preisrenner",
}

def _fetchData(canteen, jsonfile):
    headers = {
        'User-Agent': 'github.com/cvzi/mensahd python-requests',
        'Accept': 'application/json',
        'Accept-Language': 'de-De,de'
    }
    r = requests.get(url + jsonfile, headers=headers)
    data = r.json().popitem()[1]

    for day, meals in data.items():
        if len(meals) == 0:
            canteen.setDayClosed(day)
        for m in meals:
            mealName = m["meal"].strip().strip(",")
            if m["description"].strip():
                mealName += "," + m["description"].strip()

            notes = [ingredients.get(i, i) for i in m["additives"].split(",") if i and i.strip()]

            prices = []
            myroles = []
            if m["price1"] and m["price1"] != "-":
                prices.append(float(m["price1"].replace(",", ".")))
                myroles.append(roles[0])
            if m["price2"] and m["price2"] != "-":
                prices.append(float(m["price2"].replace(",", ".")))
                myroles.append(roles[1])
            if m["price3"] and m["price3"] != "-":
                prices.append(float(m["price3"].replace(",", ".")))
                myroles.append(roles[2])
            if m["weight_unit"]:
                notes.append(weight % (m["weight_unit"],))

            canteen.addMeal(day, m["category"], mealName, notes, prices, myroles)

    return canteen


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
            "name": mensa["name"],
            "adress": "%s %s %s %s" % (mensa["name"], mensa["strasse"], mensa["plz"], mensa["ort"]),
            "city": mensa["ort"],
            "phone": mensa["phone"],
            "latitude": mensa["latitude"],
            "longitude": mensa["longitude"],
            "feed": template_feedURL % (baseurl, urllib.parse.quote(shortname)),
            "source": sourceUrl,
        }
        openingTimes = {}
        infokurz = mensa["infokurz"]
        pattern = re.compile(
            "([A-Z][a-z])( - ([A-Z][a-z]))? (\d{1,2})\.(\d{2}) - (\d{1,2})\.(\d{2}) Uhr")
        m = re.findall(pattern, infokurz)
        for result in m:
            fromDay, _, toDay, fromTimeH, fromTimeM, toTimeH, toTimeM = result
            openingTimes[fromDay] = "%02d:%02d-%02d:%02d" % (
                int(fromTimeH), int(fromTimeM), int(toTimeH), int(toTimeM))
            if toDay:
                select = False
                for short, long in weekdaysMap:
                    if short == fromDay:
                        select = True
                    elif select:
                        openingTimes[short] = "%02d:%02d-%02d:%02d" % (
                            int(fromTimeH), int(fromTimeM), int(toTimeH), int(toTimeM))
                    if short == toDay:
                        select = False

            for short, long in weekdaysMap:
                if short in openingTimes:
                    data[long] = 'open="%s"' % openingTimes[short]
                else:
                    data[long] = 'closed="true"'

        xml = template.format(**data)
        return xml

    return '<openmensa xmlns="http://openmensa.org/open-mensa-v2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.1" xsi:schemaLocation="http://openmensa.org/open-mensa-v2 http://openmensa.org/open-mensa-v2.xsd"/>'


class Parser:
    def __init__(self, baseurl):
        self.baseurl = baseurl
        self.metaObj = json.load(open(metaJson))

        self.xmlnames = []
        self.xml2json = {}
        self.canteens = self.xml2json
        for mensa in self.metaObj["mensen"]:
            self.xmlnames.append(mensa["xml"])
            self.xml2json[mensa["xml"]] = mensa["json"]

    @staticmethod
    def __now():
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

    def feed(self, name):
        canteen = LazyBuilder()
        _fetchData(canteen, self.xml2json[name])
        return canteen.toXMLFeed()


def getParser(baseurl):
    return Parser(baseurl)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    #print(getParser("http://localhost/").meta("horb"))
    #print(getParser("http://localhost/").feed("horb"))
