#
# For testing only
#
if __name__ == '__main__':

    from mensahd import wsgi
    from wsgiref.simple_server import make_server
    httpd = make_server('localhost', 80, wsgi.application)
    print("http://localhost:80/")
    httpd.serve_forever()
