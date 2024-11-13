### Background

A background on how I use my system might explain some of the rational...

I have 6.4kWp SSW solar feeding 5kW hybrid-gen3 inverter and 9.5kWh battery (daytime consumption probably down at the 6kWh level).

Tariff is IOG. The inverter does not see the chargepoint, so I don't have to worry about it discharging into the car when it's charging. But do have to avoid exporting when the car is charging, since the car will take it instead of importing from the grid. Charging is normally finished during normal cheap rate, but sometimes as late as 7am weekday, and 10am at the weekend.

Because export is a generous 15p, During the summer I inhibit charging battery from solar during the day, just exporting everything. A separate [modbus-based monitor](modbus.md) handles clipping-avoidance (and an increasing amount of other stuff).

I don't start the battery charge until after midnight, and therefore pause discharge from 2330 until start of charging. This is mainly for accounting purposes - it's convenient for all the charging to happen within one day, rather than having it happen at the end of one day for use the next day. But also, it seems rebalancing happens at low voltages if the battery is left idle, so it's now getting an hour to idle before charging.

When forcing charge/discharge, I try to do it at lower power for longer, when possible, in the belief that this is better for battery health. (Would be nice if you could store a power with each discharge slot, rather than having to keep swapping between max (when in dynamic mode) and around 1.5kW when doing a forced discharge.

Tend to cook main meal around 1830, and from 2000 we don't use very much, so start dumping excess to grid. I might also add an extra rule to dump between 4pm and 5pm if there's a lot of charge in the battery at 4pm. More useful to the grid at this time, though don't want to impact savings sessions rewards (makes it a bit of a negative consequence of savings sessions).

A rpi is running 24/7 anyway (doing other stuff), and so it's easy enough to add these to its relatively small workload.

### Next things to implement

Now that winter is here, and with ASHP, battery may not last all day.
Previously I've not really tried to take advantage of bonus charging slots, but now I'm tempted. I realised that there is a rather easy way to feed information into the modbus script without requiring networking or anything - I can use a mmap-ed file.

So next project is for external scripts to download zappi state and IOG planned dispatches and stuff them into a binary file - /tmp/sensors perhaps - and the modbus script will have this mmap-ed and can pick up any changes each cycle.

### Bugs to workaround

A bit of an anomaly in the AC charging limit: there are (at least) two different settings available via the API: #77 and #101. (The former is a generic one, the latter is specific for charging slot #1.) Unfortunately, #101 seems to be the one that the inverter actually uses, but #77 is the one the app sets. Because it's quite convenient to set via the app, my scripts copy from #77 to #101 in the evening.
 - that bug seems to have been fixed now - app/portal seem to update the correct register.
 
The accumulating meter data for battery in/out seem broken (both record the average of in/out, rather than separate totals), and daily meter resets at midnight, which is one of the reasons for not starting the batterty charge until after midnight.

To idle the battery between 2330 and 0030 (since may as well run from cheap grid rate), I used to use either a charge timer with a low target SoC, or a discharge timer with a high target SoC, but lately, charging seems to charge to at least 20%, and discharge will *charge* gently (around 300W ?) if SoC is below the limit. So now I just turn eco mode off at 2330 via modbus script.

One new unexpected feature: if a timed-discharge is configured with a lower limit, that seems to be active even if timed-export flag is clear. I'm using that to try to save some battery charge for the peak period. (No financial impertative, but trying to do my bit for the grid.)

### Summary

To summarise:
* 0030 to 0529 - charging from grid, charging power calculated
* 0530 to X    - dynamic (with solar charging) if car is charging
*    X to 1955 - pause timer is active, modbus script drives things
* 2000 to 2230 - scheduled discharge, power calculated to end with 8%
* 2230 to 2330 - normal eco mode
* 2330 to 0035 - discharge paused (via discharge slot #2/3 with min SoC 100%)

X is dynamically set based on car-charging activity. It's usually 0530, but if the car is charging beyond the normal cheap hours, X is increased until the end of car charging. (This is the mechanism by which the modbus script doesn't get involved while car is charging.) Because the pause timer is not active, the battery charges from solar.

#### Static configuration
* charge timer 2 0030 to 0529 - variable charge power depending on what is required to reach target SoC
* discharge timer 1 typically runs from 2200 to 2330
* charge timers 3 and 4 reserved for use by the modbus script. The time slots are not used, so the inverter ignores them, but the charging limit is used by the script. Limit 3 is used until 1630 when it switches to limit 4.
* discharge timers 3 and 4 are used to save battery for peak period. Slot 3 is active until 16:30 with a discharge limit of 25%, and #4 after that with a limit of 4. The script uses the range start#3 to end#4 to decide when it's allowed to discharge the battery, down to the limit set by the charging timers.
* discharge timer 2 reserved for use by the modbus script, typically 0800 to 1810 with a discharge limit of 30% (but modbus script stops the discharge before it reaches that limit)
* pause timer 0530 to 1955 (with pause mode adjusted dynamically by modbus script)

Note that discharge #4 should end before the pause timer (to give the modbus script a chance to turn off forced discharge while it is still in charge).

#### Dynamic stuff implemented by these scripts, via cron
* around 2330, run givenergy-offpeak.py to calculate charging power required, and reduce discharge power
* around 0500, run givenergy-iog.py to check whether car is charging, and set pause start time
* around 0530, switch to "day mode" - pause-type = pause-charge, disable timed discharge, set charge/discharge power to max
* around 2200, run givenergy-discharge.py to decide whether to dump to grid, and adjust discharge power and/or ending time.

#### Dynamic stuff implemented via modbus script
Use charge limit 3/4 to charge / export as required (by turning enable-dc-discharge on and off). The script should initiate a discharge if SoC >= (limit+5%), and stop when it gets down to limit. And if SoC is less than limit-5%, it will permit solar charging back up to limit.
