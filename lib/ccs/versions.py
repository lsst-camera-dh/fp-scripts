#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS

def write_versions(fp):
   vList = [];
   versions = fp.getCCSVersions()
   group = fp.getAgentProperty("group")
   has_snapshot = False
   for agent in versions.getAgents():
      agentGroup = agent.getAgentProperty("group")
      if agent.isAgentWorkerOrService() and agentGroup == group:
         version = versions.getDistributionInfo(agent).getVersion()
         has_snapshot = has_snapshot or version.endswith("SNAPSHOT")
         vList.append("%s = %s\n" % (agent.getName(), version))
   vList.sort()
   if has_snapshot:
      print "WaRNING, non released CCS subsystem in use"
   with open("ccs_versions.txt", "w") as file:
	for version in vList:
           file.write(version)
