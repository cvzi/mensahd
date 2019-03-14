#!/usr/bin/env python
#
# Python 3
import sys
import os
import socket
import urllib.error
import urllib.request
import traceback
import datetime

import pytz

from eppelheim import getParser as geteppelheim
from stuttgart import getParser as getstuttgart
from koeln import getParser as getkoeln
from mannheim import getParser as getmannheim
from heidelberg import getParser as getheidelberg
from ulm import getParser as getulm


if __name__ == '__main__':
    include = os.path.relpath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, include)


page_errors = []

baseurl = os.getenv("PUBLIC_URL", False)
if not baseurl:
    if __name__ == '__main__' or 'idlelib' in sys.modules:
        baseurl = "http://127.0.0.1/"
    else:
        raise RuntimeError("Environment variable PUBLIC_URL is not set.")

heidelberg = getheidelberg(baseurl)
mannheim = getmannheim(baseurl)
koeln = getkoeln(baseurl)
stuttgart = getstuttgart(baseurl)
eppelheim = geteppelheim(baseurl)
ulm = getulm(baseurl)


def timeStrBerlin():
    berlin = pytz.timezone('Europe/Berlin')
    now = datetime.datetime.now(berlin)
    return now.strftime("%Y-%m-%d %H:%M")


def application(environ, start_response):
    ctype = 'text/plain; charset=utf-8'
    cache_control = 'no-cache, no-store, must-revalidate'
    status = '200 OK'

    if environ['PATH_INFO'] == '/health':
        response_body = "1"

    elif environ['PATH_INFO'] == '/favicon.ico':
        ctype = 'image/x-icon'
        cache_control = 'public, max-age=8640000'
        response_body = open(os.path.join(
            os.path.dirname(__file__), "favicon.ico"), "rb").read()
        response_headers = [('Content-Type', ctype), ('Content-Length',
                                                      str(len(response_body))), ('Cache-Control', cache_control)]
        start_response(status, response_headers)
        return [response_body]

    elif environ['PATH_INFO'] == '/status':
        statusmessage = []

        for url in ("https://www.stw.uni-heidelberg.de/", "https://www.stw-ma.de/", "https://www.max-manager.de/", "https://sws2.maxmanager.xyz/", "https://www.uni-ulm.de/"):
            hostname = url.split("//")[1].split("/")[0]
            try:
                request = urllib.request.Request(url)
                result = urllib.request.urlopen(request, timeout=7)
                if result.getcode() != 200:
                    raise RuntimeError("HTTP status code: %r" % result.status)
            except (urllib.error.URLError, socket.timeout) as e:
                statusmessage.append("%s is not reachable" % hostname)
                print("%s is not reachable" % hostname)
            except RuntimeError as e:
                if result is not None:
                    statusmessage.append("%s status code %d" %
                                         (hostname, result.getcode()))
                else:
                    statusmessage.append("%s %r" % (hostname, e))
                print("%s %r" % (hostname, e))
            except BaseException as e:
                statusmessage.append("%s %r" % (hostname, e))
                print("%s %r" % (hostname, e))

        if not statusmessage:
            statusmessage = "Ok"
        else:
            statusmessage = ". ".join(statusmessage)

        response_body = "%s. %d errors.\n" % (statusmessage, len(page_errors))
        for exc in reversed(page_errors):
            response_body += "%s \t %s \t %s\n" % exc

    elif environ['PATH_INFO'].startswith('/today'):
        ctype = 'application/xml; charset=utf-8'
        if len(environ['PATH_INFO']) > 7:
            name = environ['PATH_INFO'][7:]
            if name.endswith(".xml"):
                name = name[:-4]
        else:
            name = ''
        try:
            response_body = heidelberg.feed_today(name).decode("utf-8")
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to www.stw.uni-heidelberg.de\n\nAn error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '533 Open www.stw.uni-heidelberg.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'].startswith('/all'):
        ctype = 'application/xml; charset=utf-8'
        if len(environ['PATH_INFO']) > 5:
            name = environ['PATH_INFO'][5:]
            if name.endswith(".xml"):
                name = name[:-4]
        else:
            name = ''
        try:
            response_body = heidelberg.feed_all(name).decode("utf-8")
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to www.stw.uni-heidelberg.de\n\nAn error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '533 Open www.stw.uni-heidelberg.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'].startswith('/meta'):
        ctype = 'application/xml; charset=utf-8'
        if len(environ['PATH_INFO']) > 6:
            name = environ['PATH_INFO'][6:]
            if name.endswith(".xml"):
                name = name[:-4]
        else:
            name = ''
        try:
            response_body = heidelberg.meta(name)
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to www.stw.uni-heidelberg.de\n\nAn error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '533 Open www.stw.uni-heidelberg.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'] == '/list':
        ctype = 'application/xml; charset=utf-8'
        try:
            response_body = heidelberg.list()
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to www.stw.uni-heidelberg.de\n\nAn error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '533 Open www.stw.uni-heidelberg.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'] == '/list.json':
        ctype = 'application/json; charset=utf-8'
        try:
            response_body = heidelberg.json()
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to www.stw.uni-heidelberg.de\n\nAn error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '533 Open www.stw.uni-heidelberg.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'] == '/time':
        berlin = pytz.timezone('Europe/Berlin')
        now = datetime.datetime.now(berlin)
        response_body = now.strftime("%Y-%m-%d %H:%M")

    elif environ['PATH_INFO'] == '/mannheim/list.json':
        ctype = 'application/json; charset=utf-8'
        try:
            response_body = mannheim.json()
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'].startswith('/mannheim/meta/'):
        ctype = 'application/xml; charset=utf-8'
        name = environ['PATH_INFO'][15:]
        if name.endswith(".xml"):
            name = name[:-4]
        try:
            response_body = mannheim.meta(name)
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to www.stw-ma.de\n\nAn error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '533 Open www.stw-ma.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'].startswith('/mannheim/feed/'):
        ctype = 'application/xml; charset=utf-8'
        name = environ['PATH_INFO'][15:]
        if name.endswith(".xml"):
            name = name[:-4]
        try:
            response_body = mannheim.feed(name)
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to www.stw-ma.de\n\nAn error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '533 Open www.stw-ma.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'] == '/mannheim' or environ['PATH_INFO'] == '/mannheim/':
        ctype = 'text/html; charset=utf-8'
        cache_control = 'public, max-age=86400'
        response_body = """
            <h1>mensahd-cuzi for Mannheim University canteens</h1>
            <div>This is a parser for <a href="https://openmensa.org/">openmensa.org</a>. It fetches and converts public data from <a href="https://www.stw-ma.de/Essen+_+Trinken/Men%C3%BCpl%C3%A4ne.html">Studierendenwerk Mannheim</a></div>
            <h2>Public interface:</h2>
            <ul>
              <li><a href="/">../ Heidelberg</a></li>
              <li><a href="/mannheim"><b>Mannheim</b></a></li>
              <li><a href="/mannheim/list.json">/mannheim/list.json</a></li>
              <li>/mannheim/meta/{id}.xml</li>
              <li>/mannheim/feed/{id}.xml</li>
              <li><a href="/eppelheim">Eppelheim</a></li>
            </ul>"""

    elif environ['PATH_INFO'] == '/koeln/list.json':
        ctype = 'application/json; charset=utf-8'
        try:
            response_body = koeln.json()
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'].startswith('/koeln/meta/'):
        ctype = 'application/xml; charset=utf-8'
        name = environ['PATH_INFO'][12:]
        if name.endswith(".xml"):
            name = name[:-4]
        try:
            response_body = koeln.meta(name)
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to www.max-manager.de\n\nAn error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '533 Open www.stw-ma.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'].startswith('/koeln/today/'):
        ctype = 'application/xml; charset=utf-8'
        name = environ['PATH_INFO'][13:]
        if name.endswith(".xml"):
            name = name[:-4]
        try:
            response_body = koeln.feed_today(name)
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to www.max-manager.de\n\nAn error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '533 Open www.max-manager.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'].startswith('/koeln/all/'):
        ctype = 'application/xml; charset=utf-8'
        name = environ['PATH_INFO'][11:]
        if name.endswith(".xml"):
            name = name[:-4]
        try:
            response_body = koeln.feed_all(name)
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to www.max-manager.de\n\nAn error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '533 Open www.max-manager.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'] == '/koeln' or environ['PATH_INFO'] == '/koeln/':
        ctype = 'text/html; charset=utf-8'
        cache_control = 'public, max-age=86400'
        response_body = """
            <h1>mensahd-cuzi for Köln University canteens</h1>
            <div>This is a parser for <a href="https://openmensa.org/">openmensa.org</a>. It fetches and converts public data from <a href="http://www.kstw.de/index.php?option=com_content&view=article&id=182&Itemid=121">Kölner Studierendenwerk</a></div>
            <h2>Public interface:</h2>
            <ul>
              <li><a href="/">../ Heidelberg</a></li>
              <li><a href="/koeln"><b>Köln</b></a></li>
              <li><a href="/koeln/list.json">/koeln/list.json</a></li>
              <li>/koeln/meta/{id}.xml</li>
              <li>/koeln/today/{id}.xml</li>
              <li>/koeln/all/{id}.xml</li>
            </ul>"""

    elif environ['PATH_INFO'] == '/stuttgart/list.json':
        ctype = 'application/json; charset=utf-8'
        try:
            response_body = stuttgart.json()
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'].startswith('/stuttgart/meta/'):
        ctype = 'application/xml; charset=utf-8'
        name = environ['PATH_INFO'][16:]
        if name.endswith(".xml"):
            name = name[:-4]
        try:
            response_body = stuttgart.meta(name)
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to www.studierendenwerk-stuttgart.de\n\nAn error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '533 Open www.stw-ma.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'].startswith('/stuttgart/today/'):
        ctype = 'application/xml; charset=utf-8'
        name = environ['PATH_INFO'][17:]
        if name.endswith(".xml"):
            name = name[:-4]
        try:
            response_body = stuttgart.feed_today(name)
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to sws2.maxmanager.xyz\n\nAn error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '533 Open sws2.maxmanager.xyz timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'].startswith('/stuttgart/all/'):
        ctype = 'application/xml; charset=utf-8'
        name = environ['PATH_INFO'][15:]
        if name.endswith(".xml"):
            name = name[:-4]
        try:
            response_body = stuttgart.feed_all(name)
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to sws2.maxmanager.xyz\n\nAn error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '533 Open sws2.maxmanager.xyz timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'] == '/stuttgart' or environ['PATH_INFO'] == '/stuttgart/':
        ctype = 'text/html; charset=utf-8'
        cache_control = 'public, max-age=86400'
        response_body = """
            <h1>mensahd-cuzi for Stuttgart University canteens</h1>
            <div>This is a parser for <a href="https://openmensa.org/">openmensa.org</a>. It fetches and converts public data from <a href="https://www.studierendenwerk-stuttgart.de/gastronomie/speiseangebot">Studierendenwerk Stuttgart</a></div>
            <h2>Public interface:</h2>
            <ul>
              <li><a href="/">../ Heidelberg</a></li>
              <li><a href="/stuttgart"><b>Stuttgart</b></a></li>
              <li><a href="/stuttgart/list.json">/stuttgart/list.json</a></li>
              <li>/stuttgart/meta/{id}.xml</li>
              <li>/stuttgart/today/{id}.xml</li>
              <li>/stuttgart/all/{id}.xml</li>
            </ul>"""

    elif environ['PATH_INFO'] == '/eppelheim/list.json':
        ctype = 'application/json; charset=utf-8'
        try:
            response_body = eppelheim.json()
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'].startswith('/eppelheim/meta/'):
        ctype = 'application/xml; charset=utf-8'
        name = environ['PATH_INFO'][16:]
        if name.endswith(".xml"):
            name = name[:-4]
        try:
            response_body = eppelheim.meta(name)
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to www.stw-ma.de\n\nAn error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '533 Open www.stw-ma.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'].startswith('/eppelheim/feed/'):
        ctype = 'application/xml; charset=utf-8'
        name = environ['PATH_INFO'][16:]
        if name.endswith(".xml"):
            name = name[:-4]
        try:
            response_body = eppelheim.feed(name)
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to www.stw-ma.de\n\nAn error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '533 Open www.stw-ma.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'] == '/eppelheim' or environ['PATH_INFO'] == '/eppelheim/':
        ctype = 'text/html; charset=utf-8'
        cache_control = 'public, max-age=86400'
        response_body = """
            <h1>mensahd-cuzi for DHBW Eppelheim</h1>
            <div>This is a parser for <a href="https://openmensa.org/">openmensa.org</a>. It fetches and converts public data from <a href="https://www.stw-ma.de/Essen+_+Trinken/Men%C3%BCpl%C3%A4ne.html">Studierendenwerk Mannheim</a></div>
            <h2>Public interface:</h2>
            <ul>
              <li><a href="/">../ Heidelberg</a></li>
              <li><a href="/eppelheim"><b>Eppelheim</b></a></li>
              <li><a href="/eppelheim/list.json">/eppelheim/list.json</a></li>
              <li>/eppelheim/meta/{id}.xml</li>
              <li>/eppelheim/feed/{id}.xml</li>
            </ul>"""

    elif environ['PATH_INFO'] == '/ulm/list.json':
        ctype = 'application/json; charset=utf-8'
        try:
            response_body = ulm.json()
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'].startswith('/ulm/meta/'):
        ctype = 'application/xml; charset=utf-8'
        name = environ['PATH_INFO'][10:]
        if name.endswith(".xml"):
            name = name[:-4]
        try:
            response_body = ulm.meta(name)
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'].startswith('/ulm/feed/'):
        ctype = 'application/xml; charset=utf-8'
        name = environ['PATH_INFO'][10:]
        if name.endswith(".xml"):
            name = name[:-4]
        try:
            response_body = ulm.feed(name)
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to www.uni-ulm.de\n\nAn error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '533 Open www.uni-ulm.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'] == '/ulm' or environ['PATH_INFO'] == '/ulm/':
        ctype = 'text/html; charset=utf-8'
        cache_control = 'public, max-age=86400'
        response_body = """
            <h1>mensahd-cuzi for Studierendenwerk Ulm canteens</h1>
            <div>This is a parser for <a href="https://openmensa.org/">openmensa.org</a>. It fetches and converts public data from <a href="https://www.uni-ulm.de/mensaplan/">https://www.uni-ulm.de/mensaplan/</a></div>
            <h2>Public interface:</h2>
            <ul>
              <li><a href="/">../ Heidelberg</a></li>
              <li><a href="/ulm"><b>ulm</b></a></li>
              <li><a href="/ulm/list.json">/ulm/list.json</a></li>
              <li>/ulm/meta/{id}.xml</li>
              <li>/ulm/feed/{id}.xml</li>
            </ul>"""



    else:
        ctype = 'text/html; charset=utf-8'
        cache_control = 'public, max-age=86400'
        response_body = """
            <h1>mensahd-cuzi for Heidelberg University canteens</h1>
            <div>This is a parser for <a href="https://openmensa.org/">openmensa.org</a>. It fetches and converts public data from <a href="http://www.stw.uni-heidelberg.de/de/speiseplan">Studierendenwerk Heidelberg</a></div>
            <h2>Public interface:</h2>
            <ul>
              <li><a href="/"><b>Heidelberg</b></a></li>
              <li><a href="/mannheim">/mannheim</a></li>
              <li><a href="/koeln">/koeln</a></li>
              <li><a href="/stuttgart">/stuttgart</a></li>
              <li><a href="/ulm">/ulm</a></li>
              <li><a href="/time">/time</a></li>
              <li><a href="/status">/status</a></li>
              <li><a href="/list">/list</a></li>
              <li><a href="/list.json">/list.json</a></li>
              <li>/meta/{id}.xml</li>
              <li>/today/{id}.xml</li>
              <li>/all/{id}.xml</li>
            </ul>
            <!-- https://github.com/tholman/github-corners -->
            <div>
            <a href="https://github.com/cvzi/mensahd" class="github-corner" aria-label="View source on GitHub"><svg width="80" height="80" viewBox="0 0 250 250" style="fill:#64CEAA; color:#fff; position: absolute; top: 0; border: 0; right: 0;" aria-hidden="true"><path d="M0,0 L115,115 L130,115 L142,142 L250,250 L250,0 Z"></path><path d="M128.3,109.0 C113.8,99.7 119.0,89.6 119.0,89.6 C122.0,82.7 120.5,78.6 120.5,78.6 C119.2,72.0 123.4,76.3 123.4,76.3 C127.3,80.9 125.5,87.3 125.5,87.3 C122.9,97.6 130.6,101.9 134.4,103.2" fill="currentColor" style="transform-origin: 130px 106px;" class="octo-arm"></path><path d="M115.0,115.0 C114.9,115.1 118.7,116.5 119.8,115.4 L133.7,101.6 C136.9,99.2 139.9,98.4 142.2,98.6 C133.8,88.0 127.5,74.4 143.8,58.0 C148.5,53.4 154.0,51.2 159.7,51.0 C160.3,49.4 163.2,43.6 171.4,40.1 C171.4,40.1 176.1,42.5 178.8,56.2 C183.1,58.6 187.2,61.8 190.9,65.4 C194.5,69.0 197.7,73.2 200.1,77.6 C213.8,80.2 216.3,84.9 216.3,84.9 C212.7,93.1 206.9,96.0 205.4,96.6 C205.1,102.4 203.0,107.8 198.3,112.5 C181.9,128.9 168.3,122.5 157.7,114.1 C157.9,116.9 156.7,120.9 152.7,124.9 L141.0,136.5 C139.8,137.7 141.6,141.9 141.8,141.8 Z" fill="currentColor" class="octo-body"></path></svg></a><style>.github-corner:hover .octo-arm{animation:octocat-wave 560ms ease-in-out}@keyframes octocat-wave{0%,100%{transform:rotate(0)}20%,60%{transform:rotate(-25deg)}40%,80%{transform:rotate(10deg)}}@media (max-width:500px){.github-corner:hover .octo-arm{animation:none}.github-corner .octo-arm{animation:octocat-wave 560ms ease-in-out}}</style>
            </div>
            """

    response_body = response_body.encode('utf-8')

    response_headers = [('Content-Type', ctype), ('Content-Length',
                                                  str(len(response_body))), ('Cache-Control', cache_control)]

    start_response(status, response_headers)
    return [response_body]
