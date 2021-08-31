#!/usr/bin/python3

from genericpath import isdir
import os
import datetime as dt
from picamera import PiCamera
import time
import logging
import socket
from systemd.journal import JournalHandler
import psutil
import glob
import shutil
import sys

log = logging.getLogger('demo')
log.addHandler(JournalHandler())
stdout_handleer = logging.StreamHandler(sys.stdout)
stdout_handleer.setFormatter(logging.Formatter('%(message)s'))
stdout_handleer.setLevel(logging.INFO)
log.addHandler(stdout_handleer)
log.setLevel(logging.INFO)

usb_dir = '/media/cp'
video_dir = os.path.join(usb_dir, 'videos')
still_dir = '/var/spool/cptv'
framerate = 16
h264_ext = ".h264"
mp4_ext = ".mp4"
resolution = (640,480)
hostname = socket.gethostname()
max_disk_usage_percent = 80

os.makedirs(video_dir, exist_ok=True)
os.makedirs(still_dir, exist_ok=True)

##TODO I frame https://raspberrypi.stackexchange.com/questions/54189/how-do-i-insert-key-frames-at-particular-times-with-picamera
# https://www.raspberrypi.org/documentation/raspbian/applications/camera.md
#camera.color_effects = (128,128)

def start_video(filename):
    log.info(f"starting recording {filename}{h264_ext}")
    camera.capture('/var/spool/cptv/still.png')
    camera.start_recording(filename+h264_ext)

def stop_video(filename):
    camera.stop_recording()
    log.info("finished recording, converting to mp4")
    os.system(f"MP4Box -quiet -add {filename}{h264_ext}:fps={framerate} {filename}{mp4_ext}")
    os.system(f"rm {filename}{h264_ext}") # delete h264 file
    log.info(f"finshed recording {filename}{mp4_ext}")

def need_more_disk_space():
    return psutil.disk_usage(video_dir).percent > max_disk_usage_percent

# Delete everything on the USB drive apart from videos from device in the video directory
def delete_other_files():
    # Delete directories apart from the video_dir
    files = os.listdir(usb_dir)
    for f in files:
        p = os.path.join(usb_dir, f)
        if os.path.basename(p) != os.path.basename(video_dir):
            if os.path.isfile(p):
                os.remove(p)
            else:
                shutil.rmtree(p)

    # Delete all files that are not recording from this device
    files = glob.glob(os.path.join(video_dir, "*"))
    for f in files:
        if os.path.isfile(f) and not f.endswith(f'{hostname}{mp4_ext}'):
            os.remove(f)
        elif os.path.isdir(f):
            shutil.rmtree(f)

# Delete the oldest video file.
def delete_oldest_video():
    files = os.listdir(video_dir)
    files.sort()
    log.info(f"deleting '{files[0]}' to make space on USB")
    os.remove(os.path.join(video_dir, files[0]))

log.info("starting IR camera")
camera = PiCamera()
camera.resolution = resolution
camera.framerate = framerate
camera.start_preview()

log.info("deleting other files on the USB drive")
delete_other_files()

while (True):
    date_str = dt.datetime.now().strftime('%Y-%m-%d_%H.%M.%S')
    file_name = f'{date_str}_{hostname}'
    file_path = os.path.join(video_dir, file_name)
    while (need_more_disk_space()):
        delete_oldest_video()
    start_video(file_path)
    time.sleep(300)
    stop_video(file_path)
