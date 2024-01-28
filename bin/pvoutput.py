#!/usr/bin/python3

# a simple script to run after sundown, to sum up
# the day's data and upload it to pvoutput.org
# TODO: probably easier to just use the meter-data, though
# would be good to extend this to also include the peak export,
# and distinguish off-peak and peak-rate grid import.

import os
import sys
from givenergy import GivEnergyApi
from datetime import date, timedelta
import time
import requests
# import json

def get_solar(api, day):
    # connect to the givenergy api and request the days data
    # It doesn't include any data for current day, so grab
    # the half-hourly data and sum it up
    # Returns a tuple [ generated, exported ]
    
    payload = {
        'start_time': str(day),
        'end_time'  : str(day + timedelta(days=1)),
        'grouping'  : 0,  #  half-hourly
        'types': [
            0,  # PV to home
            1,  # PV to battery
            2,  # PV to grid
        ],
        'context': 'pvoutput'
    }

    data = api.post('/energy-flows', payload=payload )

    # Now go through and sum up the various contributions
    generated=0.0
    exported=0.0
    for result in data.values():
        data = result['data']
        home = float(data['0'])
        battery = float(data['1'])
        grid = float(data['2'])
        generated += home + battery + grid
        exported += grid
    return [generated, exported]

def upload(config, day, solar):
    # upload the results to pvoutput.org
    url='https://pvoutput.org/service/r2/addoutput.jsp'
    
    headers = {
        'X-Pvoutput-Apikey': config['key'],
        'X-Pvoutput-SystemId': config['id']
    }
    payload={
        'd': day.strftime('%Y%m%d'),
        'g': int(solar[0]*1000),
        'e': int(solar[1]*1000)
    }
    #print(url, headers, payload)
    response = requests.request('POST', url, headers=headers, data=payload)
    response.raise_for_status()
    #print(response, response.text)

def main():
    api = GivEnergyApi('pvoutput')
    if len(sys.argv) > 1:
        day=date.fromisoformat(sys.argv[1])
    else:
        now = time.time()
        day=date.fromtimestamp(now)
    solar = get_solar(api, day)
    print(solar)
    upload(api.config['pvoutput'], day, solar)

main()
