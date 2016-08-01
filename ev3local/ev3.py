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
    """

    _basefolder = None
        # Needs to be overriden in derived classes to point
        # to the folder that contains connected devices of
        # the type that the derived class represents
        #

    _propertyfilemap = {}

    def __init__(self, port):

        if self.__class__._basefolder == None:
            raise RuntimeError

        nport = self._normalizeport(port)
        self._devicefolder = self._finddevice(nport)

        self._filehandles = {}
            # Mapping of filenames to filehandles
            #

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
        return self


    def __exit__(self, type_, value, traceback):
        """Close any managed file handles.
        """
        self._closefilahandles()

    def __del__(self):
        self._closefilahandles()

    def _closefilahandles(self):
        for file, handle in self._filehandles.iteritems():
            handle.close()

        self._filehandles.clear()

    def _open_file(self, file, mode):
        """Open a file in the device folder
        """
        import os.path
        return open(os.path.join(self._devicefolder, file), mode)

    def _write_file(self, file, value):
        """Write a value to a file in the device folder

        Args:
            file (str): Name of the file to write to
            value (str): Value to write
            type_ (type): Type to write, `value` will be cast before written
        """
        try:
            if not self._filehandles.has_key(file):
                import os
                cmdpath = os.path.join(self._devicefolder, file)
                try:
                    filehandle = open(cmdpath, 'r+')
                except IOError:
                    filehandle = open(cmdpath, 'w')
                self._filehandles[file] = filehandle

            filehandle = self._filehandles[file]
            filehandle.write(value)
            filehandle.flush()

        except IOError as e:
            print "Error writing %(v)s to %(f)s"%{'v': value, 'f': file}
            raise

    def _read_fhandle(self, fhandle):
        fhandle.seek(0)
        return fhandle.read()[0:-1]

    def _read_file(self, file):
        """Read a value from a file in the device folder

        Args:
            file (str): Name of file to read from

        Returns:
            str: Value red from the file
        """
        try:
            if not self._filehandles.has_key(file):
                import os
                cmdpath = os.path.join(self._devicefolder, file)
                try:
                    filehandle = open(cmdpath, 'r+')
                except IOError:
                    filehandle = open(cmdpath, 'r')
                self._filehandles[file] = filehandle

            filehandle = self._filehandles[file]
            return self._read_fhandle(filehandle)

        except IOError as e:
            print "Error reading from %(f)s"%{'f': file}
            raise

    def _get_address(self):
        """Name of the port this motor is connected to

        Returns:
            str: Name of the port
        """
        return self._read_file('address')

    Address = property(_get_address)

    def _get_driver_name(self):
        """Returns the name of the driver that provides this tacho motor device

        Returns:
            str: Driver name
        """
        return self._read_file('driver_name')

    Driver_Name = property(_get_driver_name)

    def _get_devicefolder(self):
        """
        Returns:
            str: Sub-folder of '/sys/class' that represents the attached device
        """
        return self._devicefolder

    DeviceFolder = property(_get_devicefolder)

    def sattribute(self, iter, name):
        try:
            filename = self.__class__._propertyfilemap[name]
            return self._filesiter(iter, filename)
        except KeyError:
            return AttributeIteratorMixin.sattribute(self, iter, name)

    def iattribute(self, name):
        """Returns an iterator over an attribute

        If the property in question is associated with a file
        via the _propertyfilemap dictionary then an iterator is
        returned within the context of a file handle. Otherwise
        the base method AttributeIteratorMixin.iattribute() is used

        """
        try:
            filename = self.__class__._propertyfilemap[name]
            return self._fileiter(filename)
        except KeyError:
            return AttributeIteratorMixin.iattribute(self, name)

    def _filesiter(self, iter, filename):
        import os.path
        filepath = os.path.join(self._devicefolder, filename)
        with open(filepath, 'w') as f:
            for value in iter:
                f.write(str(value))
                f.flush()
                yield value

    def _fileiter(self, filename):
        import os.path
        filepath = os.path.join(self._devicefolder, filename)
        with open(filepath, 'r') as f:
            while True:
                f.seek(0)
                yield int(f.read()[:-1])

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


    def __init__(self, port):

        propertyfilemap = {
            "Position": "position",
            "Position_SP": "position_sp",
            "Duty_Cycle": "duty_cycle",
            "Duty_Cycle_SP": "duty_cycle_sp",
            "Speed": "speed",
            "Speed_SP": "speed_sp",
        }
        TachoMotor._propertyfilemap = dict(Device._propertyfilemap.items() + propertyfilemap.items())

        super(TachoMotor, self).__init__(port)


        # Folder with all files for controling and reading the motor
        #
        self._motorfolder   = self._devicefolder

    def getreadproperties(self):
        return TachoMotor._propertyfilemap.keys()

    def _get_command(self):
        """
        """
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
            duty_cycle_sp (int): Duty cycle setpoint in percents. Can be negative
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
        """
        Returns:
            str: The currently set command used for stopping the motor
        """
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
    """
    _basefolder = "/sys/class/lego-sensor"

    def __init__(self, port):

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

        super(Infrared_Sensor, self).__init__(port)


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
        """
        Args:
            i (int): Value to read

        Returns:
            int: Value from value `i`
        """
        return int(self._read_file('value%(n)d'%{'n': i}))

    def _get_proximity(self):
        """
        Assumption:
            Mode == 'Proximity'

        Returns:
            int: Proximity value
        """
        return self._get_value(0)

    Proximity = property(_get_proximity)

    def _seekheadingvalueindex(self, channel):
        """
        Args:
            channel (int): Channel

        Returns:
            int: Value index for reading heading for channel `channel`
        """
        return (channel-1)*2

    def _seekdistancevalueindex(self, channel):
        """
        Args:
            channel (int): Channel

        Returns:
            int: Value index for reading distance for channel `channel`
        """
        return (channel-1)*2 +1

    def SeekHeading(self, channel):
        """
        Assumption:
            Mode == 'Seek'

        Args:
            channel (int): Channel

        Returns:
            int: Heading for channel `channel`
        """
        return self._get_value(self._seekheadingvalueindex(channel))

    def SeekDistance(self, channel):
        """
        Assumption:
            Mode == 'Seek'

        Args:
            channel (int): Channel

        Returns:
            int: Distance for channel `channel`
        """
        return self._get_value(self._seekdistancevalueindex(channel))

    def _get_modes(self):
        """
        Returns:
            list of str: List of available modes
        """
        modes = self._read_file('modes')
        return modes.split(' ')

    Modes = property(_get_modes)

    def _get_mode(self):
        """
        Returns:
            str: Current set mode
        """
        return self._read_file('mode')

    def _set_mode(self, mode):
        """
        Args:
            mode (str): Mode to set
        """
        self._write_file('mode', mode)

    Mode = property(_get_mode, _set_mode)

    def _get_num_values(self):
        """
        Returns:
            int: Number of different values
        """
        return int(self._read_file('num_values'))

    Num_Values = property(_get_num_values)

