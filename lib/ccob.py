#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState
from java.time import Duration
from ccs import proxies
import time

ccob = CCS.attachProxy("ccob-subsystem")
driver = ccob.ccobDriver()

def sanityCheck():
   alerts = ccob.getRaisedAlertSummary()
   if alerts.alertState!=AlertState.NOMINAL:
      print "WARNING: CCOB subsystem is in alarm state %s" % alerts.alertState 

def fireLED(led="red", current=0.009, seconds=0.05):
   sanityCheck()
   print "Firing CCOB LED=%s current=%g seconds=%g" % (led,current,seconds)
   driver.pulse()
   # FIXME: Should not have to use sendSynchCommand here, and if we do should 
   # not have to prepend ccobDriver, but otherwise need explicit import of LED enum
   driver.sendSynchCommand("ccobDriver selectLed "+led)
   driver.setExposureTime(seconds)
   driver.setLedCurrent(current)
   # Does this wait for the LED? (Apparently not)
   driver.startExposure()
   time.sleep(seconds+0.1) # hopefully that is long enough?
   after = driver.getAdcValues().getPhotodiodeCurrent()
   return after



