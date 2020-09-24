#!/usr/bin/env python
# Python 3
import datetime
import time
import os
import json
import urllib
import re
import logging
import string
import textwrap
from threading import Lock

import pytz
import requests
from bs4 import BeautifulSoup
from pyopenmensa.feed import LazyBuilder

try:
    from version import __version__, useragentname, useragentcomment
except ModuleNotFoundError:
    __version__, useragentname, useragentcomment = 0.1, requests.utils.default_user_agent(), "Python 3"

# Based on https://github.com/mswart/openmensa-parsers/blob/master/magdeburg.py

metaJson = os.path.join(os.path.dirname(__file__), "koeln.json")

metaTemplateFile = os.path.join(
    os.path.dirname(__file__), "metaTemplate_koeln.xml")

template_metaURL = "%skoeln/meta/%s.xml"
template_todayURL = "%skoeln/today/%s.xml"
template_fullURL = "%skoeln/all/%s.xml"
template_source = r"https://www.kstw.de/speiseplan?l="
templace_url = "https://www.kstw.de/speiseplan?l={ids}&t={{date}}"

with open(metaJson, 'r', encoding='utf8') as f:
    canteenDict = json.load(f)

url = templace_url.format(ids=",".join(canteenDict.keys()))

headers = {
    'User-Agent': f'{useragentname}/{__version__} ({useragentcomment}) {requests.utils.default_user_agent()}'
}

weekdaysMap = [
    ("Mo", "monday"),
    ("Di", "tuesday"),
    ("Mi", "wednesday"),
    ("Do", "thursday"),
    ("Fr", "friday"),
    ("Sa", "saturday"),
    ("So", "sunday")
]

rolesOrder = ('student', 'employee', 'other')


# Global vars for caching
cache_mealsURL_lock = Lock()
cache_mealsURL_data = {}
cache_mealsURL_time = {}


def _getMealsURL(url, max_age_minutes=30):
    """Download website, if available use a cached version"""
    if url in cache_mealsURL_data:
        age_seconds = (time.time() - cache_mealsURL_time[url])
        if age_seconds < max_age_minutes*60:
            logging.debug(f"From cache: {url} [{round(age_seconds)}s old]")
            return cache_mealsURL_data[url]

    content = requests.get(url, headers=headers).text
    with cache_mealsURL_lock:
        cache_mealsURL_data[url] = content
        cache_mealsURL_time[url] = time.time()
    return content


def parse_url(lazyBuilder, mensaId, day=None):
    if day is None:
        day = datetime.date.today()
    date = day.strftime("%Y-%m-%d")

    content = _getMealsURL(url.format(date=date))
    document = BeautifulSoup(content, "html.parser")

    mensaDivs = document.find_all(
        "div", class_="tx-epwerkmenu-menu-location-wrapper")
    mensaDivs = [
        mensaDiv for mensaDiv in mensaDivs if mensaDiv.attrs["data-location"] == str(mensaId)]
    if len(mensaDivs) != 1:
        logging.error(f"Mensa not found id={mensaId}")
        return False

    mensaDiv = mensaDivs.pop()
    menuTiles = mensaDiv.find_all("div", class_="menue-tile")

    foundAny = False
    for menuTile in menuTiles:
        category = string.capwords(menuTile.attrs["data-category"])
        mealName = menuTile.find(
            class_="tx-epwerkmenu-menu-meal-title").text.strip()
        desc = menuTile.find(class_="tx-epwerkmenu-menu-meal-description")
        if desc and desc.text.strip():
            mealName = f"{mealName} {desc.text.strip()}"

        additives = menuTile.find(class_="tx-epwerkmenu-menu-meal-additives")
        for sup in additives.find_all('sup'):
            sup.extract()
        notes = [note.strip()
                 for note in additives.text.split("\n") if note.strip()]

        pricesDiv = menuTile.find(
            class_="tx-epwerkmenu-menu-meal-prices-values")

        roles = []
        prices = []
        for j, price in enumerate(pricesDiv.text.split('/')):
            price = price.strip().replace(',', '.')
            try:
                price = float(price)
                prices.append(price)
                roles.append(rolesOrder[j])
            except ValueError:
                pass

        for j, mealText in enumerate(textwrap.wrap(mealName, width=250)):
            lazyBuilder.addMeal(date, category, mealName,
                                notes if j == 0 else None,
                                prices if j == 0 else None,
                                roles if j == 0 else None)
        foundAny = True

    if foundAny:
        return True

    lazyBuilder.setDayClosed(date)

    return False


def _generateCanteenMeta(mensa, baseurl):
    """Generate an openmensa XML meta feed from the static json file using an XML template"""
    template = open(metaTemplateFile).read()

    data = {
        "name": mensa["name"],
        "adress": "%s %s %s %s" % (mensa["name"], mensa["strasse"], mensa["plz"], mensa["ort"]),
        "city": mensa["ort"],
        "phone": mensa["phone"],
        "latitude": mensa["latitude"],
        "longitude": mensa["longitude"],
        "feed_today": template_todayURL % (baseurl, urllib.parse.quote(mensa["reference"])),
        "feed_full": template_fullURL % (baseurl, urllib.parse.quote(mensa["reference"])),
        "source_today": template_source + mensa["id"],
        "source_full": template_source + mensa["id"]
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


class Parser:
    def __init__(self, baseurl):
        self.baseurl = baseurl
        self.canteens = {}
        for mensaId in canteenDict:
            canteenDict[mensaId]["id"] = mensaId
            self.canteens[canteenDict[mensaId]
                          ["reference"]] = canteenDict[mensaId]

    @staticmethod
    def __now():
        berlin = pytz.timezone('Europe/Berlin')
        now = datetime.datetime.now(berlin)
        return now

    def json(self):
        tmp = {}
        for reference in self.canteens:
            tmp[reference] = template_metaURL % (self.baseurl, reference)
        return json.dumps(tmp, indent=2)

    def meta(self, name):
        if name in self.canteens:
            return _generateCanteenMeta(self.canteens[name], self.baseurl)
        return 'Wrong mensa name'

    def feed_today(self, name):
        if name in self.canteens:
            today = self.__now().date()
            lazyBuilder = LazyBuilder()
            mensaId = self.canteens[name]["id"]
            parse_url(lazyBuilder, mensaId, today)
            return lazyBuilder.toXMLFeed()
        return 'Wrong mensa name'

    def feed_all(self, name):
        if name in self.canteens:
            mensaId = self.canteens[name]["id"]
            lazyBuilder = LazyBuilder()

            date = self.__now()

            # Get this week
            while parse_url(lazyBuilder, mensaId, date.date()):
                date += datetime.timedelta(days=1)

            # Skip over weekend
            if date.weekday() > 4:
                date += datetime.timedelta(days=7 - date.weekday())

                # Get next week
                while parse_url(lazyBuilder, mensaId, date.date()):
                    date += datetime.timedelta(days=1)

            return lazyBuilder.toXMLFeed()
        return 'Wrong mensa name'


def getParser(baseurl):
    parser = Parser(baseurl)
    return parser


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(getParser("http://localhost/").feed_today("iwz-deutz"))
