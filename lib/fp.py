#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState
from java.time import Duration
from ccs import proxies

class FocalPlane(object):

    def __init__(self):
        self.fp = CCS.attachProxy("focal-plane")
        self.autoSave = True
        self.imageTimeout = Duration.ofSeconds(60)

    def sanityCheck(self):
        #biasOn = fp.isBackBiasOn()
        #if not biasOn:
        #  print "WARNING: Back bias is not on"
        state = self.fp.getState()
        alert = state.getState(AlertState)
        if alert != AlertState.NOMINAL:
            print "WARNING: focal-plane subsystem is in alert state %s" % alert

    def clear(self, n=1):
        print "Clearing CCDs (%d)" % n
        self.fp.clear(n)
        self.fp.waitForSequencer(Duration.ofSeconds(10))

    def takeBias(self, fitsHeaderData):
        # TODO: This may not be the best way to take bias images
        # It may be better to define a takeBias command at the subsystem layer, since
        # this could skip the startIntegration/endIntegration and go straight to readout
        return self.takeExposure(fitsHeaderData=fitsHeaderData)

    def takeExposure(self, exposeCommand=None, fitsHeaderData=None):
        self.sanityCheck()
        self.clear()
        print "Setting FITS headers %s" % fitsHeaderData
        self.fp.setPrimaryHeaderKeyword(fitsHeaderData)
        imageName = self.fp.startIntegration()
        print "Image name: %s" % imageName
        if exposeCommand:
            extraData = exposeCommand()
            if extraData:
                self.fp.setPrimaryHeader(extraData)
        self.fp.endIntegration()
        if self.autoSave:
            return (imageName, self.fp.waitForFitsFiles(self.imageTimeout))
        else:
            self.fp.waitForImages(self.imageTimeout)
            return (imageName, None)

    def rafts(self):
        #TODO: Should not be hardwired
        return [self.fp.R10(), self.fp.R22() ]

    def rebs(self):
       result = []
       for r in self.rafts():
         result += [r.Reb0(), r.Reb1(), r.Reb2()]
       return result

    def aspics(self):
       result = []
       for r in self.rebs():
          result += [r.ASPIC0(), r.ASPIC1(), r.ASPIC2(), r.ASPIC3(), r.ASPIC4(), r.ASPIC5() ]
       return result

    def getSequencerParameter(self, name):
        params = []
        for raft in rafts():
           params += raft.getSequencerParameter(name)
        unique = set(params)
        if len(unique)!=1:
           raise "Inconsistent sequencer parameters "+params
        return unqiue.pop()

    def setSequencerParameter(self, name, value):
       for raft in rafts():
          raft.setSequencerParameter(name, value)

    def isScanMode(self):
       result = []
       for reb in rebs():
          result += reg.getRegister(0x330000,1)
       unique = set(result)
       if len(unique)!=1:
          raise "Inconsistent scan mode "+result
       return unique.pop()

    def setScanMode(self, value):
       for reb in rebs():
          reb.setRegister(0x330000, 1 if value else 0) 

    def isTransparentMode(self):
       result = []
       for aspic in aspics():
          result += aspic.getTm()
       unique = set(result)
       if len(unique)!=1:
          raise "Inconsistent transparent mode "+result
       return unique.pop()   

    def setTransparentMode(self, value):
       for aspic in aspics():
          aspic.change(tm,  1 if value else 0)

