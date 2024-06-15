#!/usr/bin/env python3

"""
Wrapper around requests for the GivEnergy API.
implements connection pooling and retries
"""

import configparser
import os
import time
import sys
from datetime import datetime
from requests import Session
from requests.adapters import HTTPAdapter, Retry

DISCHARGE_START=53
DISCHARGE_END=54
CHARGE_POWER=72
DISCHARGE_POWER=73
CHARGE_LIMIT=77     # the one set by app
PAUSE_MODE=96
CHARGE_LIMIT_1=101  # the one actually used by the inverter
PAUSE_START=155
PAUSE_END=156

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
        retries = Retry(total=10, backoff_factor=5, allowed_methods=None)
        #retries = Retry(total=10, backoff_factor=5, method_whitelist=frozenset(['HEAD', 'TRACE', 'GET', 'PUT', 'OPTIONS', 'DELETE']))
        session.mount(self.url, HTTPAdapter(max_retries=retries))
        self.session = session

        self.latest = None  # cache of system data

        # doesn't really belong here, but since I have
        # most scripts redirecting stdout to a logfile,
        # it is useful.
        # Perhaps add a log() fn which prefixes this ?
        now = datetime.now()
        print(context, now.strftime(': %Y-%m-%d %H:%M:%S'))

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
        delay = 2
        for attempt in range(10):
            json = self.post(f"/settings/{reg!s}/read")
            value = json['value']
            # errors are returned as a -ve integer.
            # Which is a bit inconvenient since a successful
            # read might give a string rather than an integer.
            if not isinstance(value, int) or value >= 0:
                return value
            print(f'read {reg} got {value}: retrying')
            time.sleep(delay)
            delay = delay * 2
        raise IOError('too many attempts to read setting')

    def modify_setting(self, reg, value):
        """write a register via the api"""
        delay = 2
        for attempt in range(10):
            json = self.post(f"/settings/{reg!s}/write", value=value)
            print(f"modify {reg}: value: {json['value']}, success: {json['success']}, message: {json['message']}")
            if json['success'] is True:
                return
            time.sleep(delay)
            delay = delay * 2
        raise IOError('too many attempts to modify setting')

def main():
    """If invoked as a script with no parameters, fetch the list of presets and settings available.
    Else each param is a setting to be either displayed or modified. eg
      cp=250 cl
    will set charge_power and display charge_limit"""

    api = GivEnergyApi()

    names = { 'cp': CHARGE_POWER,
              'dp': DISCHARGE_POWER,
              'ds': DISCHARGE_START,
              'de': DISCHARGE_END,
              'cl': CHARGE_LIMIT,
              'pt': PAUSE_MODE,
              'ps': PAUSE_START,
              'pe': PAUSE_END }

    if len(sys.argv) > 1:
        # each arg is a setting to be either displayed or (if followed by =val) modified.
        for arg in [x.split('=', 1) for x in sys.argv[1:]]:
            s = arg[0]
            if s in names: s=names[s]
            if len(arg) == 1:
                # just retrieve the setting
                val = api.read_setting(s)
                print(s, val)
            else:
                # set the value
                api.modify_setting(s, arg[1])
    else:
        # just display the available settings
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
