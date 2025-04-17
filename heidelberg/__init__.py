#!/usr/bin/env python
# Python 3
import urllib.request
import os
import json
import re
import time
import io
import logging
from threading import Lock

import lxml.etree
import defusedxml.lxml

try:
    from version import __version__, useragentname, useragentcomment
    from util import now_local, weekdays_map
except ModuleNotFoundError:
    import sys
    include = os.path.relpath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, include)
    from version import __version__, useragentname, useragentcomment
    from util import now_local, weekdays_map

mealsURL = 'https://www.stw.uni-heidelberg.de/appdata/sp.xml'
mealsURL_authorization = False
if os.path.isfile(os.path.join(os.path.dirname(__file__), '.password.txt')):
    with open(os.path.join(os.path.dirname(__file__), '.password.txt')) as af:
        mealsURL_authorization = af.read()
else:
    mealsURL_authorization = os.getenv('HEIDELBERG_AUTH')

if not mealsURL_authorization:
    raise RuntimeError("Authentication data not found")

metaURL = 'https://www.stw.uni-heidelberg.de/sites/default/files/download/pdf/stwhd-de.json'
__timeoutSeconds = 20

xslFile = os.path.join(os.path.dirname(__file__), "heidelberg.xsl")
metaTemplateFile = os.path.join(os.path.dirname(__file__), "metaTemplate.xml")

template_sourceURL = "https://www.studentenwerk.uni-heidelberg.de/de/speiseplan_neu"

emptyFeed = '<openmensa xmlns="http://openmensa.org/open-mensa-v2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.1" xsi:schemaLocation="http://openmensa.org/open-mensa-v2 http://openmensa.org/open-mensa-v2.xsd"/><!-- %s -->'

# Maps arbitrary ids to the actual names in the XML feed. The ids are used in the feed URLs
nameMap = {
    "zeughaus": "zeughaus-Mensa im Marstall",
    "triplex": "Triplex-Mensa am Uniplatz",
    "inf304": "Mensa Im Neuenheimer Feld 304",
    "heilbronn_sontheim": "Mensa Heilbronn TechCampus",
    "heilbronn_bildungscampus": "Mensa Bildungscampus Heilbronn",
    "kiau": "Mensa Künzelsau"
}

# Maps arbitrary ids to the actual names in the Meta JSON file.
nameMapMeta = {
    "zeughaus": "zeughaus-Mensa im Marstall",
    "triplex": "Triplex-Mensa am Uniplatz",
    "inf304": "Mensa Im Neuenheimer Feld 304",
    "heilbronn_sontheim": "Mensa Heilbronn",
    "heilbronn_bildungscampus": "Mensa Bildungscampus Heilbronn",
    "kiau": "Mensa Künzelsau"
}


# Maps actual names from the XML feed to the desired names, that will be shown on openmensa.org
desiredName = {
    "zeughaus-Mensa im Marstall": "Heidelberg, zeughaus-Mensa im Marstall",
    "Triplex-Mensa am Uniplatz": "Heidelberg, Triplex-Mensa am Uniplatz",
    "Mensa Im Neuenheimer Feld 304": "Heidelberg, Mensa Im Neuenheimer Feld 304",
    "Mensa Heilbronn TechCampus": "Heilbronn, Mensa Sontheim",
    "Mensa Bildungscampus Heilbronn": "Heilbronn, Mensa Bildungscampus/Europaplatz",
    "Mensa Künzelsau": "Künzelsau, Mensa Reinhold-Würth-Hochschule"
}

weekdays_map = [
    ("Mo", "monday"),
    ("Di", "tuesday"),
    ("Mi", "wednesday"),
    ("Do", "thursday"),
    ("Fr", "friday"),
    ("Sa", "saturday"),
    ("So", "sunday")
]

# Global vars for caching
cache_mealsURL_lock = Lock()
cache_mealsURL_data = None
cache_mealsURL_time = 0

cache_metaURL_lock = Lock()
cache_metaURL_data = None
cache_metaURL_time = 0


def getEmptyFeed(comment="empty"):
    return emptyFeed % comment


def _getShortName(longname):
    """Reverse function for global nameMap dict"""
    for short in nameMap:
        if nameMap[short] == longname:
            return short
    return None

def _getShortNameMeta(longname):
    """Reverse function for global nameMapMeta dict"""
    for short in nameMapMeta:
        if nameMapMeta[short] == longname:
            return short
    return None



def _getMealsURL():
    """Download meals information from XML feed"""
    if not mealsURL.startswith("http://") and not mealsURL.startswith("https://"):
        raise RuntimeError(f"mealsUrl is not an allowed URL: '{mealsURL}'")
    request = urllib.request.Request(mealsURL)
    request.add_header("Authorization", "Basic %s" % mealsURL_authorization)
    request.add_header(
        "User-Agent", f"{useragentname}/{__version__} ({useragentcomment}) Python-urllib/{urllib.request.__version__}")
    result = urllib.request.urlopen(request, timeout=__timeoutSeconds)  # nosec
    return result, 0


def _getMealsURL_cached(max_age_minutes=15):
    """Download meals information from XML feed, if available use a cached version"""
    global cache_mealsURL_lock
    global cache_mealsURL_data
    global cache_mealsURL_time

    age_seconds = (time.time() - cache_mealsURL_time)
    if age_seconds > max_age_minutes*60:
        with cache_mealsURL_lock:
            cache_mealsURL_data = _getMealsURL()[0].read()
            cache_mealsURL_time = time.time()
            age_seconds = 0
            logging.info("##CACHE## Meals cache updated")

    return io.BytesIO(cache_mealsURL_data), age_seconds


def _getMetaURL():
    """Download meta information from JSON source"""
    if not metaURL.startswith("http://") and not metaURL.startswith("https://"):
        raise RuntimeError("metaURL is not an allowed URL: '%s'" % metaURL)
    request = urllib.request.Request(metaURL)
    request.add_header(
        "User-Agent", f"{useragentname}/{__version__} ({useragentcomment}) Python-urllib/{urllib.request.__version__}")
    result = urllib.request.urlopen(request, timeout=__timeoutSeconds)  # nosec
    return result, 0


def _getMetaURL_cached(max_age_minutes=120):
    """Download meta information from JSON source, if available use a cached version"""
    global cache_metaURL_lock
    global cache_metaURL_data
    global cache_metaURL_time
    age_seconds = (time.time() - cache_metaURL_time)
    if age_seconds > max_age_minutes*60:
        with cache_metaURL_lock:
            cache_metaURL_data = _getMetaURL()[0].read()
            cache_metaURL_time = time.time()
            age_seconds = 0
            logging.info("##CACHE## Meta cache updated")

    return io.BytesIO(cache_metaURL_data), age_seconds


def _generateFeed(source, name, date='', lastFetched=0):
    """Generate an openmensa XML feed from the source feed using XSLT"""
    if date == 'today':
        now = now_local()
        date = now.strftime("%Y-%m-%d")

    name = nameMap[name]

    dom = defusedxml.lxml.parse(source)
    xslt_tree = defusedxml.lxml.parse(xslFile)
    xslt = lxml.etree.XSLT(xslt_tree)
    newdom = xslt(dom, canteenName=lxml.etree.XSLT.strparam(name), canteenDesiredName=lxml.etree.XSLT.strparam(
        desiredName[name]), specificDate=lxml.etree.XSLT.strparam(date), lastFetched=lxml.etree.XSLT.strparam('%d' % lastFetched))
    return lxml.etree.tostring(newdom,
                               pretty_print=True,
                               xml_declaration=True,
                               encoding=newdom.docinfo.encoding)


def _generateCanteenMeta(source, name, url_template):
    """Generate an openmensa XML meta feed from the source feed using an XML template"""
    obj = json.loads(source.read().decode("utf-8-sig"))
    with open(metaTemplateFile) as f:
        template = f.read()

    shortname = name
    name = nameMap[shortname]

    for mensa in obj["mensen"]:
        if not mensa["xml"]:
            continue

        if name != mensa["xml"]:
            continue

        data = {
            "name": desiredName[mensa["xml"]],
            "adress": "%s, %s %s" % (mensa["strasse"], mensa["plz"], mensa["ort"]),
            "city": mensa["ort"],
            "latitude": mensa["latitude"],
            "longitude": mensa["longitude"],
            "feed_today": url_template.format(metaOrFeed='today', mensaReference=urllib.parse.quote(shortname)),
            "feed_full": url_template.format(metaOrFeed='feed', mensaReference=urllib.parse.quote(shortname)),
            "source_today": template_sourceURL,
            "source_full": template_sourceURL
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

    return getEmptyFeed("Unkown canteen - wrong name?")


def _generateCanteenList_JSON(source, url_template):
    """Generate a JSON file for openmensa.org containing basic information about all available canteens"""
    obj = json.loads(source.read().decode("utf-8-sig"))
    data = {}

    for mensa in obj["mensen"]:
        if not mensa["xml"]:
            continue

        shortName = _getShortNameMeta(mensa["xml"])

        data[shortName] = url_template.format(
            metaOrFeed='meta', mensaReference=urllib.parse.quote(shortName))

    return json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))


class Parser:
    def __init__(self, url_template):
        self.url_template = url_template
        self.canteens = nameMap

    def json(self):
        """Return a list of all the canteens as JSON"""
        stream, _ = _getMetaURL_cached()
        return _generateCanteenList_JSON(stream, self.url_template)

    def meta(self, name):
        """Return a feed with all available meta information for openmensa.org"""
        stream, _ = _getMetaURL_cached()
        return _generateCanteenMeta(stream, name, self.url_template)

    @staticmethod
    def feed_today(name=""):
        """Return today's meal feed for openmensa.org"""
        stream, age_seconds = _getMealsURL_cached()
        return _generateFeed(stream, name, 'today', age_seconds)

    @staticmethod
    def feed_all(name=""):
        """Return a feed with all available meal information for openmensa.org"""
        stream, age_seconds = _getMealsURL_cached()
        return _generateFeed(stream, name, '', age_seconds)


def getParser(url_template):
    parser = Parser(url_template)
    return parser


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(getParser("http://localhost/").feed_all("inf304").decode("utf-8"))
