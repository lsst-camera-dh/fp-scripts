#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from ccs import proxies
import time
import jarray
from java.lang import String

def write_config(fp, categories):
   config = fp.printConfigurationParameters(jarray.array(categories, String ))
   with open("ccs_config.txt", "w") as file:
      file.write(config)
