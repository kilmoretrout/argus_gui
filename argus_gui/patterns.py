#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import pickle
import sys

import cv2
import numpy as np
import scipy.spatial.distance


# Script called by patterns-gui. Runs through a video frame by frame and saves the object points (in arbitrary coordinates) and images points (pixel coordinates) to a pickle file
# for use with argus-calibrate
class PatternFinder:
    def __init__(self, rows, cols, spacing, ofile, ifile, start=None, stop=None, display=True, dots=True):
        self.rows = rows
        self.cols = cols
        self.spacing = spacing
        self.ofile = ofile
        self.ifile = ifile
        self.movie = cv2.VideoCapture(self.ifile)
        self.start = start
        self.stop = stop

        # print start, stop

        # If the user doesn't specify an end and start point, set to the end and beginning of the video
        if not self.start is None:
            self.start = int(np.floor(self.start * self.movie.get(cv2.CAP_PROP_FPS)))
        else:
            self.start = 0
        if not self.stop is None:
            self.stop = int(np.floor(self.stop * self.movie.get(cv2.CAP_PROP_FPS)))
        else:
            self.stop = None

        if ((self.stop is None) or \
                (int(self.stop) < 0) or \
                (int(self.stop) > int(self.movie.get(cv2.CAP_PROP_FRAME_COUNT)))):
            self.stop = int(self.movie.get(cv2.CAP_PROP_FRAME_COUNT))
        if ((self.start < 0) or \
                (self.start > self.stop)):
            self.start = 0

        self.display = display
        self.dots = dots

        # Print some stuff for the user about the process
        print("Using from frame {0} to {1}".format(self.start, self.stop))
        sys.stdout.flush()
        self.imageSize = (int(self.movie.get(cv2.CAP_PROP_FRAME_WIDTH)),
                          int(self.movie.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        print("Image size is {0}".format(self.imageSize))
        print("Number of rows in grid: " + str(self.rows))
        print("Number of columns in grid: " + str(self.cols))
        sys.stdout.flush()

    def getSec(self, s):
        return 60. * s

    # make the object points, depth = 0, right hand corner of the grid is the origin
    # moving from point to point with grid spacing
    def getObjectPoints(self):
        boardsize = (self.rows, self.cols)
        single_board = []
        for col in range(self.cols):
            for row in range(self.rows):
                single_board.append([row, col, 0])
        single_board = np.array(single_board, dtype=np.float32).reshape(-1, 1, 3)
        single_board = single_board * self.spacing
        return single_board

    def getPattern(self, single_board):
        # find patterns in range
        boardsize = (self.rows, self.cols)
        objectPoints = dict()
        imagePoints = dict()
        if self.display:
            cv2.namedWindow('Grids')
        print("Beginning frame by frame pattern search")
        sys.stdout.flush()
        n = 0
        skipping = True
        for frame in range(self.stop):
            retval, raw = self.movie.read()  # read the frame

            if retval and (frame >= self.start):
                print('Reading frame ' + str(frame - self.start) + ' of ' + str(int(self.stop - self.start)))
                sys.stdout.flush()
                draw = raw
                gray = cv2.cvtColor(raw, cv2.COLOR_RGB2GRAY)  # convert to gray
                if self.dots:  # detect dot pattern
                    try:
                        retval, corners = cv2.findCirclesGrid(gray, boardsize)
                    except:
                        retval, corners = cv2.findCirclesGridDefault(gray, boardsize)
                else:  # detect chessboard
                    retval, corners = cv2.findChessboardCorners(gray, boardsize)
                    if retval:
                        cv2.cornerSubPix(gray,
                                         corners,
                                         (3, 3), (-1, -1),
                                         (cv2.TERM_CRITERIA_MAX_ITER |
                                          cv2.TERM_CRITERIA_EPS, 30, 0.1)
                                         )
                # show results
                cv2.drawChessboardCorners(draw, boardsize, corners, retval)

                # add quality control check here for duplicate points
                # or very tiny boards
                if retval:
                    check = np.array(corners)
                    check = check.reshape(-1, 2)
                    dists = scipy.spatial.distance.pdist(check)
                    if (dists < 1).any():
                        retval = False
                        print("Duplicate point detected")
                        sys.stdout.flush()
                    if np.max(dists) < 100:
                        retval = False
                        print("Pattern too small")
                        sys.stdout.flsuh()

                # add to output
                if retval:
                    objectPoints[frame] = single_board
                    imagePoints[frame] = corners
                    n += 1

                # display result if ordered to
                if self.display:
                    newSize = (int(self.imageSize[0] / 2), int(self.imageSize[1] / 2))
                    cv2.imshow('Grids', cv2.resize(draw, newSize))
                    cv2.waitKey(1)
            else:
                if skipping:
                    print('Skipping to start frame...')
                    sys.stdout.flush()
                    skipping = False

        # save results
        print("Saving results to {0}".format(self.ofile))
        sys.stdout.flush()
        ofile = open(self.ofile, "wb")
        pickle.dump(objectPoints, ofile)
        pickle.dump(imagePoints, ofile)
        pickle.dump(self.imageSize, ofile)
        ofile.close()
        print("Found " + str(n) + " patterns in total\nIf this is too few, modify settings and try again.")
