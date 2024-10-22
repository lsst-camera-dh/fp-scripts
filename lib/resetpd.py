from __future__ import print_function
import os
import sys
import glob
import time
from java.time import Duration
from collections import namedtuple
import logging
import re
import datetime
from org.lsst.ccs.command import CommandInvocationException

try:
    import java.lang
except ImportError:
    print("could not import java.lang")
from ccs_scripting_tools import CcsSubsystems, CCS
from ccs import aliases
from ccs import proxies

#bbsub = CCS.attachProxy("bot-bench")
bbsub = CCS.attachProxy("ccob")

##
##  The bleow 3 lines are needed for workaround.
devName   = "PhotoDiode"
bbsub.PhotoDiode = bbsub.PhotoDiode
agentName = bbsub.getAgentProperty("agentName")
#if  agentName != "bot-bench":
#    bbsub = CCS.attachProxy(agentName) # re-attach to ccs subsystem
#if  agentName == "ts8-bench":
#    bbsub.PhotoDiode = bbsub.Monitor2
#    devName = "Monitor2"
#bbsub_PhotoDiode = CCS.attachSubsystem("ts8-bench/Monitor")

cmds = """
reset
send :INP:STAT ON
waitAccum 20
send TRAC:FEED:CONT NEV
send :TRIG:SOUR TIM
send :TRIG:TIM 0.02
send :SENS:CURR:MED:RANK 1
send :SENS:CURR:MED:STAT 1
"""


for acmd in cmds.split("\n"):
	if len(acmd)==0:
		continue
	cmdtobeissued ="%s %s" % ( devName, acmd ) 
	print(cmdtobeissued)
	splitted = acmd.split()
	func = getattr(bbsub.PhotoDiode(),splitted[0])
	if len(splitted)==1:
		func()
	elif splitted[0]=="waitAccum":
		try:
			func(java.lang.Integer(splitted[1]),timeout=Duration.ofSeconds(60))
		except CommandInvocationException as ex:
			print( ex.getMessage() )

	else:
		func(" ".join(splitted[1:]))
