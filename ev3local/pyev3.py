def coroutine(f):
    def g(*args):
        h = f(*args)
        h.next()
        return h
    g.__name__ = f.__name__
    return g


def joints():
    m1 = AbsPosition('outA')
    j1 = Joint(m1, [8, 56])

    m2 = AbsPosition('outB')
    j2 = Joint(m2, [12, 20, 56], -1)

    js = Joints((j1, j2))

    return js


def inversekinematics():

    from kinematics.kinematics import CCD
    ccd = CCD([17.5, 20])


    def g(tx, ty):
        angles = ccd_then_normalize(ccd, tx, ty)
        if validateangles(angles):
            return angles
        ccd.set_angles((135, 0))
        angles = ccd_then_normalize(ccd, tx, ty)
        if validateangles(angles):
            return angles

        return angles


    def validateangles(angles):
        if angles[1]<-100 or angles[1]>100:
            return False
        if angles[0]<0 or angles[0]>100:
            return False
        return True


    def ccd_then_normalize(ccd, tx, ty):
        ccd.iterate(tx, ty)
        angles = ccd.get_angles()
        angles = normalizeangles(angles)
        return angles


    def normalizeangles(angles):
        return [normalizeangle(angle) for angle in angles]


    def normalizeangle(angle):
        while angle>180:
            angle -= 360
        while angle<-180:
            angle += 360
        return angle


    return g


class Joints(object):
    """Convenience class for operating several joints at once

    """
    def __init__(self, joints, maxspeed=20.0):
        self._joints = joints
        self._maxspeed = maxspeed


    def _set_angles(self, angles):
        self.__setuniformspeeds(angles)
        self.__setangles(angles)


    def __setuniformspeeds(self, targetangles):
        import itertools
        arcdistances = [abs(targetangle - joint.Angle) for joint, targetangle in itertools.izip(self._joints, targetangles)]
        maxarcdistance = max(arcdistances)
        if maxarcdistance > 0:
            for joint, arcdistance in itertools.izip(self._joints, arcdistances):
                joint.Speed = (arcdistance / maxarcdistance) * self._maxspeed


    def __setangles(self, angles):
        import itertools
        for joint, angle in itertools.izip(self._joints, angles):
            joint.Angle = angle


    def _get_angles(self):
        return tuple((joint.Angle for joint in self._joints))


    Angles = property(_get_angles, _set_angles)


    def reset(self):
        for joint in self._joints:
            joint.reset()


class Joint(object):
    """A revolute joint operated by a motor and some gearing

    Arguments:
        acturator (object): Used to set the absolute position of a motor. Must have a 'Position' property
        gearing (list of num): List of numbers of tooths on a gear, starting with the gear
            closest to the actuator
        polarity (int): Either 1 or -1. Used to switch the direction of rotation
    """

    # TODO: Add contrainst
    # TODO: Allow port name instead of actuator

    def __init__(self, actuator, gearing, polarity=1):

        if polarity not in [1, -1]:
            raise RuntimeError("Polarity needs to be 1 or -1, got %(p)s"%{'p': str(polarity)})

        self._actuator = actuator
        self._ratio = self._computeratio(gearing, polarity)


    def _computeratio(self, gearing, polarity):
        import itertools
        fractions = (float(x)/float(y) for (x, y) in itertools.izip(gearing[1:], gearing[0:]))
        return polarity * reduce(lambda x, y: x*y, fractions, 1)


    def _set_angle(self, angle):
        self._actuator.Position = self._ratio * float(angle)


    def _get_angle(self):
        return self._actuator.Position / self._ratio


    Angle = property(_get_angle, _set_angle)


    def _get_speed(self):
        return self._actuator.Speed / self._ratio


    def _set_speed(self, speed):
        self._actuator.Speed = self._ratio * speed


    Speed = property(_get_speed, _set_speed)


    def reset(self):
        self.Angle = 0


class DutyCycle(object):
    """Control a Tacho-Motor by directly setting the Duty-Cyle

    """
    def __init__(self, port):
        port = _normalizeport(port)
        self._port = port
        self._devicefolder = _finddevicefolder('/sys/class/tacho-motor', port)

        import os.path
        with open(os.path.join(self._devicefolder, 'command'), 'w') as f:
            f.write('run-direct')
            f.flush()


    @coroutine
    def setdutycyclesp(self):
        import os.path
        with open(os.path.join(self._devicefolder, 'duty_cycle_sp'), 'w') as f:
            try:
                while True:
                    value = yield
                    f.write(str(value))
                    f.flush()
            except GeneratorExit:
                pass

    def __iter__(self):
        return self.getdutycycle()


    def getdutycycle(self):
        import os.path
        with open(os.path.join(self._devicefolder, 'duty_cycle'), 'r') as f:
            while True:
                f.seek(0)
                value = f.readline()
                yield int(value[:-1])


class AbsPosition(object):
    """Setting the absolute position of a Tacho-Motor

    """
    def __init__(self, port, speed=75, stop_action='hold'):
        port = _normalizeport(port)
        self._devicefolder = _finddevicefolder('/sys/class/tacho-motor', port)

        import os.path

        with open(os.path.join(self._devicefolder, 'speed_sp'), 'w') as f:
            f.write(str(int(speed)))
            f.flush()

        with open(os.path.join(self._devicefolder, 'stop_action'), 'w') as f:
            f.write(stop_action)
            f.flush()


    def callibrate(self):
        import os.path
        with open(os.path.join(self._devicefolder, 'position_sp'), 'w') as f:
            with open(os.path.join(self._devicefolder, 'position'), 'w') as s:
                f.write('0')
                f.flush()
                s.write('0')
                s.flush()


    def _set_absposition(self, position):
        import os.path
        with open(os.path.join(self._devicefolder, 'position_sp'), 'w') as f:
            with open(os.path.join(self._devicefolder, 'command'), 'w') as c:
                f.write(str(int(position)))
                f.flush()
                c.write('run-to-abs-pos')
                c.flush()


    def _get_absposition(self):
        import os.path
        with open(os.path.join(self._devicefolder, 'position'), 'r') as f:
            f.seek(0)
            s = f.read()
            return int(s[:-1])


    Position = property(_get_absposition, _set_absposition)


    def _get_speed(self):
        import os.path
        with open(os.path.join(self._devicefolder, 'speed'), 'r') as f:
            f.seek(0)
            s = f.read()
            return int(s[:-1])


    def _set_speed(self, speed):
        import os.path
        with open(os.path.join(self._devicefolder, 'speed_sp'), 'w') as f:
            f.write(str(int(speed)))


    Speed = property(_get_speed, _set_speed)


    @coroutine
    def setabsposition(self):
        import os.path
        with open(os.path.join(self._devicefolder, 'position_sp'), 'w') as f:
            with open(os.path.join(self._devicefolder, 'command'), 'w') as c:
                while True:
                    position_sp = yield
                    f.write(str(position_sp))
                    f.flush()
                    c.write('run-to-abs-pos')
                    c.flush()


def _normalizeport(port):
    """Normalize a port name

    Args:
        port (str or int): Port name

    Returns:
        str: Name of `port` in the form 'outX' or 'inY'

    Raises:
        RuntimeError: If `port` is not recognized as a name
                      of a port
    """
    port = str(port)

    if port in ['A', 'B', 'C', 'D']:
        port = 'out' + port

    if port in ['1', '2', '3', '4']:
        port = 'in' + port

    if not port[:2]=='in' and not port[:3]=='out':
        raise RuntimeError

    return port


def _finddevicefolder(basefolder, port):
    """Search for a device connected to a given port

    Args:
        port (str): Port in normalized form. See _normalizeport()

    Returns:
        str: Path to the device

    Raises:
        IOError: When no device can be found
    """
    import os, os.path
    for device in os.listdir(basefolder):
        device = os.path.join(basefolder, device)

        with open(os.path.join(device, 'address'), 'r') as handle:
            portname = handle.read()
            portname = portname[0:-1]
            if portname == port:
                return device

    raise IOError("No device on port '%(p)s' found"%{'p': port})