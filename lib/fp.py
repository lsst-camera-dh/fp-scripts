#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import *
from org.lsst.ccs.bus.states import AlertState
from datetime import date
from optparse import OptionParser
from org.lsst.ccs.subsystem.rafts.fpga.compiler import FPGA2ModelBuilder
from java.io import File
import time
from org.lsst.ccs.utilities.image.samp import SampUtils
from java.io import File
from java.time import Duration

#CCS.setThrowExceptions(True)
#fp = CCS.attachSubsystem("focal-plane")

def sanityCheck(ccs_sub):
   #biasOn = ccs_sub.fp.sendSynchCommand("isBackBiasOn")
   #if not biasOn:
   #  print "WARNING: Back bias is not on"

   alerts = ccs_sub.fp.sendSynchCommand("getRaisedAlertSummary")
   if alerts.alertState!=AlertState.NOMINAL:
      print "WARNING: focal-plane subsystem is in alarm state %s" % alerts.alertState 

def clear(ccs_sub):
   print "Clearing CCDs "
   ccs_sub.fp.sendSynchCommand(10, "clear",1)
   ccs_sub.fp.sendSynchCommand("waitForSequencer", Duration.ofSeconds(10))

def takeBias(ccs_sub):
   sanityCheck(ccs_sub)
   clear(ccs_sub)
   imageName = ccs_sub.fp.sendSynchCommand(10,"startIntegration")
   print "Image name: %s" % imageName
   ccs_sub.fp.sendSynchCommand(10,"endIntegration")
   return (imageName, ccs_sub.fp.sendSynchCommand("waitForFitsFiles", Duration.ofSeconds(30)))

def takeExposure(ccs_sub, exposeCommand):
   sanityCheck(ccs_sub)
   clear(ccs_sub)
   imageName = ccs_sub.fp.sendSynchCommand("startIntegration")
   print "Image name: %s" % imageName
   exposeCommand()
   ccs_sub.fp.sendSynchCommand("endIntegration")
   return (imageName, ccs_sub.fp.sendSynchCommand("waitForFitsFiles", Duration.ofSeconds(30)))    
