"""Interface to EV3 Hardware

Evan Goris
2015
"""

class TachoMotor(object):
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
                
        # Folder with all files for controling and reading the motor
        #
        self._motorfolder   = self._findmotor(port)
        
        # File handles to file to set speed etc. Is initialized in __enter__()
        #
        self._duty_cycle_sp = None
        
    def _findmotor(self,port):
        """Look for a motor connected to `port`.
        
        Args:
            port (str): Port on which to look for a motor, either 'A', 'B', 'C', or 'D'.

        Raises:
            IOError: When no motor on `port` can be found.
        """
        import os
        if not port[:3]=="out":
            port = "out" + port
        
        # Run through all connected motors and see whether they
        # are connected to `port`
        #
        for motor in os.listdir(TachoMotor._basefolder):
            motor = os.path.join(TachoMotor._basefolder,motor)
         
            # Read the port_name atrribute and see if its equal
            # to `port`
            #
            with open(os.path.join(motor,'address'),'r') as handle:
                portname = handle.read()
                portname = portname[0:-1]
                if portname == port:
                    return motor
                    
        raise IOError("No motor on port %(p)s found"%{'p':port})
    
    def __str__(self):
        return self._motorfolder
    
    def __enter__(self):
        """
        Open 'duty_cycle_sp' in read/write mode
        if they not already are.
        """
        import os
        if self._duty_cycle_sp==None:
            mdpath = os.path.join(self._motorfolder,"duty_cycle_sp")
            self._duty_cycle_sp = open(mdpath, 'r+')
        
        return self
        
    def __exit__(self, type_, value, traceback):
        """Close any managed file handles.
        """
        if self._duty_cycle_sp:
            self._duty_cycle_sp.close()
            self._duty_cycle_sp = None
            
    def _get_address(self):
        """Name of the port this motor is connected to
        """
        return self._read_file('address')

    Address = property(_get_address)

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

    def _get_driver_name(self):
        """Returns the name of the driver that provides this tacho motor device
        """
        return self._read_file('driver_name')

    Driver_Name = property(_get_driver_name)

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
        if self._duty_cycle_sp:
            self._duty_cycle_sp.seek(0)
            return int(self._duty_cycle_sp.read())
        else:
            return int(self._read_file('duty_cycle_sp'))

    def _set_duty_cycle_sp(self, duty_cycle):
        """Sets the duty cycle setpoint

        Args:
            duty_cycle_sp (int or str): Duty cycle setpoint in percents. Can be negative
        """
        if self._duty_cycle_sp:
            self._duty_cycle_sp.write(str(duty_cycle))
            self._duty_cycle_sp.flush()
        else:
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
        return self._read_file('speed_regulation')

    def _set_speed_regulation_enabled(self, on_or_off):
        """Turns speed regulation on or off

        Args:
            on_or_off (str): Either 'on' or 'off'
        """
        self._write_file('speed_regulation', on_or_off)

    Speed_Regulation_Enabled = property(_get_speed_regulation_enabled, _set_speed_regulation_enabled)


    def get_motorfolder(self):
        return self._motorfolder
        
    motorfolder = property(get_motorfolder)

    
    def reset(self):
        import os
        cmd = os.path.join(self._motorfolder,'command')
        with open(cmd,'w') as c:
            c.write('reset')
        

    

    

    


    

    

    
    def stop(self):
        self.Command = 'stop'
    
    def set_stop(self,command):
        """Set the behaviour of self.stop()
        
        Args:
            command (str): Either 'coast', 'break', or 'hold'
        """
        self._write_file('stop_command',command)
        
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
        
    def _write_file(self,file,value):
        import os
        cmdpath = os.path.join(self._motorfolder, file)
        with open(cmdpath,'w') as cmd:
            cmd.write(value)
    
    def _read_file(self,file):
        import os
        cmdpath = os.path.join(self._motorfolder,file)
        with open(cmdpath,'r') as cmd:
            return cmd.read()[0:-1]
        

    def stop(self):
        self.Command = 'stop'
        
    def run_forever(self):
        self.Command = 'run-forever'
    
    def run_direct(self):
        self.Command = 'run-direct'


class Infrared_Sensor(object):

    _basefolder = "/sys/class/lego-sensor"
    _maxvalues  = 8

    def __init__(self, port):
        self._sensorfolder = self._findsensor(str(port))
        self._valuefps     = [ None for i in range(Infrared_Sensor._maxvalues) ]

    def __enter__(self):
        import os.path
        for i in range(8):
            self._valuefps[i] = open(os.path.join(self._sensorfolder, 'value%(n)d'%{'n':i}))

    def __exit__(self, type_, value, traceback):
        for fp in self._valuefps:
            if fp:
                fp.close()
        self._valuefps = [ None for i in range(Infrared_Sensor._maxvalues) ]

    def _findsensor(self, port):
        """Look for a sensor connected to `port`.

        Args:
            port (int): Port on which to look for a sensor, either 1, 2, 3, or 4.

        Raises:
            IOError: When no sensor on `port` can be found.
        """
        import os
        if not port[:2]=="in":
            port = "in" + port

        # Run through all connected motors and see whether they
        # are connected to `port`
        #
        for sensor in os.listdir(Infrared_Sensor._basefolder):
            sensor = os.path.join(Infrared_Sensor._basefolder, sensor)

            # Read the port_name atrribute and see if its equal
            # to `port`
            #
            with open(os.path.join(sensor, 'address'), 'r') as handle:
                portname = handle.read()
                portname = portname[0:-1]
                if portname == port:
                    return sensor

        raise IOError("No sensor on port %(p)s found"%{'p':port})

    def _write_file(self,file,value):
        import os
        cmdpath = os.path.join(self._sensorfolder, file)
        with open(cmdpath, 'w') as cmd:
            cmd.write(value)

    def _read_file(self,file):
        import os
        cmdpath = os.path.join(self._sensorfolder, file)
        with open(cmdpath, 'r') as cmd:
            return cmd.read()[0:-1]

    def _get_value(self, i):
        if self._valuefps[i]:
            self._valuefps[i].seek(0)
            return self._valuefps[i].read()[0:-1]
        else:
            return self._read_file('value%(n)d'%{'n': i})

    def _get_proximity(self):
        return self._get_value(0)

    Proximity = property(_get_proximity)

    def SeekHeading(self, channel):
        return self._get_value((channel-1)*2)

    def SeekDistance(self, channel):
        return self._get_value((channel-1)*2 +1)

    def _get_address(self):
        return self._read_file('address')

    Address = property(_get_address)

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

    def _get_driver_name(self):
        return self._read_file('driver_name')

    Driver_Name = property(_get_driver_name)

if __name__=='__main__':
    import time
    
    try:
        motor = TachoMotor('A')
        print motor._motorfolder    
        print motor.position
        print motor.duty_cycle_sp
        
        motor.reset()
        
        motor.duty_cycle_sp = 100
        motor.run_forever()
        for i in range(0,4):
            time.sleep(0.5)
            print motor.speed

        motor.stop()
        motor.duty_cycle_sp = -50
        motor.run_forever()
        for i in range(0,4):
            time.sleep(0.5)
            print motor.speed
        motor.stop()
        
        motor.reset()


    finally:    
        motor.stop()
    
    