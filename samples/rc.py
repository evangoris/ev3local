import ev3local.ev3
import ev3local.pid

import logging

from ev3local.evdev import XBoxStateController

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
   irun()


def irun(steerport='A', driveport='B', maxcontrol=100.0, fadezone=60.0, loopfreq=120.0):
    import ev3local.ev3 as ev3
    with ev3.TachoMotor(steerport) as steermotor, ev3.TachoMotor(driveport) as drivemotor:
        run(drivemotor, steermotor, maxcontrol, fadezone, loopfreq)


def run(drivemotor, steermotor, maxcontrol, fadezone, loopfreq):
    import ev3local.evdev as xbox
    with xbox.EventLoop() as xcevents:

        # Start reading xbox events
        #
        xcevents.start()

        # Connect an xbox axis to the drive motor
        #
        drivemotor.run_direct()
        def f(value):
            drivemotor.Duty_Cycle_SP = int(value)
        xcevents.connectaxes(f, 49, -100, 0)


        # Use a PID to control the position of the steer motor and
        # connect an xbox axis to the setpoint of the PID
        #
            # Set state of steer motor
            #
        steermotor.reset()
        steermotor.run_direct()

            # PID Controller
            #
        kp  = maxcontrol / fadezone
        kd  = 0.05
        import ev3local.pid
        pid = ev3local.pid.PController(kp, kd, maxcontrol, -maxcontrol)
        pid.Driver_Name = 'PID'
        pid.Address = steermotor.Address

            # Connect the streams
            #
        import itertools
        isetp = itertools.imap(lambda x: 540*x, xcevents.iattribute('EV_ABS', 2))
        impos = steermotor.iattribute('Position')
        icont = pid.iprocess(isetp, impos)
        steermotor_dutycycle = steermotor.sattribute(itertools.imap(int, icont), 'Duty_Cycle_SP')

        # Set up a stream server to stream the PID setpoint and
        # process variable
        #
        import threading, ev3local.streamserver
        portmap = {steermotor.Address: steermotor, 'pid': pid}
        streamserver = ev3local.streamserver.server(portmap)
        streamthread = threading.Thread(target=streamserver)
        streamthread.daemon = True
        streamthread.start()

        try:
            import time
            logger.info("Controlloop started")
            while True:
                steermotor_dutycycle.next()
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


