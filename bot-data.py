#!/usr/bin/env ccs-script
from optparse import OptionParser
import config

# Parse command line options

parser=OptionParser()
parser.add_option("--dry-run", action="store_true", dest="dry_run")
parser.add_option("-9","--ds9", action="store_true", dest="ds9")
(options, args) = parser.parse_args()

if len(args)!=1:
  parser.print_help()
  exit(1)

cfg = config.parseConfig(args[0])
config.execute(cfg, {"dry_run": options.dry_run})
