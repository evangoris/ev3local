"""Callbacks for operating motors that can be added to xbox.XCEvents instances

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


def printstate(scontroller):
    import time
    while True:
        print scontroller.value, scontroller.pvalue
        time.sleep(1)



    
    
    
    
    
    
    
    
    
    
    
    
    
    
    