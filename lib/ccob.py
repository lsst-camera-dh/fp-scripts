#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState
from java.time import Duration
from ccs import proxies
import time
from threading import Thread


ccob = CCS.attachProxy("ccob")
driver = ccob.ccobDriver()

def sanityCheck():
   state = ccob.getState()
   alert = state.getState(AlertState)
   if alert!=AlertState.NOMINAL:
      print "WARNING: CCOB subsystem is in alert state %s" % alert

def turnOnLed(led="red", current=0.009):
   driver.sendSynchCommand("ccobDriver selectLed "+led)
   driver.setLedCurrent(current)
   driver.shutter()
   driver.startExposure()
   global t1
   t1=time.time()

def turnOffLed():
   driver.pulse()
   driver.startExposure()

def prepLED(led="red", current=0.009, seconds=0.05):
   sanityCheck()
   print "Firing CCOB LED=%s current=%g seconds=%g" % (led,current,seconds)
   driver.pulse()
   # FIXME: Should not have to use sendSynchCommand here, and if we do should 
   # not have to prepend ccobDriver, but otherwise need explicit import of LED enum
   driver.sendSynchCommand("ccobDriver selectLed "+led)
   driver.setExposureTime(seconds)
   driver.setLedCurrent(current)

def WaitAndReadLED():
   while driver.pollEnd():
      time.sleep(0.1) # hopefully that is long enough?
   t2=time.time()
   after = driver.getAdcValues()
   return {
       "CCOBADC": after.getPhotodiodeCurrent(),
#       "CCOBCURR": after.getLedCurrent(),
       "CCOBTMPBRD": after.getTempBrd(),
       "CCOBTMPLED1": after.getTempLed1(),
       "CCOBTMPLED2": after.getTempLed2(),
       "CCOBLEDV": after.getLedVoltage(),
       "CCOBLEDVREF": after.getLedVref(),
       "PROJTIME": t2-t1,
       "MJD-PBEG": t1,
       "MJD-PEND": t2
   }

def flashAndWait(led="red", current=0.009, seconds=0.05,exptime=15):
   t=Thread(target=time.sleep,args=[exptime])
   t.daemon=True
   t.start()

   prepLED(led, current, seconds)
   global t1
   driver.startExposure()
   t1=time.time()
   time.sleep(seconds)
   adc=WaitAndReadLED()

   t.join()
   return adc

