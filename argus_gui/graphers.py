#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

# import matplotlib
# matplotlib.use('Qt5Agg')

# commented for pyqtgraph
# from mpl_toolkits.mplot3d import Axes3D
# from matplotlib.patches import FancyArrowPatch
# from mpl_toolkits.mplot3d import proj3d
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
from PySide6.QtGui import QFont
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from pyqtgraph.opengl.items.GLTextItem import GLTextItem
# from pyqtgraph import GraphicsLayoutWidget, LabelItem, PlotWidget
from moviepy.config import get_setting

# import wandOutputter
from .output import *
import pandas
import sys

from numpy import *
import numpy as np
import scipy.signal
import scipy.io.wavfile
import scipy.spatial
import scipy
import sys
import os.path
# import matplotlib.pyplot as plt
from moviepy.config import get_setting
# import matplotlib.patches as mpatches
import random
from .colors import *
import subprocess
from .tools import *

# import pickle # debug


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
            
        app = QApplication([])
        win = pg.GraphicsLayoutWidget(show=True, title="Audio Streams")
        win.resize(1000, 600)
        win.setWindowTitle('Audio Streams')
        win.setBackground('w')
        
        plot = win.addPlot()
        plot.showGrid(x=True, y=True)
        plot.setLabel('bottom', 'Minutes')
        plot.getAxis('left').setTicks([])
        plot.getAxis('left').setLabel('')

        legend = plot.addLegend(offset=(70, 30))
        
        # Calculate signal ranges and vertical offsets to avoid overflow
        signal_ranges = []
        for signal in signals:
            # Handle edge cases with NaN or infinite values
            finite_signal = signal[np.isfinite(signal)]
            if len(finite_signal) > 0:
                # Convert to float64 to prevent overflow in arithmetic operations
                signal_min = float(np.min(finite_signal))
                signal_max = float(np.max(finite_signal))
                signal_range = signal_max - signal_min
                signal_ranges.append(signal_range)
            else:
                signal_ranges.append(1.0)  # fallback for all NaN/inf signals
        
        # Use float64 to avoid overflow and calculate reasonable vertical separation
        if signal_ranges:
            max_range = signal_ranges[0]
            for sr in signal_ranges[1:]:
                if sr > max_range:
                    max_range = sr
        else:
            max_range = 1.0
        # Clamp the max_range to prevent extremely large offsets
        if max_range > 1e6:
            max_range = 1e6
        vertical_offset = float(max_range * 1.5)  # 50% padding between signals
        
        # Debug output for Windows troubleshooting
        print(f"Signal ranges: {signal_ranges}")
        print(f"Max range: {max_range}, Vertical offset: {vertical_offset}")
        sys.stdout.flush()
        
        for k in range(len(signals)):
            color = colors[k % len(colors)]
            #convert tuple of [0,1] to tuple of [0,255] for pyqtgraph
            color = tuple(int(c * 255) for c in color)
            print(f"Plotting signal {k} with color {color}")  # Debugging statement
            sys.stdout.flush()
            t = np.linspace(0, len(signals_[k]) / 48000., num=len(signals[k])) / 60.
            # Use the signal's offset from its center, then apply vertical separation
            finite_signal = signals[k][np.isfinite(signals[k])]
            if len(finite_signal) > 0:
                # Convert to float64 to prevent overflow in arithmetic operations
                signal_min = float(np.min(finite_signal))
                signal_max = float(np.max(finite_signal))
                signal_center = (signal_max + signal_min) / 2.0
            else:
                signal_center = 0.0  # fallback for all NaN/inf signals
            y_offset = k * vertical_offset
            # Debug output for Windows troubleshooting
            adjusted_signal = signals[k] - signal_center - y_offset
            print(f"Signal {k}: center={signal_center:.2f}, y_offset={y_offset:.2f}, range=[{np.min(adjusted_signal):.2f}, {np.max(adjusted_signal):.2f}]")
            sys.stdout.flush()
            curve = plot.plot(t, adjusted_signal, pen=pg.mkPen(color=color, width=2))
            legend.addItem(curve, self.files[k].split('/')[-1])

        app.exec_()
        signals_ = None
        # a = 0
        # patches = list()
        # width = 35
        # height = 3 * len(signals)
        # plt.figure(figsize=(width, height))
        # frame1 = plt.gca()
        # frame1.axes.get_yaxis().set_visible(False)
        # # Make a plot with colors chosen by circularly pulling from the colors vector
        # for k in range(len(signals)):
        #     color = colors[k % len(colors)]
        #     patches.append(mpatches.Patch(color=color, label=self.files[k].split('/')[-1]))
        #     t = np.linspace(0, len(signals_[k]) / 48000., num=len(signals[k])) / 60.
        #     plt.plot(t, signals[k] + float(a), color=color)
        #     a += np.nanmax(signals[k]) * 2
        # plt.legend(handles=patches)
        # plt.title('Audio Streams')
        # plt.xlabel('Minutes')
        # signals_ = None
        # plt.show()


# rigid_transform_3D
# Returns the estimated translation and rotation matrix for a rigid transform from one set of points to another.
# used here to transform points based on specified axis directions
#
# Uses a nifty SVD method
# https://igl.ethz.ch/projects/ARAP/svd_rot.pdf
#
# Input: expects Nx3 matrices of points in A and B of matched N
# Returns: R,t
#   R = 3x3 rotation matrix
#   t = 3x1 column vector
def rigid_transform_3D(A, B):
    assert len(A) == len(B)

    N = A.shape[0];  # total points

    centroid_A = mean(A, axis=0)
    centroid_B = mean(B, axis=0)

    # center the points
    AA = A - tile(centroid_A, (N, 1))
    BB = B - tile(centroid_B, (N, 1))

    # dot is matrix multiplication for array
    H = transpose(AA).dot(BB)

    U, S, Vt = linalg.svd(H)

    R = Vt.T.dot(U.T)

    # special reflection case
    if linalg.det(R) < 0:
        print('Reflection detected - likely due to an underlying left-handed coordinate system')
        # do nothing (commented the below lines out on 2020-05-26)
        #Vt[2, :] *= -1
        #R = Vt.T.dot(U.T)
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

# calculate camera xyz position from DLT coefficients
def DLTtoCamXYZ(dlts):
    camXYZ = []
    for i in range(len(dlts)):
        m1=np.hstack([dlts[i,0:3],dlts[i,4:7],dlts[i,8:11]]).T
        m2=np.vstack([-dlts[i,3],-dlts[i,7],-1])
        camXYZ.append(np.dot(np.linalg.inv(m1),m2))
        
    camXYZa = np.array(camXYZ)
    return camXYZa

# takes unpaired and paired points along with other information about the scene, and manipulates the data for outputting and graphing in 3D
class wandGrapher(QWidget):
    def __init__(self, my_app, key, nppts, nuppts, scale, ref, indices, ncams, npframes, nupframes=None, name=None, temp=None,
                 display=True, uvs=None, nRef=0, order=None, report=True, cams=None, reference_type='Axis points', recording_frequency=100):
        super().__init__()
        self.my_app = my_app
        layout = QVBoxLayout(self)
        # Create a GL View widget for displaying 3D data with grid and axes (data will come later)
        self.view = gl.GLViewWidget()
        self.view.setWindowTitle('3D Graph')
        self.view.setCameraPosition(distance=20)
        # Create grid items for better visualization
        grid = gl.GLGridItem()
        grid.scale(2, 2, 1)
        self.view.addItem(grid)
        
        # Add x, y, z axes lines
        axis_length = 10
        x_axis = gl.GLLinePlotItem(pos=np.array([[0, 0, 0], [axis_length, 0, 0]]), color=(1, 0, 0, 1), width=2)  # Red line for x-axis
        y_axis = gl.GLLinePlotItem(pos=np.array([[0, 0, 0], [0, axis_length, 0]]), color=(0, 1, 0, 1), width=2)  # Green line for y-axis
        z_axis = gl.GLLinePlotItem(pos=np.array([[0, 0, 0], [0, 0, axis_length]]), color=(0, 0, 1, 1), width=2)  # Blue line for z-axis
        self.view.addItem(x_axis)
        self.view.addItem(y_axis)
        self.view.addItem(z_axis)
                
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
        self.reference_type = reference_type
        self.recording_frequency = recording_frequency

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
        
        # Subtract the origin from the points and reference
        t = ref[0]
        ret = xyzs - np.tile(t, (xyzs.shape[0], 1))
        ref = ref - ref[0]
            
        # process Axis points
        # if we only got one reference point
        if ref.shape[0] == 1 and self.reference_type == 'Axis points':
            print('Using 1-point (origin) reference axes')
            # we actually already did this above since it's the starting point
            # for all alignment operations
            
        # If we only have 2 reference points: origin, +Z (plumb line):
        elif ref.shape[0] == 2 and self.reference_type == 'Axis points':
            print('Using 2-point (origin,+Z) reference axes')    
            a = (ref[1] - ref[0]) * (1. / np.linalg.norm(ref[1] - ref[0]))

            # Get the current z-axis and the wanted z-axis
            pts1 = np.asarray([[0., 0., 1.]])
            pts2 = np.asarray([a])

            # Get the transform from one to the other
            R = rotation(pts2[0], pts1[0])

            # Perform the transform
            for k in range(ret.shape[0]):
                ret[k] = R.dot(ret[k].T).T
            
        # If we have origin,+x,+y axes:
        elif ref.shape[0] == 3 and self.reference_type == 'Axis points':
            print('Using 3-point (origin,+x,+y) reference axes')        
            A = ref

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
        
        # If we have origin,+x,+y,+z axes:
        elif ref.shape[0] == 4 and self.reference_type == 'Axis points':
            print('Using 4-point (origin,+x,+y,+z) reference axes')
            A = ref

            # define the same points in our coordinate system
            B = np.zeros((4, 3))
            B[1] = np.array([np.linalg.norm(A[1]), 0., 0.])
            B[2] = np.array([0., np.linalg.norm(A[2]), 0.])
            B[3] = np.array([0., 0., np.linalg.norm(A[3])])

            # find rotation and translation, translation ~ 0 by definition
            R, t = rigid_transform_3D(A, B)

            # rotate
            ret = R.dot(ret.T).T
            
        # If we have a gravity reference
        elif self.reference_type == 'Gravity':
            print('Using gravity alignment, +Z will point anti-parallel to gravity')
            rfreq=float(self.recording_frequency)
            t=np.arange(ref.shape[0]) # integer timebase
            
            print(ref) # debug
            
            # perform a least-squares fit of a 2nd order polynomial to each
            # of x,y,z components of the reference, evaluate the polynomial
            # and get the acceleration
            acc=np.zeros(3)
            idx=np.where(np.isfinite(ref[:,0])) # can only send real data to polyfit
            for k in range(3):
                p=np.polyfit(t[idx[0]],ref[idx[0],k],2)
                pv=np.polyval(p,t)
                acc[k]=np.mean(np.diff(np.diff(pv)))*rfreq*rfreq
            
            # need a rotation to point acceleration at -1 (i.e. -Z is down)
            an=acc/np.linalg.norm(acc) # unit acceleration vector
            vv=np.array([0,0,-1]) # target vector
            rv=np.cross(an,vv) # axis for angle-axis rotation
            rv=rv/np.linalg.norm(rv) # unit axis
            ang=np.arccos(np.dot(an,vv)) # rotation magnitude
            r = scipy.spatial.transform.Rotation.from_rotvec(rv*ang) # compose angle-axis rotation 
            ret = r.apply(ret) # apply it
            
            # reporting
            pg=np.linalg.norm(acc)/9.81*100
            print('Gravity measured with {:.2f}% accuracy!'.format(pg))
            
        # If we have a reference plane
        elif self.reference_type == 'Plane':
            print('Aligning to horizontal plane reference points')

            avg = np.mean(ref.T, axis=1)
            centered = ref - avg  # mean centered plane
            
            # do a principal components analysis via SVD
            uu, ss, vh = np.linalg.svd(centered, full_matrices=True)
            vh=vh.T # numpy svd vector is the transpose of the MATLAB version
            #print('svd results')
            #print(vh)
            
            #print('plane xyz points pre-rotation')
            #print(centered)
            
            # check to see if vh is a rotation matrix
            if np.linalg.det(vh) == -1:
                #print('found det of -1')
                vh=-vh
                
            # test application of rotation to plane points
            #rTest = np.matmul(centered,vh)
            #print('Rotation test on plane points')
            #print(rTest)
            
            # apply to the whole set of input values
            centered = xyzs - avg   # center on center of reference points
            rCentered = np.matmul(centered,vh)
            
            # check to see if Z points are on average + or -
            # if they're negative, multiply in a 180 degree rotation about the X axis
            rca=np.mean(rCentered.T,axis=1)
            if rca[2]<0:
                #print('reversing the direction')
                r180 = np.array([[1,0,0],[0,-1,0],[0,0,-1]])
                vh = np.matmul(vh,r180)
                rCentered = np.matmul(centered,vh)

            ret = rCentered

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
        # added rcond option 2020-05-26 in response to FutureWarning from numpy
        L = np.linalg.lstsq(A, B, rcond=None)[0]

        # reproject to calculate rmse
        reconsted = np.zeros((len(indices), 2))
        for k in range(len(indices)):
            u = (np.dot(L[:3].T, xyz[indices[k]]) + L[3]) / (np.dot(L[-3:].T, xyz[indices[k]]) + 1.)
            v = (np.dot(L[4:7].T, xyz[indices[k]]) + L[7]) / (np.dot(L[-3:].T, xyz[indices[k]]) + 1.)
            reconsted[k] = [u[0], v[0]]

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

        # This part finds outliers and their frames
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
        # If we've got paired points, define a scale
        if self.nppts != 0:
            paired = xyzs[self.nRef:self.nppts + self.nRef]
            p1, p2, pairedSet1, pairedSet2 = self.pairedIsomorphism(paired)
            dist, std = self.averDist(pairedSet1, pairedSet2)
            factor = self.scale / dist
        else:
            # else no scale, just arbitrary
            p1, p2 = None, None
            factor = 1.

        xyzs = xyzs*factor # apply scale factor to all xyz points
        
        if self.ref:
            print('Using reference points')
            xyzs = self.transform(xyzs, xyzs[:self.nRef, :])
            ref = xyzs[:self.nRef, :] # transformed reference points

        else:
            print('No reference points available - centering the calibration on the mean point location.')
            ref = None
            t = np.mean(xyzs, axis=0)
            for k in range(xyzs.shape[0]):
                xyzs[k] = xyzs[k] - t # changed by Ty from + to - to center an unaligned calibration 2020-05-26 version 2.1.2
        # now that we've applied the scale and alignment, re-extract the paired points for proper display
        if self.nppts != 0:
            paired = xyzs[self.nRef:self.nppts + self.nRef]
            p1, p2, pairedSet1, pairedSet2 = self.pairedIsomorphism(paired)

        # get DLT coefficients
        camn = 0
        errs = list()
        dlts = list()
        outliers = []
        ptsi = []
        for uv in self.uvs:
            cos, error, outlier, ind = self.getCoefficients(xyzs, uv, camn)
            camn += 1
            outliers = outliers + outlier
            ptsi = ptsi + ind
            # print len(ind)
            # print len(outlier)
            dlts.append(cos)
            errs.append(error)

        dlts = np.asarray(dlts)
        errs = np.asarray(errs)
        self.dlterrors = errs
        #print errors and wand score to the log
        self.outputDLT(dlts, errs)
        sys.stdout.flush()
        
        if self.nppts != 0:
            self.wandscore = 100. * (std / dist)
            print('\nWand score: ' + str(self.wandscore))
            sys.stdout.flush()
        else:
            print('\nWand score: not applicable')
        sys.stdout.flush()
        
        # start making the graph
        # app = QApplication([])
        # Create a main widget

        # main_layout = QVBoxLayout()
        # main_widget.setLayout(main_layout)
        
        # Create a GL View widget for displaying 3D data
        # view = gl.GLViewWidget()
        # view.show()
        # view.setWindowTitle('3D Graph')
        # view.setCameraPosition(distance=20)

        # # Create grid items for better visualization
        # grid = gl.GLGridItem()
        # grid.scale(2, 2, 1)
        # view.addItem(grid)

        # # Add x, y, z axes lines
        # axis_length = 10
        # x_axis = gl.GLLinePlotItem(pos=np.array([[0, 0, 0], [axis_length, 0, 0]]), color=(1, 0, 0, 1), width=2)  # Red line for x-axis
        # y_axis = gl.GLLinePlotItem(pos=np.array([[0, 0, 0], [0, axis_length, 0]]), color=(0, 1, 0, 1), width=2)  # Green line for y-axis
        # z_axis = gl.GLLinePlotItem(pos=np.array([[0, 0, 0], [0, 0, axis_length]]), color=(0, 0, 1, 1), width=2)  # Blue line for z-axis
        # view.addItem(x_axis)
        # view.addItem(y_axis)
        # view.addItem(z_axis)

        # Add labels for x, y, z axes - not working
        # font = QFont()
        # font.setPointSize(20)
        # x_label = GLTextItem(text='X', color=(1, 0, 0, 1), pos=(axis_length, 0, 0), font=font)
        # y_label = GLTextItem(text='Y', color=(0, 1, 0, 1), pos=(0, axis_length, 0), font=font)
        # z_label = GLTextItem(text='Z', color=(0, 0, 1, 1), pos=(0, 0, axis_length), font=font)
        # view.addItem(x_label)
        # view.addItem(y_label)
        # view.addItem(z_label)
        
        # Trim off the reference points as we don't want to graph them with the other xyz
        xyzs = xyzs[self.nRef:, :]

        # Plot unpaired points
        if self.nuppts != 0:
            up = xyzs[self.nppts:, :]
            if self.display:
                x = up[:, 0]
                y = up[:, 1]
                z = up[:, 2]
                scatter = gl.GLScatterPlotItem(pos=np.array([x, y, z]).T, color=(0, 1, 1, 1), size=20)  # Cyan color, larger markers
                scatter.setGLOptions('translucent')
                self.view.addItem(scatter)

        # Plot paired points and draw lines between each paired set
        if self.nppts != 0 and self.display:
            for k in range(len(pairedSet1)):
                points = np.vstack((pairedSet1[k], pairedSet2[k]))
                x = points[:, 0]
                y = points[:, 1]
                z = points[:, 2]
                line = gl.GLLinePlotItem(pos=np.array([x, y, z]).T, color=(1, 0, 1, 1), width=5, antialias=True)  # Magenta color
                self.view.addItem(line)

        # Plot reference points
        if self.nRef != 0 and self.display:
            scatter = gl.GLScatterPlotItem(pos=ref, color=(1, 0, 0, 1), size=20)  # Red color, larger markers
            scatter.setGLOptions('translucent')
            self.view.addItem(scatter)

        # Get the camera locations as expressed in the DLT coefficients
        camXYZ = DLTtoCamXYZ(dlts)
        plotcamXYZ = np.array(camXYZ).reshape(-1, 3)  # Ensure camXYZ is a 2D array of shape (n_points, 3)
        scatter = gl.GLScatterPlotItem(pos=plotcamXYZ, color=(0, 1, 0, 1), size=10)  # Green color, larger markers
        scatter.setGLOptions('translucent')
        self.view.addItem(scatter)

        outputter = WandOutputter(self.name, self.ncams, self.npframes, pairedSet1, pairedSet2, self.indices['paired'], up, self.indices['unpaired'], self.nupframes)
        outputter.output()

        # if self.display:
        #     app.exec_()
            
        
        # fig = plt.figure()
        # ax = fig.add_subplot(111, projection='3d')
        # # ax.set_aspect('equal') # doesn't look good for 3D
        # # main trick for getting axes to be equal (getting equal scaling) is to create "bounding box" points that set
        # # upper and lower axis limits to the same values on all three axes (https://stackoverflow.com/questions/13685386/matplotlib-equal-unit-length-with-equal-aspect-ratio-z-axis-is-not-equal-to)
        # # trim off the reference points as we don't want to graph them with the other xyz
        # xyzs = xyzs[self.nRef:, :]

        # # vP = vP
        # # x = vP[:,:3][:,0]
        # # y = vP[:,:3][:,1]
        # # z = vP[:,:3][:,2]

        # # plot unpaired points
        # # ax.scatter(x,y,z)
        # if self.nuppts != 0:
        #     up = xyzs[self.nppts:, :]
        #     if self.display:
        #         x = up[:, 0]
        #         y = up[:, 1]
        #         z = up[:, 2]
        #         ax.scatter(x, y, z,c='c',label='Unpaired points')
        # else:
        #     up = None

        # # plot the paired points if there are any. draw a line between each paired set.
        # if self.nppts != 0 and self.display:
        #     ax.set_xlabel('X (Meters)')
        #     ax.set_ylabel('Y (Meters)')
        #     ax.set_zlabel('Z (Meters)')
        #     for k in range(len(pairedSet1)):
        #         _ = np.vstack((pairedSet1[k], pairedSet2[k]))
        #         x = _[:, 0]
        #         y = _[:, 1]
        #         z = _[:, 2]
        #         if k == 0:
        #             ax.plot(x, y, z,c='m',label='Paired points')
        #         else:
        #             ax.plot(x, y, z,c='m')
                
        # # plot the reference points if there are any
        # if self.nRef != 0 and self.display:
        #     ax.scatter(ref[:,0],ref[:,1],ref[:,2], c='r', label='Reference points')
            
        # # get the camera locations as expressed in the DLT coefficients
        # camXYZ = DLTtoCamXYZ(dlts)
        # ax.scatter(camXYZ[:,0],camXYZ[:,1],camXYZ[:,2], c='g', label='Camera positions')
            
        # # add the legend, auto-generated from label='' values for each plot entry
        # if self.display:
        #     ax.legend()

        # outputter = WandOutputter(self.name, self.ncams, self.npframes, p1, p2, self.indices['paired'], up,
        #                           self.indices['unpaired'], self.nupframes)
        # outputter.output()

        # if self.display:
        #     try:
        #         if sys.platform == 'linux2':
        #             # have to block on Linux, looking for fix...
        #             plt.show()
        #         else:
        #             if self.report:
        #                 plt.show(block=False)
        #             else:
        #                 plt.show()
        #     except Exception as e:
        #         print('Could not graph!\n' + e)

        return outliers, ptsi