#!/usr/bin/env ccs-script
from optparse import OptionParser
import logging
import config
from ccs_scripting_tools import CcsSubsystems

# Parse command line options

parser=OptionParser()
parser.add_option("--dry-run", action="store_true", dest="dry_run", default=False)
parser.add_option("-9","--ds9", action="store_true", dest="ds9")
parser.add_option("--run", dest="run", default=9999)
parser.add_option("--activity", dest="activity", default=12345678)
parser.add_option("--output", dest="output", default='/tmp')
(options, args) = parser.parse_args()

if len(args)!=1:
  parser.print_help()
  exit(1)

logging.basicConfig(format="%(message)s",
                    level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger('bot-data.py')

subsystems = dict(fp = 'focal-plane', bb='bot-bench')
ccs_sub = CcsSubsystems(subsystems, logger=logger)
ccs_sub.write_versions()


cfg = config.parseConfig(args[0])
config.execute(cfg, ccs_sub, {"dry_run": options.dry_run, "run": options.run, "activity": options.activity, "output": options.output})
