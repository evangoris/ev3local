"""Simple HTTP Server that can return the state of servos and sensors

The devices and the ports to which they are connected need to be given
at startup. For example if a servo is attached to port A and an infra-red
sensor to port 3 then we can start the server as follows

    python httpserver.py --outA=tachomotor --in3=infrared

A client can then request the state of these devides with queries like

   http://ev3dev:500/data?outA!Speed&outA!Position&in3!Proximity

Evan Goris, 2016
"""
def main():
    from ev3local.httpserver import Server, RequestHandler
    import argparse, ev3local.ev3 as ev3, ev3local.edutil

    ports = ['outA', 'outB', 'outC', 'outD', 'in1', 'in2', 'in3', 'in4']
    constructors = {
        'tachomotor': ev3.TachoMotor,
        'infrared': ev3.Infrared_Sensor
    }

    parser = argparse.ArgumentParser(usage='', description='')
    parser.add_argument('--xbox', action='store_true', default=False, dest='xbox', help='deliver xbox controller events')
    for port in ports:
        parser.add_argument('--%(p)s'%{'p': port}, type=str, dest=port, default=None, help='device attached to port %(p)s'%{'p': port[-1:]})
    args = parser.parse_args()


    devices = {}
    for port in ports:
        device = getattr(args, port)
        if device:
            devices[port] = constructors[device](port)

    xcevents = None
    if args.xbox:
        import ev3local.edutil
        xcevents = ev3local.edutil.EventLoop()
        xcevents.__enter__()

    try:
        server = Server(("0.0.0.0", 5000), RequestHandler, devices, xcevents)
        server.serve_forever()
    finally:
        if xcevents:
            xcevents.__exit__(None, None, None)

if __name__=='__main__':
    import socket
    print socket.gethostname()
    try:
        main()
    except KeyboardInterrupt:
        p