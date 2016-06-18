"""Software to run locally on the ev3

    The modules in this package are devided in 2 layers:

    1. Interface to the hardware
        ev3: Access different devices attached to the ev3 brick
        xbox: Access a wireless xbox controller attached to the ev3 brick

    2. Application modules
        httpserver: Simple HTTP server for reading sensor data over a network
        pid: PID Controller implementation
        callback: Callbacks for xbox.XCEvents that control ev3.TachoMotor

    Evan Goris, 2016
"""