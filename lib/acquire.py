import fp
import bot_bench
import os

def symlink(options, imageName, fileList, imagetype):
      print "Saved %d FITS files to %s" % (fileList.size(),fileList.getCommonParentDirectory())
      activity = int(options['activity'])
      run = int(options['run']);
      output = options['output'];
      acqtype = options['acqtype']
      symdir = "%s/LCA-10134_Cryostat/LCA-10134_Cryostat-0001/%06d/%s/%08d" % (output, run, acqtype, activity)
      symname = "%s/%s-%06d" % (symdir, imagetype,  imageName.number)
      if not os.path.exists(symdir): 
         os.makedirs(symdir);
      os.symlink(fileList.getCommonParentDirectory().toString(), symname)
      print "Symlinked from %s" % symname; 
   
def do_bias(ccs_sub, options):
   print "bias called %s" % options
   count = int(options.get('count','10'))
   for i in range(count):
      imageName,fileList = fp.takeBias(ccs_sub)
      symlink(options,imageName,fileList,'BIAS')

def do_fe55(ccs_sub, options):
   print "fe55 called %s" % options

def do_dark(ccs_sub, options):
   print "dark called %s" % options

def do_persistence(ccs_sub, options):
   print "persistence called %s" % options

def do_flat(ccs_sub, options):
   print "flat called %s" % options
   bcount = int(options.get('bcount','1'))
   wl = options.get('wl')
   bot_bench.setColorFilter(ccs_sub, wl)
   flats = options.get('flat').replace('\n','').split(',')
   for flat in flats:
     for i in range(bcount):
        imageName,fileList = fp.takeBias(ccs_sub)
        symlink(options,imageName,fileList,'BIAS')
     e_per_pixel,filter = flat.split()
     exposure = int(e_per_pixel)/100.0	
     print "e %s filter %s" % (exposure,filter)   
     bot_bench.setNDFilter(ccs_sub, filter)
     exposeCommand = lambda: bot_bench.openShutter(ccs_sub, exposure)
     imageName,fileList = fp.takeExposure(ccs_sub, exposeCommand)
     symlink(options,imageName,fileList,'FLAT')

def do_sflat(ccs_sub, options):
   print "superflat called %s" % options

def do_lambda(ccs_sub, options):
   print "lambda called %s" % options
