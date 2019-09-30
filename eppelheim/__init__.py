#!python3
import requests
from bs4 import BeautifulSoup
import os
import re
import datetime
import json
from pyopenmensa.feed import LazyBuilder
import urllib
import logging

# Based on https://github.com/mswart/openmensa-parsers/blob/master/magdeburg.py

metaJson = os.path.join(os.path.dirname(__file__), "eppelheim.json")

metaTemplateFile = os.path.join(os.path.dirname(
    __file__), "metaTemplate_mannheim.xml")

template_metaURL = "%seppelheim/meta/%s.xml"
template_todayURL = "%seppelheim/feed/%s.xml"
template_fullURL = "%seppelheim/feed/%s.xml"

weekdaysMap = [
    ("Mo", "monday"),
    ("Di", "tuesday"),
    ("Mi", "wednesday"),
    ("Do", "thursday"),
    ("Fr", "friday"),
    ("Sa", "saturday"),
    ("So", "sunday")
]

daysGerman = ["Montag", "Dienstag", "Mittwoch",
              "Donnerstag", "Freitag", "Samstag", "Sonntag"]

roles = ('student', 'employee', 'other')


def correctCapitalization(s):
    return s[0].upper() + s[1:].lower()


day_regex = re.compile(r'(?P<date>\d{2}\.\d{2}\.\d{4})')
removeextras_regex = re.compile(r'\s+\[(\w,?)+\]')
price_employee_regex = re.compile(r'Dozenten\s*\((?P<employee>\d+,\d+)')
price_guest_regex = re.compile(r'Gäste\s*\((?P<employee>\d+,\d+)')
euro_regex = re.compile(r'(\d+,\d+) €')
datespan_regex = re.compile(
    '(?P<from>\d+\.\d+\.\d{0,4})\s*–\s*(?P<to>\d+\.\d+\.\d{0,4})')


def parse_url(url, today=False):
    today = datetime.date.today()
    if today.weekday() == 6:  # Sunday
        today += datetime.timedelta(days=1)  # Tomorrow

    if "%s" in url:
        url = url % today.strftime('%Y_%m_%d')

    try:
        content = requests.get(url).text
    except requests.exceptions.ConnectionError as e:
        logging.warning(str(e))
        content = requests.get(url, verify=False).text

    document = BeautifulSoup(content, "html.parser")
    canteen = LazyBuilder()

    # Prices for employees and guests
    try:
        p = price_employee_regex.search(document.find("main").text).groupdict()
        employee = float(p["employee"].split(",")[0]) + \
            float(p["employee"].split(",")[1]) / 100

        p = price_guest_regex.search(document.find("main").text).groupdict()
        guest = float(p["employee"].split(",")[0]) + \
            float(p["employee"].split(",")[1]) / 100
    except (AttributeError, TypeError, KeyError, ValueError):
        employee_multiplier = 1.25
        guest_multiplier = 1.60
        employee = None
        guest = None

    # Date
    p = datespan_regex.search(document.find(
        "div", {"class": "maincontent"}).find("h2").text).groupdict()

    if len(p["from"].split(".")[2]) == 0:
        p["from"] += p["to"].split(".")[2]
    fromdate = datetime.datetime.strptime(p["from"], "%d.%m.%Y")

    maincontent = document.find("div", {"class": "maincontent"})
    table = maincontent.find("table")
    if not table:
        if maincontent:
            # Die Speisenausgabe DHBW Eppelheim ist vom dd.mm.yyyy – dd.mm.yyyy
            # geschlossen
            p = datespan_regex.search(maincontent.text)
            if p:
                fromdate = datetime.datetime.strptime(p["from"], "%d.%m.%Y")
                todate = datetime.datetime.strptime(p["to"], "%d.%m.%Y")
                while fromdate <= todate:
                    canteen.setDayClosed(fromdate.strftime('%d.%m.%Y'))
                    fromdate += datetime.timedelta(1)

        return canteen.toXMLFeed()

    trs = table.find_all("tr")

    date = None
    for tr in trs:

        tds = tr.find_all("td")

        if len(tds) == 4:
            td0, td1, td2, td3 = tds

            day = td0.text.strip()
            if '(' in day:
                day = day.split('(')[0].strip()

            date = fromdate + datetime.timedelta(days=daysGerman.index(day))
            date = date.strftime('%d.%m.%Y')

        else:
            td0 = None
            td1, td2, td3 = tds

        notes = []

        if "feiertag" in td1.text.lower() or "geschlossen" in td1.text.lower() or  (td0 and "feiertag" in td0.text.lower()):
            canteen.setDayClosed(date)
            continue

        categoryName = td1.text.strip()[:-1]
        mealName = td2.text.strip()

        if not categoryName or not mealName:
            continue

        prices = []
        try:
            price = float(euro_regex.search(
                td3.text).group(1).replace(",", "."))
            prices.append(price)
            if employee is not None:
                prices.append(employee)
            else:
                prices.append(price * employee_multiplier)
            if guest is not None:
                prices.append(guest)
            else:
                prices.append(price * guest_multiplier)
        except (AttributeError, TypeError, KeyError, ValueError):
            notes.append(td3.text.strip())

        notes = [x for x in notes if x]
        canteen.addMeal(date, categoryName, mealName, notes if notes else None,
                        prices if prices else None, roles if prices else None)

    return canteen.toXMLFeed()


def _generateCanteenMeta(name, baseurl):
    """Generate an openmensa XML meta feed from the static json file using an XML template"""
    obj = json.load(open(metaJson))
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
            "feed_today": template_todayURL % (baseurl, urllib.parse.quote(shortname)),
            "feed_full": template_fullURL % (baseurl, urllib.parse.quote(shortname)),
            "source_today": mensa["source_today"],
            "source_full": mensa["source_week"],
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
    def __init__(self, baseurl, city, handler, shared_prefix):
        self.baseurl = baseurl
        self.handler = handler
        self.shared_prefix = shared_prefix
        self.canteens = {}

    def define(self, name, suffix):
        self.canteens[name] = self.shared_prefix + suffix

    def json(self):
        tmp = self.canteens.copy()
        for name in tmp:
            tmp[name] = template_metaURL % (self.baseurl, name)
        return json.dumps(tmp, indent=2)

    def meta(self, name):
        return _generateCanteenMeta(name, self.baseurl)

    def feed(self, name):
        return self.handler(self.canteens[name])


def getParser(baseurl):
    parser = Parser(baseurl, 'eppelheim',
                    handler=parse_url,
                    shared_prefix='https://www.stw-ma.de/')
    parser.define(
        'dhbw', suffix='Essen+_+Trinken/Speisepläne/Speisenausgabe+DHBW+Eppelheim.html')

    return parser


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    # print(getParser("http://localhost/").json("https://localhost/meta/%s.xml"))
    print(getParser("http://localhost/").feed("dhbw"))
