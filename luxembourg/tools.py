import os
import re
import datetime
import logging
import textwrap
from collections.abc import Iterable

import requests
import bs4
from bs4 import BeautifulSoup
from pyopenmensa.feed import LazyBuilder

__all__ = ['getMenu', 'askRestopolis']

try:
    from version import __version__, useragentname, useragentcomment
except ModuleNotFoundError:
    __version__, useragentname, useragentcomment = 0.1, "Python", "3"

url = "https://ssl.education.lu/eRestauration/CustomerServices/Menu"
s = requests.Session()

s.headers = {
    'User-Agent': f'{useragentname}/{__version__} ({useragentcomment}) {requests.utils.default_user_agent()}',
    'Accept-Language': 'fr-LU,fr,lb-LU,lb,de-LU,de,en',
    'Accept-Encoding': 'utf-8'
}

requests.utils.add_dict_to_cookiejar(s.cookies, {
    ".AspNetCore.Culture":  "c=fr|uic=fr",
    "CustomerServices.Restopolis.DisplayAllergens": "True"
})

allergens = {
    1: "Céréales contenant du gluten et produits à base de ces céréales",
    2: "Crustacés et produits à base de crustacés",
    3: "Oeufs et produits à base d‘oeufs",
    4: "Poissons et produits à base de poissons",
    5: "Arachides et produits à base d‘arachides",
    6: "Soja et produits à base de soja",
    7: "Lait et produits à base de lait (y compris le lactose)",
    8: "Fruits à coque et produits à base de ces fruits",
    9: "Céleri et produits à base de céleri",
    10: "Moutarde et produits à base de moutarde",
    11: "Graines de sésame et produits à base de graines de sésame",
    12: "Anhydride sulfureux et sulfites en concentrations de plus de 10mg/kg ou 10mg/litre",
    13: "Lupin et produits à base de lupin",
    14: "Mollusques et produits à base de mollusques"
}

imgs = {
    "/terroir.png": "produit culinaire du terroir",
    "/bio.png": "bio",
    "/transfair.png": "produit Transfair"
}


def allergen(key):
    try:
        key = int(key)
    except ValueError:
        logging.info("Unkown allergen :" + str(key))
        return key
    return allergens[key] if key in allergens else str(key)


def askRestopolis(restaurant=None, service=None, date=None):
    """
    Fetch raw data from Restopolis
    """
    cookies = {}
    if restaurant is not None:
        cookies["CustomerServices.Restopolis.SelectedRestaurant"] = str(restaurant)
    if service is not None:
        cookies["CustomerServices.Restopolis.SelectedService"] = str(service)
    if date is not None:
        cookies["CustomerServices.Restopolis.SelectedDate"] = date.strftime("%d.%m.%Y")

    return s.get(url, cookies=cookies, proxies=dict(https=os.getenv('LUXEMBOURG_PROXY')) if os.getenv('LUXEMBOURG_PROXY', '') else None)


def getMenu(restaurantId, datetimeDay=None, serviceIds=None):
    """
    Create openmensa feed from restopolis website
    """
    lazyBuilder = LazyBuilder()

    if not datetimeDay:
        datetimeDay = datetime.date.today()

    if isinstance(serviceIds, str) or not isinstance(serviceIds, Iterable):
        serviceIds = [(serviceIds, ""), ]
    for i, service in enumerate(serviceIds):
        if isinstance(service, str) or isinstance(service, int):
            serviceIds[i] = (service, "")

    mealCounter = 0
    dayCounter = set()
    weekdayCounter = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
    for service in serviceIds:
        serviceSuffix = f"({service[1]})" if service[1] and len(serviceIds) > 1 else ""
        r = askRestopolis(restaurant=restaurantId,
                          service=service[0], date=datetimeDay)
        if r.status_code != 200:
            status = 'Could not open restopolis'
            if 'status' in r.headers:
                status = f"{status}: {r.headers['status']}"
            logging.error(status)
            from pprint import pprint
            pprint(r.headers)
            return status, 0, 0, weekdayCounter

        document = BeautifulSoup(r.text, "html.parser")

        # Extract available dates from date selector
        dateButtons = document.find(
            "div", {"class": "date-selector-desktop"}).find_all("button", {"class": "day"})
        dates = []
        for button in dateButtons:
            dates.append(datetime.datetime.strptime(
                button.attrs["data-full-date"], '%d.%m.%Y').date())

        # Extract menu for each date
        for i, oneDayDiv in enumerate(document.select(".daily-menu>div")):
            dayCounter.add(dates[i])
            date = dates[i]
            weekDay = date.weekday()
            courseName = ""
            notes = []
            productSection = ""
            productName = ""
            productAllergens = []
            productDescription = ""

            oneDayDiv.append(document.new_tag("div", attrs={"class":"fake-last"}))
            for div in oneDayDiv.children:
                if not isinstance(div, bs4.element.Tag):
                    # Skip text node children
                    continue

                if courseName and productName and "class" in div.attrs and ("fake-last" in div.attrs["class"] or "product-name" in div.attrs["class"] or "course-name" in div.attrs["class"] or "product-section" in div.attrs["class"]):
                    # Add meal
                    mealCounter += 1
                    weekdayCounter[weekDay] += 1
                    category = courseName
                    if productSection:
                        category += " " + productSection
                    if serviceSuffix:
                        category += " " + serviceSuffix
                    if productDescription:
                        notes += textwrap.wrap(productDescription, width=250)
                    if productAllergens:
                        notes += productAllergens
                    lazyBuilder.addMeal(
                        date, category, productName[0:249], [note[0:249] for note in notes])
                    productName = ""
                    productAllergens = []
                    productDescription = ""
                    notes = []

                # walk through all div and collect info
                if "class" in div.attrs:
                    if "fake-last" in div.attrs["class"]:
                        pass
                    elif "course-name" in div.attrs["class"]:
                        courseName = div.text.strip()
                        productSection = ""
                    elif "product-section" in div.attrs["class"]:
                        productSection = div.text.strip()
                    elif "product-allergens" in div.attrs["class"]:
                        productAllergensGen = (
                            a.strip() for a in div.text.split(",") if a.strip())
                        productAllergens += [re.sub("\d+", lambda m: allergen(m[0]), a)
                                             for a in productAllergensGen]
                    elif "product-description" in div.attrs["class"]:
                        productDescription = div.text.strip()
                    elif "product-name" in div.attrs["class"]:
                        productName = div.text.strip()
                        productName = productName.replace("''", '"')
                        productName = productName.replace("1/2 ", '½ ')
                    elif "product-flag" in div.attrs["class"]:
                        unknownImg = True
                        for img in imgs:
                            if div.attrs["src"].endswith(img):
                                notes.append(imgs[img])
                                unknownImg = False
                        if unknownImg:
                            logging.warning(f"Unkown img {div.attrs['src']} [restaurant={restaurantId}]")
                    elif "wrapper-theme-day" in div.attrs["class"]:
                        logging.info(f"Theme day: {div.text.strip()} [restaurant={restaurantId}]")
                    elif "no-products" in div.attrs["class"]:
                        # Closed (No meals)
                        lazyBuilder.setDayClosed(date)
                    elif "fermé" in div.text.lower() or "fermé" in str(div.attrs).lower():
                        # Closed (explicit)
                        lazyBuilder.setDayClosed(date)
                    else:
                        logging.debug(div)
                        raise RuntimeWarning(
                            f"unknown tag <{div.name}> with class {div.attrs['class']}: oneDayDiv->else [restaurant={restaurantId}]")
                elif div.name == 'ul':
                    mealCounter += 1
                    weekdayCounter[weekDay] += 1
                    for li in div.select('li'):
                        # Add meal
                        category = courseName
                        if productSection:
                            category += " " + productSection
                        lazyBuilder.addMeal(
                            date, category, li.text.strip()[0:249])
                        productName = ""
                        productAllergens = []
                        productDescription = ""
                else:
                    logging.debug(div)
                    raise RuntimeWarning(
                        f"unknown tag <{div.name}>: oneDayDiv->else")

    return lazyBuilder.toXMLFeed(), len(dayCounter), mealCounter, weekdayCounter


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
