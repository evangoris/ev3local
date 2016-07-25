import ev3local.ev3
import ev3local.pid

import logging

from ev3local.xbox import XBoxStateController

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
   irun()


def irun(steerport='A', driveport='B', maxcontrol=100.0, fadezone=60.0, loopfreq=120.0):
    """Same as run() but implemented with iterator interface
    """
    import ev3local.streamserver, ev3local.xbox as xbox, ev3local.ev3 as ev3
    import time

    drivemotor = ev3.TachoMotor(driveport)
    steermotor = ev3.TachoMotor(steerport)

    with xbox.XCEvents() as xcevents, drivemotor.propertycontextmanager('Duty_Cycle_SP', 'w') as drivefile, steermotor.propertycontextmanager('Duty_Cycle_SP', 'w') as steerfile:

        # Start reading xbox events
        #
        xcevents.start()

        # Connect an xbox axis to the drive motor
        #
        drivemotor.run_direct()
        def d(v):
            drivefile.write(str(int(v)))
        xcevents.connectaxes(d, 'ABS_X', 100, -100)

        # Use a PID to control the position of the steer motor and
        # connect an xbox axis to the setpoint of the PID
        #
        steermotor.reset()
        steermotor.run_direct()
        kp  = maxcontrol / fadezone
        kd  = 0.05
        pid = ev3local.pid.PController(kp, kd, maxcontrol, -maxcontrol)
        pid.Driver_Name = 'PID'
        pid.Address = steerport
        import itertools
        isetp = itertools.imap(lambda x: 360*x, xcevents.iattribute('EV_ABS', 'ABS_RX'))
        impos = steermotor.iattribute('Position', type_=float)
        icont = pid.iprocess(isetp, impos)

        #controller = ev3local.ev3.TachoMotorPIDPositionManager(steerport, maxcontrol, fadezone)
        #axissetpoint = axissetpointf(xcevents)

        #
        #
        import threading
        portmap = {steerport: steermotor, 'pid': pid}
        streamserver = ev3local.streamserver.server(portmap)
        streamthread = threading.Thread(target=streamserver)
        streamthread.daemon = True
        streamthread.start()

        try:
            logger.info("Controlloop started")
            for cont in icont:
                steerfile.write(str(int(cont)))
                time.sleep(1.0/loopfreq)
        finally:
            steermotor.reset()
            drivemotor.reset()
            xcevents.stop()
            streamserver.stop()

if __name__=='__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass


