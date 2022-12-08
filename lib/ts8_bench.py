#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState
from java.time import Duration
from ccs import proxies
import time
import re

bb = CCS.attachProxy("ts8-bench")

def sanityCheck():
   state = bb.getState()
   alert = state.getState(AlertState)
   if alert!=AlertState.NOMINAL:
      print "WARNING: bot_bench subsystem is in alert state %s" % alert

def setNDFilter(filter):
   sanityCheck()
   print "Setting 1 and 2 SlitWidth",filter
   if filter == "unspecified":
      return
#   bb.Monochromator().setSlitSize(1,int(re.match(r"slit(\d+)",filter).group(1)))
#   bb.Monochromator().setSlitSize(2,int(re.match(r"slit(\d+)",filter).group(1)))
   bb.NeutralFWheel().setNamedPosition(filter)

def setColorFilter(filter):
   sanityCheck()
   print "Setting color filter ",filter
#   bb.Monochromator().setWaveAndFilter(int(filter))
   bb.ColorFWheel().setNamedPosition(filter)

def setSpotFilter(filter):
   sanityCheck()
   print "Setting Spot filter "+filter
   bb.SpotProjFWheel().setNamedPosition(filter)

# Open the flat field projector shutter
def openShutter(exposure):
   open_delay  = 0.01
   close_delay = 0.01   # newport 76994 has 4ms/7ms open/close time
   sanityCheck()
   print "Open shutter for %s seconds" % exposure
#   bb.Monochromator().openShutter()
   bb.ProjectorShutter().openShutter()
#   bb.TS8Shutter().setShutterPosition(True)
   time.sleep(exposure)
#   bb.Monochromator().closeShutter()
   bb.ProjectorShutter().closeShutter()
#   bb.TS8Shutter().setShutterPosition(False)
   time.sleep(close_delay)  # give time for shutter to close before readout starts
   print "Shutter closed"

def openFe55Shutter(exposure):
   sanityCheck()
   print "Open Fe55 shutter for %s seconds" % exposure
   bb.fe55OpenShutters()
   time.sleep(exposure)
   bb.fe55CloseShutters()

def readPDCurrent():
   return bb.Monitor().readCurrent()
