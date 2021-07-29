import subprocess
import os
import sys
from shutil import copyfile, rmtree
import wave

import numpy as np
import matplotlib.pyplot as plt
import math

from scipy.fft import fft
from scipy.signal import savgol_filter, find_peaks
from scipy.ndimage import gaussian_filter

from datetime import timedelta


# from pydrive.auth import GoogleAuth
# from pydrive.drive import GoogleDrive


def createPath(s):
    try:
        os.mkdir(s)
    except OSError:
        assert False, "Creation of the directory %s failed. " \
                      "(The " + str(s) + " folder may already exist. Delete or rename it, and try again.)"


def deletePath(s):  # Dangerous! Watch out!
    try:
        rmtree(s, ignore_errors=False)
    except OSError:
        print("Deletion of the directory %s failed" % s)
        print(OSError)


def getAudio(INPUT_FILE, AUDIO, SAMPLE_RATE):
    print("separating audio")
    command = pathName + "ffmpeg -i " + INPUT_FILE + " -ab 160k -ac 1 -ar " + str(SAMPLE_RATE) + " -vn " + AUDIO
    subprocess.call(command, shell=True)


def splitVideo(videoStarts, videoEnds, videos, overlayFile, loops):
    print("splitting videos")
    overlayEffect = ""
    loopEffect = ""
    if overlayFile != "":
        print("overlaying videos")
        overlayEffect = "-vf \"movie=" + str(
            overlayFile) + ", scale=600:-1 [a]; [in][a] overlay=main_w-(overlay_w+8):8 [c]\" "

    # TODO integrate loop command
    # if loops != 0:
    #     print("looping videos")
    #     loopEffect = " -stream_loop " + str(loops - 1)
    # takes 17 seconds with separate looping

    for i in range(videos):
        command = pathName + "ffmpeg -ss " + str(videoStarts[i]) + " -to " + \
                  str(videoEnds[i]) + loopEffect + " -i " + INPUT_FILE + " " + overlayEffect \
                  + videoName(i)
        print(command)
        subprocess.call(command, shell=True)


def loopVideos(loops, videos):
    print("looping videos")
    for i in range(videos):
        command = pathName + "ffmpeg -stream_loop " + str(loops - 1) + " -i " + videoName(
            i) + " -c copy " + videoNameLooped(i)
        print(command)
        subprocess.call(command, shell=True)
        os.remove(videoName(i))


def videoName(i):
    name = str(VIDEO_FOLDER + "/video" + str(i + 1).zfill(2) + ".mp4")
    return name


def videoNameLooped(i):
    # name = str(VIDEO_FOLDER + "/videoLoop_" + str(i + 1).zfill(2) + ".mp4")
    name = str(VIDEO_FOLDER + "/" + str(i + 1).zfill(2) + "videoLoop" + ".mp4")
    return name


# def uploadFiles(videos):
#     print("uploading f5iles...")
#
#     gauth = GoogleAuth()
#     drive = GoogleDrive(gauth)
#     upload_file_list = [videoName(i) for i in range(videos)]
#     for upload_file in upload_file_list:
#         print("uploading " + upload_file)
#         gfile = drive.CreateFile({'parents': [{'id': '1TqqqqrhS-2EakkrQKQDoZBFyOJkl9Bee'}]})  # folder ID (from URL)
#
#         gfile.SetContentFile(upload_file)
#         gfile.Upload()


def getFreqAmplitude(signal, audioSampleCount, samplesPerFrame, freq):
    print("analyzing audio frequencies")
    freqAmplitude = []
    samplesPerWindow = 64 * 2
    sigma = .5
    factor = 54 / 52
    indexOfFreq = int(round(freq / SAMPLE_RATE * samplesPerWindow * factor))
    print(f'{indexOfFreq = }')
    print(f'{samplesPerFrame = }')

    for i in range(10000, audioSampleCount - samplesPerWindow, int(samplesPerFrame)):
        audioChunk = signal[i:(i + samplesPerWindow)]
        audioChunkSmooth = gaussian_filter(audioChunk, sigma)
        audioTransform = fft(audioChunkSmooth)
        audioTransformAbs = np.abs(audioTransform)

        # ax = plt.subplot()
        # ax.set_ylim(0, 400000)
        # ax.plot(audioTransformAbs)
        # plt.show()

        freqAmplitude.append(audioTransformAbs[indexOfFreq])

    freqAmplitudeFiltered = savgol_filter(freqAmplitude, 31, 1)
    return freqAmplitudeFiltered


def getPeaks():
    peaks = find_peaks(freqAmplitudeFiltered, height=threshold, distance=framesPerSecond * (VIDEO_DURATION + 3))
    return peaks


# def adjustThreshold(freqAmplitudeFiltered, peaksGoal, oldThreshold):
#     threshold = oldThreshold
#     iterations = 0
#     factor = 1000
#     maxIterations = 100000 / factor
#
#     peaksNum = len(getPeaks()[0])
#     if peaksNum / peaksGoal < .8 or peaksNum / peaksGoal > 1.2:
#         ans = input("about " + str(peaksNum) + " beeps found. Is " + str(
#             peaksGoal) + " the correct number of checkpoints? (y/n) ")
#         if ans == 'n':
#             print("please correct that in the code")
#             sys.exit()
#
#     while True:
#         peaks = getPeaks()[0]
#         peaksNum = len(peaks)
#
#         print("current peaks: " + str(peaksNum))
#         print("goal: " + str(peaksGoal))
#
#         plt.plot(freqAmplitudeFiltered)
#         plt.plot(peaks, freqAmplitudeFiltered[peaks], "x")
#         plt.plot(np.full(len(freqAmplitudeFiltered), threshold), "--", color="gray")
#         plt.show()
#
#         if peaksNum == peaksGoal or iterations > maxIterations:
#             break
#
#         if peaksNum < peaksGoal:
#             threshold = threshold - factor
#         elif peaksNum > peaksGoal:
#             threshold = threshold + factor
#         iterations += 1
#
#     if threshold != oldThreshold:
#         print("threshold adjusted from " + str(oldThreshold) + " to " + str(threshold))
#
#     return threshold


def getTimes(freqAmplitudeFiltered, threshold):
    print("extrapolating video times")
    videoStarts = []
    videoEnds = []
    offsetSeconds = 1

    peaks = getPeaks()
    for peak in peaks[0]:
        startFrame = (peak + offsetSeconds * framesPerSecond)

        videoStarts.append(timedelta(seconds=startFrame / framesPerSecond))
        videoEnds.append(timedelta(seconds=(startFrame / framesPerSecond) + VIDEO_DURATION))

    return videoStarts, videoEnds


########################################## main
# INPUT_FILE = "trainVid10.3.mp4"
INPUT_FILE = "trainVid8.mp4"
# INPUT_FILE = "~1khz.mp4"
CHECKPOINTS = 32
OVERLAY_FILE = "code10.mp4"  # empty string if no overlay
# OVERLAY_FILE = ""
VIDEO_DURATION = 4
# BEEP_FREQ = 2000
BEEP_FREQ = 1046.5 * 2  # <-- C6
VIDEO_FOLDER = "processedVideos"
FRAME_QUALITY = 3
SAMPLE_RATE = 44100
threshold = 17000
LOOPED_VIDEO_DURATION = 30
loops = 7  # 0 for no loops
AUDIO = "audio.wav"
framesPerSecond = 30 * 10  # this is for the audio

############### pathName = "./Downloads/PythonParserProgram/"  # for macOS

######################### CHANGE THE FOLLOWING LINES FOR MAC VS WINDOWS !!!!!!!!!!!!!!!!!!!!!!!!!!
pathName = "./"  # for macOS
# pathName = ""  # for Windows

### for mac
os.chdir("./Downloads/PythonParserProgram")


def getInputs():
    INPUT_FILE = input(
        "enter the name of the input file (it should be in the same folder as main) (include filetype suffix): ")
    CHECKPOINTS = int(input("enter the number of times the robot completes its action during the recording: "))
    VIDEO_DURATION = int(input("enter the length (in seconds) of each action: "))
    BEEP_FREQ = float(input("enter the frequency (in Hz) of the beeps (default is 2093 for beep 96 on spike): "))
    OVERLAY_FILE = input("enter the name of the code file to overlay on the recording (press enter if none): ")

    return INPUT_FILE, CHECKPOINTS, VIDEO_DURATION, BEEP_FREQ, OVERLAY_FILE


try:
    os.remove(AUDIO)
except:
    pass

INPUT_FILE, CHECKPOINTS, VIDEO_DURATION, BEEP_FREQ, OVERLAY_FILE = getInputs()
loops = int(LOOPED_VIDEO_DURATION / VIDEO_DURATION)
getAudio(INPUT_FILE, AUDIO, SAMPLE_RATE)
wf = wave.open(AUDIO, "r")

# Extract Raw Audio from Wav File
signal = wf.readframes(-1)
signal = np.frombuffer(signal, dtype='int16')
audioSampleCount = len(signal)

samplesPerFrame = SAMPLE_RATE / framesPerSecond
audioFrameCount = int(math.ceil(audioSampleCount / samplesPerFrame))

high = .25
low = .1
freqAmplitudeFiltered = getFreqAmplitude(signal, audioSampleCount, samplesPerFrame, BEEP_FREQ)

# threshold = adjustThreshold(freqAmplitudeFiltered, CHECKPOINTS, threshold)
videoStarts, videoEnds = getTimes(freqAmplitudeFiltered, threshold)

print(f'{len(videoStarts) = }')
if (len(videoStarts) != CHECKPOINTS):
    sys.exit("error: failure to parse videos. please try again. check the number of checkpoints")

deletePath(VIDEO_FOLDER)
createPath(VIDEO_FOLDER)

splitVideo(videoStarts, videoEnds, CHECKPOINTS, OVERLAY_FILE, loops)
loopVideos(loops, CHECKPOINTS)
# uploadFiles(CHECKPOINTS)
