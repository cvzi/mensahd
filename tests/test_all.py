import sys
import os
import logging
import lxml.etree
import defusedxml.lxml
import urllib.request

include = os.path.relpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, include)

isPyIdle = "idlelib" in sys.modules
endVT = "" if isPyIdle else "\033[0m"
yellowVT = "" if isPyIdle else "\033[1;33m"
greenVT = "" if isPyIdle else "\033[1;32m"
redVT = "" if isPyIdle else "\033[1;31m"
greenOk = f"{greenVT}Ok{endVT}"


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
    print("Content", end="", flush=True)

    # Check syntax
    try:
        defusedxml.lxml.fromstring(content.encode('utf8'), xmlParser)
    except lxml.etree.XMLSyntaxError as error:
        raise RuntimeWarning(
            "Invalid document meta [%s]: %s" % (name, str(error)))

    # Content length
    if len(content) < 450:
        print(" -> Probably too short meta. [%s]" % (name, ), file=sys.stderr)
        return False
    else:
        print(f" -> {greenOk}.")
    return True


def check_feed(content, encoding='utf8', name=''):
    print("Content", end="", flush=True)

    # Check syntax
    try:
        source = content
        if not isinstance(source, bytes):
            source = content.encode(encoding)
        else:
            content = content.decode(encoding)

        defusedxml.lxml.fromstring(source, xmlParser)
    except lxml.etree.XMLSyntaxError as error:
        raise RuntimeWarning(f"Invalid document feed [{name}]: {error}")

    # Content length
    if len(content) < 300:
        # raise RuntimeWarning("[%s] probably empty feed." % (name,))
        print(f"{yellowVT}[{name}] probably empty feed.{endVT}")
        return False
    elif len(content) < 360:
        print(
            f" -> {yellowVT}Probably closed. [{name}]{endVT}", file=sys.stderr)
    else:
        print(f" -> {greenOk}.")

    # Count closed days:
    closed = content.count('<closed')
    if closed > 0:
        print(
            f"{yellowVT}Found closed days: {closed} [{name}]{endVT}", file=sys.stderr)

    return True


def check_xml(parser, canteen):
    name = "%s/%s" % (parser.__module__, canteen)
    print("Canteen: %s" % (name, ))

    print("meta()", end="", flush=True)
    content = parser.meta(canteen)
    print(f" -> {greenOk}.")
    print("meta() ", end="", flush=True)
    check_meta(content, name=name)

    has_feed = 0

    if hasattr(parser, "feed_today"):
        print("feed_today()", end="", flush=True)
        content = parser.feed_today(canteen)
        print(f" -> {greenOk}.")
        print("feed_today() ", end="", flush=True)
        check_feed(content, name=name)
        has_feed += 1

    if hasattr(parser, "feed_all"):
        print("feed_all()", end="", flush=True)
        content = parser.feed_all(canteen)
        print(f" -> {greenOk}.")
        print("feed_all() ", end="", flush=True)
        check_feed(content, name=name)
        has_feed += 1

    if hasattr(parser, "feed"):
        print("feed()", end="", flush=True)
        content = parser.feed(canteen)
        print(f" -> {greenOk}.")
        print("feed() ", end="", flush=True)
        check_feed(content, name=name)
        has_feed += 1

    if has_feed == 0:
        raise RuntimeWarning("No feeds found for [%s]." % (name, ))


def test_all_modules():
    moduleNames = ['eppelheim', 'heidelberg', 'mannheim', 'stuttgart', 'ulm']

    print("Importing %s" % (", ".join(moduleNames), ), end="", flush=True)

    modules = map(__import__, moduleNames)

    print(f" -> {greenOk}.")

    errors = []
    for mod in modules:
        try:
            print("Module: %s" % mod.__name__)

            parser = mod.getParser('http://localhost/')
            canteens = list(parser.canteens.keys())

            for canteen in canteens:
                check_xml(parser, canteen)
        except (KeyboardInterrupt, SystemExit) as e:
            raise e
        except Exception as e:
            print(f" {redVT}Error in {mod.__name__} ", end="")
            if canteen:
                print(f"{redVT}in canteen %r: {endVT}" % (canteen, ), end="")
            print("{redVT}%r{endVT}" % (e, ))
            errors.append(e)

    if errors:
        raise errors[0]


def one_module(name):
    print(f"Importing {name}", end="", flush=True)

    mod = __import__(name)

    print(f" -> {greenOk}.")

    parser = mod.getParser('http://localhost/')
    canteens = list(parser.canteens.keys())

    for canteen in canteens:
        check_xml(parser, canteen)


def run_all():
    for fname, f in list(globals().items()):
        if fname.startswith('test_'):
            print(f"{fname}()...")
            f()
            print(f"...{fname}() -> {greenOk}.")


if __name__ == '__main__':
    if len(sys.argv) == 2:
        logging.basicConfig(level=logging.DEBUG)
        one_module(sys.argv[1])
    else:
        logging.basicConfig(level=logging.WARNING)
        run_all()
