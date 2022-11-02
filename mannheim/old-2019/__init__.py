#!python3
import requests
from bs4 import BeautifulSoup
import os
import re
import datetime
import logging
import json
import urllib

try:
    from version import __version__, useragentname, useragentcomment
    from util import StyledLazyBuilder, now_local
except ModuleNotFoundError:
    import sys
    include = os.path.relpath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, include)
    from version import __version__, useragentname, useragentcomment
    from util import StyledLazyBuilder, now_local

# Based on https://github.com/mswart/openmensa-parsers/blob/master/magdeburg.py

metaJson = os.path.join(os.path.dirname(__file__), "mannheim.json")

metaTemplateFile = os.path.join(os.path.dirname(
    __file__), "metaTemplate_mannheim.xml")

template_metaURL = "%smannheim/meta/%s.xml"
template_todayURL = "%smannheim/today/%s.xml"
template_fullURL = "%smannheim/all/%s.xml"

weekdays = [
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag"
]

weekdaysMap = [
    ("Mo", "monday"),
    ("Di", "tuesday"),
    ("Mi", "wednesday"),
    ("Do", "thursday"),
    ("Fr", "friday"),
    ("Sa", "saturday"),
    ("So", "sunday")
]

headers = {
    'User-Agent': f'{useragentname}/{__version__} (+{useragentcomment}) {requests.utils.default_user_agent()}'
}

roles = ('student', 'employee', 'other')


def correctCapitalization(s): return s[0].upper() + s[1:].lower()


day_regex = re.compile(r'(?P<date>\d{2}\.\d{2}\.\d{4})')
removeextras_regex = re.compile(r'\s+\[(\w,?)+\]')
price_regex = re.compile(
    'Bedienstete \+ (?P<employee>\d+)\%, Gäste \+ (?P<guest>\d+)\%')
euro_regex = re.compile(r'(\d+,\d+) €')
whitespace = re.compile(r'\s+')


def parse_url(url, today=False):
    today = now_local()
    if today.weekday() == 6:  # Sunday
        today += datetime.timedelta(days=1)  # Tomorrow

    url = url.format(year=today.strftime(
        '%Y'), month=today.strftime('%m'), day=today.strftime('%d'))

    if not url.startswith("http://") and not url.startswith("https://"):
        raise RuntimeError("url is not an allowed URL: '%s'" % url)

    try:
        content = requests.get(url, headers=headers).text
    except requests.exceptions.ConnectionError as e:
        logging.warning(e)
        content = requests.get(url, headers=headers, verify=False).text

    # Fix table
    content = content.replace("</th>", "</td>").replace("<th ", "<td ")

    document = BeautifulSoup(content, "html.parser")
    canteen = StyledLazyBuilder()

    # date
    fromTo = document.find("h2").text.strip()
    fromMatch = day_regex.search(fromTo).group("date")
    fromDatetime = datetime.datetime.strptime(fromMatch, "%d.%m.%Y")

    # Legend
    legend = {}
    for span in document.select("#legend>span"):
        sup = span.find("sup")
        if sup and sup.text:
            key = sup.text.strip()
            sup.clear()
            value = span.text.strip()
            legend[key] = value

    # Prices for employees and guests
    try:
        p = price_regex.search(document.find(
            "p", {"id": "message"}).text).groupdict()
        employee_multiplier = 1.0 + int(p["employee"]) / 100.0
        guest_multiplier = 1.0 + int(p["guest"]) / 100.0
    except (AttributeError, TypeError, KeyError, ValueError):
        employee_multiplier = 1.25
        guest_multiplier = 1.60

    table = document.find("table", {"id": "previewTable"})
    if not table:
        # previewTable not found, e.g. temporary closed
        # Set 7 days closed
        for i in range(7):
            canteen.setDayClosed(
                (datetime.date.today() + datetime.timedelta(i)))

        return canteen.toXMLFeed()

    trs = table.find_all("tr")

    canteenCategories = []

    firstTr = True
    previous = None   # previous tr row
    for tr in trs:
        closed = False
        mealsFound = False
        if firstTr:
            # First table row contains the names of the different categories
            firstTr = False

            for th in tr.find_all("td")[1:]:
                canteenCategories.append(th.text.strip())
        elif previous is None:
            # Normal table row containing meal information
            previous = tr

        else:
            # Price table row
            datetd = previous.find("td", {"class": "first"})
            weekday = datetd.text.strip()
            date = fromDatetime
            i = 0
            while weekdays.index(weekday) != date.weekday() and i < 8:
                date += datetime.timedelta(days=1)
                i += 1
            if i > 7:
                logging.error(
                    "Date could not be calculated from %r" % (weekday,))
            date = date.date()

            if len(previous.find_all("td")) < 2 or "geschlossen" == previous.find_all("td")[1].text.strip():
                closed = date

            cat = 0

            for td0, td1 in zip(previous.find_all("td")[1:], tr.find_all("td")):
                if "heute kein Angebot" in td0.text or "geschlossen" in td0.text:
                    cat += 1
                    continue

                notes = set()

                # Category
                if td0.find("h2"):
                    categoryName = canteenCategories[cat] + " " + \
                        correctCapitalization(td0.find("h2").text.strip())
                else:
                    categoryName = canteenCategories[cat]

                if "Kubusangebote am Themenpark" in td0.text:
                    canteen.addMeal(date, categoryName,
                                    "Kubusangebote am Themenpark", [])
                    cat += 1
                    continue

                # Additives: SI,Mi,G,1,2,...
                for sup in td0.find_all("sup"):
                    keep = []
                    for a in sup.text.strip("()").split(","):
                        if a == "Veg":
                            keep.append("🥕")
                            notes.add("🥕 = Vegetarisch")
                        elif a == "Vga":
                            keep.append("🌿")
                            notes.add("🌿 = Vegan")
                        elif a == "Bio":
                            keep.append("♻️")
                            keep.append("♻️ = Bio")
                        elif a and a in legend:
                            notes.add(legend[a])
                        elif a:
                            notes.add(a)
                    sup.clear()
                    if keep:
                        sup.append("%s" % (",".join(keep), ))

                # Name
                name = whitespace.sub(" ", td0.text).strip().replace(" ,", ",")

                # Prices
                prices = []
                spans = td1.find_all("span", {"class": "label"})
                if spans:
                    try:
                        price = float(euro_regex.search(
                            spans[0].text).group(1).replace(",", "."))
                    except (AttributeError, TypeError, KeyError, ValueError):
                        notes.add(spans[0].text.strip() + " Preis")
                    if len(spans) == 2:
                        notes.add(spans[1].text.strip() + " Preis")
                    prices = (price, price * employee_multiplier,
                              price * guest_multiplier)

                canteen.addMeal(date, categoryName, name,
                                notes, prices, roles if prices else None)

                mealsFound = True
                cat += 1

            previous = None
        if not mealsFound and closed:
            canteen.setDayClosed(closed)

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

    def feed_today(self, name):
        return self.handler(self.canteens[name])

    def feed_all(self, name):
        return self.handler(self.canteens[name])


def getParser(baseurl):
    parser = Parser(baseurl, 'mannheim', handler=parse_url,
                    shared_prefix='https://www.stw-ma.de/')

    parser.define(
        'schloss', suffix='menüplan_schlossmensa-date-{year}%25252d{month}%25252d{day}-view-week.html')
    parser.define(
        'hochschule', suffix='Essen+_+Trinken/Speisepl%C3%A4ne/Hochschule+Mannheim-date-{year}%25252d{month}%25252d{day}-view-week.html')
    parser.define(
        'wagon', suffix='Essen+_+Trinken/Speisepläne/MensaWagon-date-{year}%25252d{month}%25252d{day}-view-week.html')
    parser.define(
        'metropol', suffix='Essen+_+Trinken/Speisepl%C3%A4ne/Mensaria+Metropol-date-{year}%25252d{month}%25252d{day}-view-week.html')
    parser.define(
        'wohlgelegen', suffix='Essen+_+Trinken/Speisepl%C3%A4ne/Mensaria+Wohlgelegen-date-{year}%25252d{month}%25252d{day}-view-week.html')
    parser.define('musikhochschule',
                  suffix='Essen+_+Trinken/Speisepl%C3%A4ne/Cafeteria+Musikhochschule-date-{year}%25252d{month}%25252d{day}-view-week.html')
    return parser


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    # print(getParser("http://localhost/").json("https://localhost/meta/%s.xml"))
    print(getParser("http://localhost/").feed_today('schloss'))
