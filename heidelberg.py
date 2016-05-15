#!/usr/bin/env python
#
# Python 3

import urllib.request
import lxml.etree
import datetime
import pytz
import os
import json
import re
import time
import io
from threading import Lock 

mealsURL = 'https://www.stw.uni-heidelberg.de/appdata/sp.xml'
mealsURL_authorization = ""
metaURL = 'http://www.stw.uni-heidelberg.de/sites/default/files/download/pdf/stwhd-de.json'

xslFile = os.path.join(os.path.dirname(__file__), "heidelberg.xsl")
metaTemplateFile = os.path.join(os.path.dirname(__file__), "metaTemplate.xml")

template_sourceURL = "http://www.studentenwerk.uni-heidelberg.de/de/speiseplan"
template_metaURL = "https://mensahd-cuzi.rhcloud.com/meta/%s.xml"
template_todayURL = "https://mensahd-cuzi.rhcloud.com/today/%s.xml"
template_fullURL = "https://mensahd-cuzi.rhcloud.com/all/%s.xml"



# Maps arbitrary ids to the actual names in the XML feed. The ids are used in the feed URLs
nameMap = {
    "zeughaus" : "zeughaus-Mensa im Marstall",
    "triplex" : "Triplex-Mensa am Uniplatz",
    "inf304" : "Mensa Im Neuenheimer Feld 304",
    "heilbronn_sontheim" : "Mensa Heilbronn",
    "heilbronn_bildungscampus" : "Mensa Bildungscampus Heilbronn",
    "kiau" : "Mensa Künzelsau"
    }

# Maps actual names from the XML feed to the desired names, that will be shown on openmensa.org
desiredName = {
    "zeughaus-Mensa im Marstall" : "Heidelberg, zeughaus-Mensa im Marstall",
    "Triplex-Mensa am Uniplatz" : "Heidelberg, Triplex-Mensa am Uniplatz",
    "Mensa Im Neuenheimer Feld 304" : "Heidelberg, Mensa Im Neuenheimer Feld 304",
    "Mensa Heilbronn" : "Heilbronn, Mensa Sontheim",
    "Mensa Bildungscampus Heilbronn" : "Heilbronn, Mensa Bildungscampus/Europaplatz",
    "Mensa Künzelsau" : "Künzelsau, Mensa Reinhold-Würth-Hochschule"
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

# Global vars for caching
cache_mealsURL_lock = Lock()
cache_mealsURL_data = None
cache_mealsURL_time = 0

cache_metaURL_lock = Lock()
cache_metaURL_data = None
cache_metaURL_time = 0

def _getShortName(longname):
    """Reverse function for global nameMap dict"""
    for short in nameMap:
        if nameMap[short] == longname:
            return short
    return None

def _getMealsURL():
    """Download meals information from XML feed"""
    request = urllib.request.Request(mealsURL)
    request.add_header("Authorization", "Basic %s" % mealsURL_authorization)
    result = urllib.request.urlopen(request)
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
            print("##CACHE## Meals cache updated")

    return io.BytesIO(cache_mealsURL_data), age_seconds

def _getMetaURL():
    """Download meta information from JSON source"""
    request = urllib.request.Request(metaURL) 
    result = urllib.request.urlopen(request)
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
            print("##CACHE## Meta cache updated")

    return io.BytesIO(cache_metaURL_data), age_seconds
    
def _generateFeed(source, name, date='', lastFetched=0):
    """Generate an openmensa XML feed from the source feed using XSLT"""
    if date == 'today':
        berlin = pytz.timezone('Europe/Berlin')
        now = datetime.datetime.now(berlin)
        date = now.strftime("%Y-%m-%d")
    
    name = nameMap[name]
    
    dom = lxml.etree.parse(source)
    xslt_tree = lxml.etree.parse(xslFile)
    xslt = lxml.etree.XSLT(xslt_tree )
    newdom = xslt(dom, canteenName=lxml.etree.XSLT.strparam(name), canteenDesiredName=lxml.etree.XSLT.strparam(desiredName[name]), specificDate=lxml.etree.XSLT.strparam(date), lastFetched=lxml.etree.XSLT.strparam('%d' % lastFetched))
    return lxml.etree.tostring(newdom, pretty_print=True)

def _generateCanteenMeta(source, name):
    """Generate an openmensa XML meta feed from the source feed using an XML template"""
    obj = json.loads(source.read().decode("utf-8-sig"))
    template = open(metaTemplateFile).read()

    shortname = name
    name = nameMap[shortname]

    for mensa in obj["mensen"]:
        if not mensa["xml"]:
            continue
        
        if name != mensa["xml"]:
            continue

        data = {
            "name" : desiredName[mensa["xml"]],
            "adress" : "%s %s %s %s" % (mensa["name"],mensa["strasse"],mensa["plz"],mensa["ort"]),
            "city" : mensa["ort"],
            "latitude" : mensa["latitude"],
            "longitude" : mensa["longitude"],
            "feed_today" : template_todayURL % urllib.parse.quote(shortname),
            "feed_full" : template_fullURL % urllib.parse.quote(shortname),
            "source_today" : template_sourceURL,
            "source_full" : template_sourceURL
            }
        openingTimes = {}
        infokurz = mensa["infokurz"]
        pattern = re.compile("([A-Z][a-z])( - ([A-Z][a-z]))? (\d{1,2})\.(\d{2}) - (\d{1,2})\.(\d{2}) Uhr")
        m = re.findall(pattern, infokurz)
        for result in m:
            fromDay,_,toDay,fromTimeH,fromTimeM,toTimeH,toTimeM = result
            openingTimes[fromDay] = "%s:%s-%s:%s" % (fromTimeH,fromTimeM,toTimeH,toTimeM)
            if toDay:
                select = False
                for short,long in weekdaysMap:
                    if short == fromDay:
                        select = True
                    elif select:
                        openingTimes[short] = "%s:%s-%s:%s" % (fromTimeH,fromTimeM,toTimeH,toTimeM)
                    if short == toDay:
                        select = False

            for short,long in weekdaysMap:
                if short in openingTimes:
                    data[long] = 'open="%s"' % openingTimes[short]
                else:
                    data[long] = 'closed="true"'
            
        
        xml = template.format(**data)
        return xml

    return '<openmensa xmlns="http://openmensa.org/open-mensa-v2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.1" xsi:schemaLocation="http://openmensa.org/open-mensa-v2 http://openmensa.org/open-mensa-v2.xsd"/>'

def _generateCanteenList(source):
    """Generate an XML feed with basic information about all available canteens"""
    obj = json.loads(source.read().decode("utf-8-sig"))
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<canteens>\n'

    for mensa in obj["mensen"]:
        if not mensa["xml"]:
            continue

        shortName = _getShortName(mensa["xml"])
        xml += "  <canteen>\n"
        xml += "    <title>%s</title>\n" % mensa["name"]
        if mensa["xml"]:
            xml += "    <name>%s</name>\n" % mensa["xml"]
            xml += "    <openmensaname>%s</openmensaname>\n" % desiredName[mensa["xml"]]
            xml += "    <id>%s</id>\n" % shortName
            xml += "    <meta>%s</meta>\n" % template_metaURL % urllib.parse.quote(shortName)
            xml += "    <today>%s</today>\n" % template_todayURL % urllib.parse.quote(shortName)
            xml += "    <full>%s</full>\n" % template_fullURL % urllib.parse.quote(shortName)
        xml += "  </canteen>\n"
    xml += '</canteens>'
    return xml
    
def _generateCanteenList_JSON(source):
    """Generate a JSON file for openmensa.org containing basic information about all available canteens"""
    obj = json.loads(source.read().decode("utf-8-sig"))
    data = {}

    for mensa in obj["mensen"]:
        if not mensa["xml"]:
            continue

        shortName = _getShortName(mensa["xml"])
        
        data[shortName] = template_metaURL % urllib.parse.quote(shortName)
    return json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))


def today(name=''):
    """Return today's meal feed for openmensa.org"""
    stream, age_seconds = _getMealsURL_cached()
    return _generateFeed(stream, name, 'today', age_seconds)

def all(name=''):
    """Return a feed with all available meal information for openmensa.org"""
    stream, age_seconds = _getMealsURL_cached()
    return _generateFeed(stream, name, '', age_seconds)

def meta(name):
    """Return a feed with all available meta information for openmensa.org"""
    stream, age_seconds = _getMetaURL_cached()
    return _generateCanteenMeta(stream, name)

def list():
    """Return a list of all the canteens as XML"""
    stream, age_seconds = _getMetaURL_cached()
    return _generateCanteenList(stream)
    
def listJSON():
    """Return a list of all the canteens as JSON"""
    stream, age_seconds = _getMetaURL_cached()
    return _generateCanteenList_JSON(stream)
    
if __name__ == '__main__':
    xml = today()
    print(xml.decode("utf-8"))
