#!/usr/bin/env python

import re
import datetime
from zoneinfo import ZoneInfo
from pyopenmensa.feed import LazyBuilder

__all__ = ['xmlEscape', 'xmlRemoveInvalidChars',
           'StyledLazyBuilder', 'nowBerlin', 'weekdays_map']

defaultStyleSheets = ('https://cdn.jsdelivr.net/npm/om-style@1.0.0/basic.css',
                      'https://cdn.jsdelivr.net/npm/om-style@1.0.0/lightgreen.css')


def xmlEscape(s, escapeDoubleQuotes=False):
    s = str(s).replace('&', '&amp;')  # amp first!
    s = s.replace('>', '&gt;')
    s = s.replace('<', '&lt;')
    if escapeDoubleQuotes:
        s = s.replace('"', '&quot;')
    return s


def xmlRemoveInvalidChars(s):
    # https://www.w3.org/TR/xml/#char32
    restricted_chars = re.compile(
        '[^\u0009\u000A\000D\u0020-\uD7FF\uE000-\uFFFD\u10000-\u10FFFF]')
    return restricted_chars.sub('', s)


class StyledLazyBuilder(LazyBuilder):
    def toXMLFeed(self, styles=defaultStyleSheets):
        feed = self.toXML()
        xml_header = '<?xml version="1.0" encoding="UTF-8"?>\n'
        if styles:
            for style in styles:
                xml_header += '<?xml-stylesheet href="' + \
                    xmlEscape(style, True) + '" type="text/css"?>\n'
        return xmlRemoveInvalidChars(xml_header + feed.toprettyxml(indent='  '))


def nowBerlin():
    berlin = ZoneInfo('Europe/Berlin')
    now = datetime.datetime.now(tz=berlin)
    return now


weekdays_map = [
    ("Mo", "monday"),
    ("Tu", "tuesday"),
    ("We", "wednesday"),
    ("Th", "thursday"),
    ("Fr", "friday"),
    ("Sa", "saturday"),
    ("Su", "sunday")
]
