"""Interface to EV3 Hardware

Evan Goris
2015
"""
from ev3local.iattribute import AttributeIteratorMixin
from ev3local.pid import PController


class Device(AttributeIteratorMixin):
    """Base class for motors and sensors

    Contains some functionality common to all devices

    Args:
        port (str or int): Name of an EV3 IO port
        rcontext (iter of str): Filename of read-only files that are managed within a 'with' statement
        wcontext (iter of str): Filename of write-only files that are managed within a 'with' statement
        rwcontext (iter of str): Filename of read-write files that are managed within a 'with' statement
    """

    _basefolder = None
        # Needs to be overriden in derived classes to point
        # to the folder that contains connected devices of
        # the type that the derived class represents
        #

    _propertyfilemap = {}

    def __init__(self, port, rcontext=None, wcontext=None, rwcontext=None):

        if self.__class__._basefolder == None:
            raise RuntimeError

        nport = self._normalizeport(port)
        self._devicefolder = self._finddevice(nport)

        self._rcontext  = rcontext or []
        self._wcontext  = wcontext or []
        self._rwcontext = rwcontext or []
        self._rfhandles  = {}
        self._wfhandles  = {}
        self._rwfhandles = {}

        self._dblogcounter = 0

    def _getrfilehandle(self, filename):
        return self._rfhandles[filename]

    def _normalizeport(self, port):
        """Normalize a port name

        Args:
            port (str or int): Port name

        Returns:
            str: Name of `port` in the form 'outX' or 'inD'

        Raises:
            RuntimeError: If `port` is not recognized as a name
                          of a port
        """
        port = str(port)

        if port in ['A', 'B', 'C', 'D']:
            port = 'out' + port

        if str(port) in ['1', '2', '3', '4']:
            port = 'in' + port

        if not port[:2]=='in' and not port[:3]=='out':
            raise RuntimeError

        return port

    def _finddevice(self, port):
        """Search for a device connected to a given port

        Args:
            port (str): Port in normalized form. See _normalizeport()

        Returns:
            str: Path to the device

        Raises:
            IOError: When no device can be found
        """
        import os
        for device in os.listdir(self.__class__._basefolder):
            device = os.path.join(self.__class__._basefolder, device)

            with open(os.path.join(device, 'address'), 'r') as handle:
                portname = handle.read()
                portname = portname[0:-1]
                if portname == port:
                    return device

        raise IOError("No device on port %(p)s found"%{'p': port})

    def __str__(self):
        return self._devicefolder



    def __enter__(self):
        """
        """
        def _openhandles(mode, fnames, map_):
            for f in fnames:
                fhandle = self._open_file(f, mode)
                map_[f] = fhandle

        _openhandles('r', self._rcontext, self._rfhandles)
        _openhandles('w', self._wcontext, self._wfhandles)
        _openhandles('r+', self._rwcontext, self._rwfhandles)

        return self


    def __exit__(self, type_, value, traceback):
        """Close any managed file handles.
        """
        def _closehandles(map_):
            for _, fhandle in map_.iteritems():
                fhandle.close()
            map_.clear()

        _closehandles(self._rfhandles)
        _closehandles(self._wfhandles)
        _closehandles(self._rwfhandles)


    def _open_file(self, file, mode):
        """Open a file in the device folder
        """
        import os.path
        return open(os.path.join(self._devicefolder, file), mode)

    def _write_file(self, file, value):
        """Write a value to a file in the device folder
        """
        try:
            if self._wfhandles.has_key(file):
                self._wfhandles[file].write(value)
                self._wfhandles[file].flush()
            elif self._rwfhandles.has_key(file):
                self._rwfhandles[file].write(value)
                self._rwfhandles[file].flush()
            else:
                import os
                cmdpath = os.path.join(self._devicefolder, file)
                with open(cmdpath, 'w') as cmd:
                    cmd.write(value)
        except IOError as e:
            print "Error writing %(v)s to %(f)s"%{'v': value, 'f': file}
            raise

    def _read_fhandle(self, fhandle):
        fhandle.seek(0)
        return fhandle.read()[0:-1]

    def _read_file(self, file):
        """Read a value from a file in the device folder
        """
        if self._rfhandles.has_key(file):
            self._rfhandles[file].seek(0)
            return self._rfhandles[file].read()[0:-1]
        elif self._rwfhandles.has_key(file):
            self._rwfhandles[file].seek(0)
            return self._rwfhandles[file].read()[0:-1]
        else:
            import os
            cmdpath = os.path.join(self._devicefolder, file)
            with open(cmdpath, 'r') as cmd:
                return cmd.read()[0:-1]

    def _get_address(self):
        """Name of the port this motor is connected to
        """
        return self._read_file('address')

    Address = property(_get_address)

    def _get_driver_name(self):
        """Returns the name of the driver that provides this tacho motor device
        """
        return self._read_file('driver_name')

    Driver_Name = property(_get_driver_name)

    def _get_devicefolder(self):
        return self._devicefolder

    DeviceFolder = property(_get_devicefolder)

    def propertycontextmanager(self, property, mode):
        """Construct a contextmanager that manages a file-handle that
        corresponds to a given property.

        The advantage if this over having a `Device` object as a context manager
        is that we can have one object that manages a device and dynamically derive
        objects that can be used in for example a stream server.

        Args:
            property (str): Property to manage a file-handle for
            mode (str): Either 'r' (for read) or 'r+' (for read-write)
        Returns:
            FileContextManager: object that manages a file-handle for `property`
        """
        import os.path
        try:
            filename = self.__class__._propertyfilemap[property]
        except KeyError:
            raise RuntimeError("Property %(p)s has no associated file"%{'p':property})

        filepath = os.path.join(self._devicefolder, filename)
        return FileContextManager(filepath, mode, self.Driver_Name, self.Address)


    def _filesiter(self, iter, filename):
        import os.path
        filepath = os.path.join(self._devicefolder, filename)
        with open(filepath, 'w') as f:
            for value in iter:
                f.write(str(int(value)))
                f.flush()
                yield value

    def sattribute(self, iter, name):
        try:
            filename = self.__class__._propertyfilemap[name]
            return self._filesiter(iter, filename)
        except KeyError:
            return AttributeIteratorMixin.sattribute(self, iter, name)

    def iattribute(self, name, type_=str):
        """Returns an iterator over an attribute

        If the property in question is associated with a file
        via the _propertyfilemap dictionary then an iterator is
        returned within the context of a file handle. Otherwise
        the base method AttributeIteratorMixin.iattribute() is used

        """
        try:
            filename = self.__class__._propertyfilemap[name]
            return self._fileiter(filename, type_)
        except KeyError:
            return AttributeIteratorMixin.iattribute(self, name)

    def _fileiter(self, filename, type_):
        import os.path
        filepath = os.path.join(self._devicefolder, filename)
        with open(filepath, 'r') as f:
            while True:
                f.seek(0)
                yield type_(f.read()[:-1])

class FileContextManager(object):

    def __init__(self, filepath, mode, drivername, address):
        self._filepath = filepath
        self._mode = mode
        self.Address = address
        self.Driver_Name = drivername

    def __enter__(self):
        self._filehandle = open(self._filepath, self._mode)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._filehandle.close()
        self._filehandle = None

    def read(self):
        self._filehandle.seek(0)
        return self._filehandle.read()[0:-1]

    def write(self, value):
        self._filehandle.write(value)
        self._filehandle.flush()

class PropertyContextManaget(object):

    def __init__(self, object, property, drivername, address):
        self._object = object
        self._property = property
        self.Address = address
        self.Driver_Name = drivername

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def read(self):
        return getattr(self._object, self._property)

    def write(self, value):
        return setattr(self._object, self._property, value)


def mapport(portname):
    """Map a port name to a class object suitable for handling the device
    connected to that port

    Args:
        portname (str): Name of the port, either 'outX' or 'inN'

    Returns:
        __class__: Class suitable for the devices connected to `portname`

    Raises:
        RunTimeError: When no device is connected on `portname`
        RunTimeError: When device connected on `portname` is inknown
    """
    map = dict(lsdevices())
    try:
        drivername = map[portname]
        return mapdriver(drivername)
    except KeyError:
        raise RuntimeError("No device attached to %(port)s"%{'port': portname})

def mapdriver(drivername):
    """Map a driver name to a class object suitable for that driver

    Args:
        drivername (str): Name of the driver as read from '/sys/class/TYPE/DEVICE/driver_name'

    Resturns:
        __class__: Class that can handle associated device

    Raises:
        RunTimeError: When `drivername` is unknown
    """
    map = {
        'lego-ev3-m-motor': TachoMotor,
        'lego-ev3-l-motor': TachoMotor,
        'lego-ev3-ir': Infrared_Sensor
    }
    try:
        return map[drivername]
    except KeyError:
        raise RuntimeError("Unkown device %(name)s"%{'name': drivername})

def _lsdevices(basefolder):
    """Return info on all devices of a specific category currently attached to the brick

    Args:
        basefolder (str): Subfolder of '/sys/class' that contains all the devices
            of a specific category

    Returns:
        list of tuple: A list of tuples (PORT, DRIVERNAME)
    """
    devices = []
    import os, os.path
    if os.path.exists(basefolder):
        for device in os.listdir(basefolder):
            with open(os.path.join(basefolder, device, 'address')) as f:
                port = f.read().strip()
            with open(os.path.join(basefolder, device, 'driver_name')) as f:
                driver_name = f.read().strip()
            devices.append((port, driver_name))
    return devices

def lsdevices():
    """Return info on all tacho-motors and all lego-sensors currently
    connected to the brick

    Returns:
        list of tuple: A list of tuples (PORT, DRIVERNAME)
    """
    return lstachomotors() + lslegosensors()

def lslegosensors():
    """Return info on all lego sensors currently attached to the brick

    Returns:
        list of tuple: A list of tuples (PORT, DRIVERNAME)
    """
    return _lsdevices("/sys/class/lego-sensor")

def lstachomotors():
    """Return info on all tacho-motors currently attached to the brick

    Returns:
        list of tuple: A list of tuples (PORT, DRIVERNAME)
    """
    return _lsdevices("/sys/class/tacho-motor")


class TachoMotor(Device):
    """Represents a motor connected to a port
    
    Responsibilities:
        Resource management (file handles for reading and writing to the motor)
        
    Abstractions:
        To some extend the fact that we access the motor via file handles
        
    Args:
        port (str): Port with a connected tacho-motor, either 'A', 'B', 'C', or 'D'.
        
    Raises:
        IOError: When no motor on `port` can be found.
    """
    _basefolder = "/sys/class/tacho-motor"


    def __init__(self, port, rcmproperties=None):

        propertyfilemap = {
            "Position": "position",
            "Position_SP": "position_sp",
            "Duty_Cycle": "duty_cycle",
            "Duty_Cycle_SP": "duty_cycle_sp",
            "Speed": "speed",
            "Speed_SP": "speed_sp",
        }
        TachoMotor._propertyfilemap = dict(Device._propertyfilemap.items() + propertyfilemap.items())

        rcmproperties = rcmproperties or []
        super(TachoMotor, self).__init__(port, rwcontext=[TachoMotor._propertyfilemap[property_] for property_ in rcmproperties])


        # Folder with all files for controling and reading the motor
        #
        self._motorfolder   = self._devicefolder

    def getreadproperties(self):
        return TachoMotor._propertyfilemap.keys()

    def _get_command(self):
        raise RuntimeError("Command is a write only property")

    def _set_command(self,command):
        """Sends a command to the motor controller. See commands for a list of possible values

        Args:
            command (str): Command to send
        """
        self._write_file('command',command)

    Command = property(_get_command, _set_command)

    def _get_commands(self):
        """Returns a list of commands that are supported by the motor

        Returns:
            list of str: List of commands supported by this motor. Each can be used as a value for `self.Command`
        """
        commands = self._read_file('commands')
        return commands.split(' ')

    Commands = property(_get_commands)

    def _get_count_per_rot(self):
        """Returns the number of tacho counts in one rotation of the motor

        Returns:
            int: Number of tacho counts in one rotation
        """
        return int(self._read_file('count_per_rot'))

    Count_Per_Rot = property(_get_count_per_rot)


    def _get_duty_cycle(self):
        """Returns the current duty cycle of the motor

        Returns:
            int: Duty cycle in percents. Can be negative
        """
        return int(self._read_file('duty_cycle'))

    Duty_Cycle = property(_get_duty_cycle)

    def _get_duty_cycle_sp(self):
        """Get the duty cycle setpoint

        Returns:
            int: Duty cycle setpoint in percents. Can be negative
        """
        return int(self._read_file('duty_cycle_sp'))

    def _set_duty_cycle_sp(self, duty_cycle):
        """Sets the duty cycle setpoint

        Args:
            duty_cycle_sp (int or str): Duty cycle setpoint in percents. Can be negative
        """
        self._write_file('duty_cycle_sp', str(duty_cycle))

    Duty_Cycle_SP = property(_get_duty_cycle_sp,_set_duty_cycle_sp)

    def _get_encoder_polarity(self):
        """The polarity of the rotary encoder

        Returns:
            str: either 'normal' or 'reversed'
        """
        return self._read_file('encoder_polarity')

    def _set_encoder_polarity(self, polarity):
        """Set the polarity of the rotary encoder

        This is an advanced feature to all use of motors that send inversed encoder signals to the EV3.
        This should be set correctly by the driver of a device. It You only need to change this value if you are
        using a unsupported device.

        Args:
            polarity (str): Either 'normal' or 'reversed'
        """
        self._read_file('encoder_polarity')

    Encoder_Polarity = property(_get_encoder_polarity, _set_encoder_polarity)

    def _get_polarity(self):
        """The polarity of the motor

        Returns:
            str: either 'normal' or 'reversed'
        """
        return self._read_file('polarity')

    def _set_polarity(self, polarity):
        """Set the polarity of the motor

        Args:
            polarity (str): Either 'normal' or 'reversed'
        """
        self._read_file('polarity')

    Polarity = property(_get_polarity, _set_polarity)

    def _get_position(self):
        """The position of the motor

        Returns:
            int: The position of the motor in tacho counts
        """
        return int(self._read_file('position'))

    def _set_position(self, position):
        """Set the position of the motor. Note that this does not
        physically rotate the motor.

        Args:
            position (int): The position in tacho counts
        """
        self._write_file('position', str(position))

    Position = property(_get_position, _set_position)

    def _get_position_sp(self):
        """The position setpoint

        Returns:
            int: The position setpoint in tacho counts
        """
        return int(self._read_file('position_sp'))

    def _set_position_sp(self, position):
        """Set the position setpoint

        Args:
            position (int): The position setpoint in tacho counts.
        """
        self._write_file('position_sp', str(position))

    Position_SP = property(_get_position_sp, _set_position_sp)

    def _get_speed(self):
        """Speed of the motor

        Returns:
            int: Speed of the motor in tacho counts per second
        """
        return int(self._read_file('speed'))

    Speed = property(_get_speed)

    def _set_speed_sp(self, speed):
        """Set the speed setpoint of the motor

        This is only used when `self.Speed_Regulation_Enabled` is 'on'

        Args:
            speed (int): Speed setpoint in tacho counts per second
        """
        self._write_file('speed_sp', str(speed))

    def _get_speed_sp(self):
        """The speed setpoint of the motor

        Returns:
            int: Speed setpoint in tacho counts per second
        """
        return int(self._read_file('speed_sp'))

    Speed_SP = property(_get_speed_sp, _set_speed_sp)


    def _get_speed_regulation_enabled(self):
        # TODO: the file 'speed_regulation' does not exist
        return self._read_file('speed_regulation')

    def _set_speed_regulation_enabled(self, on_or_off):
        """Turns speed regulation on or off

        Args:
            on_or_off (str): Either 'on' or 'off'
        """
        # TODO: the file 'speed_regulation' does not exist
        self._write_file('speed_regulation', on_or_off)

    Speed_Regulation_Enabled = property(_get_speed_regulation_enabled, _set_speed_regulation_enabled)

    def reset(self):
        import os
        cmd = os.path.join(self._motorfolder, 'command')
        with open(cmd, 'w') as c:
            c.write('reset')

    def set_stop(self,command):
        """Set the behaviour of self.stop()
        
        Args:
            command (str): Either 'coast', 'break', or 'hold'
        """
        self._write_file('stop_command', command)
        
    def get_stop(self):
        return self._read_file('stop_command')
        
    stop_command = property(get_stop,set_stop)
    
    def runtorelpos(self, position=None, duty_cycle=None):
        if position!=None:
            self.position_sp = position
        if duty_cycle!=None:
            self.duty_cycle_sp = duty_cycle
        self.Command = 'run-to-rel-pos'
    
    def runtoabspos(self):
        self.Command = 'run-to-abs-pos'

    def stop(self):
        self.Command = 'stop'
        
    def run_forever(self):
        self.Command = 'run-forever'
    
    def run_direct(self):
        self.Command = 'run-direct'

class Infrared_Sensor(Device):
    """Interface to the Infra-red sensor

    Args:
        port (str): Port on which the device is connected
        rcmproperties (iter of str): List of properties whoes files will be managed within a 'with' statement
    """
    _basefolder = "/sys/class/lego-sensor"

    def __init__(self, port, rcmproperties=None):

        propertyfilemap = {
            "Proximity": "value0",
            "SeekHeading_1": "value0",
            "SeekHeading_2": "value2",
            "SeekHeading_3": "value4",
            "SeekHeading_4": "value6",
            "SeekDistance_1": "value1",
            "SeekDistance_2": "value3",
            "SeekDistance_3": "value5",
            "SeekDistance_4": "value7"
        }
        Infrared_Sensor._propertyfilemap = dict(super(Infrared_Sensor, self)._propertyfilemap.items() + propertyfilemap.items())

        self._rcmproperties  = rcmproperties or []
        values = set([ Infrared_Sensor._propertyfilemap[p] for p in self._rcmproperties])
        super(Infrared_Sensor, self).__init__(port, rcontext=values)

        # Generate properties for seekheading and seekdistance for all the channels
        #
        # TODO: Little experiment, better spell them out as there are only 4 of each
        # TODO: or code the managed properties as functions where functions with zero arguments are just values
        #
        """
        for i in range(4):
            pname  = "SeekDistance_%(i)d"%{'i': i+1}
            fvalue = lambda i:property(lambda slf: slf._get_value(self._seekdistancevalueindex(i+1)))
            setattr(Infrared_Sensor, pname, fvalue(i))

            pname  = "SeekHeading_%(i)d"%{'i': i+1}
            fvalue = lambda i:property(lambda slf: slf._get_value(self._seekheadingvalueindex(i+1)))
            setattr(Infrared_Sensor, pname, fvalue(i))
        """

    SeekDistance_1 = property(lambda self: self.SeekDistance(1))
    SeekDistance_2 = property(lambda self: self.SeekDistance(2))
    SeekDistance_3 = property(lambda self: self.SeekDistance(3))
    SeekDistance_4 = property(lambda self: self.SeekDistance(4))

    SeekHeading_1 = property(lambda self: self.SeekHeading(1))
    SeekHeading_2 = property(lambda self: self.SeekHeading(2))
    SeekHeading_3 = property(lambda self: self.SeekHeading(3))
    SeekHeading_4 = property(lambda self: self.SeekHeading(4))

    def __enter__(self):
        super(Infrared_Sensor, self).__enter__()

    def getreadproperties(self):
        return Infrared_Sensor._propertyfilemap.keys()

    def _get_value(self, i):
        return self._read_file('value%(n)d'%{'n': i})

    def _get_proximity(self):
        return self._get_value(0)

    Proximity = property(_get_proximity)

    def _seekheadingvalueindex(self, channel):
        return (channel-1)*2

    def _seekdistancevalueindex(self, channel):
        return (channel-1)*2 +1

    def SeekHeading(self, channel):
        return self._get_value(self._seekheadingvalueindex(channel))

    def SeekDistance(self, channel):
        return self._get_value(self._seekdistancevalueindex(channel))

    def _get_modes(self):
        modes = self._read_file('modes')
        return modes.split(' ')

    Modes = property(_get_modes)

    def _get_mode(self):
        return self._read_file('mode')

    def _set_mode(self, mode):
        self._write_file('mode', mode)

    Mode = property(_get_mode, _set_mode)

    def _get_num_values(self):
        return int(self._read_file('num_values'))

    Num_Values = property(_get_num_values)

class TachoMotorPIDPositionManager(AttributeIteratorMixin):
    """Device manager that controls the position of
    a tacho-motor with a proportional controler

    """
    def __init__(self, port, maxcontrol, fadezone):
        import ev3local.ev3
        self._device = ev3local.ev3.TachoMotor(port)

        # TODO: Make _device an optional argument, when provided here we should check the state instead of setting it
        #
        self._device.reset()
        self._device.run_direct()

        kp = 0.5*maxcontrol / fadezone
        kd = 0.05
        self._pcntr = PController(kp, kd, maxcontrol, -maxcontrol)


    def reset(self):
        self._device.reset()

    def _set_duty_cycle(self):
        self._device.Duty_Cycle_SP = self._pcntr.ControlVariable

    def _get_position_sp(self):
        return self._pcntr.SetPoint

    def _set_position_sp(self, sp):
        self._pcntr.SetPoint = sp

    Position_SP = property(_get_position_sp, _set_position_sp)

    def _get_device(self):
        return self._device

    Device = property(_get_device)

    def _get_pcntrl(self):
        return self._pcntr

    PCntrl = property(_get_pcntrl)

    def step(self, setpoint):
        self._pcntr.SetPoint = setpoint
        self._pcntr.ProcesVariable = self.Device.Position
        self._pcntr.step()
        self._device.Duty_Cycle_SP = int(self._pcntr.ControlVariable)

    def propertycontextmanager(self, property, mode):
        if property=='Position_SP':
            return PropertyContextManaget(self, property, self.Device.Driver_Name, self.Device.Address)
        else:
            return self.Device.propertycontextmanager(property, mode)
