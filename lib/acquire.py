import os
import time
import config
import sys
import fp
#import ccob
import bot
from pd import PhotodiodeReadout
from org.lsst.ccs.utilities.location import LocationSet
import jarray
from java.lang import String
from org.lsst.ccs.scripting import CCS
from ccs import aliases
from ccs import proxies
from java.time import Duration
bb = CCS.attachProxy("bot-bench")
agentName = bb.getAgentProperty("agentName")
if  agentName == "ts8-bench":
    import ts8_bench as bot_bench
elif agentName == "bot-bench":
    import bot_bench

# This is a global variable, set to zero when the script starts, and updated monotonically (LSSTTD-1473)
test_seq_num = 0

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
            image_name, file_list = fp.takeExposure(expose_command, fits_header_data, self.annotation, self.locations, self.clears)
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
        if not file_list: # Indicates --nofits option was used
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
        self.take_image(exposure, expose_command, image_type, symlink_image_type)

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

class FlatFieldTestCoordinator(BiasPlusImagesTestCoordinator):
    ''' A TestCoordinator for all tests that involve taking flatS with the flat field generator '''
    def __init__(self, options, test_type, image_type):
        super(FlatFieldTestCoordinator, self).__init__(options, test_type, image_type)
        self.bcount = options.getInt('bcount', 1)
        self.use_photodiodes = True
        self.hilim = options.getFloat('hilim',999.0)
        self.lolim = options.getFloat('lolim',1.0)
        self.filterConfigFile = options.get('filterconfig','filter.cfg')
        self.filterConfig = config.Config(dict(config.parseConfig(self.filterConfigFile).items('FILTER')))
        if not self.filterConfig:
           raise Exception("Missing filter config file: %s" % self.filterConfigFile)

    def set_filters(self, nd_filter, wl_filter):
        bot_bench.setNDFilter(nd_filter)
        bot_bench.setColorFilter(wl_filter)

    def take_image(self, exposure, expose_command, image_type=None, symlink_image_type=None):
        use_pd = self.use_photodiodes and not self.noop
        if use_pd:
            pd_readout = PhotodiodeReadout(exposure)
            pd_readout.start_accumulation()
        image_name, file_list = super(FlatFieldTestCoordinator, self).take_image(exposure, expose_command, image_type, symlink_image_type)
        if use_pd:
            # TODO: Why does this need the last argument - in fact it is not used?
            pd_readout.write_readings(file_list.getCommonParentDirectory().toString(),image_name.toString().split('_')[-1],image_name.toString().split('_')[-2])
        return (image_name, file_list)

    def compute_exposure_time(self, nd_filter, wl_filter, e_per_pixel):
        e_per_pixel = float(e_per_pixel)
        source = self.filterConfig.getFloat("source")
        dnf = self.filterConfig.getFloat(nd_filter.lower())
        wlf = self.filterConfig.getFloat(wl_filter.lower())
        seconds = e_per_pixel/source/dnf/wlf
        if seconds>self.hilim:
           print "Warning: exposure time %g > hilim (%g)" % (seconds, self.hilim)
           seconds = self.hilim
        if seconds<self.lolim:
           print "Warning: exposure time %g < lolim (%g)" % (seconds, self.lolim)
           seconds = self.lolim
        print "Computed Exposure %g for nd=%s wl=%s e_per_pixel=%g" % (seconds, nd_filter, wl_filter, e_per_pixel)
        return seconds

class FlatPairTestCoordinator(FlatFieldTestCoordinator):
    ''' A TestCoordinator for flat pairs'''
    def __init__(self, options):
        super(FlatPairTestCoordinator, self).__init__(options, 'FLAT', 'FLAT')
        self.wl_filter = options.get('wl')
        self.flats = options.getList('flat')

    def take_images(self):
        for flat in self.flats:
            e_per_pixel, nd_filter = flat.split()
            e_per_pixel = float(e_per_pixel)
            exposure = self.compute_exposure_time(nd_filter, self.wl_filter, e_per_pixel)
            expose_command = lambda: bot_bench.openShutter(exposure)
            print "exp %s filter %s" % (exposure, nd_filter)
            if not self.noop or self.skip - test_seq_num < self.bcount + 2:
                self.set_filters(nd_filter, self.wl_filter)
            self.take_bias_images(self.bcount)
            for pair in range(2):
                self.take_image(exposure, expose_command, symlink_image_type='%s_%s_%s_flat%d' % (nd_filter, self.wl_filter, e_per_pixel, pair))

class SuperFlatTestCoordinator(FlatFieldTestCoordinator):
    def __init__(self, options):
        super(SuperFlatTestCoordinator, self).__init__(options, 'SFLAT', 'FLAT')
        self.sflats = options.getList('sflat')

    def approx_equals(self, a, b):
        return (a-b)/(a+b) < .2

    def low_or_high(self, e_per_pixel):
        if self.approx_equals(e_per_pixel, 1000):
            return 'L'
        elif self.approx_equals(e_per_pixel, 50000):
            return 'H'
        else:
            return '?'

    def take_images(self):
        for sflat in self.sflats:
            wl_filter, e_per_pixel, count, nd_filter = sflat.split()
            count = int(count)
            e_per_pixel = float(e_per_pixel)
            exposure = self.compute_exposure_time(nd_filter, wl_filter, e_per_pixel)
            expose_command = lambda: bot_bench.openShutter(exposure)
            if not self.noop or self.skip - test_seq_num < count*(self.bcount + 1):
                self.set_filters(nd_filter, wl_filter)
            for c in range(count):
                self.take_bias_plus_image(exposure, expose_command, symlink_image_type='flat_%s_%s'% (wl_filter, self.low_or_high(e_per_pixel)))

class LambdaTestCoordinator(FlatFieldTestCoordinator):
    def __init__(self, options):
        super(LambdaTestCoordinator, self).__init__(options, 'LAMBDA', 'FLAT')
        self.imcount = int(options.get('imcount', 1))
        self.lambdas = options.getList('lambda')

    def take_images(self):
        for lamb in self.lambdas:
            wl_filter, e_per_pixel, nd_filter = lamb.split()
            exposure = self.compute_exposure_time(nd_filter, wl_filter, e_per_pixel)
            expose_command = lambda: bot_bench.openShutter(exposure)
            if not self.noop or self.skip - test_seq_num < self.bcount + 1:
                self.set_filters(nd_filter, wl_filter)
            self.take_bias_plus_image(exposure, expose_command, symlink_image_type='flat_%s_%s' % (wl_filter, e_per_pixel))

class PersistenceTestCoordinator(FlatFieldTestCoordinator):
    ''' A TestCoordinator for all tests that involve taking persitence with the flat field generator '''
    def __init__(self, options):
        super(PersistenceTestCoordinator, self).__init__(options, "BOT_PERSISTENCE", "FLAT")
        self.bcount = options.getInt('bcount', 10)
        self.wl_filter = options.get('wl')
        self.nd_filter= options.get('nd')
        self.persistence= options.getList('persistence')

    def take_images(self):
        e_per_pixel, n_of_dark, exp_of_dark, t_btw_darks= self.persistence[0].split()
        e_per_pixel = float(e_per_pixel)
        exposure = self.compute_exposure_time(self.nd_filter, self.wl_filter, e_per_pixel)
        self.set_filters(self.nd_filter, self.wl_filter)

        # bias acquisitions
        self.take_bias_images(self.bcount)

        # dark acquisition
        expose_command = lambda: bot_bench.openShutter(exposure)
        image_name, file_list = super(PersistenceTestCoordinator, self).take_image(exposure, expose_command, "FLAT",  symlink_image_type='flat_%s'% (self.wl_filter))

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
        self.nd_filter = options.get('nd')
        self.use_photodiodes = False

    def create_fits_header_data(self, exposure, image_type):
        data = super(Fe55TestCoordinator, self).create_fits_header_data(exposure, image_type)
        if image_type != 'BIAS':
            data.update({'ExposureTime2': self.fe55exposure})
        return data

    def take_images(self):
        for flat in self.flats:
            wl_filter, e_per_pixel = flat.split()
            exposure = self.compute_exposure_time(self.nd_filter, wl_filter, e_per_pixel)
            print "exp %s filter %s,%s" % (exposure, wl_filter, self.nd_filter)
            def expose_command():
                if exposure>0:
                    bot_bench.openShutter(exposure) # Flat
                bot_bench.openFe55Shutter(self.fe55exposure) # Fe55
            if not self.noop or self.skip - test_seq_num < self.fe55count*(self.bcount + 1):
                self.set_filters(self.nd_filter, wl_filter)
            for i in range (self.fe55count):
                self.take_bias_plus_image(exposure, expose_command, symlink_image_type='%s_flat_%s' % (wl_filter, e_per_pixel))

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
            if not self.noop or self.skip - test_seq_num < self.exposures*self.imcount*(self.bcount + 1):
                (x, y) = [float(x) for x in point.split()]
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


class XTalkTestCoordinator(BiasPlusImagesTestCoordinator):
    def __init__(self, options):
        super(XTalkTestCoordinator, self).__init__(options, 'XTALK', 'XTALK')
        self.imcount = int(options.get('imcount', '1'))
        xoffset = float(options.get('xoffset'))
        yoffset = float(options.get('yoffset'))
        bot.setLampOffset(xoffset, yoffset)
        self.exposures = options.getList('expose')
        self.points = options.getList('point')

    def take_images(self):
        for point in self.points:
            if not self.noop or self.skip - test_seq_num < self.exposures*self.imcount*(self.bcount + 1):
                (x, y) = [float(x) for x in point.split()]
                bot.moveTo(x, y)
            for exposure in self.exposures:
                exposure = float(exposure)
                expose_command = lambda: bot_bench.openShutter(exposure)
                for i in range(self.imcount):
                    self.take_bias_plus_image(exposure, expose_command, symlink_image_type='%03.1f_%03.1f_%03.1f' % (x, y, exposure))

class SpotTestCoordinator(BiasPlusImagesTestCoordinator):
    def __init__(self, options):
        super(SpotTestCoordinator, self).__init__(options, 'SPOT_FLAT', 'SPOT')
        self.imcount = int(options.get('imcount', '1'))
        xoffset = float(options.get('xoffset'))
        yoffset = float(options.get('yoffset'))
        self.mask1 = options.get('mask1')
        self.mask2 = options.get('mask2', 'empty6')
        bot.setLampOffset(xoffset, yoffset)
        self.exposures = options.getList('expose')
        self.points = options.getList('point')

    def create_fits_header_data(self, exposure, image_type):
        data = super(SpotTestCoordinator, self).create_fits_header_data(exposure, image_type)
        if image_type != 'BIAS':
            data.update({'ExposureTime2': self.exposure2})
        return data

    def set_filter(self, mask_filter):
        bot_bench.setSpotFilter(mask_filter)

    def take_images(self):
        for point in self.points:
            (x, y) = [float(x) for x in point.split()]
            if not self.noop or self.skip - test_seq_num < len(self.exposures)*self.imcount*(self.bcount + 1):
                bot.moveTo(x, y)
            for exposure in self.exposures:
                (exposure1, exposure2) = exposure.split()
                self.exposure1 = float(exposure1)
                self.exposure2 = float(exposure2)
                def expose_command():
                    self.set_filter(self.mask1)
                    bot_bench.openShutter(self.exposure1)
                    if self.exposure2 != 0.:
                        self.set_filter(self.mask2)
                        bot_bench.openShutter(self.exposure2)

                for i in range(self.imcount):
                    self.take_bias_plus_image(self.exposure1, expose_command, symlink_image_type='%03.1f_%03.1f_FLAT_%s_%03.1f_%03.1f' % (x, y, self.mask, self.exposure1, self.exposure2))

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
        self.prerows = options.getInt("prerows")
        self.readrows = options.getInt("readrows")
        self.postrows = options.getInt("postrows")
        self.overrows = options.getInt("overrows")
        # TODO: Work about e2v sensors

    def take_images(self):
        if self.noop or self.skip - test_seq_num < self.scanmode + self.transparent:
            preCols = fp.fp.getSequencerParameter("PreCols")
            readCols = fp.fp.getSequencerParameter("ReadCols")
            postCols = fp.fp.getSequencerParameter("PostCols")
            overCols = fp.fp.getSequencerParameter("OverCols")
            preRows = fp.fp.getSequencerParameter("PreRows")
            readRows = fp.fp.getSequencerParameter("ReadRows")
            postRows = fp.fp.getSequencerParameter("PostRows")
            scanMode = fp.fp.isScanEnabled()
            idleFlushTimeout = fp.fp.getSequencerParameter("idleFlushTimeout")
            print "Initial sequencer parameters"

            print "preCols="  , preCols
            print "readCols=" , readCols
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
            fp.fp.commitBulkChange()
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
            fp.fp.commitBulkChange(timeout=timeout)

        for i in range(self.transparent):
           self.take_image(exposure, expose_command, image_type=None, symlink_image_type=None)

        # Restore settings
        fp.fp.dropAllChanges()

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
