"""Streaming server

This is a server that streams property values of sensors and tacho motors.
The server accepts up to N requests for such a stream. A client can request
a stream by sending the string 'STREAM:' followed by a message of the form
PORT!PROPERTY;. The server will then
respond with a potentially endless stream of ; separated pairs TIMESTAMP,VALUE.
Here TIMESTAMP is a float indicating the time at which VALUE was sampled
in the number of seconds since the server started.


Implementation
    For each stream the server starts a thread. On this thread
    every 1/Fth second a value is red from a device and then
    synchronously send to the client.


TODO:
    Error handling
    Separate the main routine from the rest

Evan Goris, 2016
"""
import logging

def server(portmap, hostname='0.0.0.0', port=5000, ncon=5, frequency=30):
    """Construct a function that starts a stream server

    Args:
        portmap (dict): Dictionary mapping portnames objects with a
            propertycontextmanager() method (see ev3.Device for example)
        hostname (str): Address of the server
        port (int): Port the server listen at
        ncon (int): Number of simultanious connections
        frequency (int): Number of samples per second that are send (default to 30)

    Returns:
        callable: Routine that starts the server
    """

    # Setup pipe
    # over which the server can be stopped
    #
    import os
    signalrfd, signalwfd = os.pipe()

    def start():
        # Set up a function for generating timestamps
        #
        import time
        starttime = time.time()
        timer = lambda: time.time() - starttime

        import socket, threading
        mainsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        mainsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            # Setup server socket
            #
            mainsocket.bind((hostname, port))
            mainsocket.listen(ncon)
            mainsocket.setblocking(0)


            logging.info("Listening [" + hostname + ":" + str(port) + "]")

            while True:
                # Accept client connections and try to handle
                # their request for a stream
                #
                import select
                rs, _, _ = select.select([mainsocket, signalrfd], [], [])
                if signalrfd in rs:
                    break

                clientsocket, address = mainsocket.accept()
                try:
                    request = readrequest(clientsocket)
                    logging.info("Received [" + request + "]")
                    contextmanager, property = processrequest(portmap, request)
                    sendstream(frequency, timer, clientsocket, contextmanager, property)
                except RuntimeError as e:
                    print str(e)
        finally:
            mainsocket.close()
            os.close(signalrfd)
            os.close(signalwfd)

    return ServerProcess(start, signalwfd)


class ServerProcess(object):
    """Process than can be started and stopped

    Args:
        process (callable): Routine representing the process
        signalwfd (int): File descriptor that makes `process` return when written to
    """
    def __init__(self, process, signalwfd):
        self._process = process
        self._signalwfd = signalwfd

    def __call__(self):
        self._process()

    def stop(self):
        import os
        os.write(self._signalwfd, "STOP")


def processrequest(portmap, request):
    """Process a request for a stream from a client

    Args:
        request (str): Request to process

    Returns:
        tuple: The device and the property that the client request
            to be streamed
    """
    import ev3local.ev3 as ev3

    port, property = parserequest(request)
    logging.info("Parsed [" + port + "] [" + property + "]")

    try:
        deviceobject = portmap[port]
    except KeyError:
        deviceclass = ev3.mapport(port)
        deviceobject = deviceclass(port)

    contextmanager = deviceobject.propertycontextmanager(property, 'r')

    #logging.info("Resolved [" + port + "] [" + deviceclass.Driver_Name + "]")
    # TODO: Make Driver_Name a class property
    #

    return (contextmanager, property)

def readrequest(sckt):
    """Read a complete request from a cocket.

    A request is either terminated with a ';' or
    is everything there is to read (e.a. the client
    closed the socket for writing)

    Args:
        sckt (_socketobject): Socket to read from

    """
    chunk = sckt.recv(1024)
    request = chunk
    while len(chunk)>0 and chunk[-1]!=';':
        chunk = sckt.recv(1024)
        request = request + chunk
    return request

def sendstream(frequency, timer, sckt, contextmanager, property):
    """Send a stream of timestamps and propertyvalues over a socket

        The stream is send asynchrone. The stream ends if the client
        closes the connection.

    Args:
        frequency (int): Frequency of the stream
        timer (callable): Returns timestamps
        sckt (_socketobject): Socket to stream over
        device (ev3.Device): Device to stream values from
        property (str): Property of `device` the stream the values of
    """
    import threading, socket
    def h():
        tname = threading.current_thread().name
        with contextmanager as propertycontext:
            try:
                    logging.info("Start stream [" + tname + "][" + propertycontext.Driver_Name + " (" + propertycontext.Address + ")] [" + property + "]")
                    f = sendvaluef(sckt, propertycontext, property, timer)
                    g = repeatf(f, frequency)
                    g()
            except socket.error as e:
                logging.info("End stream [" + tname + "][" + propertycontext.Driver_Name + "] [" + property + "]")
            finally:
                sckt.close()
    thread = threading.Thread(target=h)
    thread.start()


def parserequest(request):
    """Parse a request that was send over a socket

    The only request understood are of the form STREAM:PORT!PROPERTY

    Args:
        request (str): The request to parse

    Returns:
        tuple of (str, str): A tuple (PORT, PROPERTY)

    Raises:
        RuntimeError: When the request cannot be parsed
    """
    if request.endswith(';'):
        request = request[:-1]

    if request.startswith("STREAM:"):
        params = request[len("STREAM:"):]
        try:
            port, property = params.split('!')
            return (port, property)
        except:
            RuntimeError("Error parsing request")
    else:
        raise RuntimeError("Unkown request")




def repeatf(f, freq):
    """Construct a function that repeatedly calls a given function

    Args:
        f (callable): Function to call repeatedly
        freq (int): Frequency at which to call `f`

    Returns:
        callable: Routine that calls `f` every 1/`freq` seconds
    """
    import time
    st = 1.0/float(freq)
    def fr():
        while True:
            t0 = time.time()
            f()
            dt = time.time() - t0
            if dt<=st:
                time.sleep(st - dt)
            else:
                print "Too much lag"
    return fr

def sendvaluef(s, propertycontext, property, timer):
    """Creates a function that sends the value of a property
    of a device over a socket

    Args:
        s (_socketobject): Socket to send the value over
        device (ev3.Device): Device to get a value from
        property (str): Property of `device` to send
        starttime (float): Time to start measuring from

    Returns:
        callable: Routine that send the value over the socket
    """
    import time
    def f():
        v = propertycontext.read()
        sendmessage(s, str(timer()) + ',' + str(v) + ';')
    return f

def sendmessage(s, message):
    """Send a tuple of floats over a socket

    Args:
        s (_socketobject): Socket to send the value over
        message (str): Message to send

    Raises:
        socket.error: When the connection is closed by the client
    """
    while len(message)>0:
        sent = s.send(message)
        message = message[sent:]

