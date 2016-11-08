"""Simple HTTP Server that can return the state of servos and sensors

The devices and the ports to which they are connected need to be given
at construction. For example if a servo is attached to port A and an infra-red
sensor to port 3 then we can construct a server as follows

    Server(('0.0.0.0', 5000), RequestHandler(), devices={'outA': ev3.TachoMotor, 'in3': ev3.InfraRed})

A client can then request the state of these devides with queries like

   http://ev3dev:5000/data?outA!Speed&outA!Position&in3!Proximity

Evan Goris, 2016
"""
import BaseHTTPServer
import ev3local.evdev

class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """Handles requests for the state of sensors and servos

    Accepted urls are of the form

        /info
            Returns the ports on which devices are attached and the
            properties of those devices whose state can be queried

        /state?portX_propertyU&portY_propertyV
            Queries the state of the named properties of the devices
            on the named ports. Returned is a list (t1, v1), (t2, v2), ...
            where ti is a timestamp and v1 the state of a
            property. The states are returned in the same order
            as the url arguments.
    """

    def do_GET(self):

        import urlparse
        u = urlparse.urlparse(self.path)

        if u.path=='/info':
            self._GET_info()
        elif u.path=='/state':
            args = [ tuple(q.split('!')) for q in u.query.split('&') if q != '' ]
            self._GET_state(*args)
        else:
            self._sendresponse(404, self.path)

    def _GET_info(self):
        info = self.server.info()

        import json
        self._sendresponse(200, json.dumps(info))

    def _GET_state(self, *args):

        def formattimedvalue(timedvalue):
            return str(timedvalue[0]) + " " + str(timedvalue[1])

        result = [ formattimedvalue(self.server.gettimeddpvalue(port, property)) for port, property in args ]
        self._sendresponse(200, ' '.join(result))

    def _sendresponse(self, code, message):
        """Send a response of type 'text/plain'

        Args:
            code (int): Return status code
            message (str): Body of the return message
        """
        from cStringIO import StringIO
        f = StringIO()
        f.write(message)
        length = f.tell()
        f.seek(0)

        self.send_response(code)
        self.send_header("Content-type", "text/plain; charset=utf8")
        self.send_header("Content-Length", str(length))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        import shutil
        shutil.copyfileobj(f, self.wfile)

class Server(BaseHTTPServer.HTTPServer):
    """HTTP Server that can be queried for the state of sensors and servos
    """

    def __init__(self, address, handler, devices, xcevents=None):
        BaseHTTPServer.HTTPServer.__init__(self, address, handler)
        self._devices  = devices
        self._xcevents = xcevents

        if self._xcevents:
            import ev3local.callback
            xcontroller = ev3local.evdev.XBoxStateController(xcevents)
            self._devices['xbox'] = xcontroller

        import time
        self._starttime = time.time()

    def getdpvalue(self, port, property):
        device = self._devices[port]
        return getattr(device, property)

    def gettimeddpvalue(self, port, property):
        return (self.getuptime(), self.getdpvalue(port, property))

    def getuptime(self):
        import time
        return time.time() - self._starttime

    def info(self):
        return [{'port':port, 'driver': device.Driver_Name, 'properties': self._deviceinfo(device)}
                for port, device in self._devices.iteritems()]

    def _deviceinfo(self, device):
        properties = device.getreadproperties()
        return properties


