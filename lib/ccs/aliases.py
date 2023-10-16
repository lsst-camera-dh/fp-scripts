from org.lsst.ccs.scripting import CCS
from java.lang import Boolean

CCS.aliases = dict()

@staticmethod
def attachAlias(key, lock=True, level=None):
   if key in CCS.aliases:
      key = CCS.aliases[key]
   if level:
      return CCS.origAttachSubsystem(key, level)
   else:
      return CCS.origAttachSubsystem(key, lock)

CCS.origAttachSubsystem = CCS.attachSubsystem
CCS.attachSubsystem = attachAlias
