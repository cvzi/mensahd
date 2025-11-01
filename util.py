#!/usr/bin/env python

import re
import datetime
import lxml
from zoneinfo import ZoneInfo
from pyopenmensa.feed import LazyBuilder

__all__ = ['xml_escape', 'xmlRemoveInvalidChars', 'StyledLazyBuilder',
           'now_local', 'xml_str_param', 'meta_from_xsl', 'weekdays_map']

defaultStyleSheets = ('https://cdn.jsdelivr.net/npm/om-style@1.0.0/basic.css',
                      'https://cdn.jsdelivr.net/npm/om-style@1.0.0/lightgreen.css')


def xml_escape(s, escape_double_quotes=False):
    s = str(s).replace('&', '&amp;')  # amp first!
    s = s.replace('>', '&gt;')
    s = s.replace('<', '&lt;')
    if escape_double_quotes:
        s = s.replace('"', '&quot;')
    return s


def xmlRemoveInvalidChars(s):
    # https://www.w3.org/TR/xml/#char32
    restricted_chars = re.compile(
        r'[^\u0009\u000A\u000D\u0020-\uD7FF\uE000-\uFFFD\u10000-\u10FFFF]')
    return restricted_chars.sub('', s)


class StyledLazyBuilder(LazyBuilder):
    def toXMLFeed(self, styles=defaultStyleSheets):
        feed = self.toXML()
        xml_header = '<?xml version="1.0" encoding="UTF-8"?>\n'
        if styles:
            for style in styles:
                xml_header += '<?xml-stylesheet href="' + \
                    xml_escape(style, True) + '" type="text/css"?>\n'
        return xmlRemoveInvalidChars(xml_header + feed.toprettyxml(indent='  '))


def now_local():
    berlin = ZoneInfo('Europe/Berlin')
    now = datetime.datetime.now(tz=berlin)
    return now


def xml_str_param(s):
    return lxml.etree.XSLT.strparam(str(s))


def meta_from_xsl(file_name, data):
    """Generate an openmensa XML meta feed using XSLT"""

    if "times" in data:
        opening_times = {}
        pattern = re.compile(
            r"([A-Z][a-z])(\s*-\s*([A-Z][a-z]))?\s*(\d{1,2})[:\.](\d{2})\s*[-–]\s*(\d{1,2})[:\.](\d{2})(?:\s*Uhr)?", flags=re.IGNORECASE)
        m = re.findall(pattern, data["times"])

        for result in m:
            from_day, _, to_day, from_time_hours, from_time_minutes, to_time_hours, to_time_minutes = result
            opening_times[from_day] = "%02d:%02d-%02d:%02d" % (
                int(from_time_hours), int(from_time_minutes), int(to_time_hours), int(to_time_minutes))
            if to_day:
                select = False
                for short, long in weekdays_map:
                    if short == from_day:
                        select = True
                    elif select:
                        opening_times[short] = "%02d:%02d-%02d:%02d" % (
                            int(from_time_hours), int(from_time_minutes), int(to_time_hours), int(to_time_minutes))
                    if short == to_day:
                        select = False

            for short, long in weekdays_map:
                if short in opening_times:
                    data[long] = xml_str_param(opening_times[short])
        data["times"] = xml_str_param(True)

    # Generate xml
    xslt_tree = lxml.etree.parse(file_name)
    xslt = lxml.etree.XSLT(xslt_tree)
    return lxml.etree.tostring(xslt(lxml.etree.Element("foobar"), **data),
                               pretty_print=True,
                               xml_declaration=True,
                               encoding="utf-8").decode("utf-8")


weekdays_map = [
    ("Mo", "monday"),
    ("Tu", "tuesday"),
    ("We", "wednesday"),
    ("Th", "thursday"),
    ("Fr", "friday"),
    ("Sa", "saturday"),
    ("Su", "sunday")
]
