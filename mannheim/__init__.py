#!/usr/bin/env python
# Python 3
import os
import datetime
import logging
import json
import re
import urllib

import requests
from bs4 import BeautifulSoup

try:
    from version import __version__, useragentname, useragentcomment
    from util import StyledLazyBuilder, nowBerlin
except ModuleNotFoundError:
    import sys
    include = os.path.relpath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, include)
    from version import __version__, useragentname, useragentcomment
    from util import StyledLazyBuilder, nowBerlin

metaJson = os.path.join(os.path.dirname(__file__), "mannheim.json")

metaTemplateFile = os.path.join(os.path.dirname(
    __file__), "metaTemplate_mannheim.xml")

weekdaysMap = [
    ("Mo", "monday"),
    ("Di", "tuesday"),
    ("Mi", "wednesday"),
    ("Do", "thursday"),
    ("Fr", "friday"),
    ("Sa", "saturday"),
    ("So", "sunday")
]

authorization = False
if os.path.isfile(os.path.join(os.path.dirname(__file__), '.password.txt')):
    with open(os.path.join(os.path.dirname(__file__), '.password.txt')) as af:
        authorization = af.read()
else:
    authorization = os.getenv('MANNHEIM_AUTH')

if not authorization:
    raise RuntimeError("Authentication data not found")

headers = {
    'User-Agent': f'{useragentname}/{__version__} (+{useragentcomment}) {requests.utils.default_user_agent()}',
    'Accept': 'application/json',
    'Accept-Language': 'de-De,de',
    'X-App-Token': authorization
}

additives = None


def additive(data, key):
    global additives
    if additives is None:
        # Build table from additives list
        additives = {}
        for a in data['additives']:
            if a['key'] and a['value']:
                additives[a['key']] = a
    if key in additives:
        return additives[key]['value']
    return key


showFilters = None


def showFilter(data, filterid):
    global showFilters
    if showFilters is None:
        # Build table from list
        showFilters = {}
        for f in data['filter']:
            showFilters[f['id']] = f['name']
    if isinstance(filterid, int):
        filterid = str(filterid)
    if filterid in showFilters:
        return showFilters[filterid]
    return None


def mensa_info(apiurl, days, canteenid, alternative, canteen=None, day=0):
    now = nowBerlin()
    now += datetime.timedelta(days=day)
    if now.weekday() == 6:  # Sunday
        now += datetime.timedelta(days=1)  # Sunday -> Monday
    morning = datetime.datetime(now.year, now.month, now.day, 11)
    timestamp = int(
        1000 * morning.replace(tzinfo=datetime.timezone.utc).timestamp())

    url = apiurl + f'mensa/info?id={canteenid}&date={timestamp}&language=de'

    if not url.startswith("http://") and not url.startswith("https://"):
        raise RuntimeError(f"url is not an allowed URL: '{url}'")

    try:
        r = requests.get(url, headers=headers)
    except requests.exceptions.ConnectionError as e:
        logging.warning(e)
        r = requests.get(url, headers=headers, verify=False)

    if r.status_code != 200:
        raise RuntimeError(f"Error {r.status_code}: {r.text}")

    try:
        data = r.json()
    except json.decoder.JSONDecodeError as e:
        logging.error(f"'{url}' response:\n{r.text}")
        raise e

    if canteen is None:
        canteen = StyledLazyBuilder()

    if 'menuList' not in data or not data['menuList'] or len(data['menuList']) == 0:
        if not isinstance(alternative, bool) and day == 0:
            logging.info(
                f"Empty menuList {morning.date().isoformat()}. Trying alternative id: {canteenid} -> {alternative}")
            return mensa_info(apiurl, days, alternative, False)
        else:
            # If empty, stop here, do not try more days
            logging.info(
                f"Empty menuList id={canteenid} {morning.date().isoformat()} (day {day + 1} of {days}).")
            canteen.setDayClosed(morning.date())
            return canteen.toXMLFeed()

    date = data['date'].split('T')[0]
    cats = {}
    for menu in data['menuList']:
        categoryName = menu['title']
        if categoryName in cats:
            cats[categoryName] += 1
            categoryName = f"{categoryName} ({cats[categoryName]})"
        else:
            cats[categoryName] = 1

        meals = []
        prices = []
        roles = []
        pricePer = None
        mainDishes = 1
        prefix = ""
        for inp in menu['inputs']:
            if inp['name'] == 'inhalt' and inp['value']:
                document = BeautifulSoup(inp['value'], "html.parser")
                spans = document.children
                notes = []
                for span in spans:
                    if isinstance(span, str):
                        text = span
                    elif span.name != 'sup':
                        text = next(span.stripped_strings)
                    if text == 'oder':
                        mainDishes += 1
                    if text in ['mit', 'an']:
                        prefix = text + " "
                    elif len(text) > 1 and text != 'und':
                        if not isinstance(span, str):
                            if span.name == 'span':
                                if span['class']:
                                    notes += [showFilter(data, c[12:]) for c in span['class'] if c.startswith(
                                        'showOnFilter') and showFilter(data, c[12:])]
                            if span.name == 'sup':
                                sup = span
                                text = ""
                            else:
                                sup = span.find("sup")
                            if sup:
                                sup = sup.text.strip()[1:-1].split(",")
                                sup = [s.strip() for s in sup]
                                notes += [additive(data, s) for s in sup]

                        if text:
                            if text.startswith(", "):
                                text = text[2:]
                            notes = [note.strip()
                                     for note in notes if note and note.strip()]
                            meals.append([prefix + text, notes])
                            notes = []
                            prefix = ""
                    if notes:
                        meals[-1][1].extend([note.strip()
                                            for note in notes if note and note.strip()])
                        notes = []
            elif inp['name'] == 'preisStudent' and inp['value']:
                prices.append(inp['value'])
                roles.append('student')
            elif inp['name'] == 'preisBediensteter' and inp['value']:
                prices.append(inp['value'])
                roles.append('employee')
            elif inp['name'] == 'preisGast' and inp['value']:
                prices.append(inp['value'])
                roles.append('other')
            elif inp['name'] == 'menge' and inp['value']:
                if inp['value'].lower().startswith('pro'):
                    pricePer = 'Preis ' + inp['value']
                else:
                    pricePer = 'Preis pro ' + inp['value']

        if meals:
            first = 0
            for meal in meals:
                mealName, notes = meal
                if first < mainDishes:
                    first += 1
                    if pricePer:
                        notes.insert(0, pricePer)
                    canteen.addMeal(date, categoryName, mealName.strip()[:249],
                                    notes, prices, roles if prices else None)
                else:
                    canteen.addMeal(date, categoryName,
                                    mealName.strip()[:249], notes)

    day = day + 1
    if days > day:
        return mensa_info(apiurl, days, canteenid, alternative, canteen, day)
    else:
        return canteen.toXMLFeed()


def _generateCanteenMeta(name, url_template):
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
            "feed_today": url_template.format(metaOrFeed='today', mensaReference=urllib.parse.quote(shortname)),
            "feed_full": url_template.format(metaOrFeed='feed', mensaReference=urllib.parse.quote(shortname)),
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
    def __init__(self, url_template, city, handler, shared_prefix):
        self.url_template = url_template
        self.handler = handler
        self.shared_prefix = shared_prefix
        self.canteens = {}

    def define(self, name, canteenid, alternative=False, disabled=False):
        self.canteens[name] = [canteenid, alternative]

    def json(self):
        tmp = self.canteens.copy()
        for name in tmp:
            tmp[name] = self.url_template.format(
                metaOrFeed='meta', mensaReference=urllib.parse.quote(name))
        return json.dumps(tmp, indent=2)

    def meta(self, name):
        return _generateCanteenMeta(name, self.url_template)

    def feed_today(self, name):
        if name not in self.canteens:
            return 'wrong mensa name'
        return self.handler(self.shared_prefix, 1, *self.canteens[name])

    def feed_all(self, name):
        if name not in self.canteens:
            return 'wrong mensa name'
        return self.handler(self.shared_prefix, 5, *self.canteens[name])


def getParser(url_template):
    parser = Parser(url_template, 'mannheim',
                    handler=mensa_info,
                    shared_prefix='https://studiplus.stw-ma.de/api/app/')
    parser.define('schloss', 610)
    parser.define('hochschule', 611, 5599)
    parser.define('metropol', 613)
    parser.define('wohlgelegen', 614)
    parser.define('horizonte', 713, 502)
    parser.define('wagon', 709, 5189)
    parser.define('musikhochschule', 714)

    # parser.define('kubus', 406) # Disabled on openmensa.org
    # parser.define('metropol2go', 5687) # Disabled on openmensa.org
    # parser.define('eo', 170) # Disabled on openmensa.org

    # parser.define('dhbw', 718) # TODO this might be eppelheim

    return parser


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(getParser("http://localhost/").feed_today("wohlgelegen"))
