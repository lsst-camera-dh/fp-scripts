#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState
from java.time import Duration
from ccs import proxies

bot = CCS.attachProxy("bot-motorplatform")

def sanityCheck():
   alerts = bot.getRaisedAlertSummary()
   if alerts.alertState!=AlertState.NOMINAL:
      print "WARNING: bot-motorplatform subsystem is in alarm state %s" % alerts.alertState 

def setLampOffset(x=0, y=0):
   sanityCheck()
   print "Setting BOT lamp offset (%g,%g)" % (x,y)
   bot.setLampOffset(x,y)

def moveTo(x=0, y=0):
   sanityCheck()
   print "Moving BOT lamp to (%g,%g)" % (x,y)
   bot.setLampPosition(x,y)
   # TODO: Wait until we are there
   
