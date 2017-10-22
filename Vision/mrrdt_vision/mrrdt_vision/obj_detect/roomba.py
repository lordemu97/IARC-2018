#!/usr/bin/env python3.5
############################################
# Multi-Rotor Robot Design Team
# Missouri University of Science and Technology
# Summer 2017
# Christopher O'Toole

'''Example showing how to use the mrrdt_vision module to detect roombas in images.'''

import numpy as np
import cv2
import threshold_gpu
import display

from sklearn.preprocessing import normalize
from timeit import default_timer as timer

from __init__ import DEFAULT_BOUNDING_BOX_COLOR, DEFAULT_BOUNDING_BOX_THICKNESS

# parameter that determines the precision of the polygon approximation.
EPSILON = .03 
# length of directional arrow
ARROW_LENGTH = 50
# color of directional arrow
ARROW_COLOR = (255, 0, 255)
# directional arrow thickness
ARROW_THICKNESS = 3
# key to quit
QUIT_KEY = 'q'

# image(s) for this file's unit test
TEST_VIDEO_PATH = '../data/roombaRed.mp4'

class Roomba():
    def __init__(self, bounding_box, center, orientation):
        self._bounding_box = bounding_box
        self._center = center
        self._orientation = orientation
        self._bounding_box_color = DEFAULT_BOUNDING_BOX_COLOR
        self._bounding_box_thickness = DEFAULT_BOUNDING_BOX_THICKNESS
    
    @property
    def bounding_box(self):
        return self._bounding_box

    @property
    def center(self):
        return self._center

    @property
    def orientation(self):
        return self._orientation

    def draw(self, img):
        x_min, y_min, x_max, y_max = self.bounding_box
        cv2.rectangle(img, (x_min, y_min), (x_max, y_max), self._bounding_box_color, self._bounding_box_thickness)
        cv2.arrowedLine(img, tuple(self.center.astype(int)), tuple((self.center+ARROW_LENGTH*self.orientation).astype(int)), ARROW_COLOR, ARROW_THICKNESS)

class RoombaDetector():
    # minimum area for a region to have a chance at being considered a roomba
    MIN_AREA = 100
    # amount to grow the proposed bounding box by on each side
    BOUNDING_BOX_SIZE_OFFSET = 30

    def __init__(self):
        pass
    
    def detect(self, img):
        proposals = []
        polygons = []
        centers = []
        orientations = []

        # detect red and green blobs in img
        img = threshold_gpu.threshold_image_for_roombas(img)
        
        # find the location of those blobs
        modified_img, contours, hierarchy = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= RoombaDetector.MIN_AREA:
                moments = cv2.moments(contour)
                # extract a polygon approximation of the roomba's flap
                epsilon = EPSILON*cv2.arcLength(contour,True)
                polygons.append(cv2.approxPolyDP(contour,epsilon,True))
                # get the centroid for the roomba's flap
                centers.append((int(moments['m10'] / moments['m00']), int(moments['m01'] / moments['m00'])))
                # get the roomba's bounding box
                x, y, w, h = cv2.boundingRect(contour)
                top_left = np.array([x, y]) - RoombaDetector.BOUNDING_BOX_SIZE_OFFSET
                bottom_right = np.array([x + w, y + h]) + RoombaDetector.BOUNDING_BOX_SIZE_OFFSET
                proposals.append((*top_left.astype(int), *bottom_right.astype(int)))

        # vectorize the list of centroids
        centers = np.asarray(centers)

        if polygons:
            # unpack the polygons array
            polygons = np.asarray([polygon[:, 0, :] for polygon in polygons])
            # compute a unit vector for the roomba's orientation
            roomba_front_approx = []
            
            for i, polygon in enumerate(polygons):
                relative_coords = polygon-centers[i]
                weights = 1/np.sqrt(np.sum(relative_coords**2,axis=1))
                roomba_front_approx.append(np.sum(relative_coords*weights[:,None], axis=0)/np.sum(weights, axis=0))

            roomba_front_approx = np.asarray(roomba_front_approx)
            orientations = normalize(roomba_front_approx)

        # return a list of detected roombas.
        return [Roomba(proposals[i], centers[i], orientations[i]) for i in range(len(proposals))]

if __name__ == '__main__':
    # unit test
    detector = RoombaDetector()

    with display.VideoReader(TEST_VIDEO_PATH) as video, display.Window(TEST_VIDEO_PATH) as window:
        try:
            should_quit = False

            for frame in video:
                if should_quit:
                    break
                if frame is None:
                    break
                
                start = timer()
                roombas = detector.detect(frame)
                print(timer()-start, 'seconds')
                
                for roomba in roombas:
                    roomba.draw(frame)

                window.show(frame)

                should_quit = window.is_key_down(QUIT_KEY)
        except KeyboardInterrupt as e:
            pass