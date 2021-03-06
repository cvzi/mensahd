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
from luxembourg import getParser as getluxembourg

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
luxembourg = getluxembourg(baseurl)


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

    elif environ['PATH_INFO'] == '/luxembourg/list.json':
        ctype = 'application/json; charset=utf-8'
        try:
            response_body = luxembourg.json()
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'].startswith('/luxembourg/meta/'):
        ctype = 'application/xml; charset=utf-8'
        name = environ['PATH_INFO'][17:]
        if name.endswith(".xml"):
            name = name[:-4]
        try:
            response_body = luxembourg.meta(name)
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'].startswith('/luxembourg/feed/'):
        ctype = 'application/xml; charset=utf-8'
        name = environ['PATH_INFO'][17:]
        if name.endswith(".xml"):
            name = name[:-4]
        try:
            response_body = luxembourg.feed(name)
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to ssl.education.lu\n\nAn error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '533 Open ssl.education.lu timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (
                e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))

    elif environ['PATH_INFO'] == '/luxembourg' or environ['PATH_INFO'] == '/luxembourg/':
        ctype = 'text/html; charset=utf-8'
        cache_control = 'public, max-age=86400'
        response_body = """
            <h1>mensahd-cuzi for Restopolis canteens</h1>
            <div>This is a parser for <a href="https://openmensa.org/">openmensa.org</a>. It fetches and converts public data from <a href="https://portal.education.lu/restopolis/">https://portal.education.lu/restopolis/</a></div>
            <h2>Public interface:</h2>
            <ul>
              <li><a href="/">../ Heidelberg</a></li>
              <li><a href="/luxembourg"><b>luxembourg</b></a></li>
              <li><a href="/luxembourg/list.json">/luxembourg/list.json</a></li>
              <li>/luxembourg/meta/{id}.xml</li>
              <li>/luxembourg/feed/{id}.xml</li>
            </ul>"""

    elif environ['PATH_INFO'] == '/api':
        links = []
        for parser in (heidelberg, eppelheim, mannheim, stuttgart, ulm, luxembourg):
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
              <li><a href="/luxembourg">/luxembourg</a></li>
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
