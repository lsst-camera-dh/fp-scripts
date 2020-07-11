#!/usr/bin/env ccs-script
import sys
import os
sys.path.insert(0,"/gpfs/slac/lsst/fs1/g/data/youtsumi/FullRafts/VoltageOptimization/fp-scripts/lib")
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState
from org.lsst.ccs.subsystem.rafts.data import RaftException
from org.lsst.ccs.command import CommandInvocationException
from org.lsst.ccs.bus.messages import EmbeddedObjectDeserializationException
from java.time import Duration
from ccs import proxies
#import bot_bench
import array
import traceback
from fp import fp

def commandTarget( self, target ):
	ccstarget = self
	for sub in target.split("/"):
		ccstarget = getattr(ccstarget,sub)()
	return ccstarget

setattr(proxies.ccsProxy, "commandTarget", commandTarget )

def setvoltages(avoltage):
	fp = CCS.attachProxy("fp-3rebs")
	for acommandtarget in avoltage:
		fp.submitChanges(acommandtarget,avoltage[acommandtarget])
		print(fp.getSubmittedChangesForComponent(acommandtarget))
	fp.commitBulkChange()
	for acommandtarget in list(set([ os.path.dirname(x) for x in avoltage.keys()])):
		fp.commandTarget(acommandtarget).loadDeltaDacs(False)

if __name__ == "__main__":
	try:
		print(fp.commandTarget("R12/Reb0/Bias0").printConfigurableParameters().keys())
		fp.submitChanges("R12/Reb0/Bias0",{ "csGateP": 0.0 })
		print(fp.getSubmittedChangesForComponent("R12/Reb0/Bias0"))
		print(fp.commandTarget("R12/Reb0/DAC").printConfigurableParameters().keys())
		fp.submitChanges("R12/Reb0/DAC",{ "pclkHighP": 2., "pclkLowP": -8.0 })
		print(fp.getSubmittedChangesForComponent("R12/Reb0/DAC"))
		fp.commitBulkChange()
		fp.commandTarget("R12/Reb0").loadDeltaDacs(False)

	except CommandInvocationException as ex:
		ex.getCause().printStackTrace()

