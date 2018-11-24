import sys
import os
import logging
import lxml.etree
import defusedxml.lxml
import urllib.request

include = os.path.relpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, include)


def downloadFile(url, filename="file.tmp"):
    if not os.path.isfile(filename):
        if not url.startswith("http://") and not url.startswith("https://"):
            raise RuntimeError("url is not an allowed URL: %r" % url)
        with urllib.request.urlopen(url) as furl:
            with open(filename, 'wb') as fout:
                fout.write(furl.read())

    return os.path.abspath(filename)


xmlParser = lxml.etree.XMLParser(schema=lxml.etree.XMLSchema(file=downloadFile(
    'http://openmensa.org/open-mensa-v2.xsd', 'open-mensa-v2.xsd')))


def check_meta(content):
    print("Content", end="")

    # Check syntax
    try:
        defusedxml.lxml.fromstring(content.encode('utf8'), xmlParser)
    except lxml.etree.XMLSyntaxError as error:
        print("- Invalid document: %s" % str(error))

    # Content length
    if len(content) < 450:
        print(" - Looks too short.")
    else:
        print(" - Ok.")
    return True


def check_feed(content, encoding='utf8'):
    print("Content", end="")

    # Check syntax
    try:
        source = content
        if not isinstance(source, bytes):
            source = content.encode(encoding)
        else:
            content = content.decode(encoding)

        lxml.etree.fromstring(source, xmlParser)
    except lxml.etree.XMLSyntaxError as error:
        print("- Invalid document: %s" % str(error))
        return False

    # Content length
    if len(content) < 300:
        print(" - Looks empty.")
    elif len(content) < 360:
        print(" - Looks closed.")
    else:
        print(" - Ok.")

    # Count closed days:
    closed = content.count('<closed')
    if closed > 0:
        print("Found closed days: %d" % closed)

    return True


def check_xml(parser, canteen):
    print("Canteen: %s" % canteen)

    print("meta()", end="")
    content = parser.meta(canteen)
    print(" - Ok.")
    print("meta() ", end="")
    check_meta(content)

    has_feed = 0

    if hasattr(parser, "feed_today"):
        print("feed_today()", end="")
        content = parser.feed_today(canteen)
        print(" - Ok.")
        print("feed_today() ", end="")
        check_feed(content)
        has_feed += 1

    if hasattr(parser, "feed_all"):
        print("feed_all()", end="")
        content = parser.feed_all(canteen)
        print(" - Ok.")
        print("feed_all() ", end="")
        check_feed(content)
        has_feed += 1

    if hasattr(parser, "feed"):
        print("feed()", end="")
        content = parser.feed(canteen)
        print(" - Ok.")
        print("feed() ", end="")
        check_feed(content)
        has_feed += 1

    if has_feed == 0:
        print("! No feeds found.")


def test_all_modules():
    moduleNames = ['eppelheim', 'heidelberg', 'koeln', 'mannheim', 'stuttgart']

    print("Importing", end="")

    modules = map(__import__, moduleNames)

    print(" - Ok.")

    for mod in modules:
        print("Module: %s" % mod.__name__)

        parser = mod.getParser('http://localhost/')
        canteens = list(parser.canteens.keys())

        for canteen in canteens:
            check_xml(parser, canteen)


def run_all():
    for fname, f in list(globals().items()):
        if fname.startswith('test_'):
            print("%s()" % fname)
            f()
            print("Ok.")


if __name__ == '__main__':
    # logging.basicConfig(level=logging.DEBUG)
    logging.basicConfig(level=logging.WARNING)
    run_all()
