#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import os
import subprocess
import sys

import cv2
import numpy as np
import scipy
import scipy.io.wavfile
import scipy.signal
from moviepy.config import get_setting
from six.moves import range
from texttable import *


class Syncer:
    def __init__(self, tmpName, start, end, crop, onam, n, files, out):
        self.tmpName = tmpName
        self.start = start
        self.end = end
        self.crop = crop
        n = n
        self.files = files
        self.oname = onam
        self.out = out

    def find_offset(self, signal0, signal1, audio_sample_rate=48000., video_fps=30.):
        """
        Finds the offset between two audio signals using fftconvolve to
        do the auto- and cross-correlations.  The signals are assumed to be
        mono and the audio sample rate and video fps must be known.
        """
        corr01 = scipy.signal.fftconvolve(signal0, signal1[::-1], mode="full")
        corr00 = scipy.signal.fftconvolve(signal0, signal0[::-1], mode="valid")
        corr11 = scipy.signal.fftconvolve(signal1, signal1[::-1], mode="valid")
        lag = corr01.argmax()
        maxcorr = np.nanmax(corr01) / ((corr00 ** 0.5) * (corr11 ** 0.5))
        offset_samples = int(len(corr01) / 2) - lag
        offset_seconds = float(offset_samples) / float(audio_sample_rate)
        offset_frames = float(offset_samples) / float(audio_sample_rate) \
                        * float(video_fps)
        integer_offset = int(np.round(offset_frames))
        return offset_seconds, offset_frames, integer_offset, maxcorr[0]

    def getSec(self, s):
        return 60. * float(s)

    def sync(self):
        tmpName = self.tmpName
        files = list(self.files)
        out = list(self.out)
        signals = list()
        # fps = VideoFileClip(files[0]).fps
        fps = float(cv2.VideoCapture(files[0]).get(cv2.CAP_PROP_FPS))
        if self.crop:
            print('Using sound from ' + self.start + ' to ' + self.end)
            sys.stdout.flush()
        for k in range(0, len(files)):
            # If no wav with the same name as the file is found, rip one with moviepy's ffmpeg binary
            if not os.path.isfile(tmpName + '/' + out[k]):
                print('Ripping audio from file number ' + str(k + 1) + '...')
                sys.stdout.flush()
                cmd = [
                    get_setting("FFMPEG_BINARY"),
                    '-loglevel', 'panic',
                    '-hide_banner',
                    '-i', files[k],
                    '-ac', '1',
                    '-codec', 'pcm_s16le',
                    tmpName + '/' + out[k]
                ]
                print(f"making cached sound file with {cmd}")
                subprocess.call(cmd)

            else:
                print('Found audio from file number ' + str(k + 1) + '...')
                sys.stdout.flush()
            # Make a list of signals
            rate, signal = scipy.io.wavfile.read(tmpName + '/' + out[k])
            # If the user specifies a time interval, only use that, else use the whole signal
            if self.crop:
                signals.append(
                    signal[int(np.round(self.getSec(self.start) * 48000)):int(np.round(self.getSec(self.end) * 48000))])
            else:
                signals.append(signal)
        sig0 = signals[0]
        offsets = list()
        for k in range(1, len(signals)):
            print('Finding offset number ' + str(k) + ' of ' + str(len(signals) - 1) + '...')
            sys.stdout.flush()
            offsets.append(self.find_offset(sig0, signals[k], video_fps=fps))
        signals, sig0 = None, None
        # Use texttable module to display results
        table = Texttable()
        table.header(['Number', 'Offset in seconds', 'Offset in video frames', 'Max correlation'])
        for k in range(len(offsets)):
            r = [str(k + 1), str(offsets[k][0]), str(offsets[k][1]), str(offsets[k][3])]
            table.add_row(r)
        print(table.draw())
        if self.oname != '':
            fo = open(self.oname, 'w')
            fo.write("Filename,second_offset,frame_offset,max_correlation\n")
            fo.write(self.files[0].split('/')[-1] + ',' + '0.0,0.0,1.0\n')
            for k in range(1, len(files)):
                fo.write(self.files[k].split('/')[-1] + ',' + str(offsets[k - 1][0]) + ',' + str(
                    offsets[k - 1][1]) + ',' + str(offsets[k - 1][3]) + '\n')
            fo.close()
