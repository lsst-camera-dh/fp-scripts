import re
import ConfigParser
import StringIO
import json
import acquire
import time

COMMA_MATCHER = re.compile(r",(?=(?:[^\"']*[\"'][^\"']*[\"'])*[^\"']*$)")

def parseConfig(file):
  with open(file) as f:
     lines = f.readlines()

  # Eliminate inline # delimited comments
  slines = map(lambda l: re.sub(r"([^#]*)\s#.*", r"\1", l), lines)
  config = ConfigParser.SafeConfigParser(allow_no_value=True)
  config.readfp(StringIO.StringIO("".join(slines)))
  return config

def execute(config, command_line_options):
  symlink = command_line_options["symlink"]

  if "CONFIG" in config.sections():
    one_time_config = config.items("CONFIG")
    acquire.do_one_time_config(Config(dict(one_time_config)))

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

  def getBool(self, key, defaultValue=None):
     value = self.get(key)
     if not value:
       if defaultValue != None:
          return defaultValue
       else:
          raise Exception('Missing config value %s' % key)
     return value.lower() in ['true', '1', 't', 'y', 'yes']


  def getList(self, key):
     str = self.get(key).replace('\n','')
     return COMMA_MATCHER.split(str)


