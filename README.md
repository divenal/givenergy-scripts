Some simple scripts using the givenergy api. Not terribly idiomatic since python isn't really my first choice of language, but it seems to be popular, and has a rich standard library (and it's growing on me).

Needs the addon `requests` package - on a debian system, package python3-requests or get it from pip.

What I should really do is make an abstraction so that you can choose to either use the api or a direct connection via givenergy-modbus, with the same interface.

*Note* that these are very much as-is, and are tailored for my system. I hope they are of use to others, but at the very least, you'll need to check that the numbers for the settings match your system - I don't know if they vary between different revisions of the hardware. Invoking `givenergy.py` with no parameters should list all the settings available on your system.

Things are in a bit of flux right now, since I use both these scripts and a modbus-based monitor which dynamically responds to solar (portal's 5-minute updates are a bit slow for that). Use the git history to see previous versions of this README, to see how things have evolved over time.

The simple rule is that during the time defined by the inverter's pause timer (typically 0530 to 19:55), the modbus script is in charge. Outside those times, it does very little and the scripts make decisions at scheduled times. The modbus script could do everything, but I want to keep that script simple and focused on its main job, which is clipping-avoidance (and not crashing).

For details of my setup, see [my setup](setup.md) or [modbus script](modbus.md)


# Configuration
The scripts expect to find a config file in `~/.solar`  - this is in a format for configparser.
There needs to be a `[givenergy]` section with
 - `inverter` setting (identify the inverter) and a
 - `api_token` setting, which is an api token granting full inverter control.

For the pvoutput script, you need a `[pvoutput]` with
 - `name` name of your system
 - `ìd` numerical id
 - `key` access key

For IO integration, you need an `[octopus]` section with
 - `key` api key
 - `account` Octopus account number

For Zappi integration, you need a `[myenergi]` section, with
 - `hub`  serial number ?
 - `zappi`  serial number ?
 - `key` security key

# Scripts
The scripts are in bin/

## givenergy.py
They share a utility file `givenergy.py` which implements the API via the `requests` package. It auto-retries on failure.
Has some configuration at the top of the file giving settings numbers, which may need to be adjusted to match your inverter.

When invoked as a script with no parameters, it retrieves and prints the presets and settings available for your inverter.
Parameters can also be given: these can either be the numbers or short names of settings to retrieve and display, or in the form setting=value, will modify a setting. Available names include 'cp' and 'dp' for charge/discharge power, 'ps' and 'pe' for pause start and ends, 'pt' for pause mode, 'ed' for enable discharge, 'eco' for eco flag,  Check the source for others.  (All rather ad-hoc.)

## octopus.py
This provides a simple interface to get hold of charging slots

## givenergy-offpeak.py
`givenergy-offpeak.py` runs from cron just before the off-peak period and sets charge rate to reach the (already set) target % SoC  over 5 hours.

## givenergy-discharge.py
`givenergy-discharge.py` runs from cron at 8pm (after we've cooked main meal). If there's lots of juice left in the battery, it sets up to dump some to the grid.

## givenergy-iog.py
`givenergy-iog.py` uses the `octopus.py` module to get charging slots, then sets the givenergy pause-start to be the later of 05:30 and the end of the last charging slot (if any).

## pvoutput.py
`pvoutput.py` runs once per day, via cron. It downloads the day's parameters, and uploads to pvoutput.


# monitor.py / mon2.py

This is the modbus script I use for clipping-avoidance. Very much still work in progress (partly because modbus itself is still work in progress).
It probably uses the latest 'dev' branch at https://github.com/divenal/givenergy-modbus-async
