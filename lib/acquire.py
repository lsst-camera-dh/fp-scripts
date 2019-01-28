import os
import time

import fp
import bot_bench
import ccob
import bot
from pd import PhotodiodeReadout

class TestCoordinator(object):
    ''' Base (abstract) class for all tests '''
    def __init__(self, options):
        self.run = options.getInt('run')
        self.symlink = options['symlink']
        self.test_seq_num = 0

    def take_images(self):
        pass

    def take_bias_images(self, count, test_type):
        for i in range(count):
            self.take_bias_image(test_type)

    def create_fits_header_data(self, exposure, test_type, image_type):
        data = {'ExposureTime': exposure, 'TestType': test_type, 'ImageType': image_type, 'TestSeqNum': self.test_seq_num}
        if self.run:
            data.update({'RunNumber': self.run})
        return data

    def take_bias_image(self, test_type):
        return self.take_image(test_type, 'BIAS', 0, None)

    def take_image(self, test_type, image_type, exposure, expose):
        fits_header_data = self.create_fits_header_data(exposure, test_type, image_type)
        image_name, file_list = fp.takeExposure(fits_header_data, expose)
        self.create_symlink(file_list, test_type.lower(), image_type.lower())
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
        TestCoordinator.__init__(options)
        self.count = options.getInt('count', 10)

    def take_images(self):
        self.take_bias_images(self.count, 'BIAS')

class BiasPlusImagesTestCoordinator(TestCoordinator):
    ''' Base class for all tests that involve n bias images per test image'''
    def __init__(self, options):
        TestCoordinator.__init__(options)
        self.bcount = int(options.get('bcount', '1'))

    def take_image(self, test_type, image_type, exposure, expose):
        super(BiasPlusImagesTestCoordinator, self).take_bias_images(self.bcount, test_type)
        super(BiasPlusImagesTestCoordinator, self).take_image(test_type, image_type, exposure, expose)

class DarkTestCoordinator(BiasPlusImagesTestCoordinator):
    ''' A TestCoordinator for darks '''
    def __init__(self, options):
        BiasPlusImagesTestCoordinator.__init__(options)
        self.darks = options.get('dark').replace('\n', '').split(',')

    def take_images(self):
        for dark in self.darks:
            integration, count = dark.split()
            integration = float(integration)
            count = int(count)
            expose_command = lambda: time.sleep(integration)

            for d in range(count):
                self.take_image('DARK', 'DARK', expose_command, integration)

class FlatFieldTestCoordinator(TestCoordinator):
    ''' A TestCoordinator for all tests that involve taking flat pairs with the flat field generator '''
    def __init__(self, options):
        super(FlatFieldTestCoordinator, self).__init__(options)
        self.bcount = int(options.get('bcount', '1'))
        self.flats = options.get('flat').replace('\n', '').split(',')

    def take_image(self, test_type, image_type, exposure, expose):
        pd_readout = PhotodiodeReadout(exposure)
        pd_readout.start_accumulation()
        image_name, file_list = super(FlatFieldTestCoordinator, self).take_image(test_type, image_type, exposure, expose)
        # TODO: Why does this need the last two arguments?
        pd_readout.write_readings(file_list.getCommonParentDirectory().toString(), self.test_seq_num)

    def take_image_pair(self, test_type, image_type, exposure, expose, nd_filter, wl_filter):
        bot_bench.setNDFilter(nd_filter)
        bot_bench.setColorFilter(wl_filter)
        super(FlatFieldTestCoordinator, self).take_bias_images(self.bcount, test_type)
        for pair in range(2):
            self.take_image(test_type, image_type, exposure, expose)

    def compute_exposure_time(self, nd_filter, wl_filter, e_per_pixel):
        # TODO: Use per-filter config file to compute exposure
        return float(e_per_pixel)/100.0

class FlatTestCoordinator(FlatFieldTestCoordinator):
    ''' A TestCoordinator for flat pairs'''
    def __init__(self, options):
        super(FlatTestCoordinator, self).__init__(options)
        self.wl_filter = options.get('wl')

    def take_images(self):
        for flat in self.flats:
            e_per_pixel, nd_filter = flat.split()
            exposure = self.compute_exposure_time(nd_filter, self.wl_filter, e_per_pixel)
            expose_command = lambda: bot_bench.openShutter(exposure)
            print "exp %s filter %s" % (exposure, nd_filter)
            # TODO: test-type = %s_%s_flat%d' % (wl,e_per_pixel,pair)
            self.take_image_pair('FLAT', 'FLAT', exposure, expose_command, nd_filter, self.wl_filter)

class SuperFlatTestCoordinator(FlatFieldTestCoordinator):
    def __init__(self, options):
        super(SuperFlatTestCoordinator, self).__init__(options)
        self.sflats = options.get('sflat').replace('\n', '').split(',')

    def take_images(self):
        for sflat in self.sflats:
            wl_filter, e_per_pixel, count, nd_filter = sflat.split()
            exposure = self.compute_exposure_time(nd_filter, wl_filter, e_per_pixel)
            expose_command = lambda: bot_bench.openShutter(exposure)
            #TODO: 'flat_%s_%s'% (wlFilter,e_per_pixel)
            #TODO: use count?
            self.take_image_pair('SFLAT', 'flat_%s_%s' % (wl_filter, e_per_pixel), exposure, expose_command, nd_filter, wl_filter)

class LambdaTestCoordinator(FlatFieldTestCoordinator):
    def __init__(self, options):
        super(LambdaTestCoordinator, self).__init__(options)
        self.imcount = int(options.get('imcount', 1))
        self.lambdas = options.get('lambda').replace('\n', '').split(',')

    def take_images(self):
        for lamb in self.lambdas:
            wl_filter, e_per_pixel, nd_filter = lamb.split()
            exposure = self.compute_exposure_time(nd_filter, wl_filter, e_per_pixel)
            expose_command = lambda: bot_bench.openShutter(exposure)
            #TODO: 'flat_%s_%s' % (wlFilter,e_per_pixel)
            self.take_image_pair('LAMBDA', 'FLAT', exposure, expose_command, nd_filter, wl_filter)

class Fe55TestCoordinator(FlatFieldTestCoordinator):
    def __init__(self, options):
        super(Fe55TestCoordinator, self).__init__(options)
        (fe55exposure, fe55count) = options.get('count').split()
        self.fe55exposure = float(fe55exposure)
        self.fe55count = int(fe55count)

    def create_fits_header_data(self, exposure, test_type, image_type):
        data = super(Fe55TestCoordinator, self).create_fits_header_data(exposure, test_type, image_type)
        data.update({'ExposureTime2': self.fe55exposure})
        return data

    def take_images(self):
        for flat in self.flats:
            wl_filter, e_per_pixel = flat.split()
            #TODO: None? which ND filter to use?
            exposure = self.compute_exposure_time(None, wl_filter, e_per_pixel)
            print "exp %s filter %s" % (exposure, wl_filter)
            def expose_command():
                bot_bench.openShutter(exposure) # Flat
                bot_bench.openFe55Shutter(self.fe55exposure) # Fe55
            #TODO: The total exposure time is needed by photodiode?
            #TODO: test_type should be '%s_flat_%s' % (filter,e_per_pixel)
            self.take_image_pair('FE55_FLAT', 'FE55', exposure, expose_command, None, wl_filter)

class CCOBTestCoordinator(BiasPlusImagesTestCoordinator):
    def __init__(self, options):
        super(CCOBTestCoordinator, self).__init__()
        self.imcount = int(options.get('imcount', '1'))
        xoffset = float(options.get('xoffset'))
        yoffset = float(options.get('yoffset'))
        bot.setLampOffset(xoffset, yoffset)
        self.exposures = options.get('expose').replace('\n', '').split(',')
        self.points = options.get('point').replace('\n', '').split(',')

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
                    # TODO:  '%s_%s_%s' % (led,x,y)
                    self.take_image('CCOB', 'CCOB', duration, expose_command)


class XTalkTestCoordinator(BiasPlusImagesTestCoordinator):
    def __init__(self, options):
        super(XTalkTestCoordinator, self).__init__()
        self.imcount = int(options.get('imcount', '1'))
        xoffset = float(options.get('xoffset'))
        yoffset = float(options.get('yoffset'))
        bot.setLampOffset(xoffset, yoffset)
        self.exposures = options.get('xtalk').replace('\n', '').split(',')
        self.points = options.get('point').replace('\n', '').split(',')

    def take_images(self):
        for point in self.points:
            (x, y) = [float(x) for x in point.split()]
            bot.moveTo(x, y)
            for exposure in self.exposures:
                (led, current, duration) = exposure.split()
                #TODO: Set LED
                current = float(current)
                duration = float(duration)
                expose_command = lambda: bot_bench.openShutter(exposure)
                for i in range(self.imcount):
                    # TODO:  '%s_%s_%s' % (x, y, exposure)
                    self.take_image('XTALK', 'XTALK', duration, expose_command)


def do_bias(options):
    print "bias called %s" % options
    tc = BiasTestCoordinator(options)
    tc.take_images()

def do_darks(options):
    print "darks called %s" % options
    tc = DarkTestCoordinator(options)
    tc.take_images()

def do_flat(options):
    print "flat called %s" % options
    tc = FlatTestCoordinator(options)
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
    