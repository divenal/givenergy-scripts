#!/usr/bin/env python3

"""
A simple script to run after sundown, to download
the day's data and upload it to pvoutput.org
"""

# TODO: would be nice to distinguish off-peak and peak-rate
# import - just need to use the datapoints version and pick
# out the transition points.

import sys
import requests
from givenergy import GivEnergyApi

def upload(config, day, solar, export):
    """upload the results to pvoutput.org"""
    url='https://pvoutput.org/service/r2/addoutput.jsp'

    headers = {
        'X-Pvoutput-Apikey': config['key'],
        'X-Pvoutput-SystemId': config['id']
    }
    payload={
        'd': day,
        'g': int(solar*1000),
        'e': int(export*1000)
    }
    #print(url, headers, payload)
    response = requests.request('POST', url, headers=headers, data=payload)
    response.raise_for_status()
    # print(response, response.text)

def main():
    api = GivEnergyApi('pvoutput')

    if len(sys.argv) > 1:
        # bit sloppy - get all the data and pick out just
        # the last one
        day = sys.argv[1]
        data = api.get(f'/data-points/{day}?pageSize=4096')
        today = data[-1]['today']
    else:
        # just use the latest meter data, and we can get
        # the date from that
        # TODO: will it always be UTC ?
        data = api.get('/meter-data/latest')
        today = data['today']
        time = data['time']  # yyyy-mm-ddThh:mm:ssZ
        day = time[0:4] + time[5:7] + time[8:10]

    solar = float(today['solar'])
    export = float(today['grid']['export'])
    print(day, solar, export)

    upload(api.config['pvoutput'], day, solar, export)

if __name__ == "__main__":
    main()
