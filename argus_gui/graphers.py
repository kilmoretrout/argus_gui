#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

from mpl_toolkits.mplot3d import Axes3D
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.mplot3d import proj3d
# import wandOutputter
from .output import *
import pandas
import sys

from numpy import *
import scipy.signal
import scipy.io.wavfile
import scipy
import sys
import os.path
import matplotlib.pyplot as plt
from moviepy.config import get_setting
import matplotlib.patches as mpatches
import random
from .colors import *
import subprocess
from .tools import *


# class that plots n wave files for the user to choose a time interval
class Shower():
    def __init__(self, tmpName, files, out):
        # temporary directory location
        self.tmpName = tmpName
        # actual wave file names
        self.files = files
        # expected temporary file names
        self.out = out

    def show(self):
        # Colors for plotting
        colors = ArgusColors().getMatplotlibColors()
        # Shuffle to make things interesting
        random.shuffle(colors)
        for k in range(len(self.files)):
            # If we don't find a wav with the same name as the file, rip one using moviepy's ffmpeg binary
            if not os.path.isfile(self.tmpName + '/' + self.out[k]):
                print('Ripping audio from file number ' + str(k + 1) + ' of ' + str(len(self.files)))
                sys.stdout.flush()
                cmd = [
                    get_setting("FFMPEG_BINARY"),
                    '-loglevel', 'panic',
                    '-hide_banner',
                    '-i', self.files[k],
                    '-ac', '1',
                    '-codec', 'pcm_s16le',
                    self.tmpName + '/' + self.out[k]
                ]
                subprocess.call(cmd)
            else:
                print('Found audio from file number ' + str(k + 1) + ' of ' + str(len(self.files)))
                sys.stdout.flush()
        # Put the full signals in a list
        signals_ = list()
        print('Reading waves and displaying...')
        sys.stdout.flush()
        for k in range(len(self.files)):
            rate, signal = scipy.io.wavfile.read(self.tmpName + '/' + self.out[k])
            signals_.append(signal)
        # Make a new list of signals but only using ever 100th sample
        signals = list()
        for k in range(len(signals_)):
            t = list()
            a = 0
            while a < len(signals_[k]):
                t.append(signals_[k][a])
                a += 100
            signals.append(np.asarray(t))
        a = 0
        patches = list()
        width = 35
        height = 3 * len(signals)
        plt.figure(figsize=(width, height))
        frame1 = plt.gca()
        frame1.axes.get_yaxis().set_visible(False)
        # Make a plot with colors chosen by circularly pulling from the colors vector
        for k in range(len(signals)):
            color = colors[k % len(colors)]
            patches.append(mpatches.Patch(color=color, label=self.files[k].split('/')[-1]))
            t = np.linspace(0, len(signals_[k]) / 48000., num=len(signals[k])) / 60.
            plt.plot(t, signals[k] + float(a), color=color)
            a += np.nanmax(signals[k]) * 2
        plt.legend(handles=patches)
        plt.title('Audio Streams')
        plt.xlabel('Minutes')
        signals_ = None
        plt.show()


# Input: expects Nx3 matrix of points
# Returns R,t
# R = 3x3 rotation matrix
# t = 3x1 column vector
# returns the estimated translation and rotation matrix for a rigid transform from one set of points to another.
# used to transform points based on specified axis directions
def rigid_transform_3D(A, B):
    assert len(A) == len(B)

    N = A.shape[0];  # total points

    centroid_A = mean(A, axis=0)
    centroid_B = mean(B, axis=0)

    # centre the points
    AA = A - tile(centroid_A, (N, 1))
    BB = B - tile(centroid_B, (N, 1))

    # dot is matrix multiplication for array
    H = transpose(AA).dot(BB)

    U, S, Vt = linalg.svd(H)

    R = Vt.T.dot(U.T)

    # special reflection case
    if linalg.det(R) < 0:
        # print "Reflection detected"
        Vt[2, :] *= -1
        R = Vt.T.dot(U.T)
    t = -R.dot(centroid_A.T) + centroid_B.T

    return R, t


def rotation(a, b):
    # make unit vectors
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    # find cross product and cross product matrix
    v = np.cross(a, b)
    v_x = np.zeros((3, 3))
    v_x[1, 0] = v[2]
    v_x[0, 1] = -v[2]
    v_x[2, 0] = -v[1]
    v_x[0, 2] = v[1]
    v_x[2, 1] = v[0]
    v_x[1, 2] = -v[0]
    s = np.linalg.norm(v)
    c = np.dot(a, b)
    R = np.eye(3) + v_x + np.linalg.matrix_power(v_x, 2) * ((1. - c) / s ** 2)
    return R


# takes unpaired and paired points along with other information about the scene, and manipulates the data for outputting and graphing in 3D
class wandGrapher():
    def __init__(self, key, nppts, nuppts, scale, ref, indices, ncams, npframes, nupframes=None, name=None, temp=None,
                 display=True, uvs=None, nRef=0, order=None, report=True, cams=None):
        self.nppts = nppts
        self.nuppts = nuppts
        self.scale = scale
        self.ref = ref
        self.indices = indices
        self.ncams = ncams
        self.npframes = npframes
        self.nupframes = nupframes
        self.name = name
        self.temp = temp
        self.display = display
        self.uvs = uvs
        self.nRef = nRef
        self.order = order
        self.key = key
        self.report = report
        cams = cams

        self.cams = []

        for c in cams:
            self.cams.append([c[u] for u in [0, 1, 2, 5, 6, 7, 8, 9]])

    # finds the average distance between two point sets
    # used to find the scale defined by the wand
    def averDist(self, pts1, pts2):
        dist = list()
        for k in range(pts1.shape[0]):
            dist.append(np.linalg.norm(pts1[k] - pts2[k]))
        return np.nanmean(np.asarray(dist)), np.nanstd(np.asarray(dist))

    # transform the points with the rigid transform function
    def transform(self, xyzs, ref):
        # Subtract the origin
        t = ref[0]
        ret = xyzs - np.tile(t, (xyzs.shape[0], 1))

        # print(ret.shape)

        # ref = ref - np.tile(t, (ref.shape[0], 1))

        # If we have all three axes:
        if ref.shape[0] == 3:
            A = ref
            A = A - A[0]

            # define an Nx4 matrix containing origin (same in both), a point on the x axis, a point on the y axis, and a point on z
            A = np.vstack((A, np.cross(A[1], A[2]) / np.linalg.norm(np.cross(A[1], A[2]))))

            # define the same points in our coordinate system
            B = np.zeros((4, 3))
            B[1] = np.array([np.linalg.norm(A[1]), 0., 0.])
            B[2] = np.array([0., np.linalg.norm(A[2]), 0.])
            B[3] = np.array([0., 0., 1.])

            # find rotation and translation, translation ~ 0 by definition
            R, t = rigid_transform_3D(A, B)

            # rotate
            ret = R.dot(ret.T).T

            # points in z need to reversed? works as expected if you change the order of the reference points
            ret[:, 2] *= -1

        # If we only have Z:
        elif ref.shape[0] == 2:
            # print('Performing transform...')
            a = (ref[1] - ref[0]) * (1. / np.linalg.norm(ref[1] - ref[0]))

            # Get the current z-axis and the wanted z-axis
            pts1 = np.asarray([[0., 0., 1.]])
            pts2 = np.asarray([a])

            # print pts2.T

            # Get the transform from one to the other
            R = rotation(pts2[0], pts1[0])

            # Perform the transform
            for k in range(ret.shape[0]):
                ret[k] = R.dot(ret[k].T).T

            # print R.dot(pts2.T).T

        # print(ret.shape)
        # If we just have an origin, simply returning the data after the subtracting the orgins ok.
        return ret

    # makes two sets of isomorphic paired points that share the same frame
    def pairedIsomorphism(self, pts):
        # get the length on the indices vector to split the paired points apart
        n1 = len(self.indices['paired'][0])
        n2 = len(self.indices['paired'][1])
        # get the maximum frame number which we found a triangulatable point at
        a = np.max(self.indices['paired'][1])
        b = np.max(self.indices['paired'][0])
        # split the paired points
        p1 = pts[:n1, :]
        p2 = pts[n1:, :]
        b = np.min([a, b])
        set1 = list()
        set2 = list()
        k = 0
        # if two paired points were found at the same frame put them each in the set
        while k <= b:
            if k in self.indices['paired'][0] and k in self.indices['paired'][1]:
                set1.append(p1[self.indices['paired'][0].index(k)])
                set2.append(p2[self.indices['paired'][1].index(k)])
            k += 1
        # return the split paired points as well as the isomorphic sets for drawing wands
        return p1, p2, np.asarray(set1), np.asarray(set2)

    # writes the DLT coefficients to a CSV using pandas
    def outputDLT(self, cos, error):
        print('\nDLT Errors: ')
        print(error)
        sys.stdout.flush()
        dat = np.asarray(cos)
        dat = dat.T[0]

        if self.order is not None:
            dat = dat[:, list(self.order)]

        dat = pandas.DataFrame(dat)
        dat.to_csv(self.name + '-dlt-coefficients.csv', header=False, index=False)

    # solves an overdetermined linear system for DLT coefficients constructed via
    # these instructions: http://kwon3d.com/theory/dlt/dlt.html
    def getCoefficients(self, xyz, uv, cam_index=0):
        # delete rows which have nan

        indices = list(np.where(~np.isnan(uv[:, 0]) == True)[0])

        # print(xyz.shape)
        # print(uv.shape)

        A = np.zeros((len(indices) * 2, 11))

        # construct matrix based on uv pairs and xyz coordinates
        for k in range(len(indices)):
            A[2 * k, :3] = xyz[indices[k]]
            A[2 * k, 3] = 1
            A[2 * k, 8:] = xyz[indices[k]] * -uv[indices[k], 0]
            A[2 * k + 1, 4:7] = xyz[indices[k]]
            A[2 * k + 1, 7] = 1
            A[2 * k + 1, 8:] = xyz[indices[k]] * -uv[indices[k], 1]

        B = np.zeros((len(indices) * 2, 1))

        for k in range(len(indices)):
            B[2 * k] = uv[indices[k], 0]
            B[2 * k + 1] = uv[indices[k], 1]

        # solve using numpy's least squared algorithm
        L = np.linalg.lstsq(A, B)[0]

        # reproject to calculate rmse
        reconsted = np.zeros((len(indices), 2))
        for k in range(len(indices)):
            u = (np.dot(L[:3].T, xyz[indices[k]]) + L[3]) / (np.dot(L[-3:].T, xyz[indices[k]]) + 1.)
            v = (np.dot(L[4:7].T, xyz[indices[k]]) + L[7]) / (np.dot(L[-3:].T, xyz[indices[k]]) + 1.)
            reconsted[k] = [u, v]

        errors = list()
        dof = float(self.ncams * 2 - 3)

        _ = np.power(reconsted - uv[indices], 2)
        _ = _[:, 0] + _[:, 1]
        errors = np.sqrt(_)
        error = np.sum(errors)

        """
        error = 0
        for k in range(len(indices)):
            s = np.sqrt((reconsted[k,0] - uv[indices[k],0])**2 + (reconsted[k,1] - uv[indices[k],1])**2)
            errors.append(s)
            error += s
        """

        # This part finds outliers and there frames
        merr = np.mean(errors)
        stderr = np.std(errors)
        outliers = list()
        ptsi = list()

        # pickle.dump(self.indices['paired'], open('paired.pkl', 'w'))

        if self.indices['paired'] is not None:
            pb_1 = len(self.indices['paired'][0])
        else:
            pb_1 = -1

        if self.indices['unpaired'] is not None:
            upindices = self.indices['unpaired'][0]
            for k in range(1, len(self.indices['unpaired'])):
                upindices = np.hstack((upindices, self.indices['unpaired'][k]))

        for k in range(len(errors)):
            if errors[k] >= 3 * stderr + merr:
                if indices[k] not in ptsi:
                    ptsi.append(indices[k])

                if self.nRef - 1 < indices[k] < pb_1 + self.nRef:
                    # if not self.indices['paired'][0][k] in frames:
                    outliers.append([self.indices['paired'][0][indices[k] - self.nRef] + 1,
                                     redistort_pts(np.array([uv[indices[k]]]), self.cams[cam_index])[0],
                                     'Paired (set 1)', errors[k]])
                    # frames.append(self.indices['paired'][0][k])
                elif pb_1 + self.nRef <= indices[k] < self.nppts + self.nRef:
                    # if not self.indices['paired'][1][k - len(self.indices['paired'][0])] in frames:
                    outliers.append(
                        [self.indices['paired'][1][indices[k] - len(self.indices['paired'][0]) - self.nRef] + 1,
                         redistort_pts(np.array([uv[indices[k]]]), self.cams[cam_index])[0], 'Paired (set 2)',
                         errors[k]])
                    # frames.append(self.indices['paired'][1][k - len(self.indices['paired'][0])])
                elif self.nppts + self.nRef <= indices[k] < self.nuppts + self.nppts + self.nRef:
                    try:
                        # if not upindices[(k - self.nppts)] in frames:
                        i = 0
                        _ = 0

                        while True:
                            if (indices[k] - self.nppts) - self.nRef < len(self.indices['unpaired'][i]) + _:
                                outliers.append([upindices[(indices[k] - self.nppts) - self.nRef] + 1,
                                                 redistort_pts(np.array([uv[indices[k]]]), self.cams[cam_index])[0],
                                                 'Unpaired ', errors[k], i])
                                break
                            else:
                                _ += len(self.indices['unpaired'][i])
                                i += 1
                        # frames.append(upindices[k - self.nppts])
                    except:
                        print('Looking for unpaired indices failed')
                        pass
                else:
                    # print pb1, self.nppts
                    pass

        rmse = error / float(len(errors))

        return L, rmse, outliers, ptsi

    def graph(self):
        # Load the points and camera profile from SBA
        xyzs = np.loadtxt(self.temp + '/' + self.key + '_np.txt')
        cam = np.loadtxt(self.temp + '/' + self.key + '_cn.txt')

        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        qT = cam[:, -7:]
        quats = qT[:, :4]
        trans = qT[:, 4:]

        """
        cameraPositions = list()
        cameraOrientations = list()

        for k in range(quats.shape[0]):
            Q = quaternions.Quaternion(quats[k][0], quats[k][1], quats[k][2], quats[k][3])
            R = Q.asRotationMatrix()

            cameraPositions.append(np.asarray(-R.T.dot(trans[k])))
            cameraOrientations.append(R.T.dot(np.asarray([0,0,np.nanmin(xyzs[:,2])/2.])))

        vP = np.zeros((quats.shape[0], 6))
        for k in range(quats.shape[0]):
            vP[k,:3] = cameraPositions[k]
            vP[k,3:] = cameraPositions[k] + cameraOrientations[k]

        """
        if self.ref:
            ref = xyzs[:self.nRef, :]
            # pickle.dump(xyzs, open('xyzs.pkl', 'w'))
            xyzs = self.transform(xyzs, ref)
            # vP[:,:3] = self.transform(vP[:,:3], ref)
            # vP[:,3:] = self.transform(vP[:,3:], ref)
        else:
            t = np.mean(xyzs, axis=0)
            for k in range(xyzs.shape[0]):
                xyzs[k] = xyzs[k] + t

        # print xyzs[:self.nRef,:]

        # trim off the reference points as we don't wan't to graph them
        # xyzs = xyzs[self.nRef:,:]

        # If we've got paired points, define a scale
        if self.nppts != 0:
            paired = xyzs[self.nRef:self.nppts + self.nRef]

            p1, p2, pairedSet1, pairedSet2 = self.pairedIsomorphism(paired)
            dist, std = self.averDist(pairedSet1, pairedSet2)
            factor = self.scale / dist
            p1 = p1 * factor
            p2 = p2 * factor
        else:
            # else no scale, just arbitrary
            p1, p2 = None, None
            factor = 1.

        errs = list()
        dlts = list()
        outliers = []
        ptsi = []

        camn = 0
        for uv in self.uvs:
            cos, error, outlier, ind = self.getCoefficients(xyzs * factor, uv, camn)
            camn += 1
            outliers = outliers + outlier
            ptsi = ptsi + ind
            # print len(ind)
            # print len(outlier)
            dlts.append(cos)
            errs.append(error)

        dlts = np.asarray(dlts)
        errs = np.asarray(errs)

        # trim off the reference points as we don't wan't to graph them
        xyzs = xyzs[self.nRef:, :]

        # vP = vP*factor
        # x = vP[:,:3][:,0]
        # y = vP[:,:3][:,1]
        # z = vP[:,:3][:,2]

        # ax.scatter(x,y,z)
        if self.nuppts != 0:
            up = xyzs[self.nppts:, :] * factor
            if self.display:
                x = up[:, 0]
                y = up[:, 1]
                z = up[:, 2]
                ax.scatter(x, y, z)
        else:
            up = None

        # plot the paired points if there are any. draw a line between each paired set.
        if self.nppts != 0 and self.display:
            ax.set_xlabel('X (Meters)')
            ax.set_ylabel('Y (Meters)')
            ax.set_zlabel('Z (Meters)')
            for k in range(len(pairedSet1)):
                _ = np.vstack((pairedSet1[k] * factor, pairedSet2[k] * factor))
                x = _[:, 0]
                y = _[:, 1]
                z = _[:, 2]
                ax.plot(x, y, z)

        self.outputDLT(dlts, errs)

        if self.nppts != 0:
            print('\nWand score: ' + str(100. * (std / dist)))
            sys.stdout.flush()
        else:
            print('\nWand score: not applicable')

        sys.stdout.flush()

        outputter = WandOutputter(self.name, self.ncams, self.npframes, p1, p2, self.indices['paired'], up,
                                  self.indices['unpaired'], self.nupframes)
        outputter.output()

        if self.display:
            try:
                if sys.platform == 'linux2':
                    # have to block on Linux, looking for fix...
                    plt.show()
                else:
                    if self.report:
                        plt.show(block=False)
                    else:
                        plt.show()
            except Exception as e:
                print('Could not graph!\n' + e)

        return outliers, ptsi
