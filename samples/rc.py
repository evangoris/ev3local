import ev3local.ev3
import ev3local.pid

import logging

from ev3local.xbox import XBoxStateController

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    run()

def run(steerport='A', driveport='B', maxcontrol=100.0, fadezone=30.0, loopfreq=120.0):
    """Operate a RC car with an xbox controller

    Args:
        steerport (str): Name of the port the steering motor is plugged into
        driveport (str): Name of the port the drive motor is plugged into
        maxcontrol (float): Maximum duty cylcle of steering motor
        fadezone (float): Steering motor will slow down within setpoint +- fadezone
        loopfreq (float): Times per second the steering motor is updated
    """
    import ev3local.streamserver, ev3local.xbox as xbox, ev3local.ev3 as ev3, ev3local.callback as controllers
    import time

    with xbox.XCEvents() as xcevents, ev3.TachoMotor(driveport, rcmproperties=['Duty_Cycle_SP']) as drivemotor:

        # Start reading xbox events
        #
        xcevents.start()

        # Connect an xbox axis to the drive motor
        #
        drivemotor.run_direct()
        def d(v):
            drivemotor.Duty_Cycle_SP = int(v)
        xcevents.connectaxes(d, 'ABS_X', 100, -100)

        # Use a PID to control the position of the steer motor and
        # connect an xbox axis to the setpoint of the PID
        #
        controller = ev3local.ev3.TachoMotorPIDPositionManager(steerport, maxcontrol, fadezone)
        axissetpoint = axissetpointf(xcevents)

        #
        #
        import threading
        portmap = {'outA': controller}
        streamserver = ev3local.streamserver.server(portmap)
        streamthread = threading.Thread(target=streamserver)
        streamthread.daemon = True
        streamthread.start()

        try:
            logger.info("Controlloop started")
            while True:
                controller.step(axissetpoint())
                time.sleep(1.0/loopfreq)
        finally:
            controller.reset()
            drivemotor.reset()
            xcevents.stop()
            streamserver.stop()

def axissetpointf(xcevents):
    """Create a function that returns the current state of an
    absolute axis of the XBox controller
    """
    state = XBoxStateController(xcevents)
    scale = 360.0

    def setpoint():
        return float(state.pvalue * scale)

    return setpoint

if __name__=='__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass


