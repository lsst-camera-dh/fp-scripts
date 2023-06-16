#!/usr/bin/env ccs-script
import sys
import time
from optparse import OptionParser
from org.lsst.ccs.scripting import CCS
from ccs import aliases
from ccs import proxies
from ccs import versions
from ccs import configs
from java.lang import Boolean
from java.time import Duration

# Temporary work around for problems with CCS responsiveness
CCS.setDefaultTimeout(Duration.ofSeconds(30))

# Parse command line options

parser=OptionParser()
parser.add_option("--dry-run", action="store_true", dest="dry_run", default=False)
parser.add_option("-9","--ds9", action="store_true", dest="ds9")
parser.add_option("--run", dest="run")
parser.add_option("--symlink", dest="symlink")
parser.add_option("--skip", dest="skip")
parser.add_option("--limit", dest="limit")

(options, args) = parser.parse_args()

if len(args)!=1:
  parser.print_help()
  exit(1)

#CCS.aliases = {'focal-plane': 'focal-plane-sim', 'bot-bench': 'bot-bench-sim'}
#CCS.aliases = {
#	'focal-plane': 'ts8-fp',
#	'bot-bench': 'ts8-bench',
#	'bot-motorplatform': 'ts8-motorplatform',
#       'mcm': 'ts8-mcm'
#}

# Assume if run is set we are running under eTraveler
if options.run:
  fp = CCS.attachProxy('focal-plane', Boolean(false))
  time.sleep(10.0)
  versions.write_versions(fp)
  configs.write_config(fp, ['Sequencer', 'Rafts'])

import config

cfg = config.parseConfig(args[0])
config.execute(cfg, {"dry_run": options.dry_run, "run": options.run, "symlink": options.symlink, "skip": options.skip, "limit": options.limit})
