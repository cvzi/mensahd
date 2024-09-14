#!/usr/bin/env python
# Python 3
import os
import re
import datetime
import json
import urllib
import logging

import requests
from bs4 import BeautifulSoup

try:
    from version import __version__, useragentname, useragentcomment
    from util import StyledLazyBuilder, now_local, weekdays_map
except ModuleNotFoundError:
    import sys

    include = os.path.relpath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, include)
    from version import __version__, useragentname, useragentcomment
    from util import StyledLazyBuilder, now_local, weekdays_map

# Based on https://github.com/mswart/openmensa-parsers/blob/master/magdeburg.py

metaJson = os.path.join(os.path.dirname(__file__), "eppelheim.json")

metaTemplateFile = os.path.join(os.path.dirname(__file__), "metaTemplate_eppelheim.xml")

daysGerman = [
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
]

roles = ("student",)

headers = {
    "User-Agent": f"{useragentname}/{__version__} ({useragentcomment}) {requests.utils.default_user_agent()}"
}


day_regex = re.compile(r"(?P<date>\d{2}\.\d{2}\.\d{4})")
euro_regex = re.compile(r"(\d+,\d+) €")
datespan_regex = re.compile(
    "(?P<from>\\d+\\.\\d+\\.\\d{0,4})\\s*[–-]\\s*(?P<to>\\d+\\.\\d+\\.\\d{0,4})"
)
calendarweek_regex = re.compile("\\(KW (\\d+)\\)")


def parse_url(url, today=False):
    today = now_local().date()
    if today.weekday() == 6:  # Sunday
        today += datetime.timedelta(days=1)  # Tomorrow

    if "%s" in url:
        url = url % today.strftime("%Y_%m_%d")

    try:
        content = requests.get(url, headers=headers).text
    except requests.exceptions.ConnectionError as e:
        logging.warning(str(e))
        content = requests.get(url, headers=headers, verify=False).text

    document = BeautifulSoup(content, "html.parser")
    canteen = StyledLazyBuilder()

    if not document.find("h2"):
        print("Page incompatible. Maintenance?")
        return canteen.toXMLFeed()

    # Date
    h2s = document.find_all("h2")
    datematch = None
    for h2 in h2s:
        match = datespan_regex.search(h2.text)
        if match:
            datematch = match

    if h2s:
        h2 = h2s[0]
        if not datematch and "geschlossen" in h2.text:
            # Set 7 days closed
            for i in range(7):
                canteen.setDayClosed((now_local().date() + datetime.timedelta(i)))
            return canteen.toXMLFeed()

        if not datematch and "nach Vorbestellung" in h2.text:
            # Set info for 7 days
            for i in range(7):
                canteen.addMeal(
                    (now_local().date() + datetime.timedelta(i)), "Info", h2.text
                )
            return canteen.toXMLFeed()

        if not datematch:
            match = calendarweek_regex.search(h2.text)
            if match:
                week = int(match.group(1))
                fromdate = datetime.datetime.fromisocalendar(now_local().year, week, 1)

    if datematch:
        p = datematch.groupdict()
        if len(p["from"].split(".")[2]) == 0:
            p["from"] += p["to"].split(".")[2]
        fromdate = datetime.datetime.strptime(p["from"], "%d.%m.%Y")

    divs = document.find_all("div", {"class": "speiseplan-manuell"})

    date = None
    for div in divs:
        h3 = div.find("h3")
        day = h3.text.strip()
        date = fromdate + datetime.timedelta(days=daysGerman.index(day))
        date = date.strftime("%d.%m.%Y")

        if "feiertag" in div.text.lower() or "geschlossen" in div.text.lower():
            canteen.setDayClosed(date)
            continue

        for p in div.find_all("p"):
            notes = []
            strongs = p.find_all("strong")
            categoryName = strongs[0].text.strip().strip(":").strip()
            priceText = strongs[-1].text.strip()
            for strong in strongs:
                strong.clear()

            mealName = p.text.strip()

            if not mealName:
                continue

            prices = []
            try:
                price = float(euro_regex.search(priceText).group(1).replace(",", "."))
                prices.append(price)
            except (AttributeError, TypeError, KeyError, ValueError):
                notes.append(priceText)

            notes = [x for x in notes if x]
            canteen.addMeal(
                date,
                categoryName,
                mealName,
                notes if notes else None,
                prices if prices else None,
                roles if prices else None,
            )

    return canteen.toXMLFeed()


def _generateCanteenMeta(name, url_template):
    """Generate an openmensa XML meta feed from the static json file using an XML template"""
    with open(metaJson) as f:
        obj = json.load(f)
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
            "feed_full": url_template.format(
                metaOrFeed="feed", mensaReference=urllib.parse.quote(shortname)
            ),
            "source_full": mensa["source"],
        }
        openingTimes = {}
        infokurz = mensa["infokurz"]
        pattern = re.compile(
            "([A-Z][a-z])( - ([A-Z][a-z]))? (\\d{1,2})\\.(\\d{2}) - (\\d{1,2})\\.(\\d{2}) Uhr"
        )
        m = re.findall(pattern, infokurz)
        for result in m:
            fromDay, _, toDay, fromTimeH, fromTimeM, toTimeH, toTimeM = result
            openingTimes[fromDay] = "%02d:%02d-%02d:%02d" % (
                int(fromTimeH),
                int(fromTimeM),
                int(toTimeH),
                int(toTimeM),
            )
            if toDay:
                select = False
                for short, long in weekdays_map:
                    if short == fromDay:
                        select = True
                    elif select:
                        openingTimes[short] = "%02d:%02d-%02d:%02d" % (
                            int(fromTimeH),
                            int(fromTimeM),
                            int(toTimeH),
                            int(toTimeM),
                        )
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
    def __init__(self, url_template, city, handler, shared_prefix):
        self.url_template = url_template
        self.handler = handler
        self.shared_prefix = shared_prefix
        self.canteens = {}

    def define(self, name, suffix):
        self.canteens[name] = self.shared_prefix + suffix

    def json(self):
        tmp = self.canteens.copy()
        for name in tmp:
            tmp[name] = self.url_template.format(
                metaOrFeed="meta", mensaReference=urllib.parse.quote(name)
            )

        return json.dumps(tmp, indent=2)

    def meta(self, name):
        return _generateCanteenMeta(name, self.url_template)

    def feed(self, name):
        return self.handler(self.canteens[name])


def getParser(url_template):
    parser = Parser(
        url_template,
        "eppelheim",
        handler=parse_url,
        shared_prefix="https://www.stw-ma.de/",
    )
    parser.define("dhbw", suffix="essen-trinken/speiseplaene/speisenausgabe-eppelheim/")

    return parser


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(getParser("http://localhost/").feed("dhbw"))
