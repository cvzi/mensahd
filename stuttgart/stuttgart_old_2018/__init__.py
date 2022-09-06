import datetime
import os
import json
import re
from threading import Lock
import urllib
import time

import pytz
import requests
from bs4 import BeautifulSoup

from pyopenmensa.feed import LazyBuilder

metaJson = os.path.join(os.path.dirname(__file__), "stuttgart.json")

metaTemplateFile = os.path.join(os.path.dirname(__file__),
                                "metaTemplate_stuttgart.xml")

template_metaURL = "%sstuttgart/meta/%s.xml"
template_fullURL = "%sstuttgart/feed/%s.xml"

sourceURL = "https://www.studierendenwerk-stuttgart.de/gastronomie/speiseangebot"

mealsURL = "https://www.studierendenwerk-stuttgart.de/speiseangebot_rss"
__timeoutSeconds = 20

roles = ('student', 'other')

ingredients = {
    "1": "mit Konservierungsstoff",
    "2": "mit Farbstoff",
    "3": "mit Antioxidationsmittel",
    "4": "mit Geschmacksverstärker",
    "5": "geschwefelt",
    "6": "gewachst",
    "7": "mit Phosphat",
    "8": "mit Süßungsmittel",
    "9": "enthält eine Phenylalaninquelle",
    "10": "geschwärzt",
    "11": "enthält Alkohol",
    "En": "enthält Erdnuss",
    "Fi": "enthält Fisch",
    "Gl": "enthält Glutenhaltiges Getreide",
    "Ei": "enthält Eier",
    "Kr": "enthält Krebstiere (Krusten- und Schalentiere)",
    "Lu": "enthält Lupine",
    "La": "enthält Milch und Laktose",
    "Nu": "enthält Schalenfrüchte (Nüsse)",
    "Sw": "enthält Schwefeldioxid (\"SO2\") und Sulfite",
    "Sl": "enthält Sellerie",
    "Sf": "enthält Senf",
    "Se": "enthält Sesam",
    "So": "enthält Soja",
    "Wt": "enthält Weichtiere"
}

weekdaysMap = [("Mo", "monday"), ("Di", "tuesday"), ("Mi", "wednesday"),
               ("Do", "thursday"), ("Fr", "friday"), ("Sa", "saturday"),
               ("So", "sunday")]

# Global vars for caching
cache_mealsURL_lock = Lock()
cache_mealsURL_text = None
cache_mealsURL_time = 0


def _getMealsURL_cached(max_age_minutes=15):
    """Download meals information from XML feed, if available use a cached version"""
    global cache_mealsURL_lock
    global cache_mealsURL_text
    global cache_mealsURL_time

    age_seconds = (time.time() - cache_mealsURL_time)
    if age_seconds > max_age_minutes * 60:
        with cache_mealsURL_lock:
            cache_mealsURL_text = requests.get(mealsURL).text
            cache_mealsURL_time = time.time()
            age_seconds = 0
            print("##CACHE## Meals cache updated")

    return cache_mealsURL_text, age_seconds


re_title = re.compile(r"<title>([^<]+) vom ([^<]+)</title>")


def parse_url(canteen, xmlname, allowedCategoryNames=None):

    rss, _ = _getMealsURL_cached()

    items = rss.split("<item>")
    for text in items:
        m = re_title.search(text)
        if not m:
            continue
        date = re_title.search(text).group(2)
        xmlescaped = text.split("<description>")[1].split("</description>")[0]
        decoded = BeautifulSoup(xmlescaped, "html.parser")
        document = BeautifulSoup("".join(decoded.contents), "html.parser")
        trs = document.find("tbody").find_all("tr")

        categoryName = "NOT_FOUND"

        for tr in trs:
            tds = tr.find_all("td")
            if len(tds) == 1:  # Category Name
                categoryName = tds[0].text.strip()
            else:  # Meal
                prices = [None, None]
                text, *prices, additives = [td.text.strip() for td in tds]

                notes = [
                    ingredients[i]
                    for i in [x.strip() for x in additives.split(",")]
                    if i in ingredients
                ]

                if allowedCategoryNames is not None:
                    if categoryName in allowedCategoryNames:
                        canteen.addMeal(date, categoryName, text, notes,
                                        prices, roles)
                else:
                    canteen.addMeal(date, categoryName, text, notes, prices,
                                    roles)


def _generateCanteenMeta(obj, name, baseurl):
    """Generate an openmensa XML meta feed from the static json file using an XML template"""
    template = open(metaTemplateFile).read()

    for mensa in obj["mensen"]:
        if not mensa["xml"]:
            continue

        if name != mensa["xml"]:
            continue

        shortname = name

        data = {
            "name":
            mensa["name"],
            "adress":
            "%s %s %s %s" %
            (mensa["name"], mensa["strasse"], mensa["plz"], mensa["ort"]),
            "city":
            mensa["ort"],
            "phone":
            mensa["phone"],
            "latitude":
            mensa["latitude"],
            "longitude":
            mensa["longitude"],
            "feed_full":
            template_fullURL % (baseurl, urllib.parse.quote(shortname)),
            "source_full":
            sourceURL.replace("&", "&amp;")
        }
        openingTimes = {}
        infokurz = mensa["infokurz"]
        pattern = re.compile(
            "([A-Z][a-z])( - ([A-Z][a-z]))? (\d{1,2})\.(\d{2}) - (\d{1,2})\.(\d{2}) Uhr"
        )
        m = re.findall(pattern, infokurz)
        for result in m:
            fromDay, _, toDay, fromTimeH, fromTimeM, toTimeH, toTimeM = result
            openingTimes[fromDay] = "%s:%s-%s:%s" % (fromTimeH, fromTimeM,
                                                     toTimeH, toTimeM)
            if toDay:
                select = False
                for short, long in weekdaysMap:
                    if short == fromDay:
                        select = True
                    elif select:
                        openingTimes[short] = "%s:%s-%s:%s" % (
                            fromTimeH, fromTimeM, toTimeH, toTimeM)
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
        for mensa in self.metaObj["mensen"]:
            if "kategorien" in mensa:
                self.xmlnames.append((mensa["xml"], mensa["kategorien"]))
            else:
                self.xmlnames.append(mensa["xml"])

        #self.xmlnames = ["mitteMusikhochschule","nordKunstakademie", "mitteMensa1Holzgartenstrasse", "vaihingenMensa2", "esslingen1Flandernstrasse", "ludwigsburg"]
        # self.xmlnames += [("esslingen2Mitte", ["Vorspeise", "Hauptgericht 1", "Hauptgericht 2", "Bio-Gericht"])] #"http://www.hs-esslingen.de/de/hochschule/service/mensa/speiseplan-stadtmitte.html")]
        # self.xmlnames += [("goeppingen", ["Hauptgericht 1", "Bio-Gericht"])] # https://www.studierendenwerk-stuttgart.de/cafeteria/cafeteria-bau-4-eg-goeppingen

    def json(self):
        tmp = {}
        for name in self.xmlnames:
            if isinstance(name, str):
                tmp[name] = template_metaURL % (self.baseurl, name)
            else:
                tmp[name[0]] = template_metaURL % (self.baseurl, name[0])
        return json.dumps(tmp, indent=2)

    def meta(self, name):
        return _generateCanteenMeta(self.metaObj, name, self.baseurl)

    def feed(self, name):
        canteen = LazyBuilder()
        if name in self.xmlnames:
            parse_url(canteen, name)  # all categories
        else:
            xmlname_enty = [x for x in self.xmlnames if x[0] == name][0]
            parse_url(canteen, *xmlname_enty)  # only certain categories

        return canteen.toXMLFeed()


def getstuttgart(baseurl):
    parser = Parser(baseurl)
    return parser


if __name__ == "__main__":
    print(getstuttgart("http://localhost/").feed("goeppingen"))
