import fp
import bot_bench
import ccob
import os

def symlink(options, imageName, fileList, imagetype):
      print "Saved %d FITS files to %s" % (fileList.size(),fileList.getCommonParentDirectory())
      run = int(options['run']);
      output = options['output'];
      acqtype = options['acqtype']
      symdir = output
      if symdir:
         symname = "%s/%s-%06d" % (symdir, imagetype,  imageName.number)
         if not os.path.exists(symdir): 
            os.makedirs(symdir);
         os.symlink(fileList.getCommonParentDirectory().toString(), symname)
         print "Symlinked from %s" % symname; 
   
def do_bias(options):
   print "bias called %s" % options
   count = int(options.get('count','10'))
   for i in range(count):
      imageName,fileList = fp.takeBias()
      symlink(options,imageName,fileList,'BIAS')

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
     for i in range(bcount):
        imageName,fileList = fp.takeBias()
        symlink(options,imageName,fileList,'BIAS')
     e_per_pixel,filter = flat.split()
     exposure = int(e_per_pixel)/100.0	
     print "e %s filter %s" % (exposure,filter)   
     bot_bench.setNDFilter(filter)
     exposeCommand = lambda: bot_bench.openShutter(exposure)
     imageName,fileList = fp.takeExposure(exposeCommand)
     symlink(options,imageName,fileList,'FLAT')

def do_sflat(options):
   print "superflat called %s" % options

def do_lambda(options):
   print "lambda called %s" % options

def do_ccob(options):
   print "ccob called %s" % options
   bcount = int(options.get('bcount','1'))
   imcount = int(options.get('imcount','1'))
   exposures = options.get('expose').replace('\n','').split(',')
   points = options.get('point').replace('\n','').split(',')
   for point in points:
      (x,y) = [float(x) for x in point.split()]
      print (x,y)
      for exposure in exposures:
         (led,current,duration) = exposure.split()
         current = float(current)
         duration = float(duration)
         exposeCommand = lambda: ccob.fireLED(led,current,duration)
         for i in range(imcount):
            for b in range(bcount):
               imageName,fileList = fp.takeBias()
               symlink(options,imageName,fileList,'BIAS')
            imageName,fileList = fp.takeExposure(exposeCommand)
            symlink(options,imageName,fileList,'CCOB')
  
