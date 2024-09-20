#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState
from org.lsst.ccs.utilities.taitime import CCSTimeStamp
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
   t1 = CCSTimeStamp.currentTime()

def turnOffLed():
   driver.setLedCurrent(0.0)    # not to overheat the board
   driver.setExposureTime(0.1)
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
   for i in range(10): # assuming we only have 1 sec delay at maximum
      time.sleep(0.1) # hopefully that is long enough?
      if driver.pollEnd()==False:
         break
   t2 = CCSTimeStamp.currentTime()
   after = driver.getAdcValues()
   driver.setLedCurrent(0.0)    # not to overheat the board
   return {
       "CCOBADC": after.getPhotodiodeCurrent(),
#       "CCOBCURR": after.getLedCurrent(),
       "CCOBTMPBRD": after.getTempBrd(),
       "CCOBTMPLED1": after.getTempLed1(),
       "CCOBTMPLED2": after.getTempLed2(),
       "CCOBLEDV": after.getLedVoltage(),
       "CCOBLEDVREF": after.getLedVref(),
       "PROJTIME": t2.getTAIDouble()-t1.getTAIDouble(),
       "MJD-PBEG": t1,
       "MJD-PEND": t2
   }

def flash(led="red", current=0.009, seconds=0.05, maxtime=1.3):
   global t1
   t1 = CCSTimeStamp.currentTime()
   accum=0.
   #for subflash in [ maxtime for i in range(int(seconds/maxtime)) ]+[seconds%maxtime]: # divide a longer flash than maxtime to multiple flashes
   numflashes=int(seconds/maxtime)+1
   for i in range(numflashes):
      subflash = seconds/numflashes
      time.sleep(0.1)
      prepLED(led, current, subflash)
      driver.startExposure()
      time.sleep(subflash)
      adc=WaitAndReadLED()
      accum+=adc["CCOBADC"]

   adc["CCOBADC"]=accum
   return adc

def flashAndWait(led="red", current=0.009, seconds=0.05,exptime=15, maxtime=1.3):
   t=Thread(target=time.sleep,args=[exptime])
   t.daemon=True
   t.start()

   flash(led=led,current=current,seconds=seconds,maxtime=maxtime)
   t.join()

   return adc

