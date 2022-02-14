#!/usr/bin/python3

import sys
import glob
import cv2
import os
import collections
import numpy as np

class Background():
    i = 0
    frame_len = 20
    frames = [None]*frame_len

    def add(self, frame):
        self.frames[self.i] = frame
        self.i+=1
        self.i = self.i%self.frame_len

    def get(self):
        return self.frames[self.i]

    def fill(self, cap):
        while self.get() is None:
        #for i in range(self.frame_len):
            _, f = cap.read()
            self.add(f)
    
    def get_all_frames(self):
        out = []
        a = self.i
        for _ in range(self.frame_len):
            out.append(self.frames[a])
            a+=1
            a = self.i%self.frame_len
        return out

back = Background()

class Motion():
    def process(self, video_f, show, out):
        cap = cv2.VideoCapture(video_f)
        back = Background()    
        back.fill(cap)
        motion_count = 0
        motion = False
        video_count = 0
        buffer = collections.deque(maxlen=20)
        kernel = np.ones((20, 20), 'uint8')
        kernel_sensitive = np.ones((10, 10), 'uint8')
        k = kernel
        writer = None

        while True:
            returned, frame = cap.read()
            if not returned:
                print("file ended")
                if writer is not None and out != None:
                    writer.release()
                break
            buffer.append(frame)

            back_frame = cv2.cvtColor(back.get(), cv2.COLOR_BGR2GRAY)
            #back_frame = cv2.GaussianBlur(back_frame, (21, 21), 0)
            
            gray2 = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            #gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)
            deltaframe=cv2.absdiff(back_frame,gray2)
            
            threshold = cv2.threshold(deltaframe, 25, 255, cv2.THRESH_BINARY)[1]
            erosion_image = cv2.erode(threshold, k)

            motion_in_frame = False
            
            if erosion_image.max() > 0:
                motion_in_frame = True

                if show:
                    f2_copy = frame.copy()
                    threshold = cv2.dilate(erosion_image,k)
                    countour,_ = cv2.findContours(threshold, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    for i in countour:
                        if cv2.contourArea(i) < 20:
                            continue
                        motion_in_frame = True

                        if show:
                            (x, y, w, h) = cv2.boundingRect(i)
                            cv2.rectangle(f2_copy, (x, y), (x + w, y + h), (255, 0, 0), 2)

            if motion > 100:
                motion = 100

            if motion_in_frame and motion_count < 10:
                if motion:
                    motion_count+=2
                else:
                    motion_count+=1
            elif not motion_in_frame and motion > 0:
                motion_count-=1

            if motion_count >= 10 and not motion:
                motion = True
                motion_count = 100
                k = kernel_sensitive
                print("Motion!")
                
                if out != None:
                    out_dir = os.path.join(os.path.dirname(video_f), "motion")
                    os.makedirs(out_dir, exist_ok=True)
                    out_name = os.path.basename(os.path.splitext(video_f)[0])+".mp4"
                    out_file = os.path.join(out_dir, out_name)

                    print("saving to ", out_file)
                    video_count+=1
                    width  = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    
                    if fps > 40:
                        fps = 10

                    writer = cv2.VideoWriter(out_file, cv2.VideoWriter_fourcc(*'mp4v'), fps, (int(width),int(height)))
                    for f in buffer:
                        writer.write(f)

            if motion_count == 0 and motion:
                motion = False
                if out != None: 
                    writer.release()
                    writer = None
                print("motion stopped")
                k = kernel

            if show:
                cv2.imshow('delta',deltaframe)
                cv2.imshow('threshold',threshold)
                cv2.imshow('window',f2_copy)
            
            if motion and out != None:
                writer.write(frame)

            #if not motion and not motion_in_frame:
            back.add(frame)
            
            #back.add(frame)


            if cv2.waitKey(20) == ord('q'):
                break
            #frames[frame_i] = frame2
        cap.release()
        cv2.destroyAllWindows()



motion = Motion()



video_folders = ["/media/cam/drone-01/test1", "/media/cam/drone-01/test2"]
video_files = []

for video_folder in video_folders:

    video_files = video_files + glob.glob(video_folder+"/*.mp4")
    video_files = video_files + glob.glob(video_folder+"/*.avi")


print(f"Number of file to process: {len(video_files)}")
print(video_files)

#video_files = ["p1.mp4"]
#video_files = ["2021-11-12_19.54.58_trap-ir-01.mp4"]
#video_files = glob.glob("/media/cam/cp/videos"+"/*.mp4")

#video_files = [""]

for video_f in video_files:
    print(f"processing {video_f}")
    #cap=cv2.VideoCapture(video_f)
    motion.process(video_f, False, True)






"""
#cap=cv2.VideoCapture("p1.mp4")  # Read from camera
cap=cv2.VideoCapture(0)  # Read from camera

back.fill(cap)
#cv2.imshow('window',back.frames[back.i])

motion_count = 0
motion = False
motion_in_frame = False

in_video = "p1.mp4"
out_video = None

show = True

#video_files = ["p1.mp4"]
video_files = glob.glob("/media/cam/cp/videos"+"/*.avi")
video_files = [""]

for video_f in video_files:
    print(f"processing {video_f}")
    #cap=cv2.VideoCapture(video_f)  # Read from camera
    cap=cv2.VideoCapture(0)  # Read from camera
    
    back = Background()    
    back.fill(cap)

    motion_count = 0
    motion = False
    motion_in_frame = False

    video_count = 0

    buffer = collections.deque(maxlen=20)

    while True:
        ret, frame = cap.read()
        buffer.append(frame)
        if not ret:
            print("file ended")
            if writer is not None:
                writer.release()
            break
        
        back_frame = cv2.cvtColor(back.get(), cv2.COLOR_BGR2GRAY)
        back_frame = cv2.GaussianBlur(back_frame, (21, 21), 0)
        
        gray2 = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)
        deltaframe=cv2.absdiff(back_frame,gray2)
        
        threshold = cv2.threshold(deltaframe, 25, 255, cv2.THRESH_BINARY)[1]
        threshold = cv2.dilate(threshold,None)
        
        countour,heirarchy = cv2.findContours(threshold, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        motion_in_frame = False
        
        f2_copy = frame.copy()

        for i in countour:
            if cv2.contourArea(i) < 200:
                continue
            motion_in_frame = True

            if show:
                (x, y, w, h) = cv2.boundingRect(i)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        
        if motion_in_frame and motion_count < 10:
            motion_count+=1
        elif not motion_in_frame and motion > 0:
            motion_count-=1

        if motion_count == 10 and not motion:
            motion = True
            print("Motion!")
            
            base_name = os.path.splitext(os.path.basename((video_f)))[0]
            print(base_name)
            out_name = f"out/{base_name}-{video_count}.mp4"
            print("saving to ", out_name)
            video_count+=1
            width  = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            if fps > 40:
                fps = 10

            writer = cv2.VideoWriter(out_name, cv2.VideoWriter_fourcc(*'mp4v'), fps, (int(width),int(height)))
            for f in buffer:
                writer.write(f)

        if motion_count == 0 and motion:
            motion = False
            writer.release()
            writer = None
            print("motion stopped")

        if show:
            cv2.imshow('delta',deltaframe)
            cv2.imshow('threshold',threshold)
            cv2.imshow('window',frame)
        
        if motion:
            writer.write(frame)

        #if not motion and not motion_in_frame:
        back.add(f2_copy)

        if cv2.waitKey(20) == ord('q'):
            break
        #frames[frame_i] = frame2

cap.release()
cv2.destroyAllWindows()
"""