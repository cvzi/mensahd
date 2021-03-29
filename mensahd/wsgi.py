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
import logging

import pytz

if __name__ == '__main__':
    include = os.path.relpath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, include)

from version import __version__
from eppelheim import getParser as geteppelheim
from stuttgart import getParser as getstuttgart
from mannheim import getParser as getmannheim
from heidelberg import getParser as getheidelberg
from ulm import getParser as getulm

page_errors = []

baseurl = os.getenv("PUBLIC_URL", False)
if not baseurl:
    if __name__ == '__main__' or 'idlelib' in sys.modules:
        baseurl = "http://127.0.0.1/"
    else:
        raise RuntimeError("Environment variable PUBLIC_URL is not set.")

heidelberg = getheidelberg(baseurl)
mannheim = getmannheim(baseurl)
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

        sites = ("https://www.stw.uni-heidelberg.de/",
                 "https://www.stw-ma.de/",
                 "https://studiplus.stw-ma.de/",
                 "https://sws.maxmanager.xyz/", # Stuttgart
                 "https://www.uni-ulm.de/",
                 "https://ssl.education.lu/eRestauration/CustomerServices/Menu")
        for url in sites:
            hostname = url.split("//")[1].split("/")[0]
            try:
                if not url.startswith("http://") and not url.startswith("https://"):
                    raise RuntimeError(f"url is not an allowed URL: '{url}'")
                request = urllib.request.Request(url)
                result = urllib.request.urlopen(request, timeout=7)  # nosec
                if result.getcode() != 200:
                    raise RuntimeError("HTTP status code: %r" % result.status)
            except (urllib.error.URLError, socket.timeout) as e:
                status = f"{e.code if hasattr(e, 'code') else '666'} {e.reason if hasattr(e, 'reason') else 'network error'}"
                statusmessage.append(f"{hostname} is not reachable: {status}")
                logging.error(f"{hostname} is not reachable #1: {e}")
            except RuntimeError as e:
                if result is not None:
                    statusmessage.append(f"{hostname} status code {result.getcode()}")
                else:
                    statusmessage.append("%s %r" % (hostname, e))
                logging.error(f"{hostname} is not reachable #2: {e}")
            except BaseException as e:
                statusmessage.append("%s %r" % (hostname, e))
                logging.error(f"{hostname} is not reachable #3: {e}")

        if not statusmessage:
            statusmessage = "Ok"
        else:
            statusmessage = ". \n".join(statusmessage)

        response_body = "%s.\n%d errors.\n" % (statusmessage, len(page_errors))
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

    elif environ['PATH_INFO'].startswith('/mannheim/today/'):
        ctype = 'application/xml; charset=utf-8'
        name = environ['PATH_INFO'][16:]
        if name.endswith(".xml"):
            name = name[:-4]
        try:
            response_body = mannheim.feed_today(name)
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to studiplus.stw-ma.de\n\nAn error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '533 Open studiplus.stw-ma.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'].startswith('/mannheim/all/'):
        ctype = 'application/xml; charset=utf-8'
        name = environ['PATH_INFO'][14:]
        if name.endswith(".xml"):
            name = name[:-4]
        try:
            response_body = mannheim.feed_all(name)
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to studiplus.stw-ma.de\n\nAn error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '533 Open studiplus.stw-ma.de timed out'
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
              <li>/mannheim/today/{id}.xml</li>
              <li>/mannheim/all/{id}.xml</li>
              <li><a href="/eppelheim">Eppelheim</a></li>
            </ul>"""

    elif environ['PATH_INFO'].startswith('/koeln'):
        redirects = {
            "/koeln": "https://cvzi.github.io/mensa/#koeln",
            "/koeln/": "https://cvzi.github.io/mensa/#koeln",
            "/koeln/list.json": "https://cvzi.github.io/mensa/koeln.json",
            "/koeln/meta/unimensa.xml": "https://cvzi.github.io/mensa/meta/koeln_unimensa.xml",
            "/koeln/today/unimensa.xml": "https://cvzi.github.io/mensa/today/koeln_unimensa.xml",
            "/koeln/all/unimensa.xml": "https://cvzi.github.io/mensa/feed/koeln_unimensa.xml",
            "/koeln/meta/iwz-deutz.xml": "https://cvzi.github.io/mensa/meta/koeln_iwz-deutz.xml",
            "/koeln/today/iwz-deutz.xml": "https://cvzi.github.io/mensa/today/koeln_iwz-deutz.xml",
            "/koeln/all/iwz-deutz.xml": "https://cvzi.github.io/mensa/feed/koeln_iwz-deutz.xml",
            "/koeln/meta/eraum.xml": "https://cvzi.github.io/mensa/meta/koeln_eraum.xml",
            "/koeln/today/eraum.xml": "https://cvzi.github.io/mensa/today/koeln_eraum.xml",
            "/koeln/all/eraum.xml": "https://cvzi.github.io/mensa/feed/koeln_eraum.xml",
            "/koeln/meta/suedstadt.xml": "https://cvzi.github.io/mensa/meta/koeln_suedstadt.xml",
            "/koeln/today/suedstadt.xml": "https://cvzi.github.io/mensa/today/koeln_suedstadt.xml",
            "/koeln/all/suedstadt.xml": "https://cvzi.github.io/mensa/feed/koeln_suedstadt.xml",
            "/koeln/meta/cafe-himmelsblick.xml": "https://cvzi.github.io/mensa/meta/koeln_cafe-himmelsblick.xml",
            "/koeln/today/cafe-himmelsblick.xml": "https://cvzi.github.io/mensa/today/koeln_cafe-himmelsblick.xml",
            "/koeln/all/cafe-himmelsblick.xml": "https://cvzi.github.io/mensa/feed/koeln_cafe-himmelsblick.xml",
            "/koeln/meta/robertkoch.xml": "https://cvzi.github.io/mensa/meta/koeln_robertkoch.xml",
            "/koeln/today/robertkoch.xml": "https://cvzi.github.io/mensa/today/koeln_robertkoch.xml",
            "/koeln/all/robertkoch.xml": "https://cvzi.github.io/mensa/feed/koeln_robertkoch.xml",
            "/koeln/meta/gummersbach.xml": "https://cvzi.github.io/mensa/meta/koeln_gummersbach.xml",
            "/koeln/today/gummersbach.xml": "https://cvzi.github.io/mensa/today/koeln_gummersbach.xml",
            "/koeln/all/gummersbach.xml": "https://cvzi.github.io/mensa/feed/koeln_gummersbach.xml",
            "/koeln/meta/kunsthochschule-medien.xml": "https://cvzi.github.io/mensa/meta/koeln_kunsthochschule-medien.xml",
            "/koeln/today/kunsthochschule-medien.xml": "https://cvzi.github.io/mensa/today/koeln_kunsthochschule-medien.xml",
            "/koeln/all/kunsthochschule-medien.xml": "https://cvzi.github.io/mensa/feed/koeln_kunsthochschule-medien.xml",
            "/koeln/meta/spoho.xml": "https://cvzi.github.io/mensa/meta/koeln_spoho.xml",
            "/koeln/today/spoho.xml": "https://cvzi.github.io/mensa/today/koeln_spoho.xml",
            "/koeln/all/spoho.xml": "https://cvzi.github.io/mensa/feed/koeln_spoho.xml",
            "/koeln/meta/lindenthal.xml": "https://cvzi.github.io/mensa/meta/koeln_lindenthal.xml",
            "/koeln/today/lindenthal.xml": "https://cvzi.github.io/mensa/today/koeln_lindenthal.xml",
            "/koeln/all/lindenthal.xml": "https://cvzi.github.io/mensa/feed/koeln_lindenthal.xml",
            "/koeln/meta/muho.xml": "https://cvzi.github.io/mensa/meta/koeln_muho.xml",
            "/koeln/today/muho.xml": "https://cvzi.github.io/mensa/today/koeln_muho.xml",
            "/koeln/all/muho.xml": "https://cvzi.github.io/mensa/feed/koeln_muho.xml",
            "/koeln/meta/philcafe.xml": "https://cvzi.github.io/mensa/meta/koeln_philcafe.xml",
            "/koeln/today/philcafe.xml": "https://cvzi.github.io/mensa/today/koeln_philcafe.xml",
            "/koeln/all/philcafe.xml": "https://cvzi.github.io/mensa/feed/koeln_philcafe.xml"
        }
        new_url = redirects[environ['PATH_INFO']] if environ['PATH_INFO'] in redirects else "https://cvzi.github.io/mensa/"

        response_body = ('<a href="%s">%s</a>' % (new_url, new_url)).encode('utf-8')

        response_headers = [('Location', new_url),
                            ('Content-Length', str(len(response_body))),
                            ('Content-Type', 'text/html; charset=utf-8'),
                            ('X-OpenMensa-ParserVersion', str(__version__))]
        status = '301 Moved Permanently'
        start_response(status, response_headers)
        return [response_body]


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
            status = '533 Open www.studierendenwerk-stuttgart.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'].startswith('/stuttgart/feed/'):
        ctype = 'application/xml; charset=utf-8'
        name = environ['PATH_INFO'][16:]
        if name.endswith(".xml"):
            name = name[:-4]
        try:
            response_body = stuttgart.feed(name)
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to sws.maxmanager.xyz\n\nAn error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '533 Open sws.maxmanager.xyz timed out'
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
              <li>/stuttgart/feed/{id}.xml</li>
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

    elif environ['PATH_INFO'].startswith('/luxembourg'):
        redirects = {
            "/luxembourg" : "https://cvzi.github.io/mensa/#luxembourg",
            "/luxembourg/" : "https://cvzi.github.io/mensa/#luxembourg",
            "/luxembourg/list.json" : "https://cvzi.github.io/mensa/luxembourg.json",
            "/luxembourg/feed/Agora.xml": "https://cvzi.github.io/mensa/feed/luxembourg_Agora.xml",
            "/luxembourg/feed/ALBBQ.xml": "https://cvzi.github.io/mensa/feed/luxembourg_ALBBQ.xml",
            "/luxembourg/feed/ALp1.xml": "https://cvzi.github.io/mensa/feed/luxembourg_ALp1.xml",
            "/luxembourg/feed/ALRca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_ALRca.xml",
            "/luxembourg/feed/ALre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_ALre.xml",
            "/luxembourg/feed/ALRint.xml": "https://cvzi.github.io/mensa/feed/luxembourg_ALRint.xml",
            "/luxembourg/feed/ALRre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_ALRre.xml",
            "/luxembourg/feed/BertCDI.xml": "https://cvzi.github.io/mensa/feed/luxembourg_BertCDI.xml",
            "/luxembourg/feed/BlvlFoodCafe.xml": "https://cvzi.github.io/mensa/feed/luxembourg_BlvlFoodCafe.xml",
            "/luxembourg/feed/BlvlFoodHouse.xml": "https://cvzi.github.io/mensa/feed/luxembourg_BlvlFoodHouse.xml",
            "/luxembourg/feed/BlvlFoodLab.xml": "https://cvzi.github.io/mensa/feed/luxembourg_BlvlFoodLab.xml",
            "/luxembourg/feed/BlvlFoodZone.xml": "https://cvzi.github.io/mensa/feed/luxembourg_BlvlFoodZone.xml",
            "/luxembourg/feed/CDIreBonne.xml": "https://cvzi.github.io/mensa/feed/luxembourg_CDIreBonne.xml",
            "/luxembourg/feed/CDIreCess.xml": "https://cvzi.github.io/mensa/feed/luxembourg_CDIreCess.xml",
            "/luxembourg/feed/CDIreWei.xml": "https://cvzi.github.io/mensa/feed/luxembourg_CDIreWei.xml",
            "/luxembourg/feed/CDMre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_CDMre.xml",
            "/luxembourg/feed/CDVre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_CDVre.xml",
            "/luxembourg/feed/ClerCDI.xml": "https://cvzi.github.io/mensa/feed/luxembourg_ClerCDI.xml",
            "/luxembourg/feed/CLreAd.xml": "https://cvzi.github.io/mensa/feed/luxembourg_CLreAd.xml",
            "/luxembourg/feed/CmpsGeessForCa.xml": "https://cvzi.github.io/mensa/feed/luxembourg_CmpsGeessForCa.xml",
            "/luxembourg/feed/CmpsGeessForRe.xml": "https://cvzi.github.io/mensa/feed/luxembourg_CmpsGeessForRe.xml",
            "/luxembourg/feed/CmpsGeessPisc.xml": "https://cvzi.github.io/mensa/feed/luxembourg_CmpsGeessPisc.xml",
            "/luxembourg/feed/CmpsGeessTruck.xml": "https://cvzi.github.io/mensa/feed/luxembourg_CmpsGeessTruck.xml",
            "/luxembourg/feed/CmpsKiBergAltius.xml": "https://cvzi.github.io/mensa/feed/luxembourg_CmpsKiBergAltius.xml",
            "/luxembourg/feed/CmpsKiBergJohns.xml": "https://cvzi.github.io/mensa/feed/luxembourg_CmpsKiBergJohns.xml",
            "/luxembourg/feed/CNFPC.xml": "https://cvzi.github.io/mensa/feed/luxembourg_CNFPC.xml",
            "/luxembourg/feed/CSAEMerl.xml": "https://cvzi.github.io/mensa/feed/luxembourg_CSAEMerl.xml",
            "/luxembourg/feed/ECGbi.xml": "https://cvzi.github.io/mensa/feed/luxembourg_ECGbi.xml",
            "/luxembourg/feed/EchtCDI.xml": "https://cvzi.github.io/mensa/feed/luxembourg_EchtCDI.xml",
            "/luxembourg/feed/eduPoleCharlemagne.xml": "https://cvzi.github.io/mensa/feed/luxembourg_eduPoleCharlemagne.xml",
            "/luxembourg/feed/eduPoleHaras.xml": "https://cvzi.github.io/mensa/feed/luxembourg_eduPoleHaras.xml",
            "/luxembourg/feed/eduPoleHarasFrupstut.xml": "https://cvzi.github.io/mensa/feed/luxembourg_eduPoleHarasFrupstut.xml",
            "/luxembourg/feed/eduPoleSchlass.xml": "https://cvzi.github.io/mensa/feed/luxembourg_eduPoleSchlass.xml",
            "/luxembourg/feed/EIDEDdayCareGaz.xml": "https://cvzi.github.io/mensa/feed/luxembourg_EIDEDdayCareGaz.xml",
            "/luxembourg/feed/EIDEDdayCareMon.xml": "https://cvzi.github.io/mensa/feed/luxembourg_EIDEDdayCareMon.xml",
            "/luxembourg/feed/EIDEDre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_EIDEDre.xml",
            "/luxembourg/feed/EIDEEca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_EIDEEca.xml",
            "/luxembourg/feed/EIDEEdayCare.xml": "https://cvzi.github.io/mensa/feed/luxembourg_EIDEEdayCare.xml",
            "/luxembourg/feed/EIDEEre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_EIDEEre.xml",
            "/luxembourg/feed/EIMLBdayCare.xml": "https://cvzi.github.io/mensa/feed/luxembourg_EIMLBdayCare.xml",
            "/luxembourg/feed/EIMLBre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_EIMLBre.xml",
            "/luxembourg/feed/Eis.xml": "https://cvzi.github.io/mensa/feed/luxembourg_Eis.xml",
            "/luxembourg/feed/ENAD.xml": "https://cvzi.github.io/mensa/feed/luxembourg_ENAD.xml",
            "/luxembourg/feed/EPOLint.xml": "https://cvzi.github.io/mensa/feed/luxembourg_EPOLint.xml",
            "/luxembourg/feed/EPOLre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_EPOLre.xml",
            "/luxembourg/feed/EschCDIre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_EschCDIre.xml",
            "/luxembourg/feed/EschCDIrume.xml": "https://cvzi.github.io/mensa/feed/luxembourg_EschCDIrume.xml",
            "/luxembourg/feed/IEAP.xml": "https://cvzi.github.io/mensa/feed/luxembourg_IEAP.xml",
            "/luxembourg/feed/INLre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_INLre.xml",
            "/luxembourg/feed/INSca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_INSca.xml",
            "/luxembourg/feed/INSre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_INSre.xml",
            "/luxembourg/feed/ISMLdayCare.xml": "https://cvzi.github.io/mensa/feed/luxembourg_ISMLdayCare.xml",
            "/luxembourg/feed/ISMLre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_ISMLre.xml",
            "/luxembourg/feed/LAMLca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LAMLca.xml",
            "/luxembourg/feed/LAMSDca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LAMSDca.xml",
            "/luxembourg/feed/LAMSDre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LAMSDre.xml",
            "/luxembourg/feed/LAMSLca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LAMSLca.xml",
            "/luxembourg/feed/LAMSLp1.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LAMSLp1.xml",
            "/luxembourg/feed/LAMSLre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LAMSLre.xml",
            "/luxembourg/feed/LBVca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LBVca.xml",
            "/luxembourg/feed/LBVre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LBVre.xml",
            "/luxembourg/feed/LBVtruck.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LBVtruck.xml",
            "/luxembourg/feed/LCDABbbq.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LCDABbbq.xml",
            "/luxembourg/feed/LCDABca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LCDABca.xml",
            "/luxembourg/feed/LCDABre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LCDABre.xml",
            "/luxembourg/feed/LCDBEre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LCDBEre.xml",
            "/luxembourg/feed/LCDMEre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LCDMEre.xml",
            "/luxembourg/feed/LCDNBca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LCDNBca.xml",
            "/luxembourg/feed/LCDNBre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LCDNBre.xml",
            "/luxembourg/feed/LCEca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LCEca.xml",
            "/luxembourg/feed/LCEgrand.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LCEgrand.xml",
            "/luxembourg/feed/LCEIntDi.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LCEIntDi.xml",
            "/luxembourg/feed/LCEpetit.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LCEpetit.xml",
            "/luxembourg/feed/LESCca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LESCca.xml",
            "/luxembourg/feed/LESCre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LESCre.xml",
            "/luxembourg/feed/LGEca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LGEca.xml",
            "/luxembourg/feed/LGEre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LGEre.xml",
            "/luxembourg/feed/LGKca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LGKca.xml",
            "/luxembourg/feed/LGKp1.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LGKp1.xml",
            "/luxembourg/feed/LGKre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LGKre.xml",
            "/luxembourg/feed/LGLca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LGLca.xml",
            "/luxembourg/feed/LGLre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LGLre.xml",
            "/luxembourg/feed/LHCEca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LHCEca.xml",
            "/luxembourg/feed/LHCEre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LHCEre.xml",
            "/luxembourg/feed/LJBMca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LJBMca.xml",
            "/luxembourg/feed/LJBMp1.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LJBMp1.xml",
            "/luxembourg/feed/LJBMre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LJBMre.xml",
            "/luxembourg/feed/LLJca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LLJca.xml",
            "/luxembourg/feed/LLJdayCare.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LLJdayCare.xml",
            "/luxembourg/feed/LLJp.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LLJp.xml",
            "/luxembourg/feed/LLJre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LLJre.xml",
            "/luxembourg/feed/LMLca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LMLca.xml",
            "/luxembourg/feed/LMLp1.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LMLp1.xml",
            "/luxembourg/feed/LMLPisc.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LMLPisc.xml",
            "/luxembourg/feed/LMLweier.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LMLweier.xml",
            "/luxembourg/feed/LMRLca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LMRLca.xml",
            "/luxembourg/feed/LMRLre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LMRLre.xml",
            "/luxembourg/feed/LNBalliance.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LNBalliance.xml",
            "/luxembourg/feed/LNBca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LNBca.xml",
            "/luxembourg/feed/LNBre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LNBre.xml",
            "/luxembourg/feed/LNca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LNca.xml",
            "/luxembourg/feed/LNp1.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LNp1.xml",
            "/luxembourg/feed/LNre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LNre.xml",
            "/luxembourg/feed/LRSLbi.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LRSLbi.xml",
            "/luxembourg/feed/LRSLhall.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LRSLhall.xml",
            "/luxembourg/feed/LRSLre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LRSLre.xml",
            "/luxembourg/feed/LRSLromarin.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LRSLromarin.xml",
            "/luxembourg/feed/LTAca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTAca.xml",
            "/luxembourg/feed/LTAIntDi.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTAIntDi.xml",
            "/luxembourg/feed/LTAre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTAre.xml",
            "/luxembourg/feed/LTBre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTBre.xml",
            "/luxembourg/feed/LTBRpv.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTBRpv.xml",
            "/luxembourg/feed/LTCKre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTCKre.xml",
            "/luxembourg/feed/LTCPp1.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTCPp1.xml",
            "/luxembourg/feed/LTCPp2.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTCPp2.xml",
            "/luxembourg/feed/LTCPp3.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTCPp3.xml",
            "/luxembourg/feed/LTCPre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTCPre.xml",
            "/luxembourg/feed/LTETTA.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTETTA.xml",
            "/luxembourg/feed/LTETTca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTETTca.xml",
            "/luxembourg/feed/LTETTre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTETTre.xml",
            "/luxembourg/feed/LTLca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTLca.xml",
            "/luxembourg/feed/LTLre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTLre.xml",
            "/luxembourg/feed/LTMAca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTMAca.xml",
            "/luxembourg/feed/LTMAjenker.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTMAjenker.xml",
            "/luxembourg/feed/LTMAre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTMAre.xml",
            "/luxembourg/feed/LTPESre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTPESre.xml",
            "/luxembourg/feed/LTPSbasch.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTPSbasch.xml",
            "/luxembourg/feed/LTPSbaSi.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTPSbaSi.xml",
            "/luxembourg/feed/LTPSebruck.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTPSebruck.xml",
            "/luxembourg/feed/LTPSmerc.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LTPSmerc.xml",
            "/luxembourg/feed/LuCDIasp.xml": "https://cvzi.github.io/mensa/feed/luxembourg_LuCDIasp.xml",
            "/luxembourg/feed/MLGbA.xml": "https://cvzi.github.io/mensa/feed/luxembourg_MLGbA.xml",
            "/luxembourg/feed/MLGca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_MLGca.xml",
            "/luxembourg/feed/MLGre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_MLGre.xml",
            "/luxembourg/feed/NOSLca.xml": "https://cvzi.github.io/mensa/feed/luxembourg_NOSLca.xml",
            "/luxembourg/feed/NOSLre.xml": "https://cvzi.github.io/mensa/feed/luxembourg_NOSLre.xml",
            "/luxembourg/feed/RoeserCDI.xml": "https://cvzi.github.io/mensa/feed/luxembourg_RoeserCDI.xml",
            "/luxembourg/feed/RooSyrCDI.xml": "https://cvzi.github.io/mensa/feed/luxembourg_RooSyrCDI.xml",
            "/luxembourg/feed/SCvisEleve.xml": "https://cvzi.github.io/mensa/feed/luxembourg_SCvisEleve.xml",
            "/luxembourg/feed/SCvisExt.xml": "https://cvzi.github.io/mensa/feed/luxembourg_SCvisExt.xml",
            "/luxembourg/feed/SportInt.xml": "https://cvzi.github.io/mensa/feed/luxembourg_SportInt.xml",
            "/luxembourg/feed/VTT.xml": "https://cvzi.github.io/mensa/feed/luxembourg_VTT.xml",
            "/luxembourg/feed/WarkCDI.xml": "https://cvzi.github.io/mensa/feed/luxembourg_WarkCDI.xml",
            "/luxembourg/meta/Agora.xml": "https://cvzi.github.io/mensa/meta/luxembourg_Agora.xml",
            "/luxembourg/meta/ALBBQ.xml": "https://cvzi.github.io/mensa/meta/luxembourg_ALBBQ.xml",
            "/luxembourg/meta/ALp1.xml": "https://cvzi.github.io/mensa/meta/luxembourg_ALp1.xml",
            "/luxembourg/meta/ALRca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_ALRca.xml",
            "/luxembourg/meta/ALre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_ALre.xml",
            "/luxembourg/meta/ALRint.xml": "https://cvzi.github.io/mensa/meta/luxembourg_ALRint.xml",
            "/luxembourg/meta/ALRre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_ALRre.xml",
            "/luxembourg/meta/BertCDI.xml": "https://cvzi.github.io/mensa/meta/luxembourg_BertCDI.xml",
            "/luxembourg/meta/BlvlFoodCafe.xml": "https://cvzi.github.io/mensa/meta/luxembourg_BlvlFoodCafe.xml",
            "/luxembourg/meta/BlvlFoodHouse.xml": "https://cvzi.github.io/mensa/meta/luxembourg_BlvlFoodHouse.xml",
            "/luxembourg/meta/BlvlFoodLab.xml": "https://cvzi.github.io/mensa/meta/luxembourg_BlvlFoodLab.xml",
            "/luxembourg/meta/BlvlFoodZone.xml": "https://cvzi.github.io/mensa/meta/luxembourg_BlvlFoodZone.xml",
            "/luxembourg/meta/CDIreBonne.xml": "https://cvzi.github.io/mensa/meta/luxembourg_CDIreBonne.xml",
            "/luxembourg/meta/CDIreCess.xml": "https://cvzi.github.io/mensa/meta/luxembourg_CDIreCess.xml",
            "/luxembourg/meta/CDIreWei.xml": "https://cvzi.github.io/mensa/meta/luxembourg_CDIreWei.xml",
            "/luxembourg/meta/CDMre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_CDMre.xml",
            "/luxembourg/meta/CDVre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_CDVre.xml",
            "/luxembourg/meta/ClerCDI.xml": "https://cvzi.github.io/mensa/meta/luxembourg_ClerCDI.xml",
            "/luxembourg/meta/CLreAd.xml": "https://cvzi.github.io/mensa/meta/luxembourg_CLreAd.xml",
            "/luxembourg/meta/CmpsGeessForCa.xml": "https://cvzi.github.io/mensa/meta/luxembourg_CmpsGeessForCa.xml",
            "/luxembourg/meta/CmpsGeessForRe.xml": "https://cvzi.github.io/mensa/meta/luxembourg_CmpsGeessForRe.xml",
            "/luxembourg/meta/CmpsGeessPisc.xml": "https://cvzi.github.io/mensa/meta/luxembourg_CmpsGeessPisc.xml",
            "/luxembourg/meta/CmpsGeessTruck.xml": "https://cvzi.github.io/mensa/meta/luxembourg_CmpsGeessTruck.xml",
            "/luxembourg/meta/CmpsKiBergAltius.xml": "https://cvzi.github.io/mensa/meta/luxembourg_CmpsKiBergAltius.xml",
            "/luxembourg/meta/CmpsKiBergJohns.xml": "https://cvzi.github.io/mensa/meta/luxembourg_CmpsKiBergJohns.xml",
            "/luxembourg/meta/CNFPC.xml": "https://cvzi.github.io/mensa/meta/luxembourg_CNFPC.xml",
            "/luxembourg/meta/CSAEMerl.xml": "https://cvzi.github.io/mensa/meta/luxembourg_CSAEMerl.xml",
            "/luxembourg/meta/ECGbi.xml": "https://cvzi.github.io/mensa/meta/luxembourg_ECGbi.xml",
            "/luxembourg/meta/EchtCDI.xml": "https://cvzi.github.io/mensa/meta/luxembourg_EchtCDI.xml",
            "/luxembourg/meta/eduPoleCharlemagne.xml": "https://cvzi.github.io/mensa/meta/luxembourg_eduPoleCharlemagne.xml",
            "/luxembourg/meta/eduPoleHaras.xml": "https://cvzi.github.io/mensa/meta/luxembourg_eduPoleHaras.xml",
            "/luxembourg/meta/eduPoleHarasFrupstut.xml": "https://cvzi.github.io/mensa/meta/luxembourg_eduPoleHarasFrupstut.xml",
            "/luxembourg/meta/eduPoleSchlass.xml": "https://cvzi.github.io/mensa/meta/luxembourg_eduPoleSchlass.xml",
            "/luxembourg/meta/EIDEDdayCareGaz.xml": "https://cvzi.github.io/mensa/meta/luxembourg_EIDEDdayCareGaz.xml",
            "/luxembourg/meta/EIDEDdayCareMon.xml": "https://cvzi.github.io/mensa/meta/luxembourg_EIDEDdayCareMon.xml",
            "/luxembourg/meta/EIDEDre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_EIDEDre.xml",
            "/luxembourg/meta/EIDEEca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_EIDEEca.xml",
            "/luxembourg/meta/EIDEEdayCare.xml": "https://cvzi.github.io/mensa/meta/luxembourg_EIDEEdayCare.xml",
            "/luxembourg/meta/EIDEEre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_EIDEEre.xml",
            "/luxembourg/meta/EIMLBdayCare.xml": "https://cvzi.github.io/mensa/meta/luxembourg_EIMLBdayCare.xml",
            "/luxembourg/meta/EIMLBre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_EIMLBre.xml",
            "/luxembourg/meta/Eis.xml": "https://cvzi.github.io/mensa/meta/luxembourg_Eis.xml",
            "/luxembourg/meta/ENAD.xml": "https://cvzi.github.io/mensa/meta/luxembourg_ENAD.xml",
            "/luxembourg/meta/EPOLint.xml": "https://cvzi.github.io/mensa/meta/luxembourg_EPOLint.xml",
            "/luxembourg/meta/EPOLre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_EPOLre.xml",
            "/luxembourg/meta/EschCDIre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_EschCDIre.xml",
            "/luxembourg/meta/EschCDIrume.xml": "https://cvzi.github.io/mensa/meta/luxembourg_EschCDIrume.xml",
            "/luxembourg/meta/IEAP.xml": "https://cvzi.github.io/mensa/meta/luxembourg_IEAP.xml",
            "/luxembourg/meta/INLre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_INLre.xml",
            "/luxembourg/meta/INSca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_INSca.xml",
            "/luxembourg/meta/INSre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_INSre.xml",
            "/luxembourg/meta/ISMLdayCare.xml": "https://cvzi.github.io/mensa/meta/luxembourg_ISMLdayCare.xml",
            "/luxembourg/meta/ISMLre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_ISMLre.xml",
            "/luxembourg/meta/LAMLca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LAMLca.xml",
            "/luxembourg/meta/LAMSDca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LAMSDca.xml",
            "/luxembourg/meta/LAMSDre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LAMSDre.xml",
            "/luxembourg/meta/LAMSLca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LAMSLca.xml",
            "/luxembourg/meta/LAMSLp1.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LAMSLp1.xml",
            "/luxembourg/meta/LAMSLre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LAMSLre.xml",
            "/luxembourg/meta/LBVca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LBVca.xml",
            "/luxembourg/meta/LBVre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LBVre.xml",
            "/luxembourg/meta/LBVtruck.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LBVtruck.xml",
            "/luxembourg/meta/LCDABbbq.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LCDABbbq.xml",
            "/luxembourg/meta/LCDABca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LCDABca.xml",
            "/luxembourg/meta/LCDABre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LCDABre.xml",
            "/luxembourg/meta/LCDBEre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LCDBEre.xml",
            "/luxembourg/meta/LCDMEre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LCDMEre.xml",
            "/luxembourg/meta/LCDNBca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LCDNBca.xml",
            "/luxembourg/meta/LCDNBre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LCDNBre.xml",
            "/luxembourg/meta/LCEca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LCEca.xml",
            "/luxembourg/meta/LCEgrand.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LCEgrand.xml",
            "/luxembourg/meta/LCEIntDi.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LCEIntDi.xml",
            "/luxembourg/meta/LCEpetit.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LCEpetit.xml",
            "/luxembourg/meta/LESCca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LESCca.xml",
            "/luxembourg/meta/LESCre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LESCre.xml",
            "/luxembourg/meta/LGEca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LGEca.xml",
            "/luxembourg/meta/LGEre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LGEre.xml",
            "/luxembourg/meta/LGKca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LGKca.xml",
            "/luxembourg/meta/LGKp1.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LGKp1.xml",
            "/luxembourg/meta/LGKre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LGKre.xml",
            "/luxembourg/meta/LGLca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LGLca.xml",
            "/luxembourg/meta/LGLre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LGLre.xml",
            "/luxembourg/meta/LHCEca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LHCEca.xml",
            "/luxembourg/meta/LHCEre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LHCEre.xml",
            "/luxembourg/meta/LJBMca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LJBMca.xml",
            "/luxembourg/meta/LJBMp1.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LJBMp1.xml",
            "/luxembourg/meta/LJBMre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LJBMre.xml",
            "/luxembourg/meta/LLJca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LLJca.xml",
            "/luxembourg/meta/LLJdayCare.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LLJdayCare.xml",
            "/luxembourg/meta/LLJp.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LLJp.xml",
            "/luxembourg/meta/LLJre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LLJre.xml",
            "/luxembourg/meta/LMLca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LMLca.xml",
            "/luxembourg/meta/LMLp1.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LMLp1.xml",
            "/luxembourg/meta/LMLPisc.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LMLPisc.xml",
            "/luxembourg/meta/LMLweier.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LMLweier.xml",
            "/luxembourg/meta/LMRLca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LMRLca.xml",
            "/luxembourg/meta/LMRLre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LMRLre.xml",
            "/luxembourg/meta/LNBalliance.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LNBalliance.xml",
            "/luxembourg/meta/LNBca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LNBca.xml",
            "/luxembourg/meta/LNBre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LNBre.xml",
            "/luxembourg/meta/LNca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LNca.xml",
            "/luxembourg/meta/LNp1.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LNp1.xml",
            "/luxembourg/meta/LNre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LNre.xml",
            "/luxembourg/meta/LRSLbi.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LRSLbi.xml",
            "/luxembourg/meta/LRSLhall.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LRSLhall.xml",
            "/luxembourg/meta/LRSLre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LRSLre.xml",
            "/luxembourg/meta/LRSLromarin.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LRSLromarin.xml",
            "/luxembourg/meta/LTAca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTAca.xml",
            "/luxembourg/meta/LTAIntDi.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTAIntDi.xml",
            "/luxembourg/meta/LTAre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTAre.xml",
            "/luxembourg/meta/LTBre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTBre.xml",
            "/luxembourg/meta/LTBRpv.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTBRpv.xml",
            "/luxembourg/meta/LTCKre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTCKre.xml",
            "/luxembourg/meta/LTCPp1.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTCPp1.xml",
            "/luxembourg/meta/LTCPp2.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTCPp2.xml",
            "/luxembourg/meta/LTCPp3.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTCPp3.xml",
            "/luxembourg/meta/LTCPre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTCPre.xml",
            "/luxembourg/meta/LTETTA.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTETTA.xml",
            "/luxembourg/meta/LTETTca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTETTca.xml",
            "/luxembourg/meta/LTETTre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTETTre.xml",
            "/luxembourg/meta/LTLca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTLca.xml",
            "/luxembourg/meta/LTLre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTLre.xml",
            "/luxembourg/meta/LTMAca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTMAca.xml",
            "/luxembourg/meta/LTMAjenker.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTMAjenker.xml",
            "/luxembourg/meta/LTMAre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTMAre.xml",
            "/luxembourg/meta/LTPESre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTPESre.xml",
            "/luxembourg/meta/LTPSbasch.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTPSbasch.xml",
            "/luxembourg/meta/LTPSbaSi.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTPSbaSi.xml",
            "/luxembourg/meta/LTPSebruck.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTPSebruck.xml",
            "/luxembourg/meta/LTPSmerc.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LTPSmerc.xml",
            "/luxembourg/meta/LuCDIasp.xml": "https://cvzi.github.io/mensa/meta/luxembourg_LuCDIasp.xml",
            "/luxembourg/meta/MLGbA.xml": "https://cvzi.github.io/mensa/meta/luxembourg_MLGbA.xml",
            "/luxembourg/meta/MLGca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_MLGca.xml",
            "/luxembourg/meta/MLGre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_MLGre.xml",
            "/luxembourg/meta/NOSLca.xml": "https://cvzi.github.io/mensa/meta/luxembourg_NOSLca.xml",
            "/luxembourg/meta/NOSLre.xml": "https://cvzi.github.io/mensa/meta/luxembourg_NOSLre.xml",
            "/luxembourg/meta/RoeserCDI.xml": "https://cvzi.github.io/mensa/meta/luxembourg_RoeserCDI.xml",
            "/luxembourg/meta/RooSyrCDI.xml": "https://cvzi.github.io/mensa/meta/luxembourg_RooSyrCDI.xml",
            "/luxembourg/meta/SCvisEleve.xml": "https://cvzi.github.io/mensa/meta/luxembourg_SCvisEleve.xml",
            "/luxembourg/meta/SCvisExt.xml": "https://cvzi.github.io/mensa/meta/luxembourg_SCvisExt.xml",
            "/luxembourg/meta/SportInt.xml": "https://cvzi.github.io/mensa/meta/luxembourg_SportInt.xml",
            "/luxembourg/meta/VTT.xml": "https://cvzi.github.io/mensa/meta/luxembourg_VTT.xml",
            "/luxembourg/meta/WarkCDI.xml": "https://cvzi.github.io/mensa/meta/luxembourg_WarkCDI.xml"
        }
        new_url = redirects[environ['PATH_INFO']] if environ['PATH_INFO'] in redirects else "https://cvzi.github.io/mensa/"

        response_body = ('<a href="%s">%s</a>' % (new_url, new_url)).encode('utf-8')

        response_headers = [('Location', new_url),
                            ('Content-Length', str(len(response_body))),
                            ('Content-Type', 'text/html; charset=utf-8'),
                            ('X-OpenMensa-ParserVersion', str(__version__))]
        status = '301 Moved Permanently'
        start_response(status, response_headers)
        return [response_body]

    elif environ['PATH_INFO'] == '/api':
        links = []
        for parser in (heidelberg, eppelheim, mannheim, stuttgart, ulm):
            moduleName = parser.__module__
            if moduleName == 'heidelberg':
                moduleName = ''
            else:
                moduleName += '/'

            canteens = list(parser.canteens.keys())
            for canteen in canteens:
                if hasattr(parser, "meta"):
                    links.append(f"{moduleName}meta/{canteen}.xml")
                if hasattr(parser, "feed_today"):
                    links.append(f"{moduleName}today/{canteen}.xml")
                if hasattr(parser, "feed_all"):
                    links.append(f"{moduleName}all/{canteen}.xml")
                if hasattr(parser, "feed"):
                    links.append(f"{moduleName}feed/{canteen}.xml")

        newline = "\n              "
        ctype = 'text/html; charset=utf-8'
        cache_control = 'public, max-age=86400'
        response_body = f"""
            <h1>mensahd-cuzi</h1>
            <div>List of all available endpoints</div>
            <h2>API:</h2>
            <ul style="font-family:Consolas,monospace">
              {newline.join([f'<li><a href="/{path}">/{path}</a></li>' for path in links])}
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
              <li><a href="/koeln">/koeln</a> moved to <a href="https://cvzi.github.io/mensa/#koeln">https://cvzi.github.io/mensa/</a></li>
              <li><a href="/stuttgart">/stuttgart</a></li>
              <li><a href="/ulm">/ulm</a></li>
              <li><a href="/luxembourg">/luxembourg</a> moved to <a href="https://cvzi.github.io/mensa/#luxembourg">https://cvzi.github.io/mensa/</a></li>
              <li><a href="/time">/time</a></li>
              <li><a href="/status">/status</a></li>
              <li><a href="/list">/list</a></li>
              <li><a href="/list.json">/list.json</a></li>
              <li>/meta/{id}.xml</li>
              <li>/today/{id}.xml</li>
              <li>/all/{id}.xml</li>
              <li><a href="/api">/api</a></li>
            </ul>
            <!-- https://github.com/tholman/github-corners -->
            <div>
            <a href="https://github.com/cvzi/mensahd" class="github-corner" aria-label="View source on GitHub"><svg width="80" height="80" viewBox="0 0 250 250" style="fill:#64CEAA; color:#fff; position: absolute; top: 0; border: 0; right: 0;" aria-hidden="true"><path d="M0,0 L115,115 L130,115 L142,142 L250,250 L250,0 Z"></path><path d="M128.3,109.0 C113.8,99.7 119.0,89.6 119.0,89.6 C122.0,82.7 120.5,78.6 120.5,78.6 C119.2,72.0 123.4,76.3 123.4,76.3 C127.3,80.9 125.5,87.3 125.5,87.3 C122.9,97.6 130.6,101.9 134.4,103.2" fill="currentColor" style="transform-origin: 130px 106px;" class="octo-arm"></path><path d="M115.0,115.0 C114.9,115.1 118.7,116.5 119.8,115.4 L133.7,101.6 C136.9,99.2 139.9,98.4 142.2,98.6 C133.8,88.0 127.5,74.4 143.8,58.0 C148.5,53.4 154.0,51.2 159.7,51.0 C160.3,49.4 163.2,43.6 171.4,40.1 C171.4,40.1 176.1,42.5 178.8,56.2 C183.1,58.6 187.2,61.8 190.9,65.4 C194.5,69.0 197.7,73.2 200.1,77.6 C213.8,80.2 216.3,84.9 216.3,84.9 C212.7,93.1 206.9,96.0 205.4,96.6 C205.1,102.4 203.0,107.8 198.3,112.5 C181.9,128.9 168.3,122.5 157.7,114.1 C157.9,116.9 156.7,120.9 152.7,124.9 L141.0,136.5 C139.8,137.7 141.6,141.9 141.8,141.8 Z" fill="currentColor" class="octo-body"></path></svg></a><style>.github-corner:hover .octo-arm{animation:octocat-wave 560ms ease-in-out}@keyframes octocat-wave{0%,100%{transform:rotate(0)}20%,60%{transform:rotate(-25deg)}40%,80%{transform:rotate(10deg)}}@media (max-width:500px){.github-corner:hover .octo-arm{animation:none}.github-corner .octo-arm{animation:octocat-wave 560ms ease-in-out}}</style>
            </div>
            """

    response_body = response_body.encode('utf-8')

    response_headers = [('Content-Type', ctype),
                        ('Content-Length', str(len(response_body))),
                        ('Cache-Control', cache_control),
                        ('X-OpenMensa-ParserVersion', str(__version__))]

    start_response(status, response_headers)
    return [response_body]
