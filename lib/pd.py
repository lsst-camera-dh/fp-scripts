"""
BOT PD module
"""
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

try:
    import java.lang
except ImportError:
    print("could not import java.lang")
#from org.lsst.ccs.scripting import CCS
from ccs_scripting_tools import CcsSubsystems, CCS
from ccs import aliases
from ccs import proxies

bbsub = CCS.attachProxy("ccob")

##  The below 3 lines are needed for workaround.
#agentName = "ts8-bench"
#devName   = "PhotoDiode"
agentName = bbsub.getAgentProperty("agentName")
bbsub = CCS.attachProxy(agentName) # re-attach to ccs subsystem
if  agentName == "ts8-bench":
    bbsub.PhotoDiode = bbsub.Monitor2
    devName = "Monitor2"
# use Monitor2 anyway for both ts8-bench and bot-bench
#bbsub.PhotoDiode = bbsub.Monitor
#devName = "Monitor"

#bbsub_PhotoDiode = CCS.attachSubsystem("ts8-bench/Monitor")

__all__ = ["PhotodiodeReadout","logger"]

CCS.setThrowExceptions(True)

logging.basicConfig(format="%(message)s",
                    level=logging.INFO,
                    stream=sys.stdout)
logger = logging.getLogger()

# waiting for keysight update
doavg = False

dopauses = False

nreads = 0
nplc = 0

class PhotodiodeReadout(object):
    """
    Class to handle monitoring photodiode readout.
    """
    def __init__(self, exposure, max_reads=100000):
        print(" **************************** ")
        print(" PD readout exposure time requested = ",exposure)
        exptime = 1.0 * exposure
        """
        Parameters
        ----------
        exptime : float
            Exposure time in seconds for the frame to be taken.
        eo_acq_object : EOAcquisition object
            An instance of a subclass of EOAcquisition.
        max_reads : int, optional
            Maximum number of reads of monitoring photodiode.  Default: 100000.
        """

        buffertime = 3.0
#        buffertime = 0.0


        # for exposures over 0.5 sec, nominal PD readout at 60Hz,
        # otherwise 240Hz

        self.nplc = .1
#        if exptime > 0.5:
#            self.nplc = 1.0
#        else:
#            self.nplc = 0.25

# a value of 5 was used before
        self.navg = int(1)

# add a buffer to duration of PD readout
        total_time = exptime + buffertime

# adjust navg so that it gets below max_reads


        if doavg:
            self.nreads = max_reads*2 

            while self.nreads > max_reads:
		self.nreads = int(total_time*60./self.nplc/self.navg)
		if self.nreads<max_reads:
			break
		self.navg = self.navg + 1
        else :
            self.nreads = min(total_time*60./self.nplc, max_reads)
        # adjust PD readout when max_reads is reached
        # (needs to be between 0.001 and 60 - add code to check)
            self.nplc = total_time*60.0/self.nreads

        print("self.nreads = ",self.nreads," self.navg = ",self.navg," self.nplc = ",self.nplc)
        self.nreads = int(self.nreads)

        pd_result = None
        self.start_time = None

    def start_accumulation(self):
        """
        Start the asynchronous accumulation of photodiode current readings.
        """


        bbsub.PhotoDiode().setCurrentRange(2e-8)
        bbsub.PhotoDiode().clrbuff()
        logger.info("AVER settings are happening with navg = %d",self.navg)

        if doavg:
            bbsub.PhotoDiode().setNAvg(self.navg)
            bbsub.PhotoDiode().setAvgOn(True)

        # start accummulating current readings
        logger.info("accumPDBuffer being called with self.nreads = %d and self.nplc = %f and self.navg = %d",self.nreads,self.nplc,self.navg)

        bbsub.PhotoDiode().setRate(self.nplc)
#        pd_result = bbsub.PhotoDiode().accumBuffer(self.nreads,self.nplc*self.navg)
        time0 = time.time()
        if dopauses :
            if (self.nreads<100) :
                bbsub.PhotoDiode().accumBuffer(self.nreads,self.nplc*self.navg,asynch=True)
            else:
                bbsub.sendAsynchCommand("%s accumBuffer %d %f %d %f" % (devName,int(0.10*self.nreads),self.nplc*self.navg,1,0.80*(self.nreads*self.nplc*self.navg/60.)) )
#            bbsub.PhotoDiode().accumBuffer(int(0.05*self.nreads),self.nplc*self.navg,1,0.90*(self.nreads*self.nplc*self.navg/60.),asynch=True)
        else :
            bbsub.PhotoDiode().accumBuffer(self.nreads,self.nplc*self.navg,asynch=True)
#        bbsub.sendAsynchCommand("%s accumBuffer %d %f" % (devName,self.nreads,self.nplc*self.navg))
        self.start_time = time.time()
        logger.info("time used for asynch call to accumbuffer = %f", self.start_time-time0)
        logger.info("Photodiode readout accumulation started at %f",
                         self.start_time)

        astart = time.time()
        running = False

# --- keeping around until proven that it is no longer needed ------------
#        time.sleep(0.05)
#        while not running:
##            time.sleep(0.25)
#            try:
#
#                running = bbsub.PhotoDiode().isAccumInProgress()
#                if not running :
#                    time.sleep(0.10)
#            except StandardError as eobj:
#                logger.info("PhotodiodeReadout.start_accumulation:")
#                logger.info(str(eobj))
#            except :
#                logger.info("isPDAccumInProgress command rejected")
#
#            logger.info("Photodiode checking that accumulation started at %f",
#                         time.time() - self.start_time)

        print("Time spent checking that accumulation started = ",(time.time()-astart)/1000.0)

    def write_readings(self, destination_spec, seqno='000000', dtstr=datetime.date.today().strftime('%Y%m%d')):
        """
        Output the accumulated photodiode readings to a text file.
        """

        self.destination = destination_spec
        logger.info("PD destination directory = %s",self.destination)

        # make sure Photodiode readout has had enough time to run
        pd_filename = os.path.join(self.destination,"Photodiode_Readings_%s_%s.txt" % (dtstr,seqno))

        print("The ultimate pd filename is ",pd_filename)

        logger.info("Photodiode about to be readout at %f",
                         time.time() - self.start_time)
        start_read = time.time()
#        readTimeout = Duration.ofSeconds(59)
        readTimeout = Duration.ofSeconds(120)
        result = bbsub.PhotoDiode().readBuffer( pd_filename, timeout=readTimeout)
        logger.info("PD_complete_at %f nreads= %d nplc= %f read_time= %f",
                         time.time()-self.start_time,self.nreads,self.nplc,time.time()-start_read)


        return pd_filename

