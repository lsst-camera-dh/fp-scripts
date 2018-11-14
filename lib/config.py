import re
import ConfigParser
import StringIO
import acquire

def parseConfig(file):
  with open(file) as f:
     lines = f.readlines()

  # Eliminate inline # delimited comments
  slines = map(lambda l: re.sub(r"([^#]*)\s#.*", r"\1", l), lines)
  config = ConfigParser.SafeConfigParser(allow_no_value=True) 
  config.readfp(StringIO.StringIO("".join(slines))) 
  return config

def execute(config, command_line_options):
  items = config.options("ACQUIRE")
  for item in items:
     options = dict(config.items(item.upper()))
     options.update(command_line_options)
     options.update({'acqtype': item.upper()})
     method = getattr(acquire,'do_%s' % item)
     result = method(options)
