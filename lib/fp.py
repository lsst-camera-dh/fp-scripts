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

CCS.setThrowExceptions(True)
fp = CCS.attachSubsystem("focal-plane")

def sanityCheck():
   #biasOn = fp.sendSynchCommand("isBackBiasOn")
   #if not biasOn:
   #  print "WARNING: Back bias is not on"

   alerts = fp.sendSynchCommand("getRaisedAlertSummary")
   if alerts.alertState!=AlertState.NOMINAL:
      print "WARNING: fo0cal-plane subsystem is in alarm state %s" % alerts.alertState 

def clear():
   print "Clearing CCDs "
   fp.sendSynchCommand("clear",1)
   fp.sendSynchCommand("waitForSequencer", Duration.ofSeconds(10))

def takeBias():
   sanityCheck()
   clear()
   imageName = fp.sendSynchCommand("startIntegration")
   print "Image name: %s" % imageName
   fp.sendSynchCommand("endIntegration")
   result = fp.sendSynchCommand("waitForFitsFiles", Duration.ofSeconds(30))
   print "Saved FITS files to %s" % result

def takeExposure(exposeCommand):
   sanityCheck()
   clear()
   imageName = fp.sendSynchCommand("startIntegration")
   print "Image name: %s" % imageName
   exposeCommand()
   fp.sendSynchCommand("endIntegration")
   result = fp.sendSynchCommand("waitForFitsFiles", Duration.ofSeconds(30))
   print "Saved FITS files to %s" % result

