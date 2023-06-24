#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  8 00:34:46 2015

@author: Dylan Ray and Dennis Evangelista
University of North Carolina at Chapel Hill
Hedrick Lab
"""

from __future__ import absolute_import
from __future__ import print_function

import shutil
import subprocess
import tempfile

import argus.ocam
import cv2
import numpy as np
import pkg_resources
from moviepy.config import get_setting
from moviepy.editor import *
from six.moves.tkinter import *

from argus_gui import ArgusError

if sys.platform == 'win32':
    from signal import signal, SIG_DFL
else:
    from signal import signal, SIGPIPE, SIG_DFL

    signal(SIGPIPE, SIG_DFL)

from PIL import Image
from subprocess import Popen, PIPE

RESOURCE_PATH = os.path.abspath(pkg_resources.resource_filename('argus_gui.resources', ''))


def array2image(a):
    mode = "L"
    return Image.frombytes(mode, (a.shape[1], a.shape[0]), a.tostring())


"""
Undistorter
Takes a video and undistorts it frame-by-frame given a set of pinhole or omnidirectional distortion coefficient
"""


class Undistorter(object):
    # Take the parameters passed from the GUI.
    def __init__(self, fnam=None, omni=None, coefficients=None, CMei=False, copy=False):
        self.infilename = fnam

        if not fnam is None and fnam != '':
            self.set_movie(fnam, copy=copy)
        else:
            self.movie = None

        if (not omni is None) and (omni != ''):
            self.set_omnidirectional(omni)
        elif CMei:
            self.set_omnidirectional(coefficients)
        else:
            self.oCamUndistorter = None
            self.omni = omni

        self.coefficients = coefficients
        self.copy_tmp = None

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
        cM = np.array([[line[0], 0.0, line[1]],
                       [0.0, line[0], line[2]], [0.0, 0.0, 1.0]])
        dC = np.array([line[3], line[4], line[5], line[6], line[7]])
        return cM, dC

    def set_omnidirectional(self, omni):
        try:
            if len(omni) > 13:
                print('Making Omnidirectional mapping...')
                sys.stdout.flush()
                # self.omni = map(float, self.omni.split(',')[:])
                model = argus.ocam.ocam_model(omni[0], int(omni[1]), int(omni[2]), c=omni[3], d=omni[4], e=omni[5],
                                              xc=omni[6], yc=omni[7], pol=np.array(omni[13:]))
                self.oCamUndistorter = argus.ocam.Undistorter(model)
                self.omni = omni
            else:
                model = argus.ocam.CMei_model.from_array(np.array(omni))
                self.oCamUndistorter = argus.ocam.CMeiUndistorter(model)
                self.omni = omni
        except:
            raise ArgusError(
                'could not make omnidirectional undistorter object. make sure the omnidirectional coefficients were provided according to the documentation')

    def get_mappings(self, crop):
        R = np.eye(3)
        cM, dC = self.calibParse()

        osize = ((int(self.movie.get(cv2.CAP_PROP_FRAME_WIDTH)),
                  int(self.movie.get(cv2.CAP_PROP_FRAME_HEIGHT))))

        newsize = ((int(self.movie.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    int(self.movie.get(cv2.CAP_PROP_FRAME_HEIGHT))))
        if crop:
            # Do it the old way
            newcM = cM
        else:
            # Do it Hedrick's way
            newcM, roi = cv2.getOptimalNewCameraMatrix(cM, dC, osize, 1, newsize)

        map1, map2 = cv2.initUndistortRectifyMap(cM, dC, R, newcM, newsize, cv2.CV_32FC1)
        return map1, map2

    def set_movie(self, fnam, copy=False):
        if copy:
            self.copy_tmp = tempfile.mkdtemp()
            cmd = [
                get_setting("FFMPEG_BINARY"),
                '-loglevel', 'panic',
                '-hide_banner',
                '-i', fnam,
                '-acodec', 'copy',
                '-vcodec', 'copy',
                os.path.join(self.copy_tmp, 'copy.mp4')]
            print('Copying video and audio codecs...')
            sys.stdout.flush()

            subprocess.call(cmd)

            print('Copy completed...')

            self.movie = cv2.VideoCapture(os.path.abspath(os.path.join(self.copy_tmp, 'copy.mp4')))
            print('Using movie at {0}'.format(os.path.join(self.copy_tmp, 'copy.mp4')))
        else:
            self.movie = cv2.VideoCapture(os.path.abspath(fnam))
            print('Using movie at ' + fnam)
        self.infilename = fnam

        try:
            self.frameCount = int(self.movie.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = float(self.movie.get(cv2.CAP_PROP_FPS))
            self.w = int(self.movie.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.h = int(self.movie.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.frame_msec = 1000. / self.fps
            return self.fps, self.frameCount
        except:
            raise ArgusError('could not read specified movie')

    # The meat and potatoes
    def undistort_movie(self, ofnam=None, frameint=25, crf=12, write=True, display=True, tmp_dir=None, crop=False):
        if self.movie is None:
            raise ArgusError('no movie specified')

        if (self.omni is None) and (self.coefficients is None):
            raise ArgusError('no distortion coefficients specified')

        if tmp_dir is None:
            tmp = tempfile.mkdtemp()
        else:
            tmp = tmp_dir

        print(tmp)

        print('Ripping audio... \n')
        sys.stdout.flush()
        cmd = [
            get_setting("FFMPEG_BINARY"),
            '-loglevel', 'panic',
            '-hide_banner',
            '-i', self.infilename,
            '-c:a', 'copy',
            '-vn', '-sn',
            tmp + '/' + 'temp.m4a']
        subprocess.call(cmd)

        if os.path.exists(tmp + '/' + 'temp.m4a'):
            statinfo = os.stat(tmp + '/' + 'temp.m4a')

            if statinfo.st_size != 0:
                audio = tmp + '/' + 'temp.m4a'
            else:
                audio = None
        else:
            audio = None

        if audio is not None:
            cmd = [get_setting("FFMPEG_BINARY"), '-y', '-f', 'rawvideo', '-thread_queue_size', '32',\
                   '-vcodec', 'rawvideo', '-s', '{0}x{1}'.format(self.w, self.h), \
                   '-r', str(self.fps), '-i', '-', '-i', audio, \
                   '-acodec', 'copy', '-vcodec', 'libx264', '-preset', 'medium', '-crf', \
                   str(crf), '-g', str(frameint), '-profile:v', 'baseline', '-threads', \
                   '0', '-pix_fmt', 'yuv420p', str(ofnam)]
        else:
            cmd = [get_setting("FFMPEG_BINARY"), '-y', '-f', 'rawvideo', '-thread_queue_size', '32',\
                   '-vcodec', 'rawvideo', '-s', '{0}x{1}'.format(self.w, self.h), \
                   '-r', str(self.fps), '-i', '-', '-an', \
                   '-acodec', 'copy', '-vcodec', 'libx264', '-preset', 'medium', '-crf', \
                   str(crf), '-g', str(frameint), '-profile:v', 'baseline', '-threads', \
                   '0', '-pix_fmt', 'yuv420p', str(ofnam)]

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

        print('Beginning to undistort images and compile with FFMPEG...')
        sys.stdout.flush()
        print(cmd)
        p = Popen(cmd, stdin=PIPE)

        if display:
            if 'linux' in sys.platform:
                cv2.imshow("Undistorted", np.zeros((1080, 1920, 3)))
            cv2.namedWindow("Undistorted")

        if write:
            # Create a list of the frames (pngs)
            fileList = []
        k = 1

        if display:
            if not 'linux' in sys.platform:
                cv2.startWindowThread()

        for a in range(int(self.movie.get(cv2.CAP_PROP_FRAME_COUNT))):
            retval, raw = self.movie.read()

            if retval:
                previous = raw
                if crop:
                    if self.oCamUndistorter is None:
                        undistorted = cv2.remap(raw, map1, map2, cv2.INTER_LINEAR)
                    else:
                        undistorted = self.oCamUndistorter.undistort_frame(raw)
                else:
                    if self.oCamUndistorter is None:
                        undistorted = cv2.remap(raw, map1, map2,
                                                interpolation=cv2.INTER_CUBIC,
                                                borderMode=cv2.BORDER_CONSTANT,
                                                borderValue=(211, 160, 86))
                    else:
                        undistorted = self.oCamUndistorter.undistort_frame(raw)

                if display:
                    cv2.imshow('Undistorted', cv2.resize(undistorted, (0, 0), fx=0.5, fy=0.5))
                    cv2.waitKey(1)
                undistorted = cv2.cvtColor(undistorted, cv2.COLOR_BGR2RGB)

                # im = Image.fromarray(undistorted, 'RGB')
                # im.save(p.stdin, 'PNG')

                if write:
                    p.stdin.write(undistorted.tostring())

                # line of code above allows you to open video clip after it is saved
                # without that line video clip will save but won't be able to open and play clip

                variable = False
                self.root = Tk()

                def __init__(self, master, title):
                    top = self.top = Toplevel(master)
                    top.resizable(width=FALSE, height=FALSE)
                    top.bind('<Return>', self.cleanup)
                    self.l = Label(top, text=title)
                    self.l.pack(padx=10, pady=10)
                    self.e = Entry(top)
                    self.e.focus_set()
                    self.e.pack(padx=10, pady=5)
                    self.b = Button(top, text='Ok', padx=10, pady=10)
                    self.b.bind('<Button-1>', self.cleanup)
                    self.b.pack(padx=5, pady=5)
                    self.crop = StringVar(self.root)
                    self.copy = StringVar(self.root)

                self.wrdispboth = IntVar(self.root)

                if a % 5 == 0:
                    print('\n', end='')
                    sys.stdout.flush()
                """
                # Write the individual frame as a png to the temporary directory
                if write:
                    cv2.imwrite(tmp + '/' + str(a) + '.png', undistorted)
                    fileList.append(tmp + '/' + str(a) + '.png')
                """
            else:
                if write:
                    print("Could not read frame number: " + str(a) + "\n writing blank frame")
                    p.stdin.write(np.zeros_like(previous).tostring())
                    sys.stdout.flush()
                else:
                    print("Could not read frame number: " + str(a))
                    sys.stdout.flush()

        p.stdin.close()
        p.wait()

        print('Undistortion finished')
        if write:
            print('Wrote mp4 to {0}'.format(ofnam))
        sys.stdout.flush()
        # Destroy movie object and the window if it was even created
        movie = None
        if display:
            cv2.waitKey(1)
            cv2.destroyAllWindows()
            cv2.waitKey(1)
        if write:
            # clip = ImageSequenceClip(fileList, fps=self.fps, with_mask = False, load_images = False)

            # Write the mp4 file
            """
            if os.path.exists(tmp + '/' + 'temp.m4a'):
                clip.write_videofile(ofnam, fps=self.fps, audio = tmp + '/' + 'temp.m4a', audio_fps = 48000, codec='libx264', threads=0, ffmpeg_params = ['-crf', str(crf), '-g', str(frameint), '-pix_fmt', 'yuv420p', '-profile' ,'baseline'])
            else:
                print('No audio stream found, writing without...')
                clip.write_videofile(ofnam, fps=self.fps, audio_fps = 48000, codec='libx264', threads=0, ffmpeg_params = ['-crf', str(crf), '-g', str(frameint), '-pix_fmt', 'yuv420p', '-profile' ,'baseline'])
            """
            sys.stdout.flush()
            clip = None

            # Destroy the temporary directory
            shutil.rmtree(tmp)
            if self.copy_tmp is not None:
                shutil.rmtree(self.copy_tmp)

    def undistort_frame(self, frame, ofile=None, crop=False):
        if self.movie is None:
            raise ArgusError('no movie specified')
            return
        if (self.omni is None) and (self.coefficients is None):
            raise ArgusError('no distortion profile provided, Argus cannot undistort')
            return

        if not self.coefficients is None:
            map1, map2 = self.get_mappings(crop)

        if 0 <= frame - 1 <= self.frameCount - 1:
            self.movie.set(cv2.CAP_PROP_POS_MSEC, (frame - 1) * self.frame_msec)
            retval, raw = self.movie.retrieve()
            if retval:
                if crop:
                    if self.oCamUndistorter is None:
                        undistorted = cv2.remap(raw, map1, map2, cv2.INTER_LINEAR)
                    else:
                        undistorted = self.oCamUndistorter.undistort_frame(raw)
                else:
                    if self.oCamUndistorter is None:
                        undistorted = cv2.remap(raw, map1, map2,
                                                interpolation=cv2.INTER_CUBIC,
                                                borderMode=cv2.BORDER_CONSTANT,
                                                borderValue=(211, 160, 86))
                    else:
                        undistorted = self.oCamUndistorter.undistort_frame(raw)
                if not ofile is None:
                    cv2.imwrite(ofile, undistorted)
                return undistorted
            else:
                raise ArgusError('Argus could not read specified frame')
        else:
            raise ArgusError('frame out of bounds')

    def undistort_array(self, array, ofile=None, crop=False):
        if (self.omni is None) and (self.coefficients is None):
            raise ArgusError('no distortion profile provided, Argus cannot undistort')
            return

        if not self.coefficients is None:
            map1, map2 = self.get_mappings(crop)

        raw = array
        if crop:
            if self.oCamUndistorter is None:
                undistorted = cv2.remap(raw, map1, map2, cv2.INTER_LINEAR)
            else:
                undistorted = self.oCamUndistorter.undistort_frame(raw)
        else:
            if self.oCamUndistorter is None:
                undistorted = cv2.remap(raw, map1, map2,
                                        interpolation=cv2.INTER_CUBIC,
                                        borderMode=cv2.BORDER_CONSTANT,
                                        borderValue=(211, 160, 86))
            else:
                undistorted = self.oCamUndistorter.undistort_frame(raw)
        if not ofile is None:
            cv2.imwrite(ofile, undistorted)
        return undistorted


class DistortionProfile(object):
    def __init__(self, model=None, mode=None):
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

    def get_coefficients(self, model=None, mode=None):
        if self.coefficients is None:
            if ((not model is None) and (not mode is None)):
                fnam = self.models[model]
                ifile = open(fnam, "r")
                # print 'Getting coefficients'

                line = ifile.readline().split(',')
                while line[0] != mode:
                    line = ifile.readline().split(',')
                    # print line
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
                            ret = list(map(float, ret))
                            self.coefficients = ret
                        except:
                            raise ArgusError('distortion profile contains non-numbers...')
                            return
                    else:
                        try:
                            ret = list(map(float, line[1:]))
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
                return Undistorter(coefficients=self.coefficients)
            else:
                return Undistorter(omni=self.coefficients)
        else:
            raise ArgusError('must specify distortion coefficients using get_coefficients or set_coefficients')

    def get_ocam_undistorter(self):
        if not self.coefficients is None:
            if len(self.coefficients) > 8:
                ret = argus.ocam.PointUndistorter(argus.ocam.ocam_model.from_array(np.array(self.coefficients)))
                print(type(ret))
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
