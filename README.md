Some simple scripts using the givenergy api. Not terribly idiomatic since python isn't really my first choice of language, but it seems to be popular, and has a rich standard library.

Needs the addon `requests` package - on a debian system, package python3-requests or get it from pip. Note that on my raspberry pi, the debian is old, and the requests package is a bit outdated. I ought to embrace `venv` and install a non-debian version for use with this script. For now, I use a deprecated way to do the retries.

What I should really do is make an abstraction so that you can choose to either use the api or a direct connection via givenergy-modbus.

# scripts
The scripts are in bin/

## givenergy.py
They share a utility file `givenergy.py` which implements the API via the `requests` package. It auto-retries on failure. When invoked as a script, it retrieves and prints the presets and settings available for your inverter.

## givenergy-offpeak.py
`givenergy-offpeak.py` runs from cron just before and after the off-peak period. With parameter `before` it sets up for overnight mode, which means setting charge rate to reach the (already set) target % SoC  over the full 6 hours. With `after` it restores daytime settings. You'll need to tweak the hard-coded constants to match your system.

There's some constants at the top to define the numerical registers for the api settings. You should check to make sure they're the same for your system. (Invoke `givenergy.py` as a script to list the avaiable register numbers.)

## givenergy-pause-times.py
`givenergy-pause-times.py` runs from cron to update pause-battery times (since I want more than one per day, but only one slot is provided).

## pvoutput.py
`pvoutput.py` runs once per day, via cron. It downloads the day's parameters, and uploads to pvoutput.

# Configuration
The scripts expect to find a config file in `~/.solar`  - this is in a format for configparser.
There needs to be a `[givenergy]` section with
 - `inverter` setting (identify the inverter) and a
 - `control` setting, which is an api token granting full inveter control. 

For the pvoutput script, you need a `[pvoutput]` with
 - `name` name of your system
 - `ìd` numerical id
 - `key` access key
