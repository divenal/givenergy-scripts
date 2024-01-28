Some simple scripts using the givenergy api. Not terribly idiomatic since python isn't really my first choice of language, but it seems to be popular, and has a rich standard library. Does need the requests package in addition, however.

What I should really do is make an abstraction so that you can choose to either use the api or a direct connection via givenergy-modbus.

# scripts
The scripts are in bin/

They share a utility file `givenergy.py` which implements the API via the `requests` package. It auto-retries on failure. Note that the system I run on has an outdated version of this package, and so I use a deprecated way of implementating that.

`givenergy-offpeak.py` runs from cron just before and after the off-peak period. With parameter `before` it sets up for overnight mode, which means setting charge rate to reach the (already set) target % SoC  over the full 6 hours. You need to tweak the hard-coded constants to match your system.

There's some constants at the top to define the numerical registers for the api settings. You should check to make sure they're the same for your system. (I'll update givenergy.py so that if you invoke it as a script, it will fetch and display the register numbers.)

`pvoutput.py` runs once per day, via cron. It downloads the days parameters, and uploads to pvoutput.

# Configuration
The scripts expect to find a config file in `~/.solar`  - this is in a format for configparser.
There needs to be a `[givenergy]` section with
 - `inverter` setting (identify the inverter) and a
 - `control` setting, which is an api token granting full inveter control. 

For the pvoutput script, you need a `[pvoutput]` with
 - `name` name of your system
 - `ìd` numerical id
 - `key` access key
