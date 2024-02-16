"""
Wrapper around requests for the GivEnergy API.
implements connection pooling and retries
"""

import os
import configparser
from requests import Session
from requests.adapters import HTTPAdapter, Retry

#
# Config is read from ~/.solar - expects a [givenergy] section, which includes
# 'inverter' id and 'control' with (at least) full api:inverter access

# Will load whatever else is there and make it available via config field
# (currently a [pvoutput] section)

class GivEnergyApi:
    """A wrapper around requests for GivEnergy api"""

    def __init__(self, context="givenergy.py"):
        config = configparser.ConfigParser()
        config.read(os.path.join(os.environ.get('HOME'), '.solar'))

        self.config = config
        self.context = context
        self.url = "https://api.givenergy.cloud/v1/inverter/" + config['givenergy']['inverter']

        session = Session()
        session.headers.update({'Authorization': 'Bearer ' + config['givenergy']['api_token'],
                                'Content-Type': 'application/json',
                                'Accept': 'application/json'})
        #allowed_methods not yet on the version on maple
        #retries = Retry(total=10, backoff_factor=5, allowed_methods=None)
        retries = Retry(total=10, backoff_factor=5, method_whitelist=frozenset(['HEAD', 'TRACE', 'GET', 'PUT', 'OPTIONS', 'DELETE']))
        session.mount(self.url, HTTPAdapter(max_retries=retries))
        self.session = session

        self.latest = None  # cache of system data


    # low-level stuff

    def get(self, url):
        """perform a GET operation on the api"""
        response = self.session.request('GET', self.url + url)
        response.raise_for_status()
        return response.json()['data']

    def post(self, url, payload=None, value=None):
        """perform a POST operation on the api"""
        if payload is None:
            payload={ 'context': self.context }
        if value is not None:
            payload['value'] = str(value)
        response = self.session.request('POST', self.url + url, json=payload)
        response.raise_for_status()
        # TODO: perhaps look for the 'remote control codes' (offline, timeout, etc)
        # Or does that come back as http code 400 ?
        return response.json()['data']

    # higher level stuff

    def get_latest_system_data(self):
        """fetch /system-data/latest as a dictionary. Cached between calls."""
        if not self.latest:
            self.latest = self.get("/system-data/latest")
        return self.latest

    def read_setting(self, reg):
        """read a register via the api"""
        json = self.post(f"/settings/{reg!s}/read")
        return json['value']

    def modify_setting(self, reg, value):
        """write a register via the api"""
        json = self.post(f"/settings/{reg!s}/write", value=value)
        print(f"modify {reg}: value: {json['value']}, success: {json['success']}, message: {json['message']}")


def main():
    """If invoked as a script, fetch the list of presets and settings available."""
    api = GivEnergyApi()

    presets = api.get("/presets")
    print('presets:')
    for p in presets:
        print("{:3d} {:40s} : {:s}".format(p['id'], p['name'], p['description']))
    settings = api.get("/settings")
    print('\nsettings:')
    for s in settings:
        print("{:3d} {:40s} : {:s}".format(s['id'], s['name'], s['validation']))

if __name__ == "__main__":
    main()