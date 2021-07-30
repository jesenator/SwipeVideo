import subprocess
import os
import sys
from shutil import rmtree
import wave

import numpy as np
import math
import time

from scipy.fft import fft
from scipy.signal import savgol_filter, find_peaks
from scipy.ndimage import gaussian_filter
from colorama import Fore, Back, Style, init

from datetime import timedelta

import matplotlib.pyplot as plt


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
    print(prefix + "separating audio")
    command = pathName + "ffmpeg -i " + INPUT_FILE + " -ab 160k -ac 1 -ar " + str(SAMPLE_RATE) + " -vn " + AUDIO + loglevel
    subprocess.call(command, shell=True)
    time.sleep(.01)


def splitVideo(videoStarts, videoEnds, videos, overlayFile, loops):
    print(prefix + "splitting videos")
    overlayEffect = ""
    loopEffect = ""
    if overlayFile != "":
        print(prefix + "overlaying videos")
        # overlayEffect = "-vf \"movie=" + str(
        #     overlayFile) + ", scale=600:-1 [a]; [in][a] overlay=main_w-(overlay_w+8):8 [c]\" "
        overlayEffect = "-filter_complex \"scale=1080:-1 [base]; " \
                        "movie=" + str(overlayFile) + ", scale=1080/3.5:-1 [a]; " \
                        "[base][a] overlay=main_w-(overlay_w+8):8 [c]\" -map \"[c]\" "
    # TODO integrate loop command
    # if loops != 0:
    #     print("looping videos")
    #     loopEffect = " -stream_loop " + str(loops - 1)
    # takes 17 seconds with separate looping

    for i in range(videos):
        command = pathName + "ffmpeg -ss " + str(videoStarts[i]) + " -to " + \
                  str(videoEnds[i]) + loopEffect + " -i " + INPUT_FILE + " " + overlayEffect \
                  + videoName(i) + loglevel
        print(command)
        subprocess.call(command, shell=True)
        time.sleep(.01)


def loopVideos(loops, videos):
    print(prefix + "looping videos")
    for i in range(videos):
        command = pathName + "ffmpeg -stream_loop " + str(loops - 1) + " -i " + videoName(
            i) + " -c copy " + videoNameLooped(i) + loglevel
        print(command)
        subprocess.call(command, shell=True)
        time.sleep(.01)
        os.remove(videoName(i))


def videoName(i):
    name = str(VIDEO_FOLDER + "/video" + str(i + 1).zfill(3) + ".mp4")
    return name


def videoNameLooped(i):
    name = str(VIDEO_FOLDER + "/" + str(i + 1).zfill(3) + "videoLoop" + ".mp4")
    return name


# def uploadFiles(videos):
#     print(prefix + "uploading f5iles...")
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


def getFreqAmplitudeFiltered(signal, audioSampleCount, samplesPerFrame, freq):
    print(prefix + "analyzing audio frequencies")
    freqAmplitude = []
    samplesPerWindow = 64 * 2
    sigma = .5
    factor = 54 / 52
    indexOfFreq = int(round(freq / SAMPLE_RATE * samplesPerWindow * factor))
    # print(f'{indexOfFreq = }')
    # print(f'{samplesPerFrame = }')

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


def getPeaks(threshold):
    peaks = find_peaks(freqAmplitudeFiltered, height=threshold, distance=framesPerSecond * (VIDEO_DURATION + 3))
    return peaks


def plot(peaks, threshold):
    print("close the window to continue")
    plt.plot(freqAmplitudeFiltered)
    plt.plot(peaks, freqAmplitudeFiltered[peaks], "x")
    plt.plot(np.full(len(freqAmplitudeFiltered), threshold), "--", color="gray")
    plt.show()


def adjustThreshold(peaksGoal, oldThreshold):
    threshold = oldThreshold
    iterations = 0
    factor = 1000
    maxIterations = 50000 / factor

    peaks = getPeaks(threshold)[0]
    peaksNum = len(peaks)
    plot(peaks, threshold)

    if peaksNum != peaksGoal:
        ans = input(str(peaksNum) + " beeps found. Is " + str(
            peaksGoal) + " the correct number of checkpoints? (y/n) ")
        if ans == 'y':
            print(prefix + "adjusting threshold")
        else:
            print("rerun with correct checkpoints value")
            sys.exit()

    while True:
        peaks = getPeaks(threshold)[0]
        peaksNum = len(peaks)

        # print("current peaks: " + str(peaksNum))
        # print("goal: " + str(peaksGoal))

        # plot(peaks, threshold)

        if peaksNum == peaksGoal or iterations > maxIterations:
            break

        if peaksNum < peaksGoal:
            threshold -= factor
        elif peaksNum > peaksGoal:
            threshold += factor
        iterations += 1

    if threshold != oldThreshold:
        print(prefix + "threshold adjusted from " + str(oldThreshold) + " to " + str(threshold))

    return threshold


def getTimes(freqAmplitudeFiltered, threshold):
    print(prefix + "extrapolating video times")
    videoStarts = []
    videoEnds = []
    offsetSeconds = 1

    peaks = getPeaks(threshold)
    for peak in peaks[0]:
        startFrame = (peak + offsetSeconds * framesPerSecond)

        videoStarts.append(timedelta(seconds=startFrame / framesPerSecond))
        videoEnds.append(timedelta(seconds=(startFrame / framesPerSecond) + VIDEO_DURATION))

    return videoStarts, videoEnds


def removeAudio():
    try:
        os.remove(AUDIO)
    except:
        pass


def getFilename(message, overlay):
    file = input(message)
    if not ((overlay and file == "") or os.path.isfile(file)):
        init()
        print(Fore.RED + "file not found. retype filename or move file into PythonParserProgram folder")
        print(Style.RESET_ALL, end="")
        file = getFilename(message, overlay)
    return file


def getInputs():
    CHECKPOINTS = int(input("enter the number of times the robot completes its action during the recording: "))
    VIDEO_DURATION = float(input("enter the length (in seconds) of each action: "))
    BEEP_FREQ = int(input("enter the frequency (in Hz) of the beeps (default is 2093 for beep 96 on SPIKE): "))
    OVERLAY_FILE = getFilename("enter the name of the video file to overlay on the recording (include filetype suffix) "
                           "(press enter if none): ", True)

    return CHECKPOINTS, VIDEO_DURATION, BEEP_FREQ, OVERLAY_FILE


########################################## main
# INPUT_FILE = "trainVid10.3.mp4"
INPUT_FILE = "trainVid8.mp4"
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
# loops = 7  # 0 for no loops
AUDIO = "audio.wav"
framesPerSecond = 30 * 10  # this is for the audio
loglevel = " -loglevel +error"
prefix = " - "

############### pathName = "./Downloads/PythonParserProgram/"  # for macOS

######################### CHANGE THE FOLLOWING LINES FOR MAC VS WINDOWS !!!!!!!!!!!!!!!!!!!!!!!!!!
# pathName = "./"  # for macOS
pathName = ""  # for Windows

### for macOS
# os.chdir("./Downloads/PythonParserProgram")

##### comment plot(peaks) call in adjust threshold function before exporting

# assign variables
removeAudio()
INPUT_FILE = getFilename("enter the name of the input file (it should be in the same folder as the executable) "
                         "(include filetype suffix): ", False)
getAudio(INPUT_FILE, AUDIO, SAMPLE_RATE)
CHECKPOINTS, VIDEO_DURATION, BEEP_FREQ, OVERLAY_FILE = getInputs()
loops = int(LOOPED_VIDEO_DURATION / VIDEO_DURATION)

# Extract Raw Audio from Wav File
wf = wave.open(AUDIO, "r")
signal = wf.readframes(-1)
signal = np.frombuffer(signal, dtype='int16')

audioSampleCount = len(signal)
samplesPerFrame = SAMPLE_RATE / framesPerSecond
audioFrameCount = int(math.ceil(audioSampleCount / samplesPerFrame))

freqAmplitudeFiltered = getFreqAmplitudeFiltered(signal, audioSampleCount, samplesPerFrame, BEEP_FREQ)

threshold = adjustThreshold(CHECKPOINTS, threshold)
videoStarts, videoEnds = getTimes(freqAmplitudeFiltered, threshold)

print(f'{len(videoStarts) = }')
if (len(videoStarts) != CHECKPOINTS):
    sys.exit("error: failure to parse videos. please try again. check the number of checkpoints")

deletePath(VIDEO_FOLDER)
createPath(VIDEO_FOLDER)

splitVideo(videoStarts, videoEnds, CHECKPOINTS, OVERLAY_FILE, loops)
loopVideos(loops, CHECKPOINTS)
print(prefix + "finished")
print("all " + str(CHECKPOINTS) + " videos are in " + VIDEO_FOLDER + " folder")

removeAudio()
# uploadFiles(CHECKPOINTS)

time.sleep(2)
path = os.path.realpath(VIDEO_FOLDER)
os.startfile(path)
