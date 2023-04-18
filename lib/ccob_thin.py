"""
Control of the CCS subsystem for the thin-beam CCOB.

Steve Tether, tether@slac.stanford.edu
2022 May 3

Exports
-------

X, Y, B, U:  Instances of an internal class each representing the
axis of the same name.

CCOB_thin : A class that represents the CCS subsystem.

"""

import inspect
from datetime import datetime, timedelta
from threading import Lock
from time import sleep

import exceptions
from java.time import Duration
from org.lsst.ccs.messaging import StatusMessageListener
from org.lsst.ccs.scripting import CCS, ScriptingStatusBusListener
from org.lsst.ccs.subsystem.motorplatform.bus import (
    AxisStatus, ControllerStatus, MotorReplyListener, MoveAxisRelative, MoveAxisAbsolute,
    StopAllMotion, SendAxisStatus, SendControllerStatus)


class _Axis:
    """
    Represents a valid axis.
    """
    def __init__(self, name):
        self.name = name


X = _Axis("X")
"""Represents the X axis."""

Y = _Axis("Y")
"""Represents the Y axis."""

B = _Axis("B")
"""Represents the B axis."""

U = _Axis("U")
"""Represents the U axis."""


class CcobThin:
    """
 An instance serves several functions:

(1) It establishes a connection with the subsystem along the CCS virtual buses.

(2) It exports methods corresponding to commands defined by the subsystem.
Generally speaking, calling the method sends the corresponding command
message out along the CCS command bus.

(3) It listens for status messages coming in from the subsystem via
the CCS status bus and stores the latest message received of each type.
It exports a "get" method for each type of status message.
"""
    def __init__(self, subsystemName):
        """
        Connect to the site's CCS bus, contact the worker subsystem
        that talks to TB Server and begin monitoring status messages
        from that subsystem.

        Arguments
        ---------
        subsystemName : str
            The name of the worker subsystem as it appears on the CCS bus.
        """
        self._target = subsystemName
        self._replies = _ReplyHandler(self._target)
        self._subsys = _SubsystemHandle(self._target, self._replies)

    def moveTo(self, axis, position, speed):
        """
        Move the axis until it's at the specified coordinate.

        Arguments
        ---------
        axis : private type
            One of the three valid axis objects.
        position : float
            The coordinate of the target position in mm.
        speed : float
            The maximum speed in axis units/sec.
        """
        _checkAxis(axis)
        self._subsys.sendCommand("moveTo", axis.name, position, speed)

    def moveBy(self, axis, change, speed):
        """
        Move the axis so that its coordinate has changed by the
        specified amount. The starting position is the one current at
        the time the move command begins execution.

        Arguments
        ---------
        axis : private type
            One of the valid axis objects.
        change : float
            The desired coordinate change.
        speed : float
            The maximum speed in axis units/sec.
        """
        _checkAxis(axis)
        self._subsys.sendCommand("moveBy", axis.name, change, speed)

    def getAxisStatus(self, axis):
        """Gets the latest AxisStatus value received (or None)."""
        return self._replies.getAxisStatus(axis)

    def getControllerStatus(self):
        """Gets the latest ControllerStatus value received (or None)."""
        return self._replies.getControllerStatus()

    def aimAgainUB(self):
        """ """
        self._subsys.sendCommand("aimAgainUB")

    def aimAgainXY(self):
        """ """
        self._subsys.sendCommand("aimAgainXY")

    def diodeOff(self):
        """ """
        self._subsys.sendCommand("diodeOff")

    def diodeOn(self):
        """ """
        self._subsys.sendCommand("diodeOn")

    def diodeStatus(self):
        """ """
        return self._subsys.sendCommand("diodeStatus")

    def getDiodeAttenuation(self):
        """ """
        return self._subsys.sendCommand("getDiodeAttenuation")

    def getLastReply(self):
        """ """
        return self._subsys.sendCommand("getLastReply")

    def getTarget(self):
        """ """
        return self._subsys.sendCommand("getTarget")

    def hyperCloseFastShutter(self):
        """ """
        self._subsys.sendCommand("hyperCloseFastShutter")

    def hyperCloseMainShutter(self):
        """ """
        self._subsys.sendCommand("hyperCloseMainShutter")

    def hyperKillLamp(self):
        """ """
        self._subsys.sendCommand("hyperKillLamp")

    def hyperLightLamp(self):
        """ """
        self._subsys.sendCommand("hyperLightLamp")

    def hyperOpenFastShutter(self):
        """ """
        self._subsys.sendCommand("hyperOpenFastShutter")

    def hyperOpenMainShutter(self):
        """ """
        self._subsys.sendCommand("hyperOpenMainShutter")

    def hyperRemoveFilter(self, grating_name):
        """ """
        self._subsys.sendCommand("hyperRemoveFilter", grating_name)

    def hyperSetWavelength(self, wavelength):
        """ """
        return self._subsys.sendCommand("hyperSetWavelength", wavelength)

    def hyperStartFastExposure(self, milliseconds):
        """ """
        self._subsys.sendCommand("hyperStartFastExposure", milliseconds)

    def hyperStatus(self):
        """ """
        return self._subsys.sendCommand("hyperStatus")

    def illuminateThenRead(self, milliseconds):
        """ """
        return self._subsys.sendCommand("illuminateThenRead", milliseconds)

    def picoGetRange(self):
        """ """
        return self._subsys.sendCommand("picoGetRange")

    def picoReadCurrent(self):
        """ """
        return self._subsys.sendCommand("picoReadCurrent")

    def picoSetRange(self, range_num):
        """ """
        self._subsys.sendCommand("picoSetRange", range_num)

    def picoSetTime(self, milliseconds):
        """ """
        self._subsys.sendCommand("picoSetTime", milliseconds)

    def picoStatus(self):
        """ """
        return str(self._subsys.sendCommand("picoStatus"))

    def readThenIlluminate(self, milliseconds):
        """ """
        return float(self._subsys.sendCommand("readThenIlluminate", milliseconds))

    def sendAxisStatus(self, axis):
        """ """
        _checkAxis(axis)
        self._subsys.sendCommand("sendAxisStatus", SendAxisStatus(axis.name))

    def sendControllerStatus(self):
        """ """
        self._subsys.sendCommand("sendControllerStatus", SendControllerStatus())

    def setTargetHere(self):
        """ """
        self._subsys.sendCommand("setTargetHere")

    def setTargetTo(self, x, y):
        """ """
        self._subsys.sendCommand("setTargetTo", x, y)

    def status(self, what):
        """ """
        return str(self._subsys.sendCommand("status", what))


class _SubsystemHandle:
    """
    Establish the command link to the worker subsystem and
    set up monitoring its status bus messages by the reply
    handler.
    """
    def __init__(self, subsystemName, replyHandler):
        self._subsysName = subsystemName
        self._subsysHandle = CCS.attachSubsystem(subsystemName)
        CCS.addStatusBusListener(replyHandler, replyHandler.getMessageFilter())

    def sendCommand(self, cmd, *args):
        # The TB Server is synchronous and so is the CCS subsystem, meaning that
        # commands, including motion commands, don't return until the command is completed.
        # So we need a pretty big timeout to cover long moves.
        # Might want to change this to an adjustable timeout after we get some more experience.
        timeout = Duration.ofSeconds(120)
        return self._subsysHandle.sendSynchCommand(timeout, cmd, *args)


class _ReplyHandler(MotorReplyListener, ScriptingStatusBusListener):
    """Save the latest status message of each type; per axis, if applicable."""
    def __init__(self, target):
        self._target = target
        self._lock = Lock()
        # The following instance variables are protected by self._lock
        self._controllerStatus = None
        self._axisStatus = dict()

    def getControllerStatus(self):
        with self._lock:
            return self._controllerStatus

    def getAxisStatus(self, axis):
        _checkAxis(axis)
        with self._lock:
            return self._axisStatus.get(axis.name, None)

    ########## Implementation of ScriptingStatusBusListener #########
    def onStatusBusMessage(self, msg):
        msg = msg.getBusMessage().getSubsystemData().getValue()
        msg.callMotorReplyHandler(self)

    def getMessageFilter(self):
        def messageFilter(msg):
            # Did it come from the right subsystem?
            if msg.getOrigin() != self._target:
                return False
            msg = msg.getBusMessage()
            # Was the message generated as key-value data by the
            # subsystem's application code and not, for example, by the CCS framework?
            if not _hasmethod(msg, "getSubsystemData"):
                return False
            msg = msg.getSubsystemData()
            if not _hasmethod(msg, "getValue"):
                return False
            # Is the payload of the message an object which implements
            # the callMotorReplyHandler() method?
            msg = msg.getValue()
            return _hasmethod(msg, "callMotorReplyHandler")
        return messageFilter

    ########## Implementation of MotorReplyListener ##########
    # An incoming status bus message will call one of these methods
    # from its own callMotorReplyHandler() method. This will happen
    # in a thread other than the one that's using this module,
    # so we sync updates and retrievals of status info.
    def axisStatus(self, axstat):
        with self._lock:
            self._axisStatus[axstat.getAxisName()] = axstat

    def controllerStatus(self, constat):
        with self._lock:
            self._controllerStatus = constat

    def ioStatus(self, iostat):
        pass

    def platformConfig(self, config):
        pass

    def capturedData(self, data):
        pass


def _hasmethod(obj, name):
    return inspect.ismethod(getattr(obj, name, None))


def _checkAxis(ax):
    if not isinstance(ax, _Axis):
        raise ValueError("The given object is not a valid axis object.")
