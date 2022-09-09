#!/usr/bin/env python
# Python 3
import os
import logging
import re
import json
import datetime
import urllib
import requests

try:
    from version import __version__, useragentname, useragentcomment
    from util import StyledLazyBuilder, nowBerlin, weekdays_map
except ModuleNotFoundError:
    import sys
    include = os.path.relpath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, include)
    from version import __version__, useragentname, useragentcomment
    from util import StyledLazyBuilder, nowBerlin, weekdays_map

metaJson = os.path.join(os.path.dirname(__file__), "ulm.json")

metaTemplateFile = os.path.join(
    os.path.dirname(__file__), "metaTemplate_ulm.xml")

price_roles_regex = re.compile(r'€\s*(?P<price>\d+[,.]\d{2})')
price_single_regex = re.compile(r'(?P<price>\d+[,.]\d{2})\s*€')
date_regex = re.compile(r'(?P<date>\d{4}-\d{2}-\d{2})')
remove_notes_regex = re.compile(
    r'\([A-Z0-9,\s]*\)\s*')  # Strip notes from meal
remove_uppercase_regex = re.compile(
    '[A-Z]{3,}')  # Strip uppercase from meal_raw

roles = ('student', 'employee', 'other')
weekdays = ('Monday', 'Tuesday', 'Wednesday',
            'Thursday', 'Friday', 'Saturday', 'Sunday')
default_category = "Essen"

legend = {
    'S': "Schwein",
    'R': "Rind",
    'G': "Geflügel",
    '1': "Farbstoff",
    '2': "Konservierungsstoff",
    '3': "Antioxidationsmittel",
    '4': "Geschmacksverstärker",
    '5': "geschwefelt",
    '6': "geschwärzt",
    '7': "gewachst",
    '8': "Phosphat",
    '9': "Süßungsmitteln",
    '10': "Phenylalani",
    '13': "Krebstieren",
    '14': "Ei",
    '22': "Erdnuss",
    '23': "Soja",
    '24': "Milch/Milchprodukte",
    '25': "Schalenfrucht (alle Nussarten)",
    '26': "Sellerie",
    '27': "Senf",
    '28': "Sesamsamen",
    '29': "Schwefeldioxid",
    '30': "Sulfit",
    '31': "Lupine",
    '32': "Weichtiere",
    '34': "Gluten",
    '35': "Fisch"
}

headers = {
    'User-Agent': f'{useragentname}/{__version__} (+{useragentcomment}) {requests.utils.default_user_agent()}',
    'Accept': 'application/json',
    'Accept-Language': 'de-De,de'
}


def _from_json(canteen, url, place):

    if not url.startswith("http://") and not url.startswith("https://"):
        raise RuntimeError(f"url is not an allowed URL: '{url}'")
    result = requests.get(url, headers=headers)
    if result.status_code == 404:
        logging.warning(f"{result} for {url}. Setting week 'closed'")
        # Set 7 days closed
        for i in range(7):
            canteen.setDayClosed((nowBerlin().date() + datetime.timedelta(i)))
        return

    try:
        data = result.json()
    except json.decoder.JSONDecodeError as e:
        logging.error(f"JSONDecodeError: {e}")
        data = None

    if not data or 'weeks' not in data or not data['weeks']:
        logging.warning(
            f'Empty/malformed json file, setting week to "closed" ({url})')
        # Set 7 days closed
        for i in range(7):
            canteen.setDayClosed((nowBerlin().date() + datetime.timedelta(i)))
        return

    for week in data['weeks']:
        for day in week['days']:
            if date_regex.match(day['date']):
                # YYYY-mm-dd
                date = day['date']
            else:
                # Monday, Tueday, ...
                today = nowBerlin().date()
                weekday = weekdays.index(day['date'])
                till_next = (weekday - today.weekday() + 7) % 7
                date = (today + datetime.timedelta(days=till_next)
                        ).strftime('%Y-%m-%d')

            if place not in day:
                continue

            mensa = day[place]

            if 'open' in mensa and not mensa['open']:
                canteen.setDayClosed(date)
                continue

            if 'meals' not in mensa:
                continue

            for meal in mensa['meals']:
                name = remove_notes_regex.sub('', meal['meal']).strip(' /')

                # Prices
                if 'price' in meal and meal['price']:
                    prices = price_roles_regex.findall(meal['price'])
                    if len(prices) > len(roles):
                        prices = prices[0:len(roles)]
                    if not prices and price_single_regex.search(meal['price']):
                        prices = [price_single_regex.search(
                            meal['price']).group('price')]
                        if len(prices) > len(roles):
                            prices = prices[0:len(roles)]

                else:
                    prices = []

                # Get the notes from the meal_raw field
                notes = []
                if 'meal_raw' in meal:
                    try:
                        # Remove duplicate info from meal_raw
                        raw = remove_uppercase_regex.sub(
                            '', meal['meal_raw'].strip()).strip(' /')
                        raw_parts = raw.split()
                        name_parts = name.split()
                        for x in name_parts:
                            if x in raw_parts:
                                raw_parts.remove(x)
                        raw = ' '.join(raw_parts)

                        # Split at whitespace, round brackets and comma
                        raw = raw.replace('(', ' ').replace(
                            ')', ' ').replace(',', ' ').replace('\uf02f', '')
                        tags = [s.strip() for s in raw.split() if s.strip()]

                        # Convert via legend
                        for tag in set(tags):
                            if tag in legend:
                                notes.append(legend[tag])
                            else:
                                notes.append(tag)
                    except Exception as e:
                        # traceback.print_exc()
                        logging.warning("Could not generate notes: %r" % (e,))

                if name:
                    canteen.addMeal(
                        date, meal['category'], name, notes, prices, roles)
                else:
                    # No meal name -> use category as name and a default
                    # category
                    canteen.addMeal(date, default_category,
                                    meal['category'], notes, prices, roles)


def _parse_url(sourcepage, filename, place):
    canteen = StyledLazyBuilder()
    _from_json(canteen, sourcepage + filename, place)
    return canteen.toXMLFeed()


def _generateCanteenMeta(obj, name, url_template):
    """Generate an openmensa XML meta feed from the static json file using an XML template"""
    template = open(metaTemplateFile).read()

    for mensa in obj["mensen"]:
        if not mensa["xml"]:
            continue

        if name != mensa["xml"]:
            continue

        data = {
            "name": mensa["name"],
            "adress": "%s, %s %s" % (mensa["strasse"], mensa["plz"], mensa["ort"]),
            "city": mensa["ort"],
            "phone": mensa["phone"],
            "latitude": mensa["latitude"],
            "longitude": mensa["longitude"],
            "feed_full": url_template.format(metaOrFeed='feed', mensaReference=urllib.parse.quote(mensa["xml"])),
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
    def __init__(self, url_template, sourceurl):
        self.url_template = url_template
        self.sourceurl = sourceurl
        self.metaObj = json.load(open(metaJson))

        self.xmlnames = []
        self.canteens = {}
        for mensa in self.metaObj["mensen"]:
            self.xmlnames.append(mensa["xml"])
            self.canteens[mensa["xml"]] = (mensa["file"], mensa["filter"])

    def json(self):
        tmp = {}
        for name in self.xmlnames:
            tmp[name] = self.url_template.format(
                metaOrFeed='meta', mensaReference=urllib.parse.quote(name))
        return json.dumps(tmp, indent=2)

    def meta(self, name):
        return _generateCanteenMeta(self.metaObj, name, self.url_template)

    def feed(self, name):
        return _parse_url(
            self.sourceurl, self.canteens[name][0], self.canteens[name][1])


def getParser(url_template):
    parser = Parser(
        url_template, sourceurl='https://www.uni-ulm.de/mensaplan/data/')
    return parser


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(getParser("http://localhost/").feed("bistro"))
