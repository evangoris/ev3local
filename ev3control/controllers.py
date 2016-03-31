"""Event handlers for operating motors

Dependencies:
    ev3
    xbox
    
Evan Goris
2015
"""

class DutyCycleController(object):
    """Use events from an Xbox controller to operate a motor
    
    Events from a given absolute axis are translated to duty cycle
    to operate the speed of a motor.
    
    Responsibilities:
        Mapping of events to state/speed of a motor
        Manage the resources of the motor if so decired (for example when
        at construction a motor port is given instead of a motor object)
        
    TODO:
        * deadzone
        * break
        * optional non linear mapping
    
    Args:
        xcevents (XCEvents): object that delivers a sequence of Xbox controller events
        motor (TachoMotor): object representing a motor
        port (str): port on which to search for a motor
        event (str or int): Name or code of an absolute axis
        
    Remarks:
        Exactly one of `motor` and `port` should be non-None
    
    Raises:
        ValueError: When either both or non of `motor` and `port` are None
    """

    def __init__(self, xcevents, motor=None, port=None, event='ABS_X', verbose=False):
    
        if motor==None and port==None:
            raise ValueError("At least one of `motor` and `port` should be non-None")
            
        if motor!=None and port!=None:
            raise ValueError("At most one of `motor` and `port` should be non-None")
                
        self._xcevents = xcevents
        
        if motor!=None:
            self._motor = motor
        else:
            import ev3
            self._motor = ev3.TachoMotor(port)
            
        if type(event)==str:
            import evdev.ecodes
            self._eventcode = evdev.ecodes.ecodes[event]
        else:
            self._eventcode = event
            
        absinfo = xcevents.absinfo(self._eventcode)
        self._min = absinfo.min
        self._max = absinfo.max
        self._verbose = verbose
        
        xcevents.add_callback(self._callback)
        
        self._motor.reset()
        self._motor.run_direct()
    
    def __enter__(self):
        self._motor.__enter__()
        return self
        
    def __exit__(self, type_, value, traceback):
        self._motor.__exit__(type_, value, traceback)
        
    def _callback(self, event):
        """Translate an input event to a duty_cycle_sp
        
        Only events with code given at construction will
        be handled. The rest is ignored.
        
        Args:
            event (InputEvent): Event from a controller
            
        Returns:
            boolean: True if the event was handled. False otherwise
        """
        import evdev.ecodes
        if event.type != evdev.ecodes.ecodes['EV_ABS'] or event.code != self._eventcode:
            return False
        
        if event.value > 0:
            duty_cycle = (100 * event.value) / self._max
        else:
            duty_cycle = -(100 * event.value) / self._min
                
        self._motor.Duty_Cycle_SP = duty_cycle
        if self._verbose:
            print duty_cycle
            
        return True

class RelPosController(object):
    """Uses key events from an xbox controller to position the motor in discrete steps.
    
    Args:
        xcevents (xbox.XCEvents): Stream of xbox events
        motor (ev3.TachoMotor): Motor to control
        left (str or int): Code or name of the button to make the motor turn left
        right (str or int): Code or name of the button to make the motor turn right
        increment (int): Number of tacho counts to rotate the motor on each step
    """
    
    def __init__(self, xcevents, motor, left='BTN_X', right='BTN_B', increment=10):
        self._motor    = motor
        self._xcevents = xcevents
        
        if type(left)==str:
            import evdev.ecodes
            self._left = evdev.ecodes.ecodes[left]
        else:
            self._left = left

        if type(right)==str:
            import evdev.ecodes
            self._right = evdev.ecodes.ecodes[right]
        else:
            self._rigth = right
        
        self._xcevents.add_callback(self._callback)
        self._motor.Duty_Cycle_SP = 50
        self._increment  = str(increment)
        self._mincrement = str(-increment)
        
    def _callback(self, event):
        """Translate an xbox event to a relative rotation of the controlled motor
        
        Args:
            event (InputEvent): Event from an xbox controller
            
        Returns:
            boolean: True if the event was handled, false otherwise
        """
        
        if event.code==self._left and event.value==1:
            self._motor.position_sp = self._increment
            self._motor.runtorelpos()
            return True
        elif event.code==self._right and event.value==1:
            self._motor.position_sp = self._mincrement
            self._motor.runtorelpos()
            return True
        else:
            return False

class XBoxStateController(object):
    """Record the state of an absolute axis of an XBox controller
    
    Event handler for xbox.XCEvents() that records the value of
    an absolute axis.
    
    Args:
        xcevents (xbox.XCEvents): Event sequence
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
    
    def _callback(self, event):
        """Callback for XCEvents()
        
        Args:
            event (InputEvent): Event from a controller
            
        Returns:
            boolean: True if the event was handled. False otherwise
        """
        if event.type!=self._typecode or event.code!=self._eventcode:
            return False
            
        self._value = float(event.value)
        return True

def printstate(scontroller):
    import time
    while True:
        print scontroller.value, scontroller.pvalue
        time.sleep(1)



class PController(object):
    """Proportional controller

    Object that implements a proportional controller and
    a feedback loop.

    Args:
        kp (float): Proportional gain
        setpoint (callable): Called to get the current setpoint
        pv (callable): Called to get the current value of the process variable
        out (callable): Called with the current control value
    """
    def __init__(self, kp, setpoint, pv, out):
        self._kp       = kp
        self._out      = out
        self._setpoint = setpoint
        self._pv       = pv

        # Frequency of the control loop
        #
        self._freq = 60.0

        # Thread on which the control loop is executed
        #
        self._thread = None

        # Flag to terminate the control loop
        #
        self._continue = None

    def _controlloop(self):
        """The control loop
        """
        import time

        while self._continue:

            # Get input
            #
            pv = self._pv()
            sp = self._setpoint()

            # Output control value
            #
            self._out(self._kp*(sp - pv))

            time.sleep(1.0/self._freq)

    def __enter__(self):
        """Start a thread and start the control loop on it

        Raises:
            RuntimeError: When the control loop is already running
        """

        if self._thread:
            raise RuntimeError("Controller already running")

        import threading
        self._thread = threading.Thread(target=self._controlloop)
        self._thread.deamon = True
        self._continue = True
        self._thread.start()

        return self

    def __exit__(self, type_, value, traceback):
        """Stop the control loop
        """
        self._continue = False
        self._thread.join()
        self._thread = None

def clampedcontrol(motor, maxcontrol):
    """Create a function that clamps an input signal before
    its forwarded to a motor
    """
    def out(control):
        if control>maxcontrol:
            motor.Duty_Cycle_SP = int(maxcontrol)
        elif control<-maxcontrol:
            motor.Duty_Cycle_SP = int(-maxcontrol)
        else:
            motor.Duty_Cycle_SP = int(control)

    return out

def axissetpoint(xcevents):
    """Create a function that returns the current state of an
    absolute axis of the XBox controller
    """
    state = XBoxStateController(xcevents)
    scale = 360.0

    def setpoint():
        return float(state.pvalue * scale)

    return setpoint

def processvariable(motor):
    """Create a function that returns the current position of a motor
    """
    def pv():
        return float(motor.Position)

    return pv



    
    
    
    
    
    
    
    
    
    
    
    
    
    
    