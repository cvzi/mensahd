#!/usr/bin/env python
#
# Python 3

import os
import datetime
import pytz
import heidelberg
from mannheim import getmannheim
import traceback

page_errors = []

baseurl = "https://mensahd-cuzi.rhcloud.com/"
mannheim = getmannheim()

def application(environ, start_response):
    ctype = 'text/plain'
    status = '200 OK'
    
    if environ['PATH_INFO'] == '/health':
        response_body = "1"
            
    elif environ['PATH_INFO'] == '/status':
        response_body = "Ok. %d errors.\n" % len(page_errors)
        for exc in page_errors:
            response_body += "%s \t %s\n" % exc
        
    elif environ['PATH_INFO'].startswith('/today'):
        ctype = 'text/xml'
        if len(environ['PATH_INFO']) > 7:
            name = environ['PATH_INFO'][7:]
            if name.endswith(".xml"):
                name = name[:-4]
        else:
            name = ''
        try:
            response_body = heidelberg.today(name).decode("utf-8")
        except Exception as e:
            ctype = 'text/plain'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((environ['PATH_INFO'], e))
            

    elif environ['PATH_INFO'].startswith('/all'):
        ctype = 'text/xml'
        if len(environ['PATH_INFO']) > 5:
            name = environ['PATH_INFO'][5:]
            if name.endswith(".xml"):
                name = name[:-4]
        else:
            name = ''
        try:
            response_body = heidelberg.all(name).decode("utf-8")
        except Exception as e:
            ctype = 'text/plain'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((environ['PATH_INFO'], e))
        
    elif environ['PATH_INFO'].startswith('/meta'):
        ctype = 'text/xml'
        if len(environ['PATH_INFO']) > 6:
            name = environ['PATH_INFO'][6:]
            if name.endswith(".xml"):
                name = name[:-4]
        else:
            name = ''
        try:
            response_body = heidelberg.meta(name)
        except Exception as e:
            ctype = 'text/plain'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((environ['PATH_INFO'], e))
        
    
    elif environ['PATH_INFO'] == '/list':
        ctype = 'text/xml'
        try:
            response_body = heidelberg.list()
        except Exception as e:
            ctype = 'text/plain'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((environ['PATH_INFO'], e))
        
    elif environ['PATH_INFO'] == '/list.json':
        ctype = 'text/json'
        try:
            response_body = heidelberg.listJSON()
        except Exception as e:
            ctype = 'text/plain'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((environ['PATH_INFO'], e))
    
    elif environ['PATH_INFO'] == '/time':
        berlin = pytz.timezone('Europe/Berlin')
        now = datetime.datetime.now(berlin)
        response_body = now.strftime("%Y-%m-%d %H:%M")

    elif environ['PATH_INFO'] == '/mannheim/list.json':
        ctype = 'text/json'
        try:
            response_body = mannheim.json(baseurl+"mannheim/meta/%s.xml")
        except Exception as e:
            ctype = 'text/plain'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((environ['PATH_INFO'], e))
    
    elif environ['PATH_INFO'].startswith('/mannheim/meta/'):
        ctype = 'text/xml'
        name = environ['PATH_INFO'][15:]
        if name.endswith(".xml"):
            name = name[:-4]            
        try:
            response_body = mannheim.meta(name)
        except Exception as e:
            ctype = 'text/plain'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((environ['PATH_INFO'], e))
            
    elif environ['PATH_INFO'].startswith('/mannheim/feed/'):
        ctype = 'text/xml'
        name = environ['PATH_INFO'][15:]
        if name.endswith(".xml"):
            name = name[:-4]            
        try:
            response_body = mannheim.feed(name)
        except Exception as e:
            ctype = 'text/plain'
            response_body = "An error occured:\n%s\n%s" % (e, traceback.format_exc())
            status = '503 Service Unavailable'
            page_errors.append((environ['PATH_INFO'], e))

    elif environ['PATH_INFO'] == '/mannheim' or environ['PATH_INFO'] == '/mannheim/':
        ctype = 'text/html'
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
 
    else:
        ctype = 'text/html'
        response_body = """
            <h1>mensahd-cuzi for Heidelberg University canteens</h1>
            <div>This is a parser for <a href="https://openmensa.org/">openmensa.org</a>. It fetches and converts public data from <a href="http://www.stw.uni-heidelberg.de/de/speiseplan">Studierendenwerk Heidelberg</a></div>
            <h2>Public interface:</h2>
            <ul>
              <li><a href="/"><b>Heidelberg</b></a></li>
              <li><a href="/mannheim">/mannheim</a></li>              
              <li><a href="/time">/time</a></li>
              <li><a href="/status">/status</a></li>
              <li><a href="/list">/list</a></li>
              <li><a href="/list.json">/list.json</a></li>
              <li>/meta/{id}.xml</li>
              <li>/today/{id}.xml</li>
              <li>/all/{id}.xml</li>
            </ul>"""
    
    response_body = response_body.encode('utf-8')

    response_headers = [('Content-Type', ctype), ('Content-Length', str(len(response_body)))]

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
