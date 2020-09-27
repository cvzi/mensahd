import os
import json
import logging
import urllib
import re

try:
    from luxembourg.tools import getMenu
except:
    from tools import getMenu

metaJson = os.path.join(os.path.dirname(__file__), "canteenDict.json")

metaTemplateFile = os.path.join(os.path.dirname(__file__), "metaTemplate_luxembourg.xml")

template_metaURL = "%sluxembourg/meta/%s.xml"
template_feedURL = "%sluxembourg/feed/%s.xml"

template_sourceURL = r"https://portal.education.lu/restopolis/Language/fr/MENUS/MENU-DU-JOUR/RestaurantId/%d/ServiceId/%d#12691"

weekdaysMap = [
    ("Mo", "monday"),
    ("Tu", "tuesday"),
    ("We", "wednesday"),
    ("Th", "thursday"),
    ("Fr", "friday"),
    ("Sa", "saturday"),
    ("Su", "sunday")
]


class Parser:
    def feed(self, refName):
        xml, _, _, _ = getMenu(restaurantId=self.canteens[refName]["id"], serviceIds=self.canteens[refName]["services"])
        return xml

    def meta(self, refName):
        """Generate an openmensa XML meta feed from the static json file using an XML template"""
        template = open(metaTemplateFile).read()

        for reference, restaurant in self.canteens.items():
            if refName != reference:
                continue

            if "source" in restaurant and restaurant["source"]:
                sourceUrl = restaurant["source"]
            else:
                sourceUrl = template_sourceURL % (int(restaurant["id"]), int(restaurant["services"][0][0]))

            address = ""
            if restaurant["street"]:
                address += restaurant["street"]
            if restaurant["zip"]:
                address += (", " if address else "") + restaurant["zip"]
            if restaurant["city"]:
                address += ((" " if restaurant["zip"] else ", ") if address else "") + restaurant["city"]

            data = {
                "name": restaurant["name"] + (f" ({restaurant['region']})" if restaurant["region"] else ""),
                "address": address,
                "city": restaurant["city"],
                "phoneXML": f"<phone>{restaurant['phone']}</phone>" if "phone" in restaurant else "",
                "latitude": restaurant["latitude"],
                "longitude": restaurant["longitude"],
                "feed": template_feedURL % (self.baseurl, urllib.parse.quote(reference)),
                "source": sourceUrl,
            }
            openingTimes = ""
            pattern = re.compile("(\d{1,2}):(\d{2}) - (\d{1,2}):(\d{2})")
            serviceStr = " ## ".join(x[1] for x in restaurant["services"])
            m = re.findall(pattern, serviceStr)
            if len(m) == 2:
                fromTimeH, fromTimeM, toTimeH, toTimeM = [int(x) for x in m[0]]
                fromTime2H, fromTime2M, toTime2H, toTime2M = [int(x) for x in m[1]]
                if (fromTime2H - toTimeH) * 60 + fromTime2M - toTimeM < 32:
                    toTimeH, toTimeM = toTime2H, toTime2M
            else:
                fromTimeH, fromTimeM, toTimeH, toTimeM = [int(x) for x in m[0]]

            openingTimes = "%02d:%02d-%02d:%02d" % (
                fromTimeH, fromTimeM, toTimeH, toTimeM)
            if "days" in restaurant:
                fromDay, toDay = [x.strip() for x in restaurant["days"].split("-")]
            else:
                fromDay, toDay = ['Mo', 'Su']

            isOpen = False
            for dayShort, dayXML in weekdaysMap:
                if fromDay == dayShort:
                    isOpen = True
                if isOpen:
                    data[dayXML] = 'open="%s"' % openingTimes
                else:
                    data[dayXML] = 'closed="true"'
                if toDay == dayShort:
                    isOpen = False

            xml = template.format(**data)
            return xml

        return '<openmensa xmlns="http://openmensa.org/open-mensa-v2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.1" xsi:schemaLocation="http://openmensa.org/open-mensa-v2 http://openmensa.org/open-mensa-v2.xsd"/>'

    def __init__(self, baseurl):
        with open(metaJson, 'r', encoding='utf8') as f:
            canteenDict = json.load(f)

        self.baseurl = baseurl

        self.canteens = {}
        for restaurantId, restaurant in canteenDict.items():
            if "active" in restaurant and restaurant["active"] and "reference" in restaurant:
                restaurant["id"] = restaurantId
                self.canteens[restaurant["reference"]] = restaurant

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


def getParser(baseurl):
    parser = Parser(baseurl)
    return parser


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(getParser("http://localhost/").feed("CmpsKiBergAltius"))
    # print(getParser("http://localhost/").meta("CmpsKiBergAltius"))
