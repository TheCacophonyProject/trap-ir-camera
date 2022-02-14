import numpy as np
import cv2
import time

class Background():
    i = 0
    frame_len = 5
    frames = [None]*frame_len

    def add(self, frame):
        self.frames[self.i] = frame
        self.i+=1
        self.i = self.i%self.frame_len

    def get(self):
        return self.frames[self.i]

class Motion:
    background = Background()
    kernel_trigger = np.ones((15, 15), 'uint8')     # kernel for erosion when not recording
    kernel_recording = np.ones((10, 10), 'uint8')   # kernel for erosion when recording
    motion = False # If there is currently considered to be motion in the video
    motion_count = 0
    show = False

    def get_kernel(self):
        if self.motion:
            return self.kernel_recording
        else:
            return self.kernel_trigger

    # Processes a frame returning True if there is motion.
    def process_frame(self, frame):
        # if background is not full yet just write frame to background
        if self.background.get() is None:
            print("writing to background")
            self.background.add(frame)
            return False
        
        # Filter and get diff from background
        delta = cv2.absdiff(self.background.get(), frame) # Get delta from current frame and background
        threshold = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
        erosion_image = cv2.erode(threshold, self.get_kernel())
        self.background.add(frame)
        
        # Calculate if there was motion in the current frame
        # TODO Chenage how much is added to the motion_count depending on how big the motion is
        if erosion_image.max() > 0:
            self.motion_count+=1
        else:
            self.motion_count-=1

        if self.motion_count > 30:
            self.motion_count = 30
        elif self.motion_count < 0:
            self.motion_count = 0

        # Check if motion has started or ended
        if not self.motion and self.motion_count > 10:
            self.motion = True
        
        elif self.motion and self.motion_count <= 0:
            self.motion = False
            
        if self.show:
            cv2.imshow('delta',delta)
            cv2.imshow('threshold',threshold)
            cv2.imshow('erosion_image', erosion_image)
            cv2.imshow('window',frame)
            cv2.waitKey(1)
                
        return self.motion

# Example 
"""
cap = cv2.VideoCapture(0)
motion = Motion()
motion.show = True
while True:
    returned, frame = cap.read()
    if not returned:
        print("no frame from video capture")
        break
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    motion.process_frame(frame)
cv2.destroyAllWindows()
"""