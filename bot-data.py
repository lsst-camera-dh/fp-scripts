#!/usr/bin/env ccs-script
from optparse import OptionParser
from org.lsst.ccs.scripting import CCS
from ccs import aliases
from ccs import proxies

# Temporary work around for problems with CCS responsiveness
#CCS.setDefaultTimeout(30)

# Parse command line options

parser=OptionParser()
parser.add_option("--dry-run", action="store_true", dest="dry_run", default=False)
parser.add_option("-9","--ds9", action="store_true", dest="ds9")
parser.add_option("--run", dest="run")
parser.add_option("--symlink", dest="symlink")
(options, args) = parser.parse_args()

if len(args)!=1:
  parser.print_help()
  exit(1)

#CCS.aliases = {'focal-plane': 'focal-plane-sim', 'bot-bench': 'bot-bench-sim'}
#ccs_sub.write_versions()

import config

cfg = config.parseConfig(args[0])
config.execute(cfg, {"dry_run": options.dry_run, "run": options.run, "symlink": options.symlink})
