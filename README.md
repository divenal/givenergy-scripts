Some simple scripts using the givenergy api. Not terribly idiomatic since python isn't really my first choice of language, but it seems to be popular, and has a rich standard library. Does need the requests package in addition, however.

What I should really do is make an abstraction so that you can choose to either use the api or a direct connection via givenergy-modbus.

The scripts expect to find a config file in ~/.solar  - this is in a format for configparser. There needs to be a [givenergy] section with an 'inverter' setting (identify the inverter) and a 'control' setting, which is an api token granting full inveter control. 
