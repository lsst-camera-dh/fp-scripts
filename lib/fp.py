#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState
from org.lsst.ccs.subsystem.focalplane.states import FocalPlaneState
from org.lsst.ccs.subsystem.rafts.states import CCDsPowerState
from java.time import Duration
from ccs import proxies
#import bot_bench
import array
import re
import os

fp = CCS.attachProxy("focal-plane") # this will be override by CCS.aliases
agentName = fp.getAgentProperty("agentName")
if  agentName != "focal-plane":
   fp = CCS.attachProxy(agentName) # re-attach to ccs subsystem
autoSave = True
imageTimeout = Duration.ofSeconds(60)
symlinkToFast = True
# These need to be changed when we switch R_and_D -> rawData
symLinkFromLocation = "/gpfs/slac/lsst/fs3/g/data/R_and_D/focal-plane/"
symLinkToLocation = "/gpfs/slac/lsst/fs3/g/fast/R_and_D/focal-plane/"

def sanityCheck():
   # Was this ever implemented on focal-plane?
   #biasOn = fp.isBackBiasOn()
   #if not biasOn:
   #   print "WARNING: Back bias is not on"

   state = fp.getState()
   alert = state.getState(AlertState)
   if alert!=AlertState.NOMINAL:
      print "WARNING: focal-plane subsystem is in alert state %s" % alert

def startIdleFlush():
   #
   # no action if already in idle flushing
   # starts on success
   # lets the subsystem throw error otherwise
   #
   state = fp.getState()
   fpstate = state.getState(FocalPlaneState)
   if fpstate == FocalPlaneState.IDLEFLUSH:
      return
   if fpstate != FocalPlaneState.QUIESCENT:
      print "WARNING: ts8-fp subsystem is in state %s != QUIESCENT" % fpstate
   fp.startIdleFlush()
   return

def endIdleFlush(n=1):
   #
   # no action if already in idle flushing
   # starts on success
   # lets the subsystem throw error otherwise
   #
   state = fp.getState()
   fpstate = state.getState(FocalPlaneState)
   if fpstate == FocalPlaneState.QUIESCENT:  # silently accept
      return
   if fpstate != FocalPlaneState.IDLEFLUSH:
      print "WARNING: ts8-fp subsystem is in state %s != IDLEFLUSH" % fpstate
      return
   fp.endIdleFlush(n)
   fp.waitForSequencer(Duration.ofSeconds(2))
   return

def clear(n=1):
   if n == 0:
      return
   endIdleFlush()
   print "Clearing CCDs (%d)" % n
   fp.clear(n)
   fp.waitForSequencer(Duration.ofSeconds(2))

def takeBias(fitsHeaderData, annotation=None, locations=None):
   # TODO: This may not be the best way to take bias images
   # It may be better to define a takeBias command at the subsystem layer, since
   # this could skip the startIntegration/endIntegration and got straigh to readout
   return takeExposure(fitsHeaderData=fitsHeaderData, annotation=annotation, locations=locations)

def takeExposure(exposeCommand=None, fitsHeaderData=None, annotation=None, locations=None):
   sanityCheck()
   endIdleFlush(0)
   clear()
   print "Setting FITS headers %s" % fitsHeaderData
   fp.setHeaderKeywords(fitsHeaderData)
   imageName = fp.startIntegration(annotation, locations)
   print "Image name: %s" % imageName

   # Horrible fix for using "fast" gpfs disk at SLAC
   # Note, the paths here are hardwired above, and must be fixed if imagehandling config is changed
   if symlinkToFast:
      date = re.sub(r".._._(........)_......", r"\1", imageName)
      oldLocation = symLinkFromLocation+date+"/"
      newLocation = symLinkToLocation+date+"/"+imageName
      os.mkdirs(oldLocation)
      os.mkdirs(newLocation)
      os.symlink(newLocation, oldLocation+imageName)

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

def rafts():
   #TODO: Should not be hardwired
   return [ fp.R22() ]

def rebs():
   result = []
   for r in rafts():
      #TODO: Not correct for non-science rafts
      result += [r.Reb0(), r.Reb1(), r.Reb2()]
   return result

def aspics():
   result = []
   for r in rebs():
      #TODO: Not correct for non-science rafts
      result += [r.ASPIC0(), r.ASPIC1(), r.ASPIC2(), r.ASPIC3(), r.ASPIC4(), r.ASPIC5() ]
   return result

def getSequencerParameter(name):
   params = []
   for raft in rafts():
      params += raft.getSequencerParameter(name)
      unique = set(params)
      if len(unique)!=1:
         raise "Inconsistent sequencer parameters "+params
      return unique.pop()

def setSequencerParameter(name, value):
   for raft in rafts():
      raft.setSequencerParameter(name, value)

def isScanMode():
   result = []
   for reb in rebs():
      reg = reb.getRegister(0x330000,1).getValues()
      result += reg
   unique = set(result)
   if len(unique)!=1:
      raise Exception("Inconsistent scan mode")
   return unique.pop()

def setScanMode(value):
   for reb in rebs():
      reb.setRegister(0x330000, array.array('i',[1] if value else [0]))

def isTransparentMode():
   result = []
   for aspic in aspics():
      result += aspic.getTm()
   unique = set(result)
   if len(unique)!=1:
      raise "Inconsistent transparent mode "+result
   return unique.pop()

def setTransparentMode(value):
   for aspic in aspics():
      aspic.change("tm",  1 if value else 0)
