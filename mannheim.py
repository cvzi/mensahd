#!python3
import requests
from bs4 import BeautifulSoup
import os
import re
import datetime
import json
from pyopenmensa.feed import LazyBuilder
import urllib

# Based on https://github.com/mswart/openmensa-parsers/blob/master/magdeburg.py

metaJson = os.path.join(os.path.dirname(__file__), "mannheim.json")

metaTemplateFile = os.path.join(os.path.dirname(__file__), "metaTemplate_mannheim.xml")

template_metaURL = "https://mensahd-cuzi.rhcloud.com/mannheim/meta/%s.xml"
template_todayURL = "https://mensahd-cuzi.rhcloud.com/mannheim/feed/%s.xml"
template_fullURL = "https://mensahd-cuzi.rhcloud.com/mannheim/feed/%s.xml"

weekdaysMap = [
    ("Mo", "monday"),
    ("Di", "tuesday"),
    ("Mi", "wednesday"),
    ("Do", "thursday"),
    ("Fr", "friday"),
    ("Sa", "saturday"),
    ("So", "sunday")
    ]


roles = ('student', 'employee', 'other')

correctCapitalization = lambda s : s[0].upper() + s[1:].lower()
day_regex = re.compile('(?P<date>\d{2}\.\d{2}\.\d{4})')
removeextras_regex = re.compile('\s+\[(\w,?)+\]')
price_regex = re.compile('Bedienstete \+ (?P<employee>\d+)\%, Gäste \+ (?P<guest>\d+)\%')
euro_regex = re.compile('(\d+,\d+) €')


def parse_url(url, today=False):
    today = datetime.date.today()
    if today.weekday() == 6: # Sunday
        today += datetime.timedelta(days=1) # Tomorrow

    url = url % today.strftime('%Y_%m_%d')
    
    content = requests.get(url).text

    document = BeautifulSoup(content, "html.parser")
    canteen = LazyBuilder()

    # Prices for employees and guests
    try:
        p = price_regex.search(document.find("p", {"id": "message"}).text).groupdict()
        employee_multiplier = 1.0 + int(p["employee"]) / 100.0
        guest_multiplier = 1.0 + int(p["guest"]) / 100.0
    except:
        employee_multiplier = 1.25
        guest_multiplier = 1.60
    

    trs = document.find("table", {"id": "previewTable"}).find_all("tr")

    canteenCategories = []

    firstTr = True
    previous = None   # previous tr row
    for tr in trs:
        if firstTr:
            # First table row contains the names of the different categories
            firstTr = False

            for th in tr.find_all("th")[1:]:
                canteenCategories.append(th.text.strip())

        elif previous is None:
            # Normal table row containing meal information
            previous = tr            

        else:
            # Price table row
            date = day_regex.search(previous.find("td", {"class": "first"})["data-date"]).group('date')

            if "geschlossen" == previous.find_all("td")[1].text.strip():
                canteen.setDayClosed(date)
            else:
                cat = 0          
                for td0,td1 in zip(previous.find_all("td")[1:], tr.find_all("td")):
                    if "heute kein Angebot" in td0.text or "geschlossen" in td0.text:
                        cat += 1
                        continue
                        
                    if "Kubusangebote am Themenpark" in td0.text:
                        canteen.addMeal(date, categoryName, "Kubusangebote am Themenpark", [])
                        cat += 1
                        continue

                    notes = []

                    # Category                    
                    if td0.find("h2"):
                        categoryName = canteenCategories[cat] + " " +correctCapitalization(td0.find("h2").text.strip())
                    else:
                        categoryName = canteenCategories[cat]

                    # Name
                    if td0.find("p"):
                        name = removeextras_regex.sub("", td0.find("p").text)
                    else:
                        name = categoryName # No name available, let's just use the category name
                    

                    # Prices
                    prices = []
                    spans = td1.find_all("span", {"class": "label"})
                    if spans:
                        try:
                            price = float(euro_regex.search(spans[0].text).group(1).replace(",","."))
                        except:
                            notes.append(spans[0].text.strip()+" Preis")
                        if len(spans) == 2:
                            notes.append(spans[1].text.strip()+" Preis")
                        prices = (price, price*employee_multiplier, price*guest_multiplier)

                    # Notes: vegan, vegetarisch, ...
                    notes += [icon["title"] for icon in td1.find_all("span", {"class": "icon"})]  
                    
                    canteen.addMeal(date, categoryName, name, notes, prices, roles if prices else None)
                    cat += 1
                    
            previous = None

    return canteen.toXMLFeed()



def _generateCanteenMeta(name):
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
            "name" : mensa["name"],
            "adress" : "%s %s %s %s" % (mensa["name"],mensa["strasse"],mensa["plz"],mensa["ort"]),
            "city" : mensa["ort"],
            "phone" : mensa["phone"],
            "latitude" : mensa["latitude"],
            "longitude" : mensa["longitude"],
            "feed_today" : template_todayURL % urllib.parse.quote(shortname),
            "feed_full" : template_fullURL % urllib.parse.quote(shortname),
            "source_today" : mensa["source_today"],
            "source_full" : mensa["source_week"]
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




class Parser:
    def __init__(self, city, handler, shared_prefix):
        self.handler = handler
        self.shared_prefix = shared_prefix
        self.canteens = {}

    def define(self, name, suffix):
        self.canteens[name] = self.shared_prefix+suffix

    def json(self, meta_url):
        tmp = self.canteens.copy()
        for name in tmp:
            tmp[name] = meta_url % name
        return json.dumps(tmp, indent=2)
    
    def meta(self, name):
        return _generateCanteenMeta(name)
    
    def feed(self, name):      
        return self.handler(self.canteens[name])
    

def getmannheim():
    parser = Parser('mannheim',
                    handler=parse_url,
                    shared_prefix='https://www.stw-ma.de/')
    parser.define('schloss', suffix='Essen+_+Trinken/Menüpläne/Mensa+am+Schloss-date-%s-pdfView-1.html')
    parser.define('hochschule', suffix='Essen+_+Trinken/Menüpläne/Hochschule+Mannheim-date-%s-pdfView-1.html')
    parser.define('kubus', suffix='Essen+_+Trinken/Menüpläne/Cafeteria+KUBUS-date-%s-pdfView-1.html')
    parser.define('metropol', suffix='speiseplan_mensaria_metropol-date-%s-pdfView-1.html')
    parser.define('wohlgelegen', suffix='Essen+_+Trinken/Menüpläne/Mensaria+Wohlgelegen-date-%s-pdfView-1.html')
    parser.define('musikhochschule', suffix='Essen+_+Trinken/Menüpläne/Cafeteria+Musikhochschule-date-%s-pdfView-1.html')
    parser.define('eo', suffix='menüplan_eo-date-%s-pdfView-1.html')
    return parser


if __name__ == "__main__":
    #print(getmannheim().json("https://localhost/meta/%s.xml"))
    print(getmannheim().feed("hochschule"))








