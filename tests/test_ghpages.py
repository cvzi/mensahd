import sys
import os
import logging
import lxml.etree
import defusedxml.lxml
import urllib.request
import json

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


def test_all_files():
    GHPAGES = 'docs/'
    FEEDS = 'feed/'
    TODAYS = 'today/'
    METAS = 'meta/'

    ghpagesPath = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', GHPAGES))
    print(f"Checking files in {ghpagesPath}")
    errors = []

    for filename in sorted(os.listdir(ghpagesPath)):
        if not filename.endswith(".json"):
            continue
        print(filename, end="", flush=True)
        path = os.path.join(ghpagesPath, filename)
        try:
            with open(path, 'r', encoding='utf8') as f:
                data = json.load(f)
            for value in data.values():
                assert value.startswith("https://")
                assert value.endswith(".xml")
            print(f" -> {greenOk}.")

        except Exception as e:
            print(f" {redVT}Error:\n%r{endVT}\n" % (e, ), end="", flush=True)
            errors.append(e)

    if os.path.isdir(os.path.join(ghpagesPath, METAS)):
        for filename in sorted(os.listdir(os.path.join(ghpagesPath, METAS))):
            prettyName = f"{METAS}{filename}"
            print(prettyName, end="", flush=True)
            path = os.path.join(ghpagesPath, METAS, filename)
            try:
                with open(path, 'r', encoding='utf8') as f:
                    check_meta(f.read(), name=prettyName)
            except Exception as e:
                print(f" {redVT}Error:\n%r{endVT}\n" %
                      (e, ), end="", flush=True)
                errors.append(e)

    if os.path.isdir(os.path.join(ghpagesPath, TODAYS)):
        for filename in sorted(os.listdir(os.path.join(ghpagesPath, TODAYS))):
            prettyName = f"{TODAYS}{filename}"
            print(prettyName, end="", flush=True)
            path = os.path.join(ghpagesPath, TODAYS, filename)
            try:
                with open(path, 'r', encoding='utf8') as f:
                    check_feed(f.read(), encoding='utf8', name=prettyName)
            except Exception as e:
                print(f" {redVT}Error:\n%r{endVT}\n" %
                      (e, ), end="", flush=True)
                errors.append(e)
    if os.path.isdir(os.path.join(ghpagesPath, FEEDS)):
        for filename in sorted(os.listdir(os.path.join(ghpagesPath, FEEDS))):
            prettyName = f"{FEEDS}{filename}"
            print(prettyName, end="", flush=True)
            path = os.path.join(ghpagesPath, FEEDS, filename)
            try:
                with open(path, 'r', encoding='utf8') as f:
                    check_feed(f.read(), encoding='utf8', name=prettyName)
            except Exception as e:
                print(f" {redVT}Error:\n%r{endVT}\n" %
                      (e, ), end="", flush=True)
                errors.append(e)

    if errors:
        print("--------- First error: ----------------", file=sys.stderr)
        raise errors[0]


def run_all():
    for fname, f in list(globals().items()):
        if fname.startswith('test_'):
            print(f"{fname}()...")
            f()
            print(f"...{fname}() -> {greenOk}.")


if __name__ == '__main__':
    # logging.basicConfig(level=logging.DEBUG)
    logging.basicConfig(level=logging.WARNING)
    run_all()
