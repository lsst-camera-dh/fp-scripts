import re
import ConfigParser
import StringIO
try:
  import acquire
except:
  pass

def parseConfig(file):
  with open(file) as f:
     lines = f.readlines()

  # Eliminate inline # delimited comments
  slines = map(lambda l: re.sub(r"([^#]*)\s#.*", r"\1", l), lines)
  config = ConfigParser.SafeConfigParser(allow_no_value=True) 
  config.readfp(StringIO.StringIO("".join(slines))) 
  return config

def setvoltage(avoltage):
  print(avoltage)

def execute(config, command_line_options):
  try:
    items = config.options("VOLTAGES")
    voltages = [ config.get("VOLTAGES",item) for item in items]
    print("VOLTAGES Block found. Acquisitions will be repeated on each settings")
  except:
    raise
    print("VOLTAGES Block not found.")
    voltages = [ None ]

  for avoltage in voltages:
    if avoltage is not None:
       setvoltage(avoltage)

    items = config.options("ACQUIRE")
    for item in items:
       options = Config(dict(config.items(item.upper())))
       options.update(command_line_options)
       options.update({'acqtype': item.upper()})
#       method = getattr(acquire,'do_%s' % item)
       print ("{}".format('do_%s' % item))
  #     result = method(options)

class Config(dict):
  ''' Simple wrapper for a dictionary with some convenience methods
      for handling common configuration tasks
  '''

  def getInt(self, key, defaultValue=None):
     value = self.get(key)
     if not value:
       if defaultValue:
          return defaultValue
       else:
          raise Exception('Missing config value %s' % key)
     return int(value)    

  def getFloat(self, key, defaultValue=None):
     value = self.get(key)
     if not value:
       if defaultValue:
          return defaultValue
       else:
          raise Exception('Missing config value %s' % key)
     return float(value)    

  def getList(self, key):
     return self.get(key).replace('\n','').split(',')
