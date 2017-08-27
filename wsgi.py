#!/usr/bin/env python
#
# Python 3

import os
import datetime
import pytz

from heidelberg import getheidelberg
from mannheim import getmannheim
from koeln import getkoeln
from stuttgart import getstuttgart

import traceback
import urllib.request
import urllib.error
import socket

page_errors = []

baseurl = "https://mensahd-cuzi.rhcloud.com/"

heidelberg = getheidelberg(baseurl)
mannheim = getmannheim(baseurl)
koeln = getkoeln(baseurl)
stuttgart = getstuttgart(baseurl)

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
        response_body = open(os.path.join(os.path.dirname(__file__), "favicon.ico"),"rb").read()
        response_headers = [('Content-Type', ctype), ('Content-Length', str(len(response_body))), ('Cache-Control', cache_control)]
        start_response(status, response_headers)
        return [response_body ]
            
    elif environ['PATH_INFO'] == '/status':
        statusmessage = []
        
        try:
            request = urllib.request.Request("http://www.stw.uni-heidelberg.de/") # No httpS available!
            result = urllib.request.urlopen(request, timeout=5)
        except:
            statusmessage.append("www.stw.uni-heidelberg.de is not reachable")
            
        try:
            request = urllib.request.Request("https://www.stw-ma.de/")
            result = urllib.request.urlopen(request, timeout=5)
        except:
            statusmessage.append("www.stw-ma.de is not reachable")
            
        try:
            request = urllib.request.Request("https://www.max-manager.de/") # No httpS available!
            result = urllib.request.urlopen(request, timeout=5)
        except:
            statusmessage.append("www.max-manager.de is not reachable")   

        try:
            request = urllib.request.Request("https://www.studierendenwerk-stuttgart.de/")
            result = urllib.request.urlopen(request, timeout=5)
        except:
            statusmessage.append("www.studierendenwerk-stuttgart.de is not reachable")
           
            
            
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
            response_body = "Could not connect to www.stw.uni-heidelberg.de\n\nAn error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '533 Open www.stw.uni-heidelberg.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
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
            response_body = "Could not connect to www.stw.uni-heidelberg.de\n\nAn error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '533 Open www.stw.uni-heidelberg.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
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
            response_body = "Could not connect to www.stw.uni-heidelberg.de\n\nAn error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '533 Open www.stw.uni-heidelberg.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        
    
    elif environ['PATH_INFO'] == '/list':
        ctype = 'application/xml; charset=utf-8'
        try:
            response_body = heidelberg.list()
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to www.stw.uni-heidelberg.de\n\nAn error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '533 Open www.stw.uni-heidelberg.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        
    elif environ['PATH_INFO'] == '/list.json':
        ctype = 'application/json; charset=utf-8'
        try:
            response_body = heidelberg.json()
        except (urllib.error.URLError, socket.timeout) as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "Could not connect to www.stw.uni-heidelberg.de\n\nAn error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '533 Open www.stw.uni-heidelberg.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
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
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
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
            response_body = "Could not connect to www.stw-ma.de\n\nAn error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '533 Open www.stw-ma.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
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
            response_body = "Could not connect to www.stw-ma.de\n\nAn error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '533 Open www.stw-ma.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
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
            </ul>"""
            
            
            
            
            
            
    elif environ['PATH_INFO'] == '/koeln/list.json':
        ctype = 'application/json; charset=utf-8'
        try:
            response_body = koeln.json()
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
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
            response_body = "Could not connect to www.max-manager.de\n\nAn error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '533 Open www.stw-ma.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
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
            response_body = "Could not connect to www.max-manager.de\n\nAn error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '533 Open www.max-manager.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
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
            response_body = "Could not connect to www.max-manager.de\n\nAn error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '533 Open www.max-manager.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
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
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
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
            response_body = "Could not connect to www.studierendenwerk-stuttgart.de\n\nAn error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '533 Open www.stw-ma.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
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
            response_body = "Could not connect to www.studierendenwerk-stuttgart.de\n\nAn error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '533 Open www.max-manager.de timed out'
            page_errors.append((timeStrBerlin(), environ['PATH_INFO'], e))
        except Exception as e:
            ctype = 'text/plain; charset=utf-8'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
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
              <li><a href="/time">/time</a></li>
              <li><a href="/status">/status</a></li>
              <li><a href="/list">/list</a></li>
              <li><a href="/list.json">/list.json</a></li>
              <li>/meta/{id}.xml</li>
              <li>/today/{id}.xml</li>
              <li>/all/{id}.xml</li>
            </ul>"""
    
    response_body = response_body.encode('utf-8')

    response_headers = [('Content-Type', ctype), ('Content-Length', str(len(response_body))), ('Cache-Control', cache_control)]

    start_response(status, response_headers)
    return [response_body ]

#
# Below for testing only
#
if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    httpd = make_server('localhost', 8051, application)
    # Wait for a single request, serve it and quit.
    httpd.handle_request()
    
