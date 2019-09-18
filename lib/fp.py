#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState
from java.time import Duration
from ccs import proxies
import bot_bench
import array

fp = CCS.attachProxy("focal-plane")
autoSave = True
imageTimeout = Duration.ofSeconds(60)

def sanityCheck():
   biasOn = fp.isBackBiasOn()
   if not biasOn:
     print "WARNING: Back bias is not on"
   
   state = fp.getState()
   alert = state.getState(AlertState)
   if alert!=AlertState.NOMINAL:
      print "WARNING: focal-plane subsystem is in alert state %s" % alert 

def clear(n=1):
   print "Clearing CCDs (%d)" % n
   fp.clear(n)
   fp.waitForSequencer(Duration.ofSeconds(10))

def takeBias(fitsHeaderData):
   # TODO: This may not be the best way to take bias images
   # It may be better to define a takeBias command at the subsystem layer, since
   # this could skip the startIntegration/endIntegration and got straigh to readout
   return takeExposure(fitsHeaderData=fitsHeaderData)    

def takeExposure(exposeCommand=None, fitsHeaderData=None):
   sanityCheck()
   clear()
   print "Setting FITS headers %s" % fitsHeaderData
   fp.setHeaderKeywords(fitsHeaderData)
   imageName = fp.startIntegration()
   print "Image name: %s" % imageName
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

def takeCombinedExposure(exposeCommand=None, fitsHeaderData=None, secondExposeCommand=None):
   sanityCheck()
   clear()
   print "Setting FITS headers %s" % fitsHeaderData
   fp.setHeaderKeywords(fitsHeaderData)
   imageName = fp.startIntegration()
   print "Image name: %s" % imageName
   if exposeCommand:
      exposeCommand()
   if secondExposeCommand:
      bot_bench.setSpotFilter('open') # change to actual name for an open spot
      secondExposeCommand()
   fp.endIntegration()
   if autoSave:
     return (imageName, fp.waitForFitsFiles(imageTimeout))
   else:
     fp.waitForImages(imageTimeout)
     return (imageName, None)   

def rafts():
   #TODO: Should not be hardwired
   return [fp.R10(), fp.R22() ]

def rebs():
   result = []
   for r in rafts():
      result += [r.Reb0(), r.Reb1(), r.Reb2()]
   return result

def aspics():
   result = []
   for r in rebs():
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
   
