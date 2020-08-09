"""
List all canteens supported by the API at https://studiplus.stw-ma.de/
"""

import os
import requests
from pprint import pprint

authorization = False
if os.path.isfile(os.path.join(os.path.dirname(__file__), '.password.txt')):
    with open(os.path.join(os.path.dirname(__file__), '.password.txt')) as af:
        authorization = af.read()
else:
    authorization = os.getenv('MANNHEIM_AUTH')

if not authorization:
    raise RuntimeError("Authentication data not found")


url = 'https://studiplus.stw-ma.de/api/app/mensas'

headers = {
    'User-Agent': 'github.com/cvzi/mensahd python-requests',
    'Accept': 'application/json',
    'Accept-Language': 'de-De,de',
    'X-App-Token': authorization
}

r = requests.get(url, headers=headers)

data = r.json()

pprint(data)
