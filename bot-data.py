#!/usr/bin/env ccs-script
import sys
#sys.path.insert(0,"/gpfs/slac/lsst/fs1/g/data/youtsumi/ts8/fp-scripts/lib")
from optparse import OptionParser
from org.lsst.ccs.scripting import CCS
from ccs import aliases
from ccs import proxies
from java.time import Duration

# Temporary work around for problems with CCS responsiveness
CCS.setDefaultTimeout(Duration.ofSeconds(30))

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
#CCS.aliases = {'focal-plane': 'ts8-fp', 'bot-bench': 'ts8-bench' }
#ccs_sub.write_versions()

import config

cfg = config.parseConfig(args[0])
config.execute(cfg, {"dry_run": options.dry_run, "run": options.run, "symlink": options.symlink})
