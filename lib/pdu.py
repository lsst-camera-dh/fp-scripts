#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState
from org.lsst.ccs.utilities.taitime import CCSTimeStamp
from java.time import Duration
from ccs import proxies
import time
from threading import Thread
import time


pdu = CCS.attachProxy("pap-pdu")
driver = pdu.PDU120()
outlet="CCOB-Narrow"

def getStatus():
	return driver.getOutletNames()


def turnOn(outlet):
	if driver.isOutletOn(outlet)==True:
		return
	driver.forceOutletOn(outlet)
	print("waiting...")
	time.sleep(5)	# arbitrary wait time


def turnOff(outlet):
	if driver.isOutletOn(outlet)==False:
		return
	driver.forceOutletOff(outlet)

if __name__ == "__main__":
	turnOn(outlet)
	print(getStatus())
