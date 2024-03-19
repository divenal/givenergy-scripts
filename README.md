Some simple scripts using the givenergy api. Not terribly idiomatic since python isn't really my first choice of language, but it seems to be popular, and has a rich standard library.

Needs the addon `requests` package - on a debian system, package python3-requests or get it from pip. Note that on my raspberry pi, the debian is old, and the requests package is a bit outdated. I ought to embrace `venv` and install a non-debian version for use with this script. For now, I use a deprecated way to do the retries.

What I should really do is make an abstraction so that you can choose to either use the api or a direct connection via givenergy-modbus.

*Note* that these are very much as-is, and are tailored for my system. I hope they are of use to others, but at the very least, you'll need to check that the numbers for the settings match your system - I don't know if they vary between different revisions of the hardware. Invoking `givenergy.py` with no parameters should list all the settings available on your system.

## My setup

### Background

A background on how I use my system might explain some of the rational...

I have 6.4kWp SSW solar feeding 5kW hybrid-gen3 inverter and 9.5kWh battery (daytime consumption probably down at the 6kWh level).

Tariff is IOG (cheap period 2330 to 0530, with random bonus hours). I tend to ask for car to be ready by 7am (alarm clock time), as a compromise between constraining Octopus to finish charge too early, and extra slots interfering with planning. Inverter can see Zappi chargepoint, which means I need to take steps to avoid battery discharging into car. Current scheme is simply to reduce discharge power to be enough to meet base load, but if the car decides to charge in a bonus slot, it will take some, but not very much, from the battery.

I don't start the battery charge until after midnight, and therefore pause discharge from 2330 until start of charging. This is simply for accounting purposes - it's convenient for all the charging to happen within one day, rather than having it happen at the end of one day for use the next day.

When forcing charge/discharge, I try to do it at lower power for longer, when possible, in the belief that this is better for battery health. (Would be nice if you could store a power with each discharge slot, rather than having to keep swapping between max (when in dynamic mode) and around 1.5kW when doing a forced discharge.

Because export is a generous 15p, I inhibit charging battery from solar during the day, just exporting everything. However, since clipping is a potential issue at peak generation, I want to be able to divert some power to the battery around noon.

Tend to cook main meal around 1830, and from 2000 we don't use very much, so start dumping excess to grid. I might also add an extra rule to dump between 4pm and 5pm if there's a lot of charge in the battery at 4pm. More useful to the grid at this time, though don't want to impact savings sessions rewards (makes it a bit of a negative consequence of savings sessions).

### Bugs to workaround

To cope with clipping, using priority of grid should have been the mode I want, but that doesn't seem to work at all. So I'm using the timed pause feature to inhibit solar charging. I want to unpause the pause around noon, with max charging power of around 1kW. There's only one pause timer, so I move it back and forth between morning and afternoon to emulate two.

A bit of an anomaly in the AC charging limit: there are (at least) two different settings available via the API: #77 and #101. Unfortunately, #101 seems to be the one that the inverter actually uses, but #77 is the one the app sets. Because it's quite convenient to set via the app, my scripts copy from #77 to #101 in the evening.


The accumulating meter data for battery in/out seem broken, and daily meter resets at midnight, which is one of the reasons for not starting the batterty charge until after midnight.

To inhibit discharge between 2330 and 0000 (when car might be charging), I abuse the discharge timers slightly: by arranging a timed discharge, but setting a min SoC of 100%, it actually results in a timed pause. Unfortunately, there appears to be a bug in that if the time window crosses midnight, it doesn't honour the discharge limit. So I have to use two discharge slots. But that's fine - there are ten available. It seems to take at least a minute at the end of a timed discharge to return to normal behaviour, so that avoids having a gap. AC charge seems to take precendence over DC discharge, so I can overlap the timers.

### Summary

So to summarise:
* 0030 to 0529 - charging from grid, discharge power 250W, charging power calculated
* 0530 to 0700 - dynamic mode, discharge power set to 250W, charge power set to 1kW
* 0700 to 1200 - dynamic mode, max discharge power, battery-charging paused
* 1200 to 1400 - dynamic mode, max discharge power, battery-charging allowed
* 1400 to 2000 - dynamic mode, max discharge power, battery-charging paused
* 2000 to 2230 - scheduled discharge, power calculated to end with 10%
* 2230 to 2330 - dynamic
* 2330 to 0035 - discharge paused (via discharge slot #2/3 with min SoC 100%)

#### Static configuration
* charge timer 1 0001 to 0529 - variable charge power depending on what is required to reach target SoC
* discharge timer 1 typically runs from 2000 to 2230 - again, variable power aiming for 15% by 2230
* discharge timer 2 bodged to inhibit discharge between 2330 and 2359 (prevent discharge to car)
* discharge timer 3 bodged to inhibit discharge between 0000 and 0035 (prevent discharge to car)
* pause mode set to pause-charge
* discharge mode set to scheduled - home demand. (ie eco + dc discharge enabled)

#### Dynamic stuff implemented by these scripts, via cron
* move pause time between two configs: 0700 to 1300, and 1530 to 1830, as required
* around 2330, calculate charging power required, and reduce discharge power
* around 0700, restore discharge power to max, and charge power to around 1kW.
* around 2000, decide whether to dump to grid, and adjust discharge power and/or ending time.

# Configuration
The scripts expect to find a config file in `~/.solar`  - this is in a format for configparser.
There needs to be a `[givenergy]` section with
 - `inverter` setting (identify the inverter) and a
 - `api_token` setting, which is an api token granting full inverter control.

For the pvoutput script, you need a `[pvoutput]` with
 - `name` name of your system
 - `ìd` numerical id
 - `key` access key

# Scripts
The scripts are in bin/

## givenergy.py
They share a utility file `givenergy.py` which implements the API via the `requests` package. It auto-retries on failure. When invoked as a script, it retrieves and prints the presets and settings available for your inverter.

## givenergy-offpeak.py
`givenergy-offpeak.py` runs from cron just before and after the off-peak period. With parameter `before` it sets up for overnight mode, which means setting charge rate to reach the (already set) target % SoC  over the full 6 hours. With `after` it restores daytime settings. You'll need to tweak the hard-coded constants to match your system.

There's some constants at the top to define the numerical registers for the api settings. You should check to make sure they're the same for your system. (Invoke `givenergy.py` as a script to list the avaiable register numbers.)

## givenergy-pause-times.py
`givenergy-pause-times.py` runs from cron to update pause-battery times (since I want more than one per day, but only one slot is provided).

## givenergy-discharge.py
`givenergy-discharge.py` runs from cron at 8pm (after we've cooked main meal). If there's lots of juice left in the battery, it sets up to dump some to the grid.

## pvoutput.py
`pvoutput.py` runs once per day, via cron. It downloads the day's parameters, and uploads to pvoutput.

