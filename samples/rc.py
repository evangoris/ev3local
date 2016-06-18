import ev3local.pid


def main():
    run()

def run(steerport='D', driveport='A', maxcontrol=100.0, fadezone=30.0, loopfreq=30.0):
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

    with xbox.XCEvents() as xcevents, ev3.TachoMotor(steerport) as motor, ev3.TachoMotor(driveport) as drivemotor:

        drivecontroller = controllers.DutyCycleController(xcevents, drivemotor)

        motor.reset()
        motor.run_direct()

        kp = maxcontrol / fadezone
        with ev3local.pid.PController(
                kp, ev3local.pid.axissetpoint(xcevents),
                ev3local.pid.processvariable(motor), ev3local.pid.clampedcontrol(motor, maxcontrol)) as controller:
            try:
                while True:
                    time.sleep(1.0/loopfreq)
            finally:
                motor.reset()
                drivemotor.reset()

if __name__=='__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass