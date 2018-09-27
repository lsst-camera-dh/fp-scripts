#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState
from java.time import Duration

CCS.setThrowExceptions(True)
bb = CCS.attachSubsystem("bot-bench")

def sanityCheck():
   #biasOn = fp.sendSynchCommand("isBackBiasOn")
   #if not biasOn:
   #  print "WARNING: Back bias is not on"

   alerts = bb.sendSynchCommand("getRaisedAlertSummary")
   if alerts.alertState!=AlertState.NOMINAL:
      print "WARNING: bot-bench subsystem is in alarm state %s" % alerts.alertState 

def setNDFilter(filter):
   sanityCheck()
   print "Setting ND filter "+filter
   bb.sendSynchCommand(10, "NeutralFWheel setNamedPosition",filter)

def setColorFilter(filter):
   sanityCheck()
   print "Setting Color filter "+filter
   bb.sendSynchCommand(10, "ColorFWheel setNamedPosition",filter)

def openShutter(exposure):
   sanityCheck()
   print "Open shutter for %s seconds" % exposure
   bb.sendSynchCommand("ProjectorShutter exposure",int(1000*exposure))
   bb.sendSynchCommand(int(exposure)+1,"ProjectorShutter waitForClosed")
