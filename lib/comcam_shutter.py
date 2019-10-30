#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState
from java.time import Duration
from ccs import proxies
import time

shutter = CCS.attachProxy("bonn-shutter")

def sanityCheck():
   state = shutter.getState()
   alert = state.getState(AlertState)
   if alert!=AlertState.NOMINAL:
      print "WARNING: bonn-shutter subsystem is in alert state %s" % alert

def openShutter(exposure):
   sanityCheck()
   print "Open shutter for %s seconds" % exposure
   shutter.takeExposure(exposure)
   shutter.waitForExposure()

