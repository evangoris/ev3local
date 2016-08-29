"""Application for detecting axes and buttons of a controller

    Evan Goris, 2016
"""
import evdev
import evdev.ecodes
import cmd

class EvdevInspect(cmd.Cmd, object):

    def __init__(self, *args):
        super(EvdevInspect, self).__init__(*args)
        self._quit = False
        self._devices = evdev.list_devices()

    def _getdevices(self):
        return [evdev.InputDevice(x) for x in self._devices]

    def do_devices(self, *args):
        """List all available devices
        """
        for i, d in enumerate(self._getdevices()):
            print "%(i)d) %(d)s"%{'i':i, 'd':d.name}
        return False

    def do_select(self, *args):
        """Select a device
        """
        try:
            idx = int(args[0])
        except ValueError:
            print "Usage: `select N`"

        try:
            self._device = self._devices[idx]
        except IndexError:
            try:
                n = len(self._devices)
            except:
                n = 0
            print "Usage: `select N` where `N` < %(n)d"%{'n':n}


    def do_device(self, *args):
        """Show device details
        """
        print evdev.InputDevice(self._device)


    def do_quit(self, *args):
        """Quit
        """
        return True


    def do_detect(self, *args):
        """Detect buttons and absolute axes
        """
        device = evdev.InputDevice(self._device)

        if len(args)!=1:
            print "Usage: `detect [ABS|KEY]`"
        if args[0]=='ABS':
            result = _detect_abs(device)
            print result
        elif args[0]=='KEY':
            result = _detect_btn(device)
            print result
        else:
            print "Usage: `detect [ABS|KEY]`"


    def do_capabilities(self, *args):
        device = evdev.InputDevice(self._device)
        print device.capabilities(verbose=True, absinfo=True)


    def do_types(self, *args):
        device = evdev.InputDevice(self._device)
        print
        for (name, code) in device.capabilities(verbose=True).keys():
            print " " + name
        print


    def do_codes(self, *args):
        device = evdev.InputDevice(self._device)
        capabilities = device.capabilities(verbose=True, absinfo=False)
        keys = [ (name, code) for (name, code) in capabilities if name==args[0] ]
        if keys==[]:
            types = _available_types(device)
            print "Usage: `codes [%(tps)s]`"%{'tps':"|".join([str(type_) for (type_, _) in types])}
        else:
            print
            for name, code in capabilities[keys[0]]:
                print " " + name + " " + str(code)
            print


    def do_absinfo(self, *args):
        try:
            code = evdev.ecodes.ecodes[args[0]]
        except KeyError:
            print "Usage `absinfo [abs_name|abs_code]`"
            return

        device = evdev.InputDevice(self._device)
        capabilities = device.capabilities(verbose=False, absinfo=True)
        try:
            absinfo = capabilities[evdev.ecodes.ecodes['EV_ABS']][code][1]
            print absinfo
        except KeyError:
            print "`%(a)s` does not identify an absolute axes"%{'a': args[0]}


    def postcmd(self, stop, line):
        return stop

def _available_types(device):
        return device.capabilities(verbose=True).keys()

def _absinfo(device, code):
    """Get the AbsInfo object for a given axes
    """
    capabilities = device.capabilities(verbose=False, absinfo=True)
    return dict(capabilities[evdev.ecodes.ecodes['EV_ABS']])[code]

def _detect_abs(device):
    """Read events from device until an absolute axes is moved to
    its maximum and to its minimum.

    Args:
        device (evdev.InputDevice): Device to read events from
    Returns:
        tuple of (str, int): Symbolic name and code of an absolute axes
    """
    import evdev, evdev.ecodes

    states = {}
        # Dictionary mapping event codes to 'states':
        #   0: Wait for maximum value
        #   1: Maximum seen, wait for minimum
        #   2: Both maximum and minimum seen, in that order

    absinfos = {}
        # Dictionary mapping event codes to tuples (min, max, range)
        #

    for event in device.read_loop():
        if event.type==evdev.ecodes.ecodes['EV_ABS']:

            if not states.has_key(event.code):
                # First time we see this event, store min, max, and range of the axis
                # and move to 'wait-for-maximum' state
                #
                states[event.code]=0
                absinfo = _absinfo(device, event.code)
                absinfos[event.code] = (absinfo.min, absinfo.max, float(absinfo.max - absinfo.min))

            if states[event.code]==0:
                absinfo = absinfos[event.code]
                if absinfo[1]-event.value < 0.2*absinfo[2]:
                    # Axes moved close to its maximum, now move to 'wait-for-minimum' state
                    #
                    states[event.code]=1

            if states[event.code]==1:
                absinfo = absinfos[event.code]
                if event.value-absinfo[0] < 0.2*absinfo[2]:
                    # Axes moved close to minimum, move to 'done' state
                    #
                    states[event.code]=2

            if states[event.code]==2:
                # We are in 'done' state, return axes information
                #
                import evdev.util
                result = evdev.util.resolve_ecodes({event.type: [event.code]}).next()[1][0]
                return result


def _detect_btn(device):
    """Read events from device until a button is pressed and released

    Args:
        device (evdev.InputDevice): Device to read events from
    Returns:
        tuple of (str, int): Symbolic name and code of a button
    """
    import evdev, evdev.ecodes
    scores = {}

    for event in device.read_loop():
        if event.type == evdev.ecodes.ecodes['EV_KEY']:
            if not scores.has_key(event.code):
                scores[event.code] = 0
            scores[event.code] = scores[event.code] +1
            best = max(scores.iteritems(), key=lambda x:x[1])
            if best[1]>=2:
                import evdev.util
                result = evdev.util.resolve_ecodes({event.type: [best[0]]}).next()[1][0]
                return result



def main():
    app = EvdevInspect()
    app.cmdloop() #"Evdev Device Inspector")

if __name__=='__main__':
    main()


