#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState
from java.time import Duration

#CCS.setThrowExceptions(True)
#bb = CCS.attachSubsystem("bot-bench")

def sanityCheck(ccs_sub):
   #biasOn = fp.sendSynchCommand("isBackBiasOn")
   #if not biasOn:
   #  print "WARNING: Back bias is not on"

   alerts = ccs_sub.bb.sendSynchCommand("getRaisedAlertSummary")
   if alerts.alertState!=AlertState.NOMINAL:
      print "WARNING: bot-bench subsystem is in alarm state %s" % alerts.alertState 

def setNDFilter(ccs_sub, filter):
   sanityCheck(ccs_sub)
   print "Setting ND filter "+filter
   ccs_sub.bb.sendSynchCommand(10, "NeutralFWheel setNamedPosition",filter)

def setColorFilter(ccs_sub, filter):
   sanityCheck(ccs_sub)
   print "Setting Color filter "+filter
   ccs_sub.bb.sendSynchCommand(10, "ColorFWheel setNamedPosition",filter)

def openShutter(ccs_sub, exposure):
   sanityCheck(ccs_sub)
   print "Open shutter for %s seconds" % exposure
   ccs_sub.bb.sendSynchCommand("ProjectorShutter exposure",int(1000*exposure))
   ccs_sub.bb.sendSynchCommand(int(exposure)+1,"ProjectorShutter waitForClosed")
