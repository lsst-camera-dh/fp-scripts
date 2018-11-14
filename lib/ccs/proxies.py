from java.time import Duration
from org.lsst.ccs.scripting import CCS 

class ccsProxy(object):
   '''The ccsProxy class can be used to wrap a CCS subsystem in such a way that
      commands in the subsystem can be called directly from python. E.g.

         demo.ping()

      instead of 
   
         demo.sendSynchCommand("ping")
  
   '''

   def __init__(self, ccs, subsystemName):
      self._ccs = ccs 
      self._subsystem = subsystemName
      self._target = None
      self._targets = ccs.sendSynchCommand("getCommandTargets")	

   @staticmethod
   def __parseTimeout(timeout):
      if isinstance(timeout, Duration):
         return timeout
      elif isinstance(timeout, int):
         return Duration.ofSeconds(timeout)
      elif isinstance(timeout, str):
         return Duration.parse(timeout) 
      else:
         raise RuntimeError("Cannot convert %s to Duration" % timeout)
   
   def __getattr__(self, key):
      # If the method already exists in _ccs, return it
      if hasattr(self._ccs, key):
         return getattr(self._ccs, key)
      # If the method corresponds to a command target, return a method which when called will
      # return a proxy mapped to that target
      if "/".join(filter(None, [self._subsystem,self._target,key])) in self._targets:
         def createNewProxy():
            newProxy = ccsProxy(self._ccs, self._subsystem)
            newProxy._target = "/".join(filter(None,[self._target,key]))
            return newProxy
         return createNewProxy         
      # otherwise return a function, which when invoked will invoke the corresponding
      # method in the underlying _ccs object
      def forward(*args, **kwargs):
         actualKey = " ".join([self._target,key]) if self._target else key
         if 'async' in kwargs and kwargs['async']:
           return self._ccs.sendAsynchCommand(actualKey,args) 
         if 'timeout' in kwargs:
           return self._ccs.sendSynchCommand(self.__parseTimeout(kwargs['timeout']), actualKey,args)
         else:
           return self._ccs.sendSynchCommand(actualKey,args)
      return forward

@staticmethod
def attachProxy(key):
   return ccsProxy(CCS.attachSubsystem(key),key)

CCS.attachProxy = attachProxy
