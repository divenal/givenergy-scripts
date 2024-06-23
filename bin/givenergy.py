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

ECO_MODE=24
DISCHARGE_START=53
DISCHARGE_END=54
ENABLE_DC_DISCHARGE=56
CHARGE_POWER=72
DISCHARGE_POWER=73
CHARGE_LIMIT=77     # the one set by app
PAUSE_MODE=96       # 0-3
CHARGE_LIMIT_1=101  # the one actually used by the inverter
PAUSE_START=155
PAUSE_END=156

DISCHARGE_START_n= (53, 41,131,134,137,140,143,146,149,152)
DISCHARGE_END_n=   (54, 42,132,135,138,141,144,147,150,153)
DISCHARGE_LIMIT_n=(129,130,133,136,139,142,145,148,151,154)


#
# Config is read from ~/.solar - expects a [givenergy] section, which includes
# 'inverter' id and 'control' with (at least) full api:inverter access

# Will load whatever else is there and make it available via config field
# (currently a [pvoutput] section)

class GivEnergyApi:
    """A wrapper around requests for GivEnergy api"""

    def __init__(self, context="givenergy.py", config=None):
        if config is None:
            config = configparser.ConfigParser()
            config.read(os.path.join(os.environ.get('HOME'), '.solar'))

        self.config = config
        self.context = context
        self.url = "https://api.givenergy.cloud/v1/inverter/" + config['givenergy']['inverter']

        session = Session()
        session.headers.update({'Authorization': 'Bearer ' + config['givenergy']['api_token'],
                                'Content-Type': 'application/json',
                                'Accept': 'application/json'})
        retries = Retry(total=10, backoff_factor=5, allowed_methods=None)  # None means all
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
              'cl': CHARGE_LIMIT,
              'pt': PAUSE_MODE,
              'ps': PAUSE_START,
              'pe': PAUSE_END,
              'ds': DISCHARGE_START,
              'de': DISCHARGE_END,
              'ed': ENABLE_DC_DISCHARGE,
              'eco': ECO_MODE,
              }

    # add numbered discharge slots
    for idx in range(1,11):
        names[f'ds{idx}'] = DISCHARGE_START_n[idx-1]
        names[f'de{idx}'] = DISCHARGE_END_n[idx-1]
        names[f'dl{idx}'] = DISCHARGE_LIMIT_n[idx-1]

    if len(sys.argv) > 1:
        # each arg is a setting to be either displayed or (if followed by =val) modified.
        for arg in (x.split('=', 1) for x in sys.argv[1:]):
            s = arg[0]
            if s in names:
                s = names[s]
            else:
                s = int(s)
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
