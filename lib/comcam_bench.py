#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState
from java.time import Duration
from ccs import proxies
import time

ndFilter = False
colorFilter = True
spot = False
shutter = True
fe55Shutter = False

cb = None
ts8mono = None

try:
   cb = CCS.attachProxy("comcam-bench")
except:
   print("No comcam-bench yet!")
   pass
try:
   ts8mono = CCS.attachSubsystem("ts8-bench/Monochromator")
except:
   print("No comcam-bench yet!")
   pass



def sanityCheck():
   state = cb.getState()
   alert = state.getState(AlertState)
   if alert!=AlertState.NOMINAL:
      print "WARNING: bot_bench subsystem is in alert state %s" % alert

def setNDFilter(filter):
   if not ndFilter :
      return
   sanityCheck()
   print "Setting ND filter "+filter
   cb.NeutralFWheel().setNamedPosition(filter)

def setColorFilter(filter):
   print "requested filter = "+filter
   if not colorFilter :
      return
   if not cb==None :
      sanityCheck()
      print "Setting Color filter "+filter
      cb.ColorFWheel().setNamedPosition(filter)
   elif not ts8mono==None :
      if "nm" in filter :
         print "Setting Color filter "+filter

         ts8mono.sendSynchCommand(Duration.ofSeconds(60),"setWaveAndFilter",float(filter.split("nm")[0]))
      else :
         print "Cannot set filter "+filter

def setSpotFilter(filter):
   if not spot :
      return
   sanityCheck()
   print "Setting Spot filter "+filter
   cb.SpotProjFWheel().setNamedPosition(filter)

# Open the flat field projector shutter
def openShutter(exposure):
   if not shutter:
      return
   if not cb==None :
      sanityCheck()
      print "Open shutter for %s seconds" % exposure
      cb.ProjectorShutter().exposure(Duration.ofMillis(int(1000*exposure)))
      cb.ProjectorShutter().waitForClosed()
   elif not ts8mono==None :
      print "Open shutter for %s seconds" % exposure
      ts8mono.sendSynchCommand("openShutter")
      time.sleep(exposure)
      ts8mono.sendSynchCommand("closeShutter")

def openFe55Shutter(exposure):
   if not fe55Shutter :
      return
   sanityCheck()
   print "Open Fe55 shutter for %s seconds" % exposure
   cb.fe55OpenShutters()
   time.sleep(exposure)
   cb.fe55CloseShutters()
