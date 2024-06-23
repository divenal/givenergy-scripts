Some simple scripts using the givenergy api. Not terribly idiomatic since python isn't really my first choice of language, but it seems to be popular, and has a rich standard library (and it's growing on me).

Needs the addon `requests` package - on a debian system, package python3-requests or get it from pip.

What I should really do is make an abstraction so that you can choose to either use the api or a direct connection via givenergy-modbus, with the same interface.

*Note* that these are very much as-is, and are tailored for my system. I hope they are of use to others, but at the very least, you'll need to check that the numbers for the settings match your system - I don't know if they vary between different revisions of the hardware. Invoking `givenergy.py` with no parameters should list all the settings available on your system.

Things are in a bit of flux right now, since I use both these scripts and a modbus-based monitor which dynamically responds to solar (portal's 5-minute updates are a bit slow for that). Use the git history to see previous versions of this README, to see how things have evolved over time.

The simple rule is that during the time defined by the inverter's pause timer (typically 0530 to 19:55), the modbus script is in charge. Outside those times, it does very little and the scripts make decisions at scheduled times. The modbus script could do everything, but I want to keep that script simple and focused on its main job, which is clipping-avoidance (and not crashing).

## My setup

### Background

A background on how I use my system might explain some of the rational...

I have 6.4kWp SSW solar feeding 5kW hybrid-gen3 inverter and 9.5kWh battery (daytime consumption probably down at the 6kWh level).

Tariff is IOG. The inverter does not see the chargepoint, so I don't have to worry about it discharging into the car when it's charging. But do have to avoid exporting when the car is charging, since the car will take it instead of importing from the grid. Charging is normally finished during normal cheap rate, but sometimes as late as 7am weekday, and 10am at the weekend.

Because export is a generous 15p, I inhibit charging battery from solar during the day, just exporting everything. A separate modbus-based monitor handles clipping-avoidance.

I don't start the battery charge until after midnight, and therefore pause discharge from 2330 until start of charging. This is mainly for accounting purposes - it's convenient for all the charging to happen within one day, rather than having it happen at the end of one day for use the next day. But also, it seems rebalancing happens at low voltages if the battery is left idle, so it's now getting an hour to idle before charging.

When forcing charge/discharge, I try to do it at lower power for longer, when possible, in the belief that this is better for battery health. (Would be nice if you could store a power with each discharge slot, rather than having to keep swapping between max (when in dynamic mode) and around 1.5kW when doing a forced discharge.

Tend to cook main meal around 1830, and from 2000 we don't use very much, so start dumping excess to grid. I might also add an extra rule to dump between 4pm and 5pm if there's a lot of charge in the battery at 4pm. More useful to the grid at this time, though don't want to impact savings sessions rewards (makes it a bit of a negative consequence of savings sessions).

A rpi is running 24/7 anyway (doing other stuff), and so it's easy enough to add these to its relatively small workload.

### Bugs to workaround

A bit of an anomaly in the AC charging limit: there are (at least) two different settings available via the API: #77 and #101. (The former is a generic one, the latter is specific for charging slot #1.) Unfortunately, #101 seems to be the one that the inverter actually uses, but #77 is the one the app sets. Because it's quite convenient to set via the app, my scripts copy from #77 to #101 in the evening.

The accumulating meter data for battery in/out seem broken, and daily meter resets at midnight, which is one of the reasons for not starting the batterty charge until after midnight.

To idle the battery between 2330 and 0030 (since may as well run from cheap grid rate), I abuse the discharge timers slightly: by arranging a timed discharge, but setting a min SoC of 100%, it actually results in a timed pause. Unfortunately, there appears to be a bug in that if the time window crosses midnight, it doesn't honour the discharge limit. (Possibly fixed in latest firmware.) So I have to use two discharge slots. But that's fine - there are ten available. It seems to take at least a minute at the end of a timed discharge to return to normal behaviour, so that avoids having a gap. AC charge seems to take precendence over DC discharge, so I can overlap the timers.


### Modbus script

I want to export as much solar as possible directly. But when power exceeds the 5kW AC limit, I need to divert some to the battery, else I get clipping. There's basically two ways to do this:
 - operate a battery-first policy, and actively manage the max charging power so that just enough goes to the battery to keep AC close to 5kW.
 - operate a grid-first policy, so that the inverter automatically sends excess to the battery.

Unfortunately, option 2 does't seem to be implemented directly. But it turns out that turning off eco mode does have that side effect. But of course it has other desirable side effects, such as losing dynamic discharge to match consumption.

First version of the script used the first approach. I'm now trying the second approach, which should require fewer adjustments. But it still requires closer monitoring of the state than is practical using the API, hence use of a direct connection to the inverter using modbus.

- When solar is low, eco mode is on, and battery-charging is paused
- When solar is high, eco mode is off, and battery-charging is unpaused.

The modbus script is also allowed to force-export when it detects that battery level is relatively high. The rule there is that it's only allowed to do that within the time period defined by discharge-timer-slot#2 (and the pause timer), and it simply turns the timed-export flag on and off as required.

One final job of the script: when I force an export, I tend to do it at less than max power. But when I'm in normal dynamic discharge mode, I want full discharge power to be available. So the script automatically detects when we are not exporting, and sets power to max.

The current, rather ad-hoc, rule, is that during the time window defined by the pause timer, the modbus script is in charge. Otherwise, it limits its activity. (By having the script configured using inverter timers, it saves having to try to send it messages by some other means while it's running. I can communicate it, rather crudely, through these timers.)


### Summary

So to summarise:
* 0030 to 0529 - charging from grid, charging power calculated
* 0530 to X    - dynamic (with solar charging) if car is charging
*    X to 1955 - pause timer is active, modbus script drives things
* 2000 to 2230 - scheduled discharge, power calculated to end with 8%
* 2230 to 2330 - normal eco mode
* 2330 to 0035 - discharge paused (via discharge slot #2/3 with min SoC 100%)

X is dynamically set based on car-charging activity. It's usually 0530, but if the car is charging beyond the normal cheap hours, X is increased until the end of car charging. (This is the mechanism by which the modbus script doesn't get involved while car is charging.) Because the pause timer is not active, the battery charges from solar.

#### Static configuration
* charge timer 1 0030 to 0529 - variable charge power depending on what is required to reach target SoC
* discharge timer 1 typically runs from 2000 to 2230
* discharge timer 2 reserved for use by the modbus script, typically 0800 to 1810 with a discharge limit of 30%
* discharge timers 3 and 4 run from 23:30 to 00:30 with a discharge limit 100%, to implement a paused-discharge (prvent discharge during cheap rate)
* pause timer 0530 to 1955 (with pause mode adjusted dynamically by modbus script)

Note that timer-2 should end before the pause timer (to give the modbus script a chance to turn off forced discharge while it is still in charge).

#### Dynamic stuff implemented by these scripts, via cron
* around 2330, run givenergy-offpeak.py to calculate charging power required, and reduce discharge power, disable timed export flag
* around 0500, run givenergy-iog.py to check whether car is charging, and set pause start time
* around 2000, run givenergy-discharge.py to decide whether to dump to grid, and adjust discharge power and/or ending time.

#### Dynamic stuff implemented via modbus script
Use discharge limit on timer 2 to export as required (by turning enable-dc-discharge on and off). The discharge limit is both config for the script and an emergency brake: the script should initiate a discharge if SoC >= (limit+10%), and stop when it gets down to (limit+5%). So it shouldn't actually get down to the limit itself, unless the script has crashed.

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
