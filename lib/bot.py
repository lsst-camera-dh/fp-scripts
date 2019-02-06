#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.scripting import ScriptingStatusBusListener
from org.lsst.ccs.bus.states import AlertState
from java.time import Duration
from ccs import proxies
import time

try:
  bot = CCS.attachProxy("bot-motorplatform")
except:
  print "BOT subsystem not available, attempting to continue"

def sanityCheck():
   state = bot.getState()
   alert = state.getState(AlertState)
   if alert!=AlertState.NOMINAL:
      print "WARNING: bot-motorplatform subsystem is in alert state %s" % alert

def setLampOffset(x=0, y=0):
   sanityCheck()
   print "Setting BOT lamp offset (%g,%g)" % (x,y)
   bot.setLampOffset(x,y)

def moveTo(x=0, y=0):
   sanityCheck()
   print "Moving BOT lamp to (%g,%g)" % (x,y)
   bot.setLampPosition(x,y)
   waitForMove()
   
def waitForMove():
   ll = LampListener()
   startListener(ll)
   while ll.isMoving:
     time.sleep(0.01)
   stopListener(ll)

class LampListener(ScriptingStatusBusListener):
   def __init__(self):
     self.isMoving = True

   def onStatusBusMessage(self, msg):
     ls = msg.getBusMessage().getSubsystemData().getValue()
     moving = ls.isMoving()
     self.isMoving = moving

def startListener(ll):
  CCS.addStatusBusListener(ll, lambda msg : msg.getOrigin() == "bot-motorplatform" and msg.getClassName()=="org.lsst.ccs.bus.messages.StatusSubsystemData" and msg.getBusMessage().getDataKey()=="LampStatus")

def stopListener(ll):
  CCS.removeStatusBusListener(ll)


