"""Monitor attributes hardware
"""

def duty_cycle(motor, interval=1):
    """Monitor duty cycle and speed of a motor
    
    Args:
        motor (ev3.TachoMotor): Motor to monitor
        interval (float): Time in seconds between each sample
    """
    import time, sys
    while True:
        sys.stderr.write('\rDuty cycle: ' + motor.Duty_Cycle + ' Speed: ' + str(int(motor.Speed)/10) + '       ')
        time.sleep(interval)

import BaseHTTPServer


class EV3HTTPServer(BaseHTTPServer.HTTPServer):
    """HTTPServer that serves info ev3 devices
    
    Args:
        host (tuple of (str, int)): IP and port the server lives
        requesthandler (BaseHTTPRequestHandler.__class__): Class to instantiate upon request
        objectproperties (list of tpl of object, list of str): Objects and properties to serve info on
    """    
    def __init__(self, host, requesthandler, objectproperties=[]):
        BaseHTTPServer.HTTPServer.__init__(self, host, requesthandler)

        # Instantiate the service(s) provides by this server
        #
        self._rootservice  = RootService()
        propservice = DelegationService('properties')
        self._rootservice.addsubservice(propservice)
        for object, properties, statics in objectproperties:
            deviceservice = ObjectService(object, object.Address, properties, statics)
            propservice.addsubservice(deviceservice)


class EV3RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """Request handler for a EV3HTTPServer
    
    Args:
        request (str): Path that triggered the request
        client_address (str): Address of the client
        server (EV3HTTPServer): Server that contains data to handle requests
    """

    def __init__(self, request, client_address, server):
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, request, client_address, server)
        

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
        
    def _serveraddress(self):
        """Try to get an address by which the server can be reached
        """
        header  = str(self.headers)
        headers = header.split("\r\n")
        address = "127.0.0.1"
        for h in headers:
            if h[:4]=="Host":
                address = h[7:]
                break
        return "http://" + address

    def do_GET(self):
        """Handle GET Request
        """
        from urlparse import urlparse
        urlp = urlparse(self.path)

        path = filter(lambda x:x!='', urlp.path.split('/'))
        if urlp.query=="":
            args = []
        else:
            args = urlp.query.split('&')
        result  = self.server._rootservice.applys(path, *args)
        if len(args)==0:
            presult = {'static': result[0], 'subservices': result[1], 'arguments': result[2]}
        else:
            presult = result
        import json
        self._sendresponse(200, json.dumps(presult))
        return

        if urlp.path=='/' or urlp.path=='/ev3':
            result = self.server.model.objects()
            self._sendresponse(200, str(result))
            return
        elif urlp.path=='/properties' or urlp.path=='/ev3/properties':
            query_components = [ cmp.split('_', 1) for cmp in urlp.query.split("&") ]

            try:
                results = self.server.model.propertyvalues(query_components)
                self._sendresponse(200, str(results))
                return
            except RuntimeWarning as w:
                self._sendresponse(400, w.message)
                return

class Service(object):
    """Abstract service

    Services are organized in a hiearchical manner, like a folder structure
    Services can be triggered by providing a list of parameters

    """
    def __init__(self):
        self._subservices = {}
        self._name = "Default Service"

    def get_name(self):
        """Name of this service
        """
        return self._name

    name = property(get_name)

    def _get_description(self):
        """Description of this service
        """
        return "Default service that does nothing"

    def subservices(self):
        """Names of subservices of this service

        The values returned by this method can be used as arguments to `getsubservice()`
        """
        return [ name for name in self._subservices ]

    def addsubservice(self, subservice):
        """Add a subservice to this service

        Args:
            subservice (Subservice: Service to add as a subservice
        """
        if self._subservices.has_key(subservice.name):
            raise RuntimeWarning("A subservice with name %(n)s already exists"%{'n': subservice.name})

        self._subservices[subservice.name] = subservice

    def apply(self, *parameters):
        """Use this service

        Args:
            *parameters: Arguments, any of the values returned by `parameters()`

        Returns:
            List of str: Result of this service given `*parameters`
        """
        pass

    def parameters(self):
        """Parameters accepted by this service

        The values returned by this method can be used as arguments to `apply()`

        Returns:
            List of str: List of parameters
        """
        return []

    def getsubservice(self, subservice):
        """Subservices of this service

        Args:
            subservice (str): Name of the subservice

        Returns:
            Service: subsurvice
        """
        try:
            return self._subservices[subservice]
        except KeyError:
            raise RuntimeError("Service %(s)s does not exist"%{'s': subservice})

class RootService(Service):
    """Root of a tree of services
    """
    def __init__(self):
        super(RootService, self).__init__()

    def apply(self, *args):
        statics = dict([ (subservice, self.getsubservice(subservice).apply()[0]) for subservice in self.subservices() ])
        return (statics, self.subservices(), [])

    def applys(self, names, *args):
        """Apply a subservice

        Args:
            names: Path down the service tree to the subservice to apply
            *args: Arguments passed to the subservice

        Returns:
            Whathever the subservice returns
        """
        service = self
        for name in names:
            service = service.getsubservice(name)
        return service.apply(*args)

class ObjectService(Service):
    """Service that provides read-access to certain properties
    of an object

    Args:
        object (object): The managed object
        name (str): Name for this service
        properties (list of str): List of (some of the) properties of `object`

    Raises:
        RuntimeError: When some item in `properties` is not a property of `object`
    """
    def __init__(self, object, name, properties, statics):
        super(ObjectService, self).__init__()
        self._object  = object
        self._name    = name
        self._statics = statics

        for propertyname in properties:
            if propertyname not in dir(object):
                raise RuntimeError("'%(p)s is not a property"%{'p': propertyname})

        self._properties = properties

    def parameters(self):
        return list(self._properties)

    def apply(self, *args):
        """
        Args:
            *args: List with properties of the managed object
        Returns:
            list: List of values of the properties in `args` of the managed object
        """
        if args==():
            staticsv = dict([(static, self._object.__getattribute__(static)) for static in self._statics ])
            staticsv['Id'] = self._name
            return (staticsv, [], self.parameters())
        else:
            import time
            values = []
            for arg in args:
                values.append((time.time(), self._object.__getattribute__(arg)))
            return values

class DelegationService(Service):
    """Service that delegates its application to its sub-services
    """
    def __init__(self, name):
        super(DelegationService, self).__init__()
        self._name = name

    def parameters(self):
        """
        Returns:
            list: List of strings of the form `subservice`_`arg`
                for each `subservice` of `self` and each `arg` that
                subservice accepts
        """
        subservices = self.subservices()
        params = []
        for subservice in subservices:
            subparams = self.getsubservice(subservice).parameters()
            for subparam in subparams:
                param = subservice + "_" + subparam
                params.append(param)
        return params

    def apply(self, *args):
        """
        Args:
            *args: List of arguments of the form subservice_subarg.
                For each such argument `subservice` gets applied to `subarg`

        Returns:
            list: Return values of the apply() calls to the sub-services
        """
        if args==():
            statics = [ self.getsubservice(subservice).apply()[0] for subservice in self.subservices() ]
            return (statics, self.subservices(), self.parameters())
        else:
            result = []
            for arg in args:
                subservice, arg = arg.split('_', 1)
                result.extend(self.getsubservice(subservice).apply(arg))
            return result

'''
class DeviceService(Service):
    """Service that provides values for properties of a single device

    """
    def __init__(self, devicename, pmodel):
        super(DeviceService, self).__init__()
        self._model = pmodel
        self._name = devicename

    def parameters(self):
        return self._model.properties(self._devicename)

    def apply(self, *args):
        if args==():
            # No arguments: return information on subservices
            # and arguments
            #
            return self._model.properties(self._name)
        else:
            raise NotImplementedError

class PropertiesService(Service):
    """Service that provides values for properties of any device

    """
    def __init__(self, pmodel):
        super(PropertiesService, self).__init__()
        self._name  = "properties"
        self._model = pmodel

    def apply(self, *args):
        if args==():
            # No arguments: return information on sub-services
            # and arguments
            #
            return self.subservices()
        else:
            raise NotImplementedError

    def parameters(self):
        parameters = []
        for object in self._model.objects():
            parameters.append(self._model.properties(object))
        return parameters

    def getsubservices(self, subservice):
        return DeviceService(subservice, self._model)
'''


if __name__=='__main__':
    try:
        from .ev3 import TachoMotor, Infrared_Sensor
        motorA = TachoMotor('A')
        sensor1 = Infrared_Sensor(2)
        #motorD = TachoMotor('D')
        server = EV3HTTPServer(("0.0.0.0", 500), EV3RequestHandler, objectproperties=[(motorA,['Speed', 'Duty_Cycle', 'Position'], ['Address', 'Driver_Name']),(sensor1,['Mode', 'Proximity'], ['Address', 'Driver_Name'])])
        server.serve_forever()
    except KeyboardInterrupt:
        pass