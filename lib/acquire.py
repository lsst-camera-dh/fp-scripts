import os
import time

import fp
import bot_bench
import ccob
import bot
from pd import PhotodiodeReadout

class TestCoordinator(object):
    ''' Base (abstract) class for all tests '''
    def __init__(self, options, test_type, image_type):
        self.run = options.getInt('run')
        self.symlink = options['symlink']
        self.test_type = test_type
        self.image_type = image_type
        self.test_seq_num = 0

    def take_images(self):
        pass

    def take_bias_images(self, count):
        for i in range(count):
            self.take_bias_image()

    def create_fits_header_data(self, exposure, image_type):
        data = {'ExposureTime': exposure, 'TestType': self.test_type, 'ImageType': image_type, 'TestSeqNum': self.test_seq_num}
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
        fits_header_data = self.create_fits_header_data(exposure, image_type)
        image_name, file_list = fp.takeExposure(expose_command, fits_header_data)
        self.create_symlink(file_list, self.symlink_test_type(self.test_type), symlink_image_type)
        self.test_seq_num += 1
        return (image_name, file_list)

    def create_symlink(self, file_list, test_type, image_type):
        ''' Create symlinks for created FITS files, based on the specification here:
            https://confluence.slac.stanford.edu/x/B244Dg
        '''
        if not file_list: # Indicates --nofits option was used
            return
        print "Saved %d FITS files to %s" % (file_list.size(), file_list.getCommonParentDirectory())
        if self.symlink:
            symname = "%s/%s_%s_%03d" % (self.symlink, test_type, image_type, self.test_seq_num)
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
        super(BiasPlusImagesTestCoordinator, self).take_bias_images(self.bcount)
        super(BiasPlusImagesTestCoordinator, self).take_image(exposure, expose_command, image_type, symlink_image_type)

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
        self.bcount = int(options.get('bcount', '1'))

    def set_filters(self, nd_filter, wl_filter):
        bot_bench.setNDFilter(nd_filter)
        bot_bench.setColorFilter(wl_filter)

    def take_image(self, exposure, expose_command, image_type=None, symlink_image_type=None):
        pd_readout = PhotodiodeReadout(exposure)
        pd_readout.start_accumulation()
        image_name, file_list = super(FlatFieldTestCoordinator, self).take_image(exposure, expose_command, image_type, symlink_image_type)
        # TODO: Why does this need the last two arguments?
        pd_readout.write_readings(file_list.getCommonParentDirectory().toString(), self.test_seq_num)

    def compute_exposure_time(self, nd_filter, wl_filter, e_per_pixel):
        # TODO: Use per-filter config file to compute exposure
        return float(e_per_pixel)/100.0

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
            self.set_filters(nd_filter, self.wl_filter)
            self.take_bias_images(self.bcount)
            for pair in range(2):
                self.take_image(exposure, expose_command, symlink_image_type='%s_%s_flat%d' % (self.wl_filter, e_per_pixel, pair))

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
            self.set_filters(nd_filter, wl_filter)
            self.take_bias_plus_image(exposure, expose_command, symlink_image_type='flat_%s_%s' % (wl_filter, e_per_pixel))

class Fe55TestCoordinator(FlatFieldTestCoordinator):
    def __init__(self, options):
        super(Fe55TestCoordinator, self).__init__(options, 'FE55_FLAT', 'FE55')
        self.flats = options.getList('flat')
        (fe55exposure, fe55count) = options.get('count').split()
        self.fe55exposure = float(fe55exposure)
        self.fe55count = int(fe55count)

    def create_fits_header_data(self, exposure, image_type):
        data = super(Fe55TestCoordinator, self).create_fits_header_data(exposure, image_type)
        if image_type != 'BIAS':
            data.update({'ExposureTime2': self.fe55exposure})
        return data

    def take_images(self):
        for flat in self.flats:
            wl_filter, e_per_pixel = flat.split()
            #TODO: None? which ND filter to use?
            nd_filter = 'None'
            exposure = self.compute_exposure_time(nd_filter, wl_filter, e_per_pixel)
            print "exp %s filter %s" % (exposure, wl_filter)
            def expose_command():
                bot_bench.openShutter(exposure) # Flat
                bot_bench.openFe55Shutter(self.fe55exposure) # Fe55
            #TODO: The total exposure time is needed by photodiode?
            self.set_filters(nd_filter, wl_filter)
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

    def take_images(self):
        for point in self.points:
            (x, y) = [float(x) for x in point.split()]
            bot.moveTo(x, y)
            for exposure in self.exposures:
                (led, current, duration) = exposure.split()
                current = float(current)
                duration = float(duration)
                expose_command = lambda: ccob.fireLED(led, current, duration)
                for i in range(self.imcount):
                    self.take_bias_plus_image(duration, expose_command, symlink_image_type='%s_%s_%s' % (led, x, y))


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
            (x, y) = [float(x) for x in point.split()]
            bot.moveTo(x, y)
            for exposure in self.exposures:
                exposure = float(exposure)
                expose_command = lambda: bot_bench.openShutter(exposure)
                for i in range(self.imcount):
                    self.take_bias_plus_image(exposure, expose_command, symlink_image_type='%s_%s_%s' % (x, y, exposure))


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
    #TODO: Implement this
    print "persistence called %s" % options

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
