#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from ccs import proxies
from java.util import HashSet
import time

def write_config(fp, categories):
   args = HashSet()
   for c in categories:
      args.add(c)
   config = fp.printConfigurationParameters(args)
   with open("ccs_config.txt", "w") as file:
      file.write(config)