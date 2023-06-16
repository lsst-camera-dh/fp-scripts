from org.lsst.ccs.scripting import CCS
from java.lang import Boolean

CCS.aliases = dict()

@staticmethod
def attachAlias(key, level=None, lock=True):
   if key in CCS.aliases:
      key = CCS.aliases[key]
   if level:
      return CCS.origAttachSubsystem(key, level)
   else:
      return CCS.origAttachSubsystem(key, Boolean(lock))

CCS.origAttachSubsystem = CCS.attachSubsystem
CCS.attachSubsystem = attachAlias
