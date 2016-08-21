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
            return
        elif args[0]=='KEY':
            result = self._detect_btn(device)
            print result
        else:
            print "Usage: `detect [ABS|KEY]`"

    def _detect_btn(self, device):
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


    def postcmd(self, stop, line):
        return stop

def main():
    app = EvdevInspect()
    app.cmdloop() #"Evdev Device Inspector")

if __name__=='__main__':
    main()


