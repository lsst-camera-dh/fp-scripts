#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.scripting import ScriptingStatusBusListener
from org.lsst.ccs.bus.states import AlertState
from java.time import Duration
from ccs import proxies
import time

try:
  bot = CCS.attachProxy("bot-motorplatform")
  agentName = bot.getAgentProperty("agentName")

except:
  print "%s not available, attempting to continue" % ( agentName )
#  raise

def sanityCheck():
   state = bot.getState()
   alert = state.getState(AlertState)
   if alert!=AlertState.NOMINAL:
      print "WARNING: bot-motorplatform subsystem is in alert state %s" % alert

def setLampOffset(x=0, y=0):
   sanityCheck()
   print "Setting BOT lamp offset (%g,%g)" % (x,y)
   bot.enable("X")
   bot.enable("Y")
   if agentName == "bot-motorplatform":
      bot.setLampOffset(x,y)
      waitForMove()
   else:
      for axis, value in [ ( "X", x ), ( "Y", y ) ]:
         bot.moveBy(axis,value,10)
         waitForMove(axis)
   bot.disable("X")
   bot.disable("Y")

def moveTo(x=0, y=0):
   sanityCheck()
   print "Moving BOT lamp to (%g,%g)" % (x,y)
   bot.enable("X")
   bot.enable("Y")
   if agentName == "bot-motorplatform":
      bot.setLampPosition(x,y)
      waitForMove()
   else:
      for axis, value in [ ( "X", x ), ( "Y", y ) ]:
         bot.moveTo(axis,value,10)
         waitForMove(axis)
   bot.disable("X")
   bot.disable("Y")
   
def waitForMove(axis=None):
   time.sleep(1)
   ll = LampListener(axis)
   startListener(ll)
   while ll.isMoving:
     time.sleep(0.01)
   stopListener(ll)

class LampListener(ScriptingStatusBusListener):
   def __init__(self,axis=None):
     self.isMoving = True
     self.axis = axis
     ScriptingStatusBusListener.__init__(self)

   def onStatusBusMessage(self, msg):
     ls = msg.getBusMessage().getSubsystemData().getValue()
     moving = ls.isMoving()
     self.isMoving = moving

def startListener(ll):
  if agentName == "bot-motorplatform":
     CCS.addStatusBusListener(ll, lambda msg : msg.getOrigin() == agentName and msg.getClassName()=="org.lsst.ccs.bus.messages.StatusSubsystemData" and msg.getBusMessage().getDataKey()=="LampStatus") 
  else:
     CCS.addStatusBusListener(ll, lambda msg: msg.getOrigin() == agentName and msg.getClassName()=="org.lsst.ccs.bus.messages.StatusSubsystemData" and msg.getBusMessage().getDataKey()=="AxisStatus" and msg.getBusMessage().getSubsystemData().getValue().getAxisName(  ) == ll.axis  )

def stopListener(ll):
  CCS.removeStatusBusListener(ll)


