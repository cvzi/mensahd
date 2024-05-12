#!/usr/bin/env python
# Python 3
import datetime
import os
import json
import urllib
import re
import logging

import requests
from bs4 import BeautifulSoup

try:
    from version import __version__, useragentname, useragentcomment
    from util import StyledLazyBuilder, now_local, weekdays_map
except ModuleNotFoundError:
    import sys
    include = os.path.relpath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, include)
    from version import __version__, useragentname, useragentcomment
    from util import StyledLazyBuilder, now_local, weekdays_map

metaJson = os.path.join(os.path.dirname(__file__), "stuttgart.json")

metaTemplateFile = os.path.join(os.path.dirname(
    __file__), "metaTemplate_stuttgart.xml")

url = r"https://sws2.maxmanager.xyz/inc/ajax-php_konnektor.inc.php"
sourceUrl = r"https://www.studierendenwerk-stuttgart.de/essen/speiseplan/"
roles = ('student', 'employee', 'other')
price_pattern = re.compile('\\d+,\\d\\d')

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
    "P": "Preisrenner"
}


def parse_url(canteen, locId, day=None):

    if day is None:
        day = datetime.date.today()

    date = day.strftime("%Y-%m-%d")

    headers = {
        'Host': 'sws2.maxmanager.xyz',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer':   'https://sws2.maxmanager.xyz/',
        'User-Agent': 'Mozilla/5.0',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Accept-Language': 'de-De,de'
    }

    startThisWeek = day - datetime.timedelta(days=day.weekday())
    startNextWeek = startThisWeek + datetime.timedelta(days=7)

    startThisWeek = startThisWeek.strftime("%Y-%m-%d")
    startNextWeek = startNextWeek.strftime("%Y-%m-%d")

    data = "func=make_spl&locId=%s&date=%s&lang=de&startThisWeek=%s&startNextWeek=%s" % (
        locId, date, startThisWeek, startNextWeek)

    r = requests.post(url, data=data, headers=headers)

    content = r.content.decode("utf-8")

    document = BeautifulSoup(content, "html.parser")

    divs = document.find(
        "div", {"class": "container-fluid"}).find_all("div", {"class", "row"})

    nextIsMenu = False
    categoryName = ""
    foundAny = False
    for div in divs:

        isCat = div.find("div", {"class": "gruppenname"})
        if isCat:
            categoryName = isCat.text.strip()
            categoryName = categoryName.replace("*", "").strip()
            categoryName = categoryName[0] + categoryName[1:].lower()
            if categoryName in ("Hinweis", "Information"):
                nextIsMenu = False
            else:
                nextIsMenu = True
            continue

        elif nextIsMenu:

            mealName = div.find(
                "div", {"class": "visible-xs-block"}).text.strip()

            if mealName.lower() == "geschlossen":
                nextIsMenu = False
                continue

            notes = div["lang"].split(",")

            if len(notes):
                notes = [ingredients[i] for i in notes if i in ingredients]
            else:
                notes = None

            if "Nudelmanufaktur" in mealName:
                mealName = re.sub(".*Nudelmanufaktur.?\\s*", "", mealName)
                notes.append("hauseigene Nudelmanufaktur")

            pricesNode = div.find("div", {"class": "preise-xs"})
            pricesText = None
            if not pricesNode:
                pricesText = str(div.find(string=re.compile('€')))
            else:
                pricesText = pricesNode.text.strip()

            if pricesText:
                prices = [float(x.replace(",", "."))
                          for x in price_pattern.findall(pricesText)]

                if len(prices) != 2:
                    logging.warning("Expected two prices, got %r" % prices)
                    if len(prices) == 0:
                        prices = [0.0, 0.0]
                    elif len(prices) == 1:
                        prices.append(0.0)
                    elif len(prices) == 3:
                        prices = prices[0:2]
                    else:
                        prices = [prices[1], prices[3]]
                    logging.warning("Assuming prices: %r" % prices)
            else:
                prices = []
                logging.warning("No prices found")

            canteen.addMeal(date, categoryName, mealName, notes, prices, roles)
            foundAny = True

    if foundAny:
        return True

    canteen.setDayClosed(date)
    return False


def _generateCanteenMeta(obj, name,  url_template):
    """Generate an openmensa XML meta feed from the static json file using an XML template"""
    with open(metaTemplateFile) as f:
        template = f.read()

    for mensa in obj["mensen"]:
        if not mensa["xml"]:
            continue

        if name != mensa["xml"]:
            continue

        shortname = name

        data = {
            "name": mensa["name"],
            "adress": "%s, %s %s" % (mensa["strasse"], mensa["plz"], mensa["ort"]),
            "city": mensa["ort"],
            "phone": mensa["phone"],
            "latitude": mensa["latitude"],
            "longitude": mensa["longitude"],
            "feed_today": url_template.format(metaOrFeed='today', mensaReference=urllib.parse.quote(shortname)),
            "feed_full": url_template.format(metaOrFeed='feed', mensaReference=urllib.parse.quote(shortname)),
            "source_today": sourceUrl,
            "source_full": sourceUrl
        }
        openingTimes = {}
        infokurz = mensa["infokurz"]
        pattern = re.compile(
            "([A-Z][a-z])( - ([A-Z][a-z]))? (\\d{1,2})\\.(\\d{2}) - (\\d{1,2})\\.(\\d{2}) Uhr")
        m = re.findall(pattern, infokurz)
        for result in m:
            fromDay, _, toDay, fromTimeH, fromTimeM, toTimeH, toTimeM = result
            openingTimes[fromDay] = "%02d:%02d-%02d:%02d" % (
                int(fromTimeH), int(fromTimeM), int(toTimeH), int(toTimeM))
            if toDay:
                select = False
                for short, long in weekdays_map:
                    if short == fromDay:
                        select = True
                    elif select:
                        openingTimes[short] = "%02d:%02d-%02d:%02d" % (
                            int(fromTimeH), int(fromTimeM), int(toTimeH), int(toTimeM))
                    if short == toDay:
                        select = False

            for short, long in weekdays_map:
                if short in openingTimes:
                    data[long] = 'open="%s"' % openingTimes[short]
                else:
                    data[long] = 'closed="true"'

        xml = template.format(**data)
        return xml

    return '<openmensa xmlns="http://openmensa.org/open-mensa-v2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.1" xsi:schemaLocation="http://openmensa.org/open-mensa-v2 http://openmensa.org/open-mensa-v2.xsd"/>'


class Parser:
    def __init__(self, url_template, handler):
        self.url_template = url_template
        with open(metaJson) as f:
            self.metaObj = json.load(f)

        self.xmlnames = []
        self.xml2locId = {}
        self.canteens = self.xml2locId
        for mensa in self.metaObj["mensen"]:
            self.xmlnames.append(mensa["xml"])
            self.xml2locId[mensa["xml"]] = mensa["locId"]

        self.handler = handler

    def json(self):
        tmp = {}
        for name in self.xmlnames:
            tmp[name] = self.url_template.format(
                metaOrFeed='meta', mensaReference=urllib.parse.quote(name))
        return json.dumps(tmp, indent=2)

    def meta(self, name):
        return _generateCanteenMeta(self.metaObj, name, self.url_template)

    def feed_today(self, name):
        today = now_local().date()
        canteen = StyledLazyBuilder()

        self.handler(canteen, self.xml2locId[name], today)
        return canteen.toXMLFeed()

    def feed_all(self, name):
        canteen = StyledLazyBuilder()

        date = now_local()

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


def getParser(url_template):
    parser = Parser(url_template, parse_url)
    return parser


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(getParser("http://localhost/").feed_all("central"))
    # print(getParser("http://localhost/").feed_all("mitteMusikhochschule"))
    # print(getParser("http://localhost/").meta("mitteMusikhochschule"))
