"""Interface to events form an Xbox controller

ISSUES:
1) When the controller disconnects (or some other internal exception happens) and then reconnects the XCEvents object is still dead

Evan Goris
2015
"""

import os

from evdev import InputDevice, list_devices


def printevent(event):
    import evdev.ecodes
    if event.type==3 and event.code==0:
        print event.code, event.type, event.value
        print evdev.ecodes.bytype[event.type][event.code]


def absinfo(device, code):
    """Get information on an absolute input axis

    Args:
        device (evdev.InputDevice): Input device
        code (int or str): Code or symbolic name of an absolute axis

    Returns:
        AbsInfo: Named tuple with info on `type_`
    """
    import evdev.ecodes
    cap = device.capabilities(absinfo=True, verbose=False)
    if type(code)==str:
        typecode = evdev.ecodes.ecodes[code]
    else:
        typecode = code
    abscode = evdev.ecodes.ecodes['EV_ABS']
    for info in cap[abscode]:
        if info[0]==typecode:
            return info[1]

class EventLoop(object):
    """Manages a sequence of events from an Xbox controller

    Objects of this class poll for events from /dev/input
    An Xbox controller can be made a device under /dev/input with
    the userspace driver `xboxdrv`.    
    
    Responsibilities:
        Delivering Xbox events, non-blocking to interested parties.
        
    Implementation:
        Resource management: Thread that polls the controller
        
    """
    def __init__(self, device=None, callbacks=None):

        # The xbox device
        #
        self._device = device or self._finddevice()

        # List of callbacks that will be called
        # when xbox events occur
        #
        self._callbacks = callbacks or []

        # The thread that polls the controller
        # Will be initialized in __enter__()
        #
        self._t = None

        # Mapping of (type_, code) tuples to
        # current state of the corresponding button or axes
        #
        self._monitor = {}

        # Filehandles for signaling the control thread to stop
        # Will be set in self._init()
        #
        self.__signalrfd, self.__signalwfd = None, None

    def add_callback(self, callback):
        self._callbacks.append(callback)

    def remove_callback(self, callback):
        self._callbacks.remove(callback)

    def clear_callbacks(self):
        self._callbacks.clear()

    def connectaxes(self, callback, axes, max=1.0, min=-1.0):
        import evdev, evdev.ecodes

        if type(axes)==str:
            eventcode = evdev.ecodes.ecodes[axes]
        else:
            eventcode = axes

        absinfo = self.absinfo(eventcode)
        axesmin = float(absinfo.min)
        axesmax = float(absinfo.max)
        axesrange = axesmax - axesmin
        valuerange = max - min

        if axesrange==0:
            raise RuntimeError("Absolute axes with zero range")

        a = valuerange / axesrange
        b = -(a*axesmin - min)

        def callback1(event):
            if event.type==evdev.ecodes.ecodes['EV_ABS'] and event.code==eventcode:
                value = a*float(event.value) + b
                callback(value)

        self.add_callback(callback1)
        return callback1

    # TODO: Deprecated decorator
    def absinfo(self, type_):
        """Get information on an absolute input axis
        
        Args:
            type_ (int or str): Code or symbolic name of an absolute axis
            
        Returns:
            AbsInfo: Named tuple with info on `type_`
        """
        import evdev.ecodes
        cap = self._device.capabilities(absinfo=True, verbose=False)
        if type(type_)==str:
            typecode = evdev.ecodes.ecodes[type_]
        else:
            typecode = type_
        abscode = evdev.ecodes.ecodes['EV_ABS']
        for info in cap[abscode]:
            if info[0]==typecode:
                return info[1]
            
    def eventtypes(self):
        return self._device.capabilities.keys()

    def eventcodes(self, type_):
        return self._device.capabilities[type_]

    def iattribute(self, type_, code):
        """Return an iterator that gives the values of
        a specific axes or button.

        Each time __next__() is called the state of the control is polled.
        So events that happen between the poll events are missed. This is ok
        for axes that control a PID for example but might not be good enough
        for transmitting button presses.

        The value of a button is represented by 0 or 1
        The value of an axes is represented by a float in [-1, 1]

        Args:
            type_: The type of the event ('EV_ABS' or 'EV_BTN')
            code: The control ('ABS_X', 'ABS_RY', ...)

        Yields:
            The value of the control determined by `type_`, `code`
        """

        # TODO: Make the iteration stop when the event loop stops
        #

        # Convert arguments to integer codes
        #
        import evdev.ecodes
        if type(type_)==str:
            type_ = evdev.ecodes.ecodes[type_]
        if type(code)==str:
            code = evdev.ecodes.ecodes[code]

        # Construct a function that normalizes the values
        # of an absolute axes
        #
        if type_ == evdev.ecodes.ecodes['EV_ABS']:
            absinfo = self.absinfo(code)
            axesmin = float(absinfo.min)
            axesmax = float(absinfo.max)
            def f(value):
                if value<0:
                    return -float(value) / axesmin
                else:
                    return float(value) / axesmax
        else:
            def f(value):
                return value

        # Add entry to the self._monitor dictionary so
        # that self._processevents() will save changes
        # in the state of the control
        #
        self._monitor[(type_, code)] = 0
        try:
            while True:
                yield f(self._monitor[(type_, code)])
        finally:
            del self._monitor[(type_, code)]

    # TODO: Deprecation
    def _finddevice(self):
        """Search for the device that represents the xbox controller
        
        Returns:
            InputDevice: The xbox controller
            
        Raises:
            IOError: When no controller can be found
        """
        devices = [ InputDevice(fn) for fn in list_devices() ]
        for dev in devices:
            if dev.name.startswith('Xbox Gamepad'):
                return dev
            if dev.name.startswith('PLAYSTATION'):
                return dev

        raise IOError("No controller found")
    
    def __enter__(self):
        self._init()
        return self

    def __exit__(self, type_, value, traceback):
        self.stop()

    def _init(self):
        # Initialize signalling file descriptors to break
        # the endless select loop. If anything is written
        # over this pipe then the event sequence generated
        # by self.eventsequence() will end.
        #
        self.__signalrfd, self.__signalwfd = os.pipe()

        # Start up a thread that waits for events from
        # the controller.
        #
        import threading
        self._t = threading.Thread(target=self._processevents,args=())
        self._t.deamon = True

    def start(self):
        """Fire up a thread that polls the controller
        """
        if not self._t:
            self._init()
        self._t.start()

    def stop(self):
        """Stop the thread that polls the controller and release resources
        """
        if not self.__signalwfd:

            if self._t:
                raise RuntimeWarning("EventLoop inproperty shut down")

            # Stopped already
            #
            return

        # Signal the event sequence to end and thus the
        # thread to end.
        #
        os.write(self.__signalwfd, "STOP")

        # Wait for tread to finish
        #
        self._t.join()
        self._t = None

        # Close communication channels
        #
        os.close(self.__signalrfd)
        os.close(self.__signalwfd)

        self.__signalrfd, self.__signalwfd = None, None

    def _processevents(self):
        """Process events from the sequence generated by the controller
        
            The sequence of events is generated by self._eventsequence()
        """
        for event in self._eventsequence():

            try:
                self._monitor[(event.type, event.code)] = event.value
            except KeyError:
                pass

            for callback in self._callbacks:
                callback(event)
        
    def _eventsequence(self):
        """Generate a sequence of xbox events
        
            This sequence ends when something is red from self._signalrfd
            
        Yields:
            Event: event generated by xbox controller
            
        """
        from select import select
        while True:
            r, w, x = select([self._device.fd, self.__signalrfd], [], [])
            if self.__signalrfd in r:
                break
            else:
                for event in self._device.read():
                    yield event


class XBoxStateController(object):
    """Record the state of an absolute axis of an XBox controller

    Event handler for xbox.EventLoop() that records the value of
    an absolute axis.

    Args:
        xcevents (xbox.EventLoop): Event sequence
        event (string or int): Name or code of an absolute axis
    """
    def __init__(self, xcevents, event='ABS_RX'):
        if type(event)==str:
            import evdev.ecodes
            self._eventcode = evdev.ecodes.ecodes[event]
        else:
            self._eventcode = event

        self._typecode = evdev.ecodes.ecodes['EV_ABS']

        self._value = 0.0

        absinfo = xcevents.absinfo(self._eventcode)
        self._min = float(absinfo.min)
        self._max = float(absinfo.max)

        xcevents.add_callback(self._callback)
        self._device = xcevents._xbox

    def __get_min(self):
        return self._min

    min = property(__get_min)
    """Minimal value the observed axis can take on
    """

    def __get_max(self):
        return self._max

    max = property(__get_max)
    """Maximal value the observed axis can take on
    """

    def __get_value(self):
        return self._value

    value = property(__get_value)
    """Current value of the observed axis
    """

    def __get_pvalue(self):
        if self._value>0:
            return self._value / self._max
        else:
            return -(self._value / self._min)

    pvalue = property(__get_pvalue)
    """Current value of the observed axis normalized to [-1,1]
    """

    def _get_driver_name(self):
        return self._device.name

    Driver_Name = property(_get_driver_name)

    def _callback(self, event):
        """Callback for EventLoop()

        Args:
            event (InputEvent): Event from a controller

        Returns:
            boolean: True if the event was handled. False otherwise
        """
        if event.type!=self._typecode or event.code!=self._eventcode:
            return False

        self._value = float(event.value)
        return True

    def getreadproperties(self):
        return ['pvalue']


# TODO: Accept multiple codes
#
def gen_events(device, code):
    """Generate EVT_ABS events from a device

    The next() method of the generator returned will return the most
    recent event since the last call to next().

    Args:
        device (str): Path to device
        code (int): Code of events to generate

    Yields:
        evdev.InputEvent: Most recent event with code `code`
    """
    from evdev import InputDevice

    if type(device)==str:
        inputdevice = InputDevice(device)
    elif isinstance(device, InputDevice):
        inputdevice = device
    else:
        raise RuntimeError("gen_events: Invalid value for argument `device`")

    import select
    pollobject = select.poll()
    pollobject.register(inputdevice.fd, select.POLLIN | select.POLLPRI)
    try:
        while True:
            events = pollobject.poll(0)
            if not events:
                yield None
            else:
                relevantevent = None
                for event in inputdevice.read():
                    import evdev.ecodes
                    if event.type==evdev.ecodes.ecodes['EV_ABS'] and event.code==code:
                        relevantevent = event
                yield relevantevent
    finally:
        pollobject.unregister(inputdevice.fd)


def grepdevice(pattern):
    """Instantiate an InputDevice object based on a regular expression
    matched on device name

    Args:
        pattern (str): Regular expression

    Returns:
        evdev.InputDevice: Device with a name that matches `pattern`

    Raises:
        IOError: When no device with appropriate name can be found
    """
    import re
    regex = re.compile(pattern)
    devices = [ (fn, InputDevice(fn)) for fn in list_devices() ]
    for path, dev in devices:
        if regex.match(dev.name):
            return path, dev

    raise IOError("No device found")


def gen_scaledvalue(events, minsource, maxsource, min, max):
    """Generate scaled values from a sequence of events

    Arguments:
        events (iter): Sequence of events
        minsource (num): Minimum of value attribute of the events
        maxsource (num): Maximum of value attribute of the events
        min (num): Minimum of generated values
        max (num): Maximum of generated values

    Yields:
        float: Values in [`min`, `max`]
    """
    a = (max - min) / float(maxsource - minsource)
    b = max - a * maxsource # max = a * 255 + b

    def scale(value):
        return a * value + b

    for event in events:
        if event:
            yield scale(event.value)
        else:
            yield None