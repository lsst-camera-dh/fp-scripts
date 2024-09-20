import os
import time
import config
import sys
import re
import fp
import ccob
#import bot
import math
from pd import PhotodiodeReadout
from org.lsst.ccs.utilities.location import LocationSet
import jarray
from java.lang import String
from org.lsst.ccs.scripting import CCS
from ccob_thin import (X, Y, U, B, CcobThin)
from ccs import aliases
from ccs import proxies
from java.time import Duration
import functools
# Needed for writing ecsv file
from org.lsst.ccs.subsystem.imagehandling.data import ECSVFile
from org.lsst.ccs.subsystem.imagehandling.data import AdditionalFile
from org.lsst.ccs.subsystem.imagehandling.data.ECSVFile import Column
from org.lsst.ccs.imagenaming import ImageName
from org.lsst.ccs.bus.messages import StatusSubsystemData
from org.lsst.ccs.bus.data import KeyValueData


# This is a global variable, set to zero when the script starts, and updated monotonically (LSSTTD-1473)
test_seq_num = 0

SPACE_MATCHER = re.compile(r"\s+(?=(?:[^\"']*[\"'][^\"']*[\"'])*[^\"']*$)")

class TestCoordinator(object):
    ''' Base (abstract) class for all tests '''
    def __init__(self, options, test_type, image_type):
        self.run = options['run']
        self.symlink = options['symlink']
        self.skip = options.getInt('skip', 0)
        self.limit = self.skip + options.getInt('limit', 10000000)
        self.noop = self.skip > 0
        self.test_type = test_type
        self.image_type = image_type
        self.annotation = options.get('annotation','')
        self.locations = LocationSet(options.get('locations',''))
        self.clears = options.getInt('clears', 1)
        self.extra_delay = options.getFloat('extradelay', 0)
        # Supported shutter modes for main camera
        # None -- do nothing, leave the shutter in whatever state it is in
        # Normal -- open and close the shutter on each image acquisition
        # Open -- open shutter and leave it open
        self.shutterMode = options.get('shutter', None)
        self.exposeTime = None
        fp.checkShutterStatus(self.shutterMode)
        # TODO: Make this a one-time option??
        self.roiSpec = options.get('roispec')

        self.darkInterrupt = options.getBool('darkinterrupt',None)
        if self.darkInterrupt:
            self.darkInterruptDarkList = options.getList('darkinterruptdarklist') # This should be formatted in the same way as 'dark' is on usual dark config
            ## Shutter state for Darks?
            # self.darkInterruptShutter = options.get("darkShutter") # Will the flat pairs now not update the shutter state?
        else:
            self.darkInterruptDarkList = None


    def take_images(self):
        pass

    def take_bias_images(self, count):
        for i in range(count):
            self.take_bias_image()

    def create_fits_header_data(self, exposure, image_type):
        data = {'ExposureTime': exposure, 'TestType': self.test_type, 'ImageType': image_type, 'TestSeqNum': test_seq_num}
        if self.run:
            data.update({'RunNumber': self.run})
        return data

    def take_bias_image(self):
        return self.__take_image(0, None, image_type='BIAS')

    def symlink_test_type(self, test_type):
        return test_type.lower()

    def symlink_image_type(self, image_type):
        return image_type.lower()

    def take_image(self, exposure, expose_command, image_type=None, symlink_image_type=None):
        return self.__take_image(exposure, expose_command, image_type, symlink_image_type)

    # This is the method that actually does the work
    #
    def __take_image(self, exposure, expose_command, image_type=None, symlink_image_type=None):
        image_type = image_type if image_type else self.image_type
        symlink_image_type = symlink_image_type if symlink_image_type else self.symlink_image_type(image_type)
        global test_seq_num
        if test_seq_num >= self.limit:
            print "Stopping since --limit reached before tSeqNum = %d" % test_seq_num
            sys.exit()

        if self.extra_delay > 0:
            print "Extra delay %g" % self.extra_delay
            time.sleep(self.extra_delay)

        if not self.noop:
            fits_header_data = self.create_fits_header_data(exposure, image_type)
            image_name, file_list = fp.takeExposure(expose_command, fits_header_data, self.annotation, self.locations, self.clears, shutterMode=self.shutterMode, exposeTime=self.exposeTime, imageType=image_type, roiSpec=self.roiSpec)
            self.create_symlink(file_list, self.symlink_test_type(self.test_type), symlink_image_type)
            test_seq_num += 1
            return (image_name, file_list)
        else:
            test_seq_num += 1
            self.noop = test_seq_num < self.skip
            return (None, None)

    def create_symlink(self, file_list, test_type, image_type):
        ''' Create symlinks for created FITS files, based on the specification here:
            https://confluence.slac.stanford.edu/x/B244Dg
        '''
        if not file_list: # Indicates --nofits option was used, or no file list is available (when using MCM that is always the case)
            return
        print "Saved %d FITS files to %s" % (file_list.size(), file_list.getCommonParentDirectory())
        if self.symlink:
            symname = "%s/%s_%s_%03d" % (self.symlink, test_type, image_type, test_seq_num)
            if not os.path.exists(self.symlink):
                os.makedirs(self.symlink)
            os.symlink(file_list.getCommonParentDirectory().toString(), symname)
            print "Symlinked from %s" % symname

class BiasTestCoordinator(TestCoordinator):
    ''' A TestCoordinator for taking only bias images '''
    def __init__(self, options):
        super(BiasTestCoordinator, self).__init__(options, 'BIAS', 'BIAS')
        self.count = options.getInt('count', 10)

    def take_images(self):
        self.take_bias_images(self.count)

class BiasPlusImagesTestCoordinator(TestCoordinator):
    ''' Base class for all tests that involve n bias images per test image'''
    def __init__(self, options, test_type, image_type):
        super(BiasPlusImagesTestCoordinator, self).__init__(options, test_type, image_type)
        self.bcount = int(options.get('bcount', '1'))

    def take_bias_plus_image(self, exposure, expose_command, image_type=None, symlink_image_type=None):
        self.take_bias_images(self.bcount)
        return self.take_image(exposure, expose_command, image_type, symlink_image_type)

class DarkTestCoordinator(BiasPlusImagesTestCoordinator):
    ''' A TestCoordinator for darks '''
    def __init__(self, options):
        super(DarkTestCoordinator, self).__init__(options, 'DARK', 'DARK')
        self.darks = options.getList('dark')

    def take_images(self):
        for dark in self.darks:
            integration, count = dark.split()
            integration = float(integration)
            count = int(count)
            expose_command = lambda: time.sleep(integration)

            for d in range(count):
                self.take_bias_plus_image(integration, expose_command)

class RampTestCoordinator(BiasPlusImagesTestCoordinator):
    ''' A TestCoordinator for ramps '''
    def __init__(self, options):
        super(RampTestCoordinator, self).__init__(options, 'RAMP', 'RAMP')
        self.ramps= options.getList('ramp')
        self.led= options.get('led','uv')
        self.current= options.getFloat('current',0.02)

        ccob.turnOnLed(self.led,self.current)

    def take_images(self):
        for ramp in self.ramps:
            integration, count = ramp.split()
            integration = float(integration)
            count = int(count)
            expose_command = lambda: time.sleep(integration)

            for d in range(count):
                self.take_bias_plus_image(integration, expose_command)
        print("LED is turned off")
        ccob.turnOffLed()


class FlatFieldTestCoordinator(BiasPlusImagesTestCoordinator):
    ''' A TestCoordinator for all tests that involve taking flatS with the flat field generator '''
    def __init__(self, options, test_type, image_type):
        super(FlatFieldTestCoordinator, self).__init__(options, test_type, image_type)
        self.bcount = options.getInt('bcount', 1)
        self.use_photodiodes = True
        self.hilim = options.getFloat('hilim',999.0)
        self.lolim = options.getFloat('lolim',1.0)
        self.ledConfigFile = options.get('filterconfig','filter.cfg')
        self.ledConfig = config.Config(dict(config.parseConfig(self.ledConfigFile).items('WBLED')))
        self.currentConfig = config.Config(dict(config.parseConfig(self.ledConfigFile).items('WBCURRENT')))
        self.camerashutter=options.get('camerashutter')
        self.ccobmode=options.get('ccobmode')
        self.exposure = options.getFloat('exposure',15.0)
        self.led = None
        self.current = None
        if self.ccobmode is not "spanShutter":
            self.expose_command = self.waitForShutter
        else:
            self.expose_command = self.spanShutter

        self.extra_delay_for_pd=self.extra_delay
        self.extra_delay=0.

        if not self.ledConfig:
           raise Exception("Missing filter config file: %s" % self.ledConfigFile)

    # Insert additional CCOB specific FITS file data
    def create_fits_header_data(self, exposure, image_type):
        data = super(FlatFieldTestCoordinator, self).create_fits_header_data(exposure, image_type)
        if image_type != 'BIAS' and image_type != 'DARK':
            data.update({
			'CCOBLED': self.wl_led,
			'CCOBCURR': self.current,
			'CCOBFLASHT': self.flashtime,
			'TGTFLUX': self.e_per_pixel
			})
        return data

    def take_image(self, exposure, expose_command, image_type=None, symlink_image_type=None):
        if self.extra_delay_for_pd > 0:
            print "Extra delay with PD %g" % self.extra_delay_for_pd
            time.sleep(self.extra_delay_for_pd)

        use_pd = self.use_photodiodes and not self.noop
        if use_pd:
            pd_readout = PhotodiodeReadout(exposure)
            pd_readout.start_accumulation()

        if self.roiSpec is not None:
            # guider mode uses exposeTime (for mcm) instead of exposure (for the fp-script shutter control)
            self.exposeTime = self.exposure

        image_name, file_list = super(FlatFieldTestCoordinator, self).take_image(exposure, expose_command, image_type, symlink_image_type)
        if use_pd:
            # TODO: Why does this need the last argument - in fact it is not used?
            pd_readout.send_readings(image_name)
        return (image_name, file_list)

    def spanShutter(self, exposure):
        print "Span mode"
        ccob.turnOnLed(self.wl_led,self.current)
        # open the shutter
        time.sleep(exposure)
        ### is there a way to check if the shutter closed?
        ccob.turnOffLed()

    def waitForShutter(self, exposure):
        print "CCOB will flash %s for %g sec with %g A" % ( self.wl_led, self.flashtime, self.current  )
        print "Flash mode"

        if self.roiSpec is None:
            return ccob.flashAndWait(self.wl_led, self.current, self.flashtime, exposure)
        else:
            return ccob.flash(self.wl_led, self.current, self.flashtime)

    def compute_current(self, wl_led, e_per_pixel):
        e_per_pixel = float(e_per_pixel)
        source = self.ledConfig.getFloat("source")
        wlf = self.ledConfig.getFloat(wl_led.lower())
        m,b = self.currentConfig.getList(wl_led)[0].split()
        targetexp = 1. # target exposure time
        current=10**(int(math.log10(max(e_per_pixel/source/(targetexp)/wlf-float(b),1)/float(m))))
        return max(min(current,0.273),0.002)

    def compute_exposure_time(self, current, wl_led, e_per_pixel):
        #### compute exposure time based on an emprical polynomial of brightness as a function of currents
        e_per_pixel = float(e_per_pixel)
        self.e_per_pixel=e_per_pixel
        source = self.ledConfig.getFloat("source")
        wlf = self.ledConfig.getFloat(wl_led.lower())
        m,b= self.currentConfig.getList(wl_led)[0].split()
        seconds = e_per_pixel/source/(current*float(m)+float(b))/wlf
        if seconds>self.hilim:
           print "Warning: exposure time %g > hilim (%g)" % (seconds, self.hilim)
           seconds = self.hilim
        if seconds<self.lolim:
           print "Warning: exposure time %g < lolim (%g)" % (seconds, self.lolim)
           seconds = self.lolim
        print "Computed Exposure %g for nd=%s wl=%s e_per_pixel=%g" % (seconds, current, wl_led, e_per_pixel)
        return seconds

class FlatPairTestCoordinator(FlatFieldTestCoordinator):
    ''' A TestCoordinator for flat pairs'''
    def __init__(self, options):
        super(FlatPairTestCoordinator, self).__init__(options, 'FLAT', 'FLAT')
        self.wl_led = options.get('wl')
        self.flats = options.getList('flat')

    def take_images(self):
        for flat in self.flats:
            ret = flat.split()
            self.exposure = float(ret[0])
            e_per_pixel = float(ret[1])
            if len(ret)==3:
               self.current = float(ret[2])
            else:
               self.current = self.compute_current(self.wl_led, e_per_pixel)
            self.flashtime = self.compute_exposure_time(self.current, self.wl_led, e_per_pixel)

            expose_command = lambda: self.expose_command(self.exposure)

            if not self.noop or self.skip - test_seq_num < self.bcount + 2:
                pass
            self.take_bias_images(self.bcount)
            for pair in range(2):
                self.take_image(self.exposure, expose_command, symlink_image_type='%s_%s_%s_flat%d' % (self.current, self.wl_led, e_per_pixel, pair))
                # Take darks specified by self.darkInterruptDarkList
                if self.darkInterrupt:
                    if self.darkInterruptDarkList.__contains__(",\n"):
                        self.darkInterruptDarkList = self.darkInterruptDarkList.split(",\n")
                    for darkEntry in self.darkInterruptDarkList:    
                        dark_expTime = float(darkEntry.split(" ")[0]) # Exposure time of one dark image
                        dark_imgNum = int(darkEntry.split(" ")[1]) # Number of exposures
                        for num in range(dark_imgNum): 
                            self.take_image(dark_expTime, expose_command, image_type="DARK", symlink_image_type=None) # Need to update the symlink, and will need formatting of the symlink
                            # This will use the same expose_command as the flat image - is that ok? Or should we set it to the sleep command?

class SuperFlatTestCoordinator(FlatFieldTestCoordinator):
    def __init__(self, options):
        super(SuperFlatTestCoordinator, self).__init__(options, 'SFLAT', 'FLAT')
        self.sflats = options.getList('sflat')

    def create_fits_header_data(self, exposure, image_type):
        data = super(SuperFlatTestCoordinator, self).create_fits_header_data(exposure, image_type)
        if image_type != 'BIAS':
            data.update({
			'FILTER1': self.fluxlevel
			})
        return data

    def approx_equals(self, a, b):
        return (a-b)/(a+b) < .2

    def low_or_high(self, e_per_pixel):
        if self.approx_equals(e_per_pixel, 1000):
            self.test_type="SFLAT_LO"
            self.fluxlevel="LOW"
            return 'L'
        elif self.approx_equals(e_per_pixel, 50000):
            self.test_type="SFLAT_HI"
            self.fluxlevel="HIGH"
            return 'H'
        else:
            self.test_type="SFLAT_?"
            self.fluxlevel="?"
            return '?'

    def take_images(self):
        for sflat in self.sflats:
            ret = sflat.split()
            self.wl_led = ret[0]
            e_per_pixel = float(ret[1])
            count = float(ret[2])
            if len(ret)==4:
                self.current=float(ret[3])
            else:
                self.current = self.compute_current(self.wl_led, e_per_pixel)

            count = int(count)
            e_per_pixel = float(e_per_pixel)
            self.flashtime = self.compute_exposure_time(self.current, self.wl_led, e_per_pixel)
            expose_command = lambda: self.expose_command(self.exposure)
            if not self.noop or self.skip - test_seq_num < count*(self.bcount + 1):
                pass
            for c in range(count):
                self.take_bias_plus_image(self.exposure, expose_command, symlink_image_type='flat_%s_%s'% (self.wl_led, self.low_or_high(e_per_pixel)))

class LambdaTestCoordinator(FlatFieldTestCoordinator):
    def __init__(self, options):
        super(LambdaTestCoordinator, self).__init__(options, 'LAMBDA', 'FLAT')
        self.imcount = int(options.get('imcount', 1))
        self.lambdas = options.getList('lambda')

    def create_fits_header_data(self, exposure, image_type):
        data = super(LambdaTestCoordinator, self).create_fits_header_data(exposure, image_type)
        if image_type != 'BIAS':
            data.update({
			'FILTER1': self.wl_led
			})
        return data

    def take_images(self):
        for lamb in self.lambdas:
            ret = lamb.split()
            self.wl_led = ret[0]
            e_per_pixel = float(ret[1])
            if len(ret)==3:
                self.current = float(ret[2])
            else:
                self.current = self.compute_current(self.wl_led, e_per_pixel)
            self.flashtime = self.compute_exposure_time(self.current, self.wl_led, e_per_pixel)
            expose_command = lambda: self.expose_command(self.exposure)
            if not self.noop or self.skip - test_seq_num < self.bcount + 1:
                pass
            self.take_bias_plus_image(self.exposure, expose_command, symlink_image_type='flat_%s_%s' % (self.wl_led, e_per_pixel))

class PersistenceTestCoordinator(FlatFieldTestCoordinator):
    ''' A TestCoordinator for all tests that involve taking persitence with the flat field generator '''
    def __init__(self, options):
        super(PersistenceTestCoordinator, self).__init__(options, "BOT_PERSISTENCE", "FLAT")
        self.bcount = options.getInt('bcount', 10)
        self.wl_led = options.get('wl')
        self.persistence= options.getList('persistence')

    def take_images(self):
        e_per_pixel, n_of_dark, exp_of_dark, t_btw_darks= self.persistence[0].split()
        e_per_pixel = float(e_per_pixel)
        self.current = self.compute_current(self.wl_led, e_per_pixel)
        self.flashtime = self.compute_exposure_time(self.current, self.wl_led, e_per_pixel)

        # bias acquisitions
        self.take_bias_images(self.bcount)

        # dark acquisition
        expose_command = lambda: self.expose_command(self.exposure)
        image_name, file_list = super(PersistenceTestCoordinator, self).take_image(self.exposure, expose_command, "FLAT",  symlink_image_type='flat_%s'% (self.wl_led))

        # dark acquisition
        self.use_photodiodes = False
        for i in range(int(n_of_dark)):
            if not self.noop:
                time.sleep(float(t_btw_darks))
            super(PersistenceTestCoordinator, self).take_image(float(exp_of_dark), lambda: time.sleep(float(exp_of_dark)), image_type="DARK")
        return (image_name, file_list)

class Fe55TestCoordinator(FlatFieldTestCoordinator):
    def __init__(self, options):
        super(Fe55TestCoordinator, self).__init__(options, 'FE55_FLAT', 'FE55')
        self.flats = options.getList('flat')
        (fe55exposure, fe55count) = options.get('count').split()
        self.fe55exposure = float(fe55exposure)
        self.fe55count = int(fe55count)
        self.current = options.get('nd')
        self.use_photodiodes = False

    def create_fits_header_data(self, exposure, image_type):
        data = super(Fe55TestCoordinator, self).create_fits_header_data(exposure, image_type)
        if image_type != 'BIAS':
            data.update({'ExposureTime2': self.fe55exposure})
        return data

    def take_images(self):
        for flat in self.flats:
            wl_led, e_per_pixel = flat.split()
            exposure = self.compute_exposure_time(self.current, wl_led, e_per_pixel)
            print "exp %s filter %s,%s" % (exposure, wl_led, self.current)
            def expose_command():
                if exposure>0:
                    bot_bench.openShutter(exposure) # Flat
                bot_bench.openFe55Shutter(self.fe55exposure) # Fe55
            if not self.noop or self.skip - test_seq_num < self.fe55count*(self.bcount + 1):
                try:
                    pass
                except:
                    print( "No flat projector installed??? taking an Fe55 image anyway")

            for i in range (self.fe55count):
                self.take_bias_plus_image(exposure, expose_command, symlink_image_type='%s_flat_%s' % (wl_led, e_per_pixel))

class CCOBTestCoordinator(BiasPlusImagesTestCoordinator):
    def __init__(self, options):
        super(CCOBTestCoordinator, self).__init__(options, 'CCOB', 'CCOB')
        self.imcount = int(options.get('imcount', '1'))
        xoffset = float(options.get('xoffset'))
        yoffset = float(options.get('yoffset'))
        bot.setLampOffset(xoffset, yoffset)
        self.exposures = options.getList('expose')
        self.points = options.getList('point')
        self.led = 'unknown'
        self.current = -999

    # Insert additional CCOB specific FITS file data
    def create_fits_header_data(self, exposure, image_type):
        data = super(CCOBTestCoordinator, self).create_fits_header_data(exposure, image_type)
        if image_type != 'BIAS':
            data.update({'CCOBLED': self.led, 'CCOBCURR': self.current})
        return data

    def take_images(self):
        for point in self.points:
            (x, y) = [float(x) for x in point.split()]
            if not self.noop or self.skip - test_seq_num < len(self.exposures)*self.imcount*(self.bcount + 1):
                bot.moveTo(x, y)
            for exposure in self.exposures:
                (self.led, self.current, duration) = exposure.split()
                self.current = float(self.current)
                duration = float(duration)
                def expose_command():
                    adc = ccob.fireLED(self.led, self.current, duration)
                    return {"CCOBADC": adc}
                for i in range(self.imcount):
                    self.take_bias_plus_image(duration, expose_command, symlink_image_type='%s_%s_%s' % (self.led, x, y))

class CCOBNarrowTestCoordinator(BiasPlusImagesTestCoordinator):
    def __init__(self, options):
        super(CCOBNarrowTestCoordinator, self).__init__(options, 'CCOBThin', 'CCOBThin')
        self.imcount = options.getInt('imcount', 1)
        self.bcount = options.getInt('bcount', 1)
        self.shots = options.getList('shots')
        self.shotDarks = options.get('shotdarks')
        self.headers  = options.getList('headers')
        self.calibration_wavelengths = options.getList('calibrate_wavelength')
        self.calibration_duration = options.getFloat('calibrate_duration', 0.2)
        self.ccob_thin = CcobThin("ccob-thin")

    # Insert additional CCOB Narrow specific FITS file data. Called from _take_image
    def create_fits_header_data(self, exposure, image_type):
        data = super(CCOBNarrowTestCoordinator, self).create_fits_header_data(exposure, image_type)
        data.update(self.extraDict)
        data.update({'id': hex(self.nid)})
        return data

    def calibrate(self, wavelengths, duration, image_name):
        dataString = ""

        self.ccob_thin.diodeOn()
        self.ccob_thin.hyperOpenFastShutter()
        self.ccob_thin.picoSetTime(int(duration*1000))
        for wavelength in wavelengths:
           wavelength=float(wavelength)
           self.ccob_thin.hyperSetWavelength(wavelength)
           dataString += "%7g %7g %7g\n" % (duration, wavelength, self.ccob_thin.picoReadCurrent())
        self.ccob_thin.hyperCloseFastShutter()
        self.ccob_thin.diodeOff()
        # convert results to an ecsv file and send to image-handling

        durationColumn = Column("DURATION", "%7g", "float64", "Duration (delta)", "s")
        waveLengthColumn = Column("WAVELENGTH", "%7g", "float64", "Wavelength", "nm")
        valueColumn = Column("CURRENT", "%7g", "float64", "Measured flux", "A")

        ecsvFile = ECSVFile([durationColumn, waveLengthColumn, valueColumn], dataString, "%s_calibrate.ecsv" % image_name, "calibrate", image_name)
        ecsvFile.setDelimiter(" ")

        msg = StatusSubsystemData(KeyValueData(AdditionalFile.EVENT_KEY, ecsvFile))
        CCS.getMessagingAccess().sendStatusMessage(msg)

    def take_images(self):

        for shot,headers in zip(self.shots,self.headers):
            print "SHOTSHOTSHOT"
            print shot
            (b, u, x, y, integ_time, expose_time, lamb, locations, id) = SPACE_MATCHER.split(shot)
            extraHeaders = SPACE_MATCHER.split(headers)
            self.extraDict = {}
            for eh in extraHeaders:
                k,v = eh.split("=")
                self.extraDict[k] = v

            if not self.noop or self.skip - test_seq_num < len(self.exposures)*self.imcount*(self.bcount + 1):
                print "Moving to b=%s u=%s x=%s y=%s lambda=%s, for shot time %s" % (b, u, x, y, lamb, expose_time)
                self.ccob_thin.moveTo(X, float(x), 20)
                time.sleep(1)
                self.ccob_thin.moveTo(Y, float(y), 20)
                time.sleep(1)
                self.ccob_thin.moveTo(B, float(b), 8)
                time.sleep(1)
                self.ccob_thin.moveTo(U, float(u), 15)
                self.ccob_thin.hyperSetWavelength(float(lamb))
                expose_time=int(float(expose_time)*1000)
                print "Move done, now starting shot of length %s ms" % (expose_time)
                self.nid = int(id, 0)
                self.locations = LocationSet(locations.strip('\"'))
                duration = float(integ_time)
                def expose_command():
                    #TODO: Need extra delay?
                    self.ccob_thin.hyperStartFastExposure(expose_time)
                    print "Shot done"
                self.exposeTime = duration
                for i in range(self.imcount):
                    self.nid += 1
                    (last_image_name, file_list) = self.take_bias_plus_image(duration, expose_command, symlink_image_type='%s_%s_%s' % (lamb, x, y))

                if self.shotDarks:
                    print "DARKS"
                    print self.shotDarks

                    integration, count = self.shotDarks.split()
                    self.exposeTime = float(integration)
                    for d in range(int(count)):
                        self.nid += 1
                        (last_image_name, file_list) = self.take_image(self.exposeTime, None, image_type='DARK')

        # Write calibration at end of data taking, using the last imageName
        self.calibrate(self.calibration_wavelengths, self.calibration_duration, last_image_name)


class XTalkTestCoordinator(BiasPlusImagesTestCoordinator):
    def __init__(self, options):
        super(XTalkTestCoordinator, self).__init__(options, 'XTALK', 'XTALK')
        self.imcount = int(options.get('imcount', '1'))
        xoffset = float(options.get('xoffset'))
        yoffset = float(options.get('yoffset'))
        bot.setLampOffset(xoffset, yoffset)
        self.exposures = options.getList('expose')
        self.points = options.getList('point')
        self.signalpersec = float(options.get('signalpersec'))

    def take_images(self):
        for point in self.points:
            splittedpoints = point.split()
            x = float(splittedpoints[0])
            y = float(splittedpoints[1])
            try:
                self.locations = LocationSet(",".join(splittedpoints[2].split("_")))
            except:
                self.locations = None
            if not self.noop or self.skip - test_seq_num < self.exposures*self.imcount*(self.bcount + 1):
                bot.moveTo(x, y)
            for exposure in self.exposures:
                exposure = float(exposure)/self.signalpersec
                expose_command = lambda: bot_bench.openShutter(exposure)
                for i in range(self.imcount):
                    self.take_bias_plus_image(exposure, expose_command, symlink_image_type='%03.1f_%03.1f_%03.1f' % (x, y, exposure))

class SpotTestCoordinator(BiasPlusImagesTestCoordinator):
    def __init__(self, options):
        super(SpotTestCoordinator, self).__init__(options, 'SPOT_FLAT', 'SPOT')
        self.imcount = int(options.get('imcount', '1'))
        self.xoffset = float(options.get('xoffset'))
        self.yoffset = float(options.get('yoffset'))
        self.mask1 = options.get('mask1')
        self.mask2 = options.get('mask2', 'empty6')
#        bot.setLampOffset(xoffset, yoffset)
        self.exposures = options.getList('expose')
        self.points = options.getList('point')
        self.signalpersec = float(options.get('signalpersec'))
        self.stagex = 0
        self.stagey = 0

    def create_fits_header_data(self, exposure, image_type):
        data = super(SpotTestCoordinator, self).create_fits_header_data(exposure, image_type)
        if image_type != 'BIAS':
            data.update({'ExposureTime2': self.exposure2})
        return data

    def set_filter(self, mask_filter):
        bot_bench.setSpotFilter(mask_filter)

    def take_images(self):
        def moveTo( point ):
            """a wrappter to "moveTo" to store the current position so that it can judge if the stage needs to move or not"""
            splittedpoints = point.split()
            x = float(splittedpoints[0])
            y = float(splittedpoints[1])
            if self.stagex == x and self.stagey == y:
                return
            if not self.noop or self.skip - test_seq_num < len(self.exposures)*self.imcount*(self.bcount + 1):
                bot.moveTo(x, y)
                self.stagex = x # store current positions
                self.stagey = y

        for j in range(len(self.points)):
            point = self.points[j]
            moveTo( point )

            try:
                self.locations = LocationSet(",".join(splittedpoints[2].split("_")))
            except:
                self.locations = None

            for exposure in self.exposures:
                (exposure1, exposure2) = exposure.split()
                self.exposure1 = float(exposure1)/self.signalpersec
                self.exposure2 = float(exposure2)/self.signalpersec
                def expose_command(**kwargs):
                    self.set_filter(self.mask1)
                    bot_bench.openShutter(self.exposure1) # this will block until the shutter gets closed
                    if self.exposure2 != 0.:
                        time.sleep(0.1)
                        self.set_filter(self.mask2)
                        bot_bench.openShutter(self.exposure2)
                    if kwargs["move"] is not True or j+1==len(self.points):
                        return kwargs
                    moveTo(self.points[j+1]) # move to the next position
                    return kwargs

                for i in range(self.imcount):

                    self.take_bias_plus_image(self.exposure1, functools.partial(expose_command,move=True if i==len(self.imcount)-1 else False),
                                        symlink_image_type='%03.1f_%03.1f_FLAT_%s_%03.1f_%03.1f' % (x, y, self.mask1, self.exposure1, self.exposure2))

class ScanTestCoordinator(TestCoordinator):
    ''' A TestCoordinator for taking scan-mode images '''
    def __init__(self, options):
        super(ScanTestCoordinator, self).__init__(options, 'SCAN', 'SCAN')
        self.transparent = options.getInt("n-transparent")
        self.scanmode = options.getInt("n-scanmode")
        self.undercols = options.getInt("undercols")
        self.overcols = options.getInt("overcols")
        self.precols = options.getInt("precols")
        self.readcols = options.getInt("readcols")
        self.postcols = options.getInt("postcols")
        self.overcols = options.getInt("overcols")
        self.readcols2 = options.getInt("readcols2")
        self.prerows = options.getInt("prerows")
        self.readrows = options.getInt("readrows")
        self.postrows = options.getInt("postrows")
        self.overrows = options.getInt("overrows")
        # TODO: Work about e2v sensors

    def take_images(self):
        if self.noop or self.skip - test_seq_num < self.scanmode + self.transparent:
            preCols = fp.fp.getSequencerParameter("PreCols")
            readCols = fp.fp.getSequencerParameter("ReadCols")
            readCols2 = fp.fp.getSequencerParameter("ReadCols2")
            postCols = fp.fp.getSequencerParameter("PostCols")
            overCols = fp.fp.getSequencerParameter("OverCols")
            preRows = fp.fp.getSequencerParameter("PreRows")
            readRows = fp.fp.getSequencerParameter("ReadRows")
            postRows = fp.fp.getSequencerParameter("PostRows")
            scanMode = fp.fp.isScanEnabled()
            idleFlushTimeout = fp.fp.getConfigurationParameterValue("sequencerConfig","idleFlushTimeout")
            print "Initial sequencer parameters"

            print "preCols="  , preCols
            print "readCols=" , readCols
            print "readCols2=" , readCols2
            print "postCols=" , postCols
            print "overCols=" , overCols

            print "preRows="  , preRows
            print "readRows=" , readRows
            print "postRows=" , postRows

            print "scanMode=" , scanMode
            print "idleFlushTimeout=" , idleFlushTimeout

            # set up scan mode
            fp.fp.sequencerConfig().submitChanges(
                {
                "underCols":self.undercols,
                "preCols":  self.precols,
                "readCols": self.readcols,
                "readCols2": self.readcols2,
                "postCols": self.postcols,
                "overCols": self.overcols,
                "preRows":  self.prerows,
                "readRows": self.readrows,
                "postRows": self.postrows,
                "overRows": self.overrows,
                "scanMode": True,
                "idleFlushTimeout": -1
                }
            )
            fp.fp.applySubmittedChanges()
            if idleFlushTimeout != -1:
                fp.clear()

        exposure = 1.0
        expose_command = lambda: time.sleep(exposure)

        for i in range(self.scanmode):
           self.take_image(exposure, expose_command, image_type=None, symlink_image_type=None)

        if self.noop or self.skip - test_seq_num < self.transparent:
            fp.fp.sequencerConfig().submitChanges(
                {
                "transparentMode": 1
                }
            )
            timeout= Duration.ofSeconds(60*5)
            fp.fp.applySubmittedChanges(timeout=timeout)

        for i in range(self.transparent):
           self.take_image(exposure, expose_command, image_type=None, symlink_image_type=None)

        # Restore settings
        fp.fp.dropChanges(jarray.array([ 'Sequencer', 'Rafts' ], String ))

        if idleFlushTimeout != -1:
            fp.clear()

def do_bias(options):
    print "bias called %s" % options
    tc = BiasTestCoordinator(options)
    tc.take_images()

def do_dark(options):
    print "dark called %s" % options
    tc = DarkTestCoordinator(options)
    tc.take_images()

def do_ramp(options):
    print "ramp called %s" % options
    tc = RampTestCoordinator(options)
    tc.take_images()

def do_flat(options):
    print "flat called %s" % options
    tc = FlatPairTestCoordinator(options)
    tc.take_images()

# This is what Seth's document calls fe55+flat, but Aaron's config calls FE55
def do_fe55(options):
    print "fe55 called %s" % options
    tc = Fe55TestCoordinator(options)
    tc.take_images()

def do_persistence(options):
    print "Persistence called %s" % options
    tc = PersistenceTestCoordinator(options)
    tc.take_images()

def do_sflat(options):
    print "superflat called %s" % options
    tc = SuperFlatTestCoordinator(options)
    tc.take_images()

def do_lambda(options):
    print "lambda called %s" % options
    tc = LambdaTestCoordinator(options)
    tc.take_images()

def do_ccob(options):
    print "ccob called %s" % options
    tc = CCOBTestCoordinator(options)
    tc.take_images()

# This does not actually result in any images.
# Is treating it as a separate test type appropriate?
def do_ccob_pd_calibrate(options):
    print "ccob pd calibrate called %s" % options
    tc = CCOBThinCalibrateTestCoordinator(options)
    tc.take_images()

def do_ccob_narrow(options):
    print "ccob narrow called %s" % options
    tc = CCOBNarrowTestCoordinator(options)
    tc.take_images()

def do_xtalk(options):
    print "xtalk called %s" % options
    tc = XTalkTestCoordinator(options)
    tc.take_images()

def do_spot(options):
    print "spot called %s" % options
    tc = SpotTestCoordinator(options)
    tc.take_images()

def do_scan(options):
    print "scan called %s" % options
    tc = ScanTestCoordinator(options)
    tc.take_images()

def do_one_time_config(options):
    print "one_time_config called %s" % options
    if "idle_flush" in options:
        idle_flush = options.getBool("idle_flush")
        fp.fp.sequencerConfig().change("idleFlushTimeout", 0 if idle_flush else -1)
