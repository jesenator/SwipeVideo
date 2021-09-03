# train controller for set up 1 - circular track around center object
import hub
import time
from utime import sleep_ms, ticks_ms, ticks_diff

colorSensor = hub.port.D.device
beeper = hub.sound
beeper.volume(2)
trainMotor = hub.port.B
colorSensor.mode(5)

threshold = 2000
tieCounter = 0.0
totalTracks = 16
totalTies = 4 * totalTracks
motorSpeed = 25  # default 35 - lower for shorter train momvement

checkpoints = 16
actionLength = 4
bufferLength = 5  # 2 is absolute min (if train doesn't have to move)

cycleLength = actionLength + bufferLength
tiesPerCheckpoint = int(round(totalTies / checkpoints * 2)) / 2  # rounds to nearest .5


def moveTrain(tiesPerCheckpoint, tieCounter):
    def getTieByRGB():
        colorSensor.mode(5)
        color = colorSensor.get()
        colorValues = (color[0] + color[1] + color[2])
        tie = (colorValues < threshold)
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
    while (tieCounter % tiesPerCheckpoint != 0 or currTies == 0):
        tie = getTieByColor()
        if tie != pastTie:
            tieCounter += .5
            currTies += .5
#             beeper.beep(1000, 50, 0)
#             print(tieCounter)

        pastTie = tie

    trainMotor.pwm(0)
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
