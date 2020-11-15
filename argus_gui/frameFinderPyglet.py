#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import copy

import cv2
import numpy as np
from pykalman import KalmanFilter
from scipy.interpolate import RectBivariateSpline
from scipy.optimize import fmin_tnc
from scipy.signal import correlate2d
from six.moves import range


def acceptable(contour, llimit=0., blimit=720.):
    m = cv2.moments(contour)
    if float(m['m00']) > 0:
        result = (float(m['m10']) / float(m['m00']) >= float(llimit)) and \
                 (float(m['m01']) / float(m['m00']) <= float(blimit))
    else:
        result = True
    return result


# gets frames from a movie file with OpenCV and formats them to Pyglet's liking.
class FrameFinder:
    def __init__(self, ifile, width=640, height=480, factor=2, offset=0, rgb=True, background_subtract=False):
        self.file = ifile
        self.movie = cv2.VideoCapture(self.file)
        self.width = width
        self.height = height
        self.current = 0
        self.offset = offset
        self.x = 0
        self.y = 0
        self.w = int(self.movie.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.h = int(self.movie.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.ow = int(self.movie.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.oh = int(self.movie.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frameCount = int(self.movie.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_rate = self.movie.get(cv2.CAP_PROP_FPS)
        self.frame_msec = 1000. / self.frame_rate
        self.factor = factor
        self.kalman_observations = None
        self.kf = None
        self.v = None
        self.rgb = rgb
        self.image = None
        self.track_image = None
        self.background_subtract = background_subtract
        # self.fgbg = cv2.createBackgroundSubtractorMOG2(detectShadows = False, history = 2)
        # self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3))

    # update the part of the image that we're viewing for zooming purposes
    def update(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    # get a specific frame. uses new method of specifying time in ms. very fast.
    def getFrame(self, n, mode='pygame', bgs=None):
        if self.image is not None:
            if self.image[0] == n:
                im = copy.copy(self.image[1])
                if mode == 'pygame':
                    return self.format(im)
        if n - 1 + self.offset >= 0 and n - 1 + self.offset <= self.frameCount - 1:
            self.movie.set(cv2.CAP_PROP_POS_MSEC, (n - 1 + self.offset) * self.frame_msec)
            # self.movie.set(cv2.CAP_PROP_POS_FRAMES, (n-1 + self.offset))
            retval, im = self.movie.read()
            self.image = [n, copy.copy(im)]
            if retval:
                self.current = n
                if mode == 'pygame':
                    return self.format(im)
                else:
                    return im
        else:
            return None

    def capture(self, folder):
        im = self.getFrame(self.current, mode='whatever')
        cv2.imwrite(folder + '/' + str(self.current) + '.jpg', im)

    def toggleBackGroundSubtract(self):
        if self.background_subtract:
            self.background_subtract = False
            # self.fgbg = cv2.createBackgroundSubtractorMOG2(detectShadows = False)
        else:
            self.fgbg = cv2.createBackgroundSubtractorMOG2()
            self.movie.set(cv2.CAP_PROP_POS_MSEC, (self.current - 4 + self.offset) * self.frame_msec)
            # self.movie.set(cv2.CAP_PROP_POS_FRAMES, (self.current - 4 + self.offset))
            retval, im = self.movie.read()
            if retval:
                self.fgbg.apply(im)
            self.background_subtract = True

    def makeKalman(self, pts):
        Transition_Matrix = [[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]]
        Observation_Matrix = [[1, 0, 0, 0], [0, 1, 0, 0]]

        xinit = pts[0, 0]
        yinit = pts[0, 1]
        vxinit = pts[1, 0] - pts[0, 0]
        vyinit = pts[1, 1] - pts[0, 1]
        initstate = [xinit, yinit, vxinit, vyinit]
        initcovariance = 1.0e-3 * np.eye(4)
        transistionCov = 1.0e-4 * np.eye(4)
        observationCov = 1.0e-1 * np.eye(2)
        self.kf = KalmanFilter(transition_matrices=Transition_Matrix,
                               observation_matrices=Observation_Matrix,
                               initial_state_mean=initstate,
                               initial_state_covariance=initcovariance,
                               transition_covariance=transistionCov,
                               observation_covariance=observationCov)
        self.means, self.covariances = self.kf.filter(pts)
        self.v = self.means[-1][2:]
        # print 'velocity: ' + str(self.v)

    def update_kalman(self, pt):
        next_mean, next_covariance = self.kf.filter_update(self.means[-1], self.covariances[-1], pt)
        self.v = next_mean[2:]
        self.means = np.vstack((self.means, next_mean))
        self.covariances = np.vstack((self.covariances, np.reshape(next_covariance, (1, 4, 4))))

        # print 'defined means and covariances'

    def destroy_kalman(self):
        # TODO come back and actually destory kalman
        self.kf = None
        self.means = None
        self.covariances = None
        self.v = None

    def predict(self, pt):
        # print 'predicting'
        return pt + self.v

    # format for Pyglet. Changes BGR to RGB, flips, rotates, then resizes 
    def format(self, image, size=None, bgs=None):
        if bgs is None:
            bgs = self.background_subtract

        if bgs:
            image = self.fgbg.apply(image)
            # image = cv2.morphologyEx(image, cv2.MORPH_OPEN, self.kernel)
        # pickle.dump(image, open("im.pkl", "wb"))

        # flip
        cv2.flip(image, 1, image)
        # BGR to RGB

        if not bgs:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        # rotate 180
        image = np.rot90(image)
        image = np.rot90(image)
        if len(image) != 0:
            if size is None:
                image = cv2.resize(image, (int(float(self.ow) / self.factor), int(float(self.oh) / self.factor)))
            else:
                image = cv2.resize(image, size)
            if (self.rgb or bgs):
                return image
            else:
                return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            return None

    def getColor(self, pt):
        return self.movie.read()[1][int(self.oh - (np.round(pt[1]))), int(np.round(pt[0]))]

    def getViewFinder(self, n, x, y, wx, wy, wf, auto_tracking=False):
        y = int(np.round(y))
        x = int(np.round(x))
        if auto_tracking and self.ro is not None:
            return self.format(copy.copy(self.ro), size=(wf * wy, wf * wx))
        if self.image is not None:
            if self.image[0] == n:
                im = copy.copy(self.image[1])
                if (y - wy >= 0) and (y + wy < im.shape[0]) and (x - wx >= 0) and (x + wx < im.shape[1]):
                    return self.format(im[y - wy: y + wy, x - wx: x + wx], size=(wf * wx, wf * wy), bgs=False)
                else:
                    return None
        if n - 1 + self.offset >= 0 and n - 1 + self.offset <= self.frameCount - 1:
            self.movie.set(cv2.CAP_PROP_POS_MSEC, (n - 1 + self.offset) * self.frame_msec)
            # print('using frame number')
            # self.movie.set(cv2.CAP_PROP_POS_FRAMES, (n - 1 + self.offset))

            retval, im = self.movie.read()
            if retval:
                self.current = n
                if (y - wy >= 0) and (y + wy < im.shape[0]) and (x - wx >= 0) and (x + wx < im.shape[1]):
                    return self.format(im[y - wy: y + wy, x - wx: x + wx], size=(wf * wx, wf * wy), bgs=False)

    # contour blob tracker
    def blobTrack(self, trackingColors):
        # find a contour with one standard deviation of the mean color marked by the user
        trackingColors = np.asarray(trackingColors)
        minc = np.mean(trackingColors, axis=0) - np.std(trackingColors, axis=0)
        maxc = np.mean(trackingColors, axis=0) + np.std(trackingColors, axis=0)
        # get the current frame
        im = self.getFrame(self.current, mode='whateber')
        if im is not None:
            # crop the image to the part the user is zoomed into
            y = self.oh - (self.y + self.h)
            im = im[y: y + self.h, self.x:self.x + self.w]

            MIN = cv2.cv.Scalar(minc[0], minc[1], minc[2])
            MAX = cv2.cv.Scalar(maxc[0], maxc[1], maxc[2])
            im = cv2.inRange(im, MIN, MAX)

            # find some contours10
            contours, _ = cv2.findContours(im, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
            scontours = sorted(contours, key=lambda c: cv2.moments(c)['m00'], reverse=True)
            if len(scontours) != 0:
                biggest = scontours[0]
            else:
                return np.asarray([np.nan, np.nan])
            moments = cv2.moments(biggest)
            if float(moments['m00']) != 0.:
                xc = float(moments['m10']) / float(moments['m00'])
                yc = float(moments['m01']) / float(moments['m00'])

                return np.asarray([xc + self.x, self.oh - (yc + y)])
            else:
                return np.asarray([np.nan, np.nan])
        else:
            return np.asarray([np.nan, np.nan])

    def cv2Track(self, x, y, wx, wy):
        x = int(np.round(x))
        y = int(np.round(y))

        frame = self.getFrame(self.current, mode='whateber')
        track_window = (x, y, wx, wy)
        # print track_window
        # set up the ROI for tracking
        roi = frame[y:y + wy, x:x + wx]
        # cv2.imwrite('test_{0}.png'.format(self.current), roi)
        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv_roi, np.array((0., 10., 25.)), np.array((180., 255., 255.)))
        roi_hist = cv2.calcHist([hsv_roi], [0], mask, [180], [0, 180])
        cv2.normalize(roi_hist, roi_hist, 0, 255, cv2.NORM_MINMAX)

        term_crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 1)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        dst = cv2.calcBackProject([hsv], [0], roi_hist, [0, 180], 1)

        # apply meanshift to get the new location
        ret, track_window = cv2.meanShift(dst, track_window, term_crit)
        # print track_window
        return np.array([track_window[0] + 0.5 * track_window[2], self.oh - track_window[1] - track_window[3] * 0.5])

    def CrossTrack(self, x, y, wx, wy):
        u = int(np.round(x))
        v = int(np.round(y))

        # print 'initial guess: {0},{1}'.format(x + 0.5*wx, (self.oh - (y + wy*0.5)))

        n = self.current

        if self.track_image is None:
            self.track_image = [n - 1, self.getFrame(n - 1, mode='whateber')]

        if not (self.image is None):
            if self.image[0] == n:
                frame_next = copy.copy(self.image[1])
            else:
                frame_next = self.getFrame(n, mode='whateber')
        else:
            frame_next = self.getFrame(n, mode='whateber')

        if self.background_subtract:
            ro = self.fgbg.apply(copy.copy(self.track_image[1]))[v:v + wy, u:u + wx].astype(float)
        else:
            ro = self.track_image[1][v:v + wy, u:u + wx]

        # self.ro = copy.copy(ro)

        if self.v is not None:
            # print 'adjusting...'
            u = int(np.round(x + self.v[0]))
            v = int(np.round(y - self.v[1]))
            y -= self.v[1]
            x += self.v[0]

        self.ro = copy.copy(frame_next[v:v + wy, u:u + wx])

        if self.background_subtract:
            roi = self.fgbg.apply(copy.copy(frame_next))[v:v + wy, u:u + wx].astype(float)
        else:
            roi = frame_next[v:v + wy, u:u + wx]

        if len(ro.shape) == 3:
            ro = ro - np.mean(ro)
            roi = roi - np.mean(roi)

            b1, g1, r1 = cv2.split(ro)
            b2, g2, r2 = cv2.split(roi)

            corr_b = correlate2d(b1, b2, boundary='symm', mode='same')
            corr_g = correlate2d(g1, g2, boundary='symm', mode='same')
            corr_r = correlate2d(r1, r2, boundary='symm', mode='same')

            corr = corr_b + corr_g + corr_r
        else:
            corr = correlate2d(ro, roi, boundary='symm', mode='same')

        oy, ox = np.unravel_index(np.argmax(corr), corr.shape)

        # mark discrete estimate with red square
        self.ro[oy, :] = np.array([0., 0., 255.])
        self.ro[:, ox] = np.array([0., 0., 255.])

        # get continuous estimate
        s = RectBivariateSpline(list(range(corr.shape[0])), list(range(corr.shape[1])), -corr)
        sol, nfeval, rc = fmin_tnc(lambda x: np.squeeze(s(x[0], x[1])), np.array([float(oy), float(ox)]), approx_grad=True,
                                   bounds=[(0., float(corr.shape[0])), (0., float(corr.shape[1]))], disp=0)

        oy, ox = sol

        oy = oy - (ro.shape[0] / 2 - 1)
        ox = -(ox - (ro.shape[1] / 2 - 1))

        # print 'offset: {0},{1}'.format(ox, oy)

        self.track_image = [n, frame_next]

        return np.array([x + 0.5 * wx + ox, (self.oh - (y + wy * 0.5)) + oy])
