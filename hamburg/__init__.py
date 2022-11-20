#!/usr/bin/env python
# Python 3
import sys
import time
import os
import json
import re
import logging
import textwrap
import urllib.parse
from threading import Lock

import requests
import requests.utils
from bs4 import BeautifulSoup

try:
    from version import __version__, useragentname, useragentcomment
    from util import StyledLazyBuilder, xml_escape, meta_from_xsl, xml_str_param
except ModuleNotFoundError:
    include = os.path.relpath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, include)
    from version import __version__, useragentname, useragentcomment
    from util import StyledLazyBuilder, xml_escape, meta_from_xsl, xml_str_param

# This parser is similar to Köln: https://github.com/cvzi/mensa/blob/b5673d3437b195057aeea3260e1979b6697ed216/koeln/__init__.py


headers = {
    'User-Agent': f'{useragentname}/{__version__} ({useragentcomment}) {requests.utils.default_user_agent()}'
}

# Global vars for caching
cacheMealsLock = Lock()
cacheMealsData = {}
cacheMealsTime = {}


def _getMealsURL(url, maxAgeMinutes=30):
    """Download website, if available use a cached version"""
    if url in cacheMealsData:
        ageSeconds = (time.time() - cacheMealsTime[url])
        if ageSeconds < maxAgeMinutes * 60:
            logging.debug(f"From cache: {url} [{round(ageSeconds)}s old]")
            return cacheMealsData[url]

    content = requests.get(url, headers=headers, timeout=10 * 60).text
    with cacheMealsLock:
        cacheMealsData[url] = content
        cacheMealsTime[url] = time.time()
    return content


class Parser:
    meta_xslt = os.path.join(os.path.dirname(__file__), "../meta.xsl")
    template_meals_url = "https://www.stwhh.de/speiseplan?l={ids}&t={{date}}"

    roles_map = {
        'studierende': 'student',
        'bedienstete': 'employee',
        'gäste': 'other'
    }

    euro_regex = re.compile(r'(\d+)[,.](\d+)\s*€')

    def __init__(self, url_template):

        canteen_json = os.path.join(os.path.dirname(__file__), "hamburg.json")

        with open(canteen_json, 'r', encoding='utf8') as f:
            canteenDict = json.load(f)

        self.meals_url_all_canteens = self.template_meals_url.format(
            ids=",".join(canteenDict.keys()))

        self.url_template = url_template
        self.canteens = {}

        for mensaId in canteenDict:
            canteenDict[mensaId]["id"] = mensaId
            self.canteens[canteenDict[mensaId]
                          ["reference"]] = canteenDict[mensaId]

    def _parseMealsUrl(self, lazyBuilder, mensaId, t_date):
        found_any_meals = False
        content = _getMealsURL(self.meals_url_all_canteens.format(date=t_date))
        document = BeautifulSoup(content, "html.parser")

        mensaDivs = document.find_all(
            "div", class_="tx-epwerkmenu-menu-location-container")
        mensaDivs = [
            mensaDiv for mensaDiv in mensaDivs if mensaDiv.attrs["data-location-id"] == str(mensaId)]

        if len(mensaDivs) != 1:
            # Check if mensa is in drowndown selector
            checkbox = document.find(class_="mselect__option", attrs={
                                     "data-filter-id": str(mensaId)})
            if checkbox:
                logging.debug(f"No meals found [id='{mensaId}']")
            else:
                logging.error(f"Mensa not found [id='{mensaId}']")
            return False

        legend_spans = document.find(class_="menulegend").find_all(
            class_="textlegend--bold")

        legend = {
            "48": "48",
        }
        for span in legend_spans:
            short = span.text.strip()
            desc = span.parent.find_all('span')[-1].text.strip()
            legend[short] = desc

        lazyBuilder.setLegendData(legend)

        mensa_div = mensaDivs.pop()

        times_wrappers = mensa_div.find_all(
            class_="tx-epwerkmenu-menu-timestamp-wrapper")
        for time_wrapper in times_wrappers:
            date = time_wrapper.attrs["data-timestamp"]
            category_wrappers = time_wrapper.find_all(
                "div", class_="menulist__categorywrapper")
            for category_wrapper in category_wrappers:

                category = category_wrapper.find(
                    class_="menulist__categorytitle").text.strip()

                menu_tiles = category_wrapper.find_all(class_="menue-tile")
                for menu_tile in menu_tiles:
                    mealName = menu_tile.find(
                        class_="singlemeal__headline").text.strip()

                    notes = []
                    roles = []
                    prices = []
                    singleMeal = menu_tile.find(class_="singlemeal")

                    for tooltip in singleMeal.find_all(
                            class_="singlemeal__icontooltip"):
                        text = tooltip.attrs["title"]
                        if "<b>" and "</b>" in text:
                            text = text.split("<b>")[1].split("</b>")[0]
                        notes.append(text.strip())

                    for el in singleMeal.select(
                            ".dlist .singlemeal__info .singlemeal__info--semibold"):
                        if "€" in el.text:
                            m = self.euro_regex.search(el.text)
                            if m:
                                price = float(f"{m.group(1)}.{m.group(2)}")
                                role_name = el.next_sibling.strip().lower()
                                if price and role_name and role_name in self.roles_map and self.roles_map[
                                        role_name] not in roles:
                                    roles.append(self.roles_map[role_name])
                                    prices.append(price)

                    for j, mealText in enumerate(
                            textwrap.wrap(mealName, width=250)):
                        lazyBuilder.addMeal(date, category, mealText,
                                            notes if j == 0 else None,
                                            prices if j == 0 else None,
                                            roles if j == 0 else None)

                    found_any_meals = True

        if found_any_meals:
            return True

        return False

    def json(self):
        tmp = {}
        for reference in self.canteens:
            tmp[reference] = self.url_template.format(
                metaOrFeed='meta', mensaReference=urllib.parse.quote(reference))
        return json.dumps(tmp, indent=2)

    def meta(self, ref):
        """Generate an openmensa XML meta feed using XSLT"""
        if ref not in self.canteens:
            return f"Unknown canteen with ref='{xml_escape(ref)}'"
        mensa = self.canteens[ref]

        data = {
            "name": xml_str_param(mensa["name"]),
            "address": xml_str_param(mensa["address"]),
            "city": xml_str_param(mensa["city"]),
            "latitude": xml_str_param(mensa["latitude"]),
            "longitude": xml_str_param(mensa["longitude"]),
            "feed_today": xml_str_param(self.url_template.format(metaOrFeed='today', mensaReference=urllib.parse.quote(ref))),
            "feed_full": xml_str_param(self.url_template.format(metaOrFeed='feed', mensaReference=urllib.parse.quote(ref))),
            "source_today": xml_str_param(self.template_meals_url.format(ids=mensa["id"]).format(date='this_week')),
            "source_full": xml_str_param(self.template_meals_url.format(ids=mensa["id"]).format(date='this_week')),
        }

        if "phone" in mensa:
            data["phone"] = xml_str_param(mensa["phone"])

        if "times" in mensa:
            data["times"] = mensa["times"]

        return meta_from_xsl(self.meta_xslt, data)

    def feed_today(self, name):
        if name in self.canteens:
            mensaId = self.canteens[name]["id"]
            lazyBuilder = StyledLazyBuilder()

            if not self._parseMealsUrl(lazyBuilder, mensaId, 'this_week'):
                self._parseMealsUrl(lazyBuilder, mensaId, 'next_week')

            return lazyBuilder.toXMLFeed()
        return 'Wrong mensa name'

    def feed_all(self, name):
        if name in self.canteens:
            mensaId = self.canteens[name]["id"]
            lazyBuilder = StyledLazyBuilder()

            self._parseMealsUrl(lazyBuilder, mensaId, 'this_week')
            self._parseMealsUrl(lazyBuilder, mensaId, 'next_week')

            return lazyBuilder.toXMLFeed()
        return 'Wrong mensa name'


def getParser(url_template):
    parser = Parser(url_template)
    return parser


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    p = Parser("http://localhost/{metaOrFeed}/koeln_{mensaReference}.xml")
    # print(p.meta("studierendenhaus"))
    print(p.feed_today("tuzessp"))
    # print(p.feed_all("studierendenhaus"))
