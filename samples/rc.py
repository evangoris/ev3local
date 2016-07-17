import ev3local.pid

import logging
logging.basicConfig(level=logging.INFO)

def main():
    run()

def run(steerport='A', driveport='B', maxcontrol=100.0, fadezone=30.0, loopfreq=30.0):
    """Operate a RC car with an xbox controller

    Args:
        steerport (str): Name of the port the steering motor is plugged into
        driveport (str): Name of the port the drive motor is plugged into
        maxcontrol (float): Maximum duty cylcle of steering motor
        fadezone (float): Steering motor will slow down within setpoint +- fadezone
        loopfreq (float): Times per second the steering motor is updated
    """
    import ev3local.xbox as xbox, ev3local.ev3 as ev3, ev3local.callback as controllers
    import time

    with xbox.XCEvents() as xcevents, ev3.TachoMotor(steerport) as motor, ev3.TachoMotor(driveport, rcmproperties=['Duty_Cycle_SP']) as drivemotor:

        # Start reading xbox events
        #
        xcevents.start()

        # Connect an xbox axis to the drive motor
        #
        drivemotor.run_direct()
        def d(v):
            drivemotor.Duty_Cycle_SP = int(v)
        xcevents.connectaxes(d, 'ABS_X', 100, -100)


        # TODO: Use the PCntrl_TachoMotorPositionManager
        #
        motor.reset()
        motor.run_direct()

        kp = maxcontrol / fadezone
        with ev3local.pid.PController(
                kp, ev3local.pid.axissetpoint(xcevents),
                ev3local.pid.processvariable(motor), ev3local.pid.clampedcontrol(motor, maxcontrol)) as controller:
            try:
                controller.start()
                while True:
                    time.sleep(1.0/loopfreq)
            finally:
                motor.reset()
                drivemotor.reset()
                xcevents.stop()


if __name__=='__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass