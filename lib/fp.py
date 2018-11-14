#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState
from java.time import Duration
from ccs import proxies

fp = CCS.attachProxy("focal-plane")

def sanityCheck():
   #biasOn = fp.isBackBiasOn()
   #if not biasOn:
   #  print "WARNING: Back bias is not on"

   alerts = fp.getRaisedAlertSummary()
   if alerts.alertState!=AlertState.NOMINAL:
      print "WARNING: focal-plane subsystem is in alarm state %s" % alerts.alertState 

def clear():
   print "Clearing CCDs "
   fp.clear(1)
   fp.waitForSequencer(Duration.ofSeconds(10))

def takeBias():
   return takeExposure()    

def takeExposure(exposeCommand=None):
   sanityCheck()
   clear()
   imageName = fp.startIntegration()
   print "Image name: %s" % imageName
   if exposeCommand: 
      exposeCommand()
   fp.endIntegration()
   return (imageName, fp.waitForFitsFiles(Duration.ofSeconds(60)))    
