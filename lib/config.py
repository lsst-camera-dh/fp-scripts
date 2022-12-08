import re
import ConfigParser
import StringIO
import json
import voltages
import acquire
import time

def parseConfig(file):
  with open(file) as f:
     lines = f.readlines()

  # Eliminate inline # delimited comments
  slines = map(lambda l: re.sub(r"([^#]*)\s#.*", r"\1", l), lines)
  config = ConfigParser.SafeConfigParser(allow_no_value=True)
  config.readfp(StringIO.StringIO("".join(slines)))
  return config

def setvoltages(avoltage):
  voltages.setvoltages(json.loads(avoltage))

def execute(config, command_line_options):
  try:
    items = config.options("VOLTAGES")
    voltages = [ ( item, config.get("VOLTAGES",item) ) for item in items]
    print("VOLTAGES Block found. Acquisitions will be repeated on each settings")
  except:
    print("VOLTAGES Block not found.")
    voltages = [ None ]

  symlink = command_line_options["symlink"]
  for args in voltages:
    if args is not None:
       alabel, avoltage = args
       print(symlink,alabel,avoltage)
       setvoltages(avoltage)
       time.sleep(30)	# wait a bit for getting settled
       if symlink is not None:
          command_line_options["symlink"] = "/".join([symlink,alabel])

    items = config.options("ACQUIRE")
    for item in items:
       options = Config(dict(config.items(item.upper())))
       options.update(command_line_options)
       acq_type = options.get('acqtype')
       if not acq_type:
          acq_type = item
       method = getattr(acquire,'do_%s' % acq_type)
       options.update({'acqtype': acq_type.upper()})
       result = method(options)

class Config(dict):
  ''' Simple wrapper for a dictionary with some convenience methods
      for handling common configuration tasks
  '''

  def getInt(self, key, defaultValue=None):
     value = self.get(key)
     if not value:
       if defaultValue != None:
          return defaultValue
       else:
          raise Exception('Missing config value %s' % key)
     return int(value)

  def getFloat(self, key, defaultValue=None):
     value = self.get(key)
     if not value:
       if defaultValue != None:
          return defaultValue
       else:
          raise Exception('Missing config value %s' % key)
     return float(value)

  def getList(self, key):
     return self.get(key).replace('\n','').split(',')
