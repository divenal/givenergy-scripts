#!/usr/bin/env python3
import configparser
import os
import requests,json
from datetime import date, datetime,timezone,timedelta
from requests.models import HTTPError
from zoneinfo import ZoneInfo
from operator import itemgetter

class IOG:
    """Access to Octopus GraphQL interface for IO charging slots"""
    
    url = "https://api.octopus.energy/v1/graphql/"

    def __init__(self, config=None):
        if config is None:
            config = configparser.ConfigParser()
            config.read(os.path.join(os.environ.get('HOME'), '.solar'))

        self.key = config['octopus']['key']
        self.acct = config['octopus']['account']

    def refreshToken(self):
        try:
            query = """
            mutation krakenTokenAuthentication($api: String!) {
            obtainKrakenToken(input: {APIKey: $api}) {
                token
            }
            }
            """
            variables = {'api': self.key}
            r = requests.post(self.url, json={'query': query , 'variables': variables})
            jsonResponse = json.loads(r.text)
            return jsonResponse['data']['obtainKrakenToken']['token']
        except HTTPError as http_err:
            print(f'HTTP Error {http_err}')
        except Exception as err:
            print(f'Another error occurred: {err}')


    def getDispatches(self, token):
        try:
            query = """
                query getData($input: String!) {
                    plannedDispatches(accountNumber: $input) {
                        start
                        end
                        delta
                    }
                    completedDispatches(accountNumber: $input) {
                        start
                        end
                        delta
                    }
                }
            """
            variables = {'input': self.acct}
            headers={"Authorization": token}
            r = requests.post(self.url, json={'query': query , 'variables': variables, 'operationName': 'getData'},headers=headers)
            return json.loads(r.text)['data']
        except HTTPError as http_err:
            print(f'HTTP Error {http_err}')
        except Exception as err:
            print(f'Another error occurred: {err}')


    @staticmethod
    def getChargingSlots(config = None):
        """Return an ordered array of 4-tuples (start, end, delta, completed).

        start and end are datetimes
        delta is the energy in kWh
        completed is True or False
        """
        
        iog = IOG(config);
        authToken = iog.refreshToken()
        dispatches = iog.getDispatches(authToken)
        zone = ZoneInfo('Europe/London')
        results = []
        completed=False
        for t in ('planned', 'completed'):
            for d in dispatches[t + 'Dispatches']:
                start = datetime.fromisoformat(d['start']).astimezone(zone)
                end = datetime.fromisoformat(d['end']).astimezone(zone)
                # delta is -ve for charging, so just chop off first character
                delta = d['delta'][1:]
                results.append( (start, end, delta, completed) )
            completed = True

        results.sort(key=itemgetter(1))  # sort by end-time
        return results




if __name__ == "__main__":
    slots = IOG.getChargingSlots()
    for x in slots:
        print(x[0], x[1], x[2], x[3])
