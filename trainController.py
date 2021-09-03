# train controller for set up 1 - circular track around center object
import hub
import time
from utime import sleep_ms, ticks_ms, ticks_diff

# make sure these 3 variables are the same as for the robot on display
checkpoints = 16  # change if needed
actionLength = 4  # in seconds, change if neede
bufferLength = 5  # extra time between videos to allow time for the train to move. 3 at minimum

colorSensor = hub.port.D.device  # change port if neccessary
trainMotor = hub.port.B  # change port if neccessary
colorSensor.mode(5)
beeper = hub.sound
beeper.volume(2)

tieColorThreshold = 2000
tieCounter = 0.0
totalTracks = 16
totalTies = 4 * totalTracks
motorSpeed = 35  # default 35 - lower for shorter train momvement

cycleLength = actionLength + bufferLength
tiesPerCheckpoint = int(round(totalTies / checkpoints * 2)) / 2  # rounds to nearest .5


def moveTrain(tiesPerCheckpoint, tieCounter):
    # two different ways of determining if the train crosses a tie
    def getTieByRGB():
        colorSensor.mode(5)
        color = colorSensor.get()
        colorValues = (color[0] + color[1] + color[2])
        tie = (colorValues < tieColorThreshold)
        return tie
    def getTieByColor():
        colorSensor.mode(0)
        color = colorSensor.get()
        tie = (color == [10])
        return tie

    pastTie = getTieByColor()
    trainMotor.pwm(motorSpeed)
    currTies = 0.0

#     print(tieCounter)
    # move train until the correct number of ties have been passed
    while (tieCounter % tiesPerCheckpoint != 0 or currTies == 0):
        tie = getTieByColor()
        if tie != pastTie:
            tieCounter += .5
            currTies += .5
#             beeper.beep(1000, 50, 0)  # for debug
#             print(tieCounter)
        pastTie = tie

    trainMotor.pwm(0)  # stop motor once the checkpoint has been reached
    return tieCounter


def getSeconds():
    seconds = round(ticks_diff(ticks_ms(), start_ms)/1000)
    return seconds


print("ready")
print("start smartphone video")
print("then simultaneously press the right arrow buttons on both spikes")

while not hub.button.right.is_pressed():
    sleep_ms(10)
    
sleep_ms(1500)
print("starting")
start_ms = ticks_ms()


for video in range(checkpoints):
    while (getSeconds() % cycleLength) != 0:
        sleep_ms(10)
    sleep_ms(1000)

    print("recording video " + str(video + 1) + " ... ", end="")
    sleep_ms(1000 * (actionLength))
    print("done")

    sleep_ms(1000)
    tieCounter = moveTrain(tiesPerCheckpoint, tieCounter)

print("recordings finished!")
print("stop smartphone video")
