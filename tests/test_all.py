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
        with urllib.request.urlopen(url) as furl:  # nosec
            with open(filename, 'wb') as fout:
                fout.write(furl.read())

    return os.path.abspath(filename)


xmlParser = lxml.etree.XMLParser(schema=lxml.etree.XMLSchema(file=downloadFile(
    'http://openmensa.org/open-mensa-v2.xsd', 'open-mensa-v2.xsd')))


def check_meta(content, name=''):
    print("Content", end="")

    # Check syntax
    try:
        defusedxml.lxml.fromstring(content.encode('utf8'), xmlParser)
    except lxml.etree.XMLSyntaxError as error:
        raise RuntimeWarning("Invalid document meta [%s]: %s" % (name, str(error)))

    # Content length
    if len(content) < 450:
        print(" -> Probably too short meta. [%s]" % (name, ), file=sys.stderr)
        return False
    else:
        print(" -> Ok.")
    return True


def check_feed(content, encoding='utf8', name=''):
    print("Content", end="")

    # Check syntax
    try:
        source = content
        if not isinstance(source, bytes):
            source = content.encode(encoding)
        else:
            content = content.decode(encoding)

        defusedxml.lxml.fromstring(source, xmlParser)
    except lxml.etree.XMLSyntaxError as error:
        raise RuntimeWarning("Invalid document feed [%s]: %s" % (name, str(error)))

    # Content length
    if len(content) < 300:
        # raise RuntimeWarning("[%s] probably empty feed." % (name,))
        print(f"[{name}] probably empty feed.")
        return False
    elif len(content) < 360:
        print(" -> Probably closed. [%s]" % (name, ), file=sys.stderr)
    else:
        print(" -> Ok.")

    # Count closed days:
    closed = content.count('<closed')
    if closed > 0:
        print("Found closed days: %d [%s]" % (closed, name), file=sys.stderr)

    return True


def check_xml(parser, canteen):
    name = "%s/%s" % (parser.__module__, canteen)
    print("Canteen: %s" % (name, ))

    print("meta()", end="")
    content = parser.meta(canteen)
    print(" -> Ok.")
    print("meta() ", end="")
    check_meta(content, name=name)

    has_feed = 0

    if hasattr(parser, "feed_today"):
        print("feed_today()", end="")
        content = parser.feed_today(canteen)
        print(" -> Ok.")
        print("feed_today() ", end="")
        check_feed(content, name=name)
        has_feed += 1

    if hasattr(parser, "feed_all"):
        print("feed_all()", end="")
        content = parser.feed_all(canteen)
        print(" -> Ok.")
        print("feed_all() ", end="")
        check_feed(content, name=name)
        has_feed += 1

    if hasattr(parser, "feed"):
        print("feed()", end="")
        content = parser.feed(canteen)
        print(" -> Ok.")
        print("feed() ", end="")
        check_feed(content, name=name)
        has_feed += 1

    if has_feed == 0:
        raise RuntimeWarning("No feeds found for [%s]." % (name, ))


def test_all_modules():
    moduleNames = ['eppelheim', 'heidelberg', 'koeln', 'mannheim', 'stuttgart', 'luxembourg']

    print("Importing %s" % (", ".join(moduleNames), ), end="")

    modules = map(__import__, moduleNames)

    print(" -> Ok.")

    errors = []
    for mod in modules:
        try:
            print("Module: %s" % mod.__name__)

            parser = mod.getParser('http://localhost/')
            canteens = list(parser.canteens.keys())

            for canteen in canteens:
                check_xml(parser, canteen)
        except Exception as e:
            print(e)
            errors.append(e)

    if errors:
        raise errors[0]


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
