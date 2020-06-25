# fp-scripts
Interim scripts for running focal-plane + bot

Scripts have been imported "as-is" to get feedback from Jim et al.

Current organization

* lib/         -- Scripts intended to be on the CCS "jython path", so installed in ~/ccs/etc or /lsst/ccs/prod/etc
* examples     -- Example configuration file
* ts8-data.py  -- Example top-level script

Can be run as

ccs-script ts8-data.py examples/aaron.cfg    

or if ccs-script is on your PATH

./ts8-data.py examples/main.cfg
