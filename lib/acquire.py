import fp
import bot_bench

def do_bias(options):
   print "bias called %s" % options
   count = int(options.get('count','10'))
   for i in range(count):
      fp.takeBias()

def do_fe55(options):
   print "fe55 called %s" % options

def do_dark(options):
   print "dark called %s" % options

def do_persistence(options):
   print "persistence called %s" % options

def do_flat(options):
   print "flat called %s" % options
   bcount = int(options.get('bcount','1'))
   wl = options.get('wl')
   bot_bench.setColorFilter(wl)
   flats = options.get('flat').replace('\n','').split(',')
   for flat in flats:
     e_per_pixel,filter = flat.split()
     exposure = int(e_per_pixel)/100.0	
     print "e %s filter %s" % (exposure,filter)   
     bot_bench.setNDFilter(filter)
     exposeCommand = lambda: bot_bench.openShutter(exposure)
     fp.takeExposure(exposeCommand)

#flat called {'hilim': '800.0', 'lolim': '0.025', 'bcount': '1', 'wl': 'SDSS_i', 'flat': '100   ND_OD0.5,\n1000   ND_OD0.4,\n10000   ND_OD0.3,\n100000   ND_OD0.2,\n200000   ND_OD0.1', 'dry_run': None}

   
def do_sflat(options):
   print "superflat called %s" % options

def do_lambda(options):
   print "lambda called %s" % options
