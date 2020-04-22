#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  8 00:34:46 2015

@author: Dylan Ray and Dennis Evangelista
University of North Carolina at Chapel Hill
Hedrick Lab
"""

import os
import platform
import sys
import cv2
import numpy as np
import shutil
from moviepy.editor import *
from moviepy.config import get_setting
import random
from Tkinter import *
from Queue import Queue
import subprocess
import shutil
import argus.ocam
import argus_gui
import pkg_resources
from argus_gui import ArgusError
from argus.ocam import PointUndistorter
import tempfile

RESOURCE_PATH = os.path.abspath(pkg_resources.resource_filename('argus_gui.resources', ''))

"""
Undistorter
Takes a video and undistorts it frame-by-frame given a set of pinhole or omnidirectional distortion coefficient
"""
class Undistorter(object):
    # Take the parameters passed from the GUI.
    def __init__(self, fnam = None, omni = None, coefficients = None):
        self.infilename = fnam

        if not fnam is None and fnam != '':
            self.set_movie(fnam)
        else:
            self.movie = None

        if (not omni is None) and (omni != ''):
            self.set_omnidirectional(omni)
        else:
            self.oCamUndistorter = None
            self.omni = omni
        
        self.coefficients = coefficients

    """
    Gets a camera matrix and distortion vector from a list of coefficients.
    Expects the list of coefficients to be in the following order:
        - Focal length (pixels)
        - Horizontal optical center
        - Vertical optical center
        - K1, K2, T1, T2, K3 (distortion coefficients)
    """
    def calibParse(self):
        line = self.coefficients
        cM = np.array([[line[0],0.0,line[1]],
               [0.0,line[0],line[2]],[0.0,0.0,1.0]])
        dC = np.array([line[3],line[4],line[5],line[6],line[7]])
        return cM, dC

    def set_omnidirectional(self, omni):
        try:
            print 'Making Omnidirectional mapping...'
            sys.stdout.flush()
            #self.omni = map(float, self.omni.split(',')[:])
            model = argus.ocam.ocam_model(omni[0], int(omni[1]), int(omni[2]), c = omni[3], d = omni[4], e = omni[5], xc = omni[6], yc = omni[7], pol = np.array(omni[13:]))
            self.oCamUndistorter = argus.ocam.Undistorter(model)
            self.omni = omni
        except:
            raise ArgusError('could not make omnidirectional undistorter object. make sure the omnidirectional coefficients were provided according to the documentation')

    def get_mappings(self, crop):
        R = np.eye(3)
        cM, dC = self.calibParse()

        osize = ((int(self.movie.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH)),
             int(self.movie.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))))

        newsize = ((int(self.movie.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH)),
            int(self.movie.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))))
        if crop:
            # Do it the old way
            newcM = cM
        else:
            # Do it Hedrick's way
            newcM, roi = cv2.getOptimalNewCameraMatrix(cM,dC,osize,1,newsize)

        map1,map2 = cv2.initUndistortRectifyMap(cM,dC,R,newcM,newsize,cv2.cv.CV_32FC1)
        return map1, map2

    def set_movie(self, fnam):
        self.movie = cv2.VideoCapture(os.path.abspath(fnam))
        print 'Using movie at ' + fnam
        self.infilename = fnam

        try:
            self.frameCount = int(self.movie.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))
            self.fps = float(self.movie.get(cv2.cv.CV_CAP_PROP_FPS))
            self.frame_msec = 1000. / self.fps
            return self.fps, self.frameCount
        except:
            raise ArgusError('could not read specified movie')
    
    # The meat and potatoes
    def undistort_movie(self, ofnam = None, frameint = 25, crf = 12, write = True, display = True, tmp_dir = None, crop = False):
        if self.movie is None:
            raise ArgusError('no movie specified')

        if (self.omni is None) and (self.coefficients is None):
            raise ArgusError('no distortion coefficients specified')

        if tmp_dir is None:
            tmp = tempfile.mkdtemp()
        else:
            tmp = tmp_dir
        
        if write:
            if ofnam == '':
                raise ArgusError('no output filename specified')
            _ = ofnam.split('.')
            if _[len(_) - 1] != 'mp4' and _[len(_) - 1] != 'MP4':
                raise ArgusError('output filename must specify an mp4 file')
                return
            if os.path.isfile(ofnam):
                raise ArgusError('output file already exists! Argus will not overwrite')
                return
        try:
            t = open(self.infilename, "r")
        except:
            raise ArgusError('input movie not found')
            return
        
        t = None

        if not self.coefficients is None:
            map1, map2 = self.get_mappings(crop)

        # if we're displaying, make a window to do so
        if display:
            cv2.namedWindow("Undistorted",cv2.cv.CV_WINDOW_NORMAL)

        if write:
            # Create a list of the frames (pngs)
            fileList = []
        k = 1

        if display:
            cv2.startWindowThread()
        
        print 'Undistorting...'
        sys.stdout.flush()
        for a in range(int(self.movie.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))):
            retval,raw = self.movie.read()
            # To keep things interesting, and also not to overload the log, update users randomly somewhere between 200 to 300 frames
            if a == k:
                print "Undistorting frame number " + str(a) + " of " + str(int(self.movie.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT)))
                sys.stdout.flush()
                k += random.randint(200,300)

            if retval:
                if crop:
                    if self.oCamUndistorter is None:
                        undistorted = cv2.remap(raw,map1,map2,cv2.INTER_LINEAR)
                    else:
                        undistorted = self.oCamUndistorter.undistort_frame(raw)
                else:
                    if self.oCamUndistorter is None:                           
                        undistorted = cv2.remap(raw,map1,map2,
                           interpolation=cv2.INTER_CUBIC,
                           borderMode=cv2.BORDER_CONSTANT,
                           borderValue=(211,160,86))
                    else:
                        undistorted = self.oCamUndistorter.undistort_frame(raw)

                if display:
                    # Non-resizable windows in Mac OS, so make half-size so it's not too obnoxious
                    if sys.platform == 'darwin':
                        cv2.imshow('Undistorted', cv2.resize(undistorted, (0,0), fx=0.5, fy=0.5))
                    else:
                        cv2.imshow('Undistorted', undistorted)
                    cv2.waitKey(1)

                # Write the individual frame as a png to the temporary directory
                if write:
                    cv2.imwrite(tmp + '/' + str(a) + '.png', undistorted)
                    fileList.append(tmp + '/' + str(a) + '.png')
            else:
                print "Could not read frame number: " + str(a)
                print "Exiting..."
                sys.stdout.flush()
                return
        print 'Undistortion finished'
        sys.stdout.flush()
        # Destroy movie object and the window if it was even created
        movie = None
        if display:
            cv2.waitKey(1)
            cv2.destroyAllWindows()
            cv2.waitKey(1)
        if write:
            # Create a clip with the original fps from the undistorted frames in the temporary directory, read in numerical order, and set the audio to that of the original video
            print 'Reading images and beginning to encode...'
            sys.stdout.flush()
            clip = ImageSequenceClip(fileList, fps=self.fps, with_mask = False, load_images = False)
            print 'Ripping audio...'
            sys.stdout.flush()
            cmd = [
               get_setting("FFMPEG_BINARY"),
               '-loglevel', 'panic',
               '-hide_banner',
               '-i', self.infilename,
               '-c:a', 'copy',
               '-vn', '-sn',
               tmp + '/' + 'temp.m4a' ]
            subprocess.call(cmd)
            # Write the mp4 file
            clip.write_videofile(ofnam, fps=self.fps, audio = tmp + '/' + 'temp.m4a', audio_fps = 48000, codec='libx264', threads=0, ffmpeg_params = ['-crf', str(crf), '-g', str(frameint), '-pix_fmt', 'yuv420p', '-profile' ,'baseline'])
            sys.stdout.flush()
            clip = None

            # Destroy the temporary directory
            shutil.rmtree(tmp)

    def undistort_frame(self, frame, ofile = None, crop = False):
        if self.movie is None:
            raise ArgusError('no movie specified')
            return
        if (self.omni is None) and (self.coefficients is None):
            raise ArgusError('no distortion profile provided, Argus cannot undistort')
            return
        
        if not self.coefficients is None:
            map1, map2 = self.get_mappings(crop)
        
        if 0 <= frame - 1 <= self.frameCount - 1:
            self.movie.set(cv2.cv.CV_CAP_PROP_POS_MSEC, (frame - 1)*self.frame_msec)
            retval, raw = self.movie.retrieve()
            if retval:
                if crop:
                    if self.oCamUndistorter is None:
                        undistorted = cv2.remap(raw,map1,map2,cv2.INTER_LINEAR)
                    else:
                        undistorted = self.oCamUndistorter.undistort_frame(raw)
                else:
                    if self.oCamUndistorter is None:                           
                        undistorted = cv2.remap(raw,map1,map2,
                           interpolation=cv2.INTER_CUBIC,
                           borderMode=cv2.BORDER_CONSTANT,
                           borderValue=(211,160,86))
                    else:
                        undistorted = self.oCamUndistorter.undistort_frame(raw)
                if not ofile is None:
                    cv2.imwrite(ofile, undistorted)
                return undistorted
            else:
                raise ArgusError('Argus could not read specified frame')
        else:
            raise ArgusError('frame out of bounds')
        
    def undistort_array(self, array, ofile = None, crop = False):
        if (self.omni is None) and (self.coefficients is None):
            raise ArgusError('no distortion profile provided, Argus cannot undistort')
            return

        if not self.coefficients is None:
            map1, map2 = self.get_mappings(crop)
        
        raw = array
        if crop:
            if self.oCamUndistorter is None:
                undistorted = cv2.remap(raw,map1,map2,cv2.INTER_LINEAR)
            else:
                undistorted = self.oCamUndistorter.undistort_frame(raw)
        else:
            if self.oCamUndistorter is None:                           
                undistorted = cv2.remap(raw,map1,map2,
                   interpolation=cv2.INTER_CUBIC,
                   borderMode=cv2.BORDER_CONSTANT,
                   borderValue=(211,160,86))
            else:
                undistorted = self.oCamUndistorter.undistort_frame(raw)
        if not ofile is None:
            cv2.imwrite(ofile, undistorted)
        return undistorted

class DistortionProfile(object):
    def __init__(self, model = None, mode = None):
        calibFiles = list()
        self.calibFolder = os.path.join(RESOURCE_PATH, 'calibrations/')
        for file in os.listdir(self.calibFolder):
            if file.endswith(".csv"):
                calibFiles.append(file)

        # list of modes for each model
        self.modes = dict()
        # dictionary that points to the calibration csv file for various camera models
        self.models = dict()

        for file in calibFiles:
            ifile = open(self.calibFolder + file)
            if file.split('.')[0] != '':
                self.models[file.split('.')[0]] = self.calibFolder + file
            line = ifile.readline()
            mods = list()
            while line != '':
                line = ifile.readline().split(',')[0]
                if line != '':
                    mods.append(line)
            if len(mods) != 0:
                self.modes[file.split('.')[0]] = mods

        self.coefficients = None
        if (mode is None) or (model is None):
            self.coefficients = None
        else:
            self.get_coefficients(model, mode)

    """
    Returns either a list of distortion and intrinsic camera information as Undistorter expects them (Pinhole).
        - Focal length (pixels)
        - Horizontal optical center
        - Vertical optical center
        - K1, K2, T1, T2, K3 (distortion coefficients)
    If the mode chosen is an omnidirectional profile, returns an Argus Ocam Undistorter object.
    """
    def get_coefficients(self, model = None, mode = None):
        if self.coefficients is None:
            if ((not model is None) and (not mode is None)):
                fnam = self.models[model]
                ifile = open(fnam,"r")
                #print 'Getting coefficients'

                line = ifile.readline().split(',')
                while line[0] != mode:
                    line = ifile.readline().split(',')
                    #print line
                    if line[0] == '':
                        break
                ifile.close()
                
                if line[0] == '':
                    raise ArgusError('camera model not found')
                    return
                else:
                    if not '(Fisheye)' in mode:
                        ret = [line[1], line[4], line[5], line[7], line[8], line[9], line[10], line[11]]
                        try:
                            ret = map(float, ret)
                            self.coefficients = ret
                        except:
                            raise ArgusError('distortion profile contains non-numbers...')
                            return
                    else:
                        try:
                            ret = map(float, line[1:])
                            self.coefficients = ret
                        except:
                            raise ArgusError('distortion profile contains non-numbers...')
                    return ret
            else:
                raise ArgusError('no mode or model specified')
        else:
            return self.coefficients

    def get_undistorter(self):
        if not self.coefficients is None:
            if len(self.coefficients) == 8:
                return Undistorter(coefficients = self.coefficients)
            else:
                return Undistorter(omni = self.coefficients)
        else:
            raise ArgusError('must specify distortion coefficients using get_coefficients or set_coefficients')

    def get_ocam_undistorter(self):
        if not self.coefficients is None:
            if len(self.coefficients) > 8:
                ret = argus.ocam.PointUndistorter(argus.ocam.ocam_model.from_array(np.array(self.coefficients)))
                print type(ret)
                return ret
            else:
                raise ArgusError('distortion coefficients specified are not omnidirectional')
        else:
            raise ArgusError('no distortion coefficients specified')

    def set_coefficients(self, coefficients):
        if ((type(coefficients) == list) or (type(coefficients) == np.ndarray)) and len(coefficients) >= 8:
            self.coefficients = coefficients
        else:
            raise ArgusError('inputted coefficients must be of iterable type and of length >= 8. See documentation.')

    def get_cam_profile(self, ncams):
        if not self.coefficients is None:
            return np.array([self.coefficients for k in range(ncams)])
        else:
            raise ArgusError('must specify distortion coefficients using get_coefficients or set_coefficients')

            
            
            

    


    

    

    
