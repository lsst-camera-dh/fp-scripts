#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState
from org.lsst.ccs.subsystem.focalplane.states import FocalPlaneState
from java.time import Duration
from ccs import proxies
#import bot_bench
import time
import array
import os

fp = CCS.attachProxy("focal-plane") # this will be override by CCS.aliases
agentName = fp.getAgentProperty("agentName")
if agentName != "focal-plane":
   fp = CCS.attachProxy(agentName) # re-attach to ccs subsystem
autoSave = True
imageTimeout = Duration.ofSeconds(60)
symlinkToFast = False
# These need to be changed when we switch R_and_D -> rawData
symLinkFromLocation = "/gpfs/slac/lsst/fs3/g/data/rawData/focal-plane/"
symLinkToLocation = "/gpfs/slac/lsst/fs3/g/fast/rawData/focal-plane/"

def sanityCheck():
   # Was this ever implemented on focal-plane?
   #biasOn = fp.isBackBiasOn()
   #if not biasOn:
   #   print "WARNING: Back bias is not on"

   state = fp.getState()
   alert = state.getState(AlertState)
   if alert!=AlertState.NOMINAL:
      print "WARNING: %s subsystem is in alert state %s" % ( agentName, alert )

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

def takeExposure(exposeCommand=None, fitsHeaderData=None, annotation=None, locations=None, clears=1):
   sanityCheck()
   print "Setting FITS headers %s" % fitsHeaderData
   fp.setHeaderKeywords(fitsHeaderData)
   imageName = fp.allocateImageName()
   print "Image name: %s" % imageName

   # Horrible fix for using "fast" gpfs disk at SLAC
   # Note, the paths here are hardwired above, and must be fixed if imagehandling config is changed
   if symlinkToFast:
      date = imageName.dateString
      oldLocation = symLinkFromLocation+date+"/"
      newLocation = symLinkToLocation+date+"/"+imageName.toString()
      if not os.path.exists(oldLocation):
         os.makedirs(oldLocation)
      if not os.path.exists(newLocation):
         os.makedirs(newLocation)
      os.symlink(newLocation, oldLocation+imageName.toString())

   fp.clearAndStartNamedIntegration(imageName, clears, annotation, locations)
   # Sleep for 70 ms to allow for clear which is part of integrate to complete
   time.sleep(0.07)

   if exposeCommand:
      extraData = exposeCommand()
      if extraData:
          fp.setHeaderKeywords(extraData)
   fp.endIntegration()
   if autoSave:
     return (imageName, fp.waitForFitsFiles(imageTimeout))
   else:
     fp.waitForImages(imageTimeout)
     return (imageName, None)
