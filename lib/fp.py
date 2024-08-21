#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState
from org.lsst.ccs.subsystem.ocsbridge.states import StandbyState
from org.lsst.ccs.subsystem.ocsbridge.states import ShutterState
from java.time import Duration
from ccs import proxies
import time

CLEARDELAY=0.07
#CLEARDELAY=2.35

mcm = CCS.attachProxy("mcm") # this will be override by CCS.aliases
agentName = mcm.getAgentProperty("agentName")
imageTimeout = Duration.ofSeconds(60)

# Called at start of run to check shutter status
def checkShutterStatus(shutterMode):
   state = mcm.getState()
   shutterState = state.getState(ShutterState)
   print "ShutterState: %s   ShuterMode: %s" % (shutterState, shutterMode)
   if shutterState==ShutterState.CLOSED and shutterMode != None and shutterMode.lower()=="open":
      print "Opening shutter"
      mcm.openShutter()
      time.sleep(1.0) # Wait for open
   if shutterState==ShutterState.OPEN and shutterMode != None and shutterMode.lower()=="normal":
      print "Closing shutter"
      mcm.closeShutter()
      time.sleep(1.0) # Wait for close

def sanityCheck():
   state = mcm.getState()
   alert = state.getState(AlertState)
   if alert!=AlertState.NOMINAL:
      print "WARNING: %s subsystem is in alert state %s" % ( agentName, alert )
   standby = state.getState(StandbyState)
   if standby==StandbyState.STANDBY:
      print "WARNING: %s subsystem is in %s, attempting to switch to STARTED" % ( agentName, standby )
      mcm.start("Normal")

def clear(n=1):
   if n == 0:
      return
   print "Clearing CCDs (%d)" % n
   fp.clear(n)
   fp.waitForSequencer(Duration.ofSeconds(2))

def takeBias(fitsHeaderData, annotation=None, locations=None):
   # TODO: This may not be the best way to take bias images
   # It may be better to define a takeBias command at the subsystem layer, since
   # this could skip the startIntegration/endIntegration and got straigh to readout
   return takeExposure(fitsHeaderData=fitsHeaderData, annotation=annotation, locations=locations)

def takeExposure(exposeCommand=None, fitsHeaderData=None, annotation=None, locations=None, clears=1, shutterMode=None, exposeTime=None, imageType=None, roiSpec=None):
   sanityCheck()
   print "Setting FITS headers %s" % fitsHeaderData

   imageName = mcm.allocateImageName()
   print "Image name: %s" % imageName

   # if exposeTime is None we assume that the exposeCommand will take care of implementing the exposure delay
   if not exposeTime:
      mcm.clearAndStartNamedIntegration(imageName, False, clears, annotation, locations, fitsHeaderData)
      # Sleep for 70 ms to allow for clear which is part of integrate to complete
      time.sleep(CLEARDELAY)
      try:
         if exposeCommand:
            extraData = exposeCommand()
            if extraData:
               mcm.setHeaderKeywords(extraData)

      except:
         mcm.closeShutter()
         raise

      finally:
         mcm.endIntegration()
         mcm.waitForImage()
      return (imageName, None)
   # if exposeTime is specified then we assume that exposeCommand will be programmed to fit within exposeTime.
   # and the MCM+shutter will take care of the overall exposure timing.
   # This is the only mode in which guiding will work.
   else:
      openShutter = shutterMode != None and shutterMode.lower() == "normal" and imageType!="DARK" and imageType!="BIAS"  
      if roiSpec:
         initGuiders(roiSpec)
      mcm.takeImage(imageName, openShutter, exposeTime, clears, annotation, locations, fitsHeaderData)
      #  Sleep for 70 ms to allow for clear which is part of integrate to complete
      time.sleep(CLEARDELAY)
      if exposeCommand:
         extraData = exposeCommand()
         if extraData:
            mcm.setHeaderKeywords(extraData)
      mcm.waitForImage()
      return (imageName, None)

def initGuiders(roiSpec):
   print "ROISPEC=%s " % roiSpec
   mcm.initGuiders(roiSpec)
