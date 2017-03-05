"""Streaming server

This is a server that streams property values of sensors and tacho motors.
The server accepts up to N requests for such a stream. A client can request
a stream by sending the string 'STREAM:' followed by a message of the form
PORT!PROPERTY;. The server will then
respond with a potentially endless stream of ; separated pairs TIMESTAMP,VALUE.
Here TIMESTAMP is a float indicating the time at which VALUE was sampled
in the number of seconds since the server started.

The server accepts the following arguments
    --address=ADDRESS (default to '0.0.0.0')
    --port=PORT (default to 5000)
    --nconnections=N (default to 5)
    --freq=F, Number of samples per second that are send (default to 30)


Implementation
    For each stream the server starts a thread. On this thread
    every 1/Fth second a value is red from a device and then
    synchronously send to the client.


TODO:
    Error handling
    Separate the main routine from the rest

Evan Goris, 2016
"""
import logging, argparse
logging.basicConfig(level=logging.INFO)
from ev3local.streamserver import server

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", help="address to listen on", dest='address', default='0.0.0.0', type=str)
    parser.add_argument("--port", help="port to listen on", dest='port', default=5000, type=int)
    parser.add_argument("--ncon", help="number of simultanious connections", dest='ncon', default=5, type=int)
    parser.add_argument("--frequency", help="frequency of the streams", dest='frequency', default=30, type=int)
    args = parser.parse_args()

    #import ev3local.ev3
    #with ev3local.ev3.TachoMotor('outA') as motorA:
    #    run(motorA, args.address, args.port, args.ncon, args.frequency)
    run(args.address, args.port, args.ncon, args.frequency)

def run(address, port, ncon, frequency, motor=None):
    import ev3local.pyev3
    propertymap = {"DUTY_CYCLE": ev3local.pyev3.DutyCycle}
    action = server(propertymap, address, port, ncon, frequency)
    action()

if __name__=='__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass