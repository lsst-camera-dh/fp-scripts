#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState
from java.time import Duration
from ccs import proxies
import time

bb = CCS.attachProxy("bot-bench")

def sanityCheck():
   state = bb.getState()
   alert = state.getState(AlertState)
   if alert!=AlertState.NOMINAL:
      print "WARNING: bot_bench subsystem is in alert state %s" % alert

def setNDFilter(filter):
   sanityCheck()
   print "Setting ND filter "+filter
   bb.NeutralFWheel().setNamedPosition(filter)

def setColorFilter(filter):
   sanityCheck()
   print "Setting Color filter "+filter
   bb.ColorFWheel().setNamedPosition(filter)

def setSpotFilter(filter):
   sanityCheck()
   print "Setting Spot filter "+filter
   bb.SpotProjFWheel().setNamedPosition(filter)

# Open the flat field projector shutter
def openShutter(exposure):
   sanityCheck()
   print "Open shutter for %s seconds" % exposure
   bb.ProjectorShutter().exposure(Duration.ofMillis(int(1000*exposure)))
   bb.ProjectorShutter().waitForClosed()

def openFe55Shutter(exposure):
   sanityCheck()
   print "Open Fe55 shutter for %s seconds" % exposure
   bb.fe55OpenShutters()
   time.sleep(exposure)
   bb.fe55CloseShutters()
