#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState
from java.time import Duration
from ccs import proxies

bb = CCS.attachProxy("bot-bench")

def sanityCheck():
   alerts = bb.getRaisedAlertSummary()
   if alerts.alertState!=AlertState.NOMINAL:
      print "WARNING: bot-bench subsystem is in alarm state %s" % alerts.alertState 

def setNDFilter(filter):
   sanityCheck()
   print "Setting ND filter "+filter
   bb.NeutralFWheel().setNamedPosition(filter)

def setColorFilter(filter):
   sanityCheck()
   print "Setting Color filter "+filter
   bb.ColorFWheel().setNamedPosition(filter)

def openShutter(exposure):
   sanityCheck()
   print "Open shutter for %s seconds" % exposure
   bb.ProjectorShutter().exposure(Duration.ofMillis(int(1000*exposure)))
   bb.ProjectorShutter().waitForClosed()
