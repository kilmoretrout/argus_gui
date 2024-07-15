#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import os

import pkg_resources

cwd = os.getcwd()
os.chdir(pkg_resources.resource_filename('argus_gui.resources', ''))

import sba
from .output import *

os.chdir(cwd)
from PySide6 import QtWidgets
from PySide6.QtCore import Qt
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from .triangulate import *
import pandas
from texttable import *
import copy
from scipy.sparse import lil_matrix
import string
import random
from .tools import undistort_pts, redistort_pts
import sys


# driver for SBA operations, graphing, and writing output
class sbaArgusDriver():
    def __init__(self, ppts, uppts, cams, display=True, scale=None, modeString=None, ref=None, name=None, temp="",
                 report=True, outputCPs=True, reorder=True, reference_type='Axis points', recording_frequency=100):
        self.ppts = ppts
        self.uppts = uppts
        self.cams = cams
        self.ncams = cams.shape[0]
        self.display = display
        self.scale = scale
        self.modeString = modeString
        self.nppts = 0
        self.nuppts = 0
        self.ref = ref
        self.name = name
        self.temp = temp
        self.report = report
        self.outputCameraProfiles = outputCPs
        self.reorder = reorder
        self.reference_type = reference_type
        self.recording_frequency = recording_frequency
        print('Parsing points...')
        sys.stdout.flush()

        if self.reorder:
            self.rearrange()
        else:
            self.order = np.arange(self.ncams)

        self.pts, self.ext, self.indices = self.getPointsAndExtArray()
    # parses through the arrays given and finds those rows which have uv coordinates that can be triangulated
    # with respect to the last camera's reference frame. puts good indices in a list to reconstruct later and
    # preserve frame count
    def parse(self, pts):
        ret = list()
        if type(pts) is lil_matrix:
            pts = pts.toarray()
        # how many points are present?
        npts = int(pts.shape[1] / (2 * self.ncams))
        # for each point column
        for k in range(npts):
            # get bad indices and remove them from a list of all indices to get good indices
            badindices = list()
            p = pts[:, k * 2 * self.ncams:(k + 1) * 2 * self.ncams]
            for k in range(p.shape[0]):
                if True in np.isnan(p[k][2 * (self.ncams - 1):]):
                    badindices.append(k)
                elif not False in np.isnan(p[k][:2 * (self.ncams - 1)]):
                    badindices.append(k)
            goodindices = np.arange(pts.shape[0])
            goodindices = np.delete(goodindices, badindices, axis=0)
            ret.append([np.delete(p, badindices, axis=0), goodindices])
        return ret

    # gives a ranking to each camera based on the number of
    # triangulatable points it enables when choosing it as reference
    def count(self, pts):
        counts = np.zeros(self.ncams)
        for k in range(pts.shape[0]):
            for j in range(int(pts.shape[1] / (2 * self.ncams))):
                if type(pts) is not lil_matrix:
                    _ = np.isnan(pts[k, self.ncams * 2 * j:self.ncams * 2 * (j + 1)])
                else:
                    _ = np.isnan(pts[k, self.ncams * 2 * j:self.ncams * 2 * (j + 1)].toarray())
                for i in range(int(len(_) / 2)):
                    if not _[i * 2]:
                        counts[i] += int(list(_).count(False) / 2) - 1
        return counts

    # rearranges the data sets to put the optimal camera in last for use as reference
    def rearrange(self):
        counts = np.zeros(self.ncams)

        if self.ppts is not None:
            counts += self.count(self.ppts)
        if self.uppts is not None:
            counts += self.count(self.uppts)

        best = np.argmax(counts)

        print('Using camera ' + str(best + 1) + ' as reference')
        sys.stdout.flush()

        # if the best camera is not the last, switch it out
        if best != self.ncams - 1:
            if self.ppts is not None:
                _ = copy.copy(self.ppts[:, 2 * (self.ncams - 1):2 * self.ncams])  # original last camera
                self.ppts[:, 2 * (self.ncams - 1):2 * self.ncams] = self.ppts[:, best * 2:best * 2 + 2]  # last now best
                self.ppts[:, best * 2:best * 2 + 2] = _  # best now original last

                _ = copy.copy(self.ppts[:, -2:])
                self.ppts[:, -2:] = self.ppts[:, 2 * self.ncams + best * 2:2 * self.ncams + best * 2 + 2]
                self.ppts[:, 2 * self.ncams + best * 2:2 * self.ncams + best * 2 + 2] = _
            if self.uppts is not None:
                for k in range(int(self.uppts.shape[1] / (2 * self.ncams))):
                    _ = copy.copy(self.uppts[:, (k + 1) * self.ncams * 2 - 2:(k + 1) * self.ncams * 2])
                    self.uppts[:, self.ncams * 2 * (k + 1) - 2:self.ncams * 2 * (k + 1)] = self.uppts[:,
                                                                                           2 * self.ncams * k + best * 2:2 * self.ncams * k + best * 2 + 2]
                    self.uppts[:, 2 * self.ncams * k + best * 2:2 * self.ncams * k + best * 2 + 2] = _
            if self.ref is not None:
                _ = copy.copy(self.ref[:, -2:])
                self.ref[:, -2:] = self.ref[:, best * 2:best * 2 + 2]
                self.ref[:, best * 2:best * 2 + 2] = _

            self.order = np.arange(self.ncams)
            self.order[best] = self.order[-1]  # change order such that best is last
            self.order[-1] = best
            # print(self.order)

            # re-arrange self.cams
            _ = copy.copy(self.cams[-1, :])  # original last camera
            self.cams[-1, :] = self.cams[best, :]
            self.cams[best, :] = _
        else:
            self.order = np.arange(self.ncams)

    # stacks everything together to pass into SBA
    def getPointsAndExtArray(self):
        indices = dict()
        # we've got both paired and unpaired points
        if self.ppts is not None and self.uppts is not None:
            parsed = self.parse(self.uppts)
            _ = parsed[0][0]
            for k in range(1, len(parsed)):
                _ = np.vstack((_, parsed[k][0]))
            unpaired = _
            _ = None

            ind = list()
            for k in range(len(parsed)):
                ind.append(list(parsed[k][1]))
            indices['unpaired'] = ind

            self.nuppts = unpaired.shape[0]

            pairedParsed = self.parse(self.ppts)
            _ = pairedParsed[0][0]
            for k in range(1, len(pairedParsed)):
                _ = np.vstack((_, pairedParsed[k][0]))
            paired = _
            _ = None

            self.nppts = paired.shape[0]

            ind = list()
            for k in range(len(pairedParsed)):
                ind.append(list(pairedParsed[k][1]))
            indices['paired'] = ind

            pts = np.vstack((paired, unpaired))
        # we've got only paired points
        elif self.ppts is not None and self.uppts is None:
            pairedParsed = self.parse(self.ppts)
            _ = pairedParsed[0][0]
            for k in range(1, len(pairedParsed)):
                _ = np.vstack((_, pairedParsed[k][0]))
            pts = _
            _ = None
            ind = list()
            for k in range(len(pairedParsed)):
                ind.append(list(pairedParsed[k][1]))
            indices['paired'] = ind
            indices['unpaired'] = None

            self.nppts = pts.shape[0]
        elif self.uppts is not None and self.ppts is None:
            parsed = self.parse(self.uppts)
            _ = parsed[0][0]
            for k in range(1, len(parsed)):
                _ = np.vstack((_, parsed[k][0]))
            pts = _
            _ = None

            self.nuppts = pts.shape[0]

            ind = list()
            for k in range(len(parsed)):
                ind.append(list(parsed[k][1]))
            indices['unpaired'] = ind
            indices['paired'] = None

        # if we've got reference points, stack them on top
        if self.ref is not None:
            print('Including reference points')
            sys.stdout.flush()
            pts = np.vstack((self.ref, pts))

        print('Triangulating...')
        sys.stdout.flush()

        # pass the big stack of UV coordingates to be triagulated
        tring = multiTriangulator(pts, self.cams)
        xyz = tring.triangulate()

        """
        x = xyz[:,0]
        y = xyz[:,1]
        z = xyz[:,2]

        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        ax.scatter(x,y,z)
        plt.show()

        """
        # put them together for SBA
        pts = np.hstack((xyz, pts))

        return pts, tring.ext, indices

    def id_generator(self, size=12, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    # fixes (as in optimizes) 3D points, camera extrinsics, and possibly intrinsics, using SBA. Then, calls a grapher class
    # which ties everything together and graphs and outputs the data in CSV format.
    def fix(self):
        print('Found ' + str(self.pts.shape[0]) + ' 3D points')

        print('Passing points to SBA...')
        sys.stdout.flush()

        points = sba.Points.fromDylan(self.pts)
        cameras = sba.Cameras.fromDylan(np.hstack((self.cams, self.ext)))
        cameras.toTxt(self.name + '-sba-profile-orig.txt')
        options = sba.Options.fromInput(cameras, points)
        options.camera = sba.OPTS_CAMS
        if self.modeString[0] == '0':
            options.nccalib = sba.OPTS_FIX5_INTR  # fix all intrinsics
        elif self.modeString[0] == '1':
            options.nccalib = sba.OPTS_FIX4_INTR  # optimize focal length
        elif self.modeString[0] == '2':
            options.nccalib = sba.OPTS_FIX2_INTR  # optimize focal length and principal point

        if self.modeString[1] == '0':
            # If you wish to fix the intrinsics do so here by setting options
            options.ncdist = sba.OPTS_FIX5_DIST  # fix all distortion coeffs
        elif self.modeString[1] == '1':
            options.ncdist = sba.OPTS_FIX4_DIST  # optimize k2
        elif self.modeString[1] == '2':
            options.ncdist = sba.OPTS_FIX3_DIST  # optimize k2, k4
        elif self.modeString[1] == '3':
            options.ncdist = sba.OPTS_FIX0_DIST  # optimize all distortion coefficients

        newcameras, newpoints, info = sba.SparseBundleAdjust(cameras, points, options)
        info.printResults()
        sys.stdout.flush()

        key = self.id_generator()

        # write out temp files as a means of passing data to grapher
        newcameras.toTxt(self.temp + '/' + key + '_cn.txt')
        newpoints.toTxt(self.temp + '/' + key + '_np.txt')

        # write out cameras for the user in the original order
        camO = np.loadtxt(self.temp + '/' + key + '_cn.txt')
        if self.order is not None:
            camO = camO[list(self.order), :]

        camO = pandas.DataFrame(camO)
        camO.to_csv(self.name + '-sba-profile.txt', header=False, index=False, sep=' ')
        # newcameras.toTxt(self.name + '-sba-profile.txt')

        if self.ppts is not None:
            npframes = self.ppts.shape[0]
        else:
            npframes = None

        if self.uppts is not None:
            nupframes = self.uppts.shape[0]
        else:
            nupframes = None

        if self.ref is not None:
            refBool = True
        else:
            refBool = False

        uvs = list()
        for k in range(self.ncams):
            # print self.cams[k]
            uvs.append(undistort_pts(self.pts[:, 3 + 2 * k:3 + 2 * (k + 1)], self.cams[k]))

        if self.ref is not None:
            nRef = self.ref.shape[0]
        else:
            nRef = 0

        # nppts - Number of triangulatable paired point correspondences in both tracks
        # nuppts - Number of triangulatable unpaired point correspondences in N tracks
        # scale - Wand distance
        # refBool - Are there reference points?
        # indices - Dictionary for paired and unpaired indices in the original CSV file
        # ncams - Number of cameras
        # npframes - Number of frames, columns, in the paired CSV file, not inculding header
        # nupframes - Number of frames in the unpaired CSV file
        # name - tag and location for output files
        # temporary directory
        # Boolean to decide on graphing
        # note that wandGrapher also does lots of other tasks: alignment, generating and saving DLT coefficients, etc.
        if self.display:
            print('Graphing and writing output files...')
            sys.stdout.flush()
        
        QtWidgets.QApplication.processEvents()
        
        self.app = QtWidgets.QApplication.instance()
        self.running = True
        if self.app is None:
            self.running = False
            # necessary for regraphing after removing outliers using openGL
            QtWidgets.QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
            self.app = QtWidgets.QApplication(sys.argv)
                 
        self.grapher = OutlierWindow(self, key, self.nppts, self.nuppts, self.scale, refBool, self.indices, self.ncams, npframes,
                              nupframes, self.name, self.temp, self.display, uvs, nRef, self.order, self.report,
                              self.cams, self.reference_type, self.recording_frequency)
        
        self.outliers = self.grapher.outliers
            
        sys.stdout.flush()   
        
        nps = np.loadtxt(self.name + '-sba-profile.txt')
        if self.outputCameraProfiles:
            for k in range(len(nps)):
                l = nps[k]
                l = np.insert(l, 0, 1.)
                l = np.delete(l, [5] + list(np.arange(11, 18)), axis=0)
                np.savetxt(self.name + '-camera-' + str(self.order[k] + 1) + '-profile.txt', np.asarray([l]),
                           fmt='%-1.5g')
        
        # if self.display:
        #     self.showGraph()
            
        #if called with CLI, and display isn't called, allow outlier processing
        if not self.display:
            if self.report:
                print('Found ' + str(len(self.outliers)) + ' possible outliers:')
                # print(table.draw())
                go_again = input('Try again without these outliers? (Y/n): ')
                if go_again == 'y' or go_again == 'Y':
                    self.redo()
                else:
                    self.exitLoop()
        else:
            self.exitLoop()
            
    def showGraph(self):
        if self.display:
            if not self.grapher.isVisible():
                self.grapher.init_UI()
                self.grapher.show()
                if not self.running:
                    self.app.exec() 
                    
    def redo(self):
        sys.stdout.flush()
        self.pts = np.delete(self.pts, self.grapher.index, axis=0)

        # print 'Index length: {0}'.format(len(index))

        # a = 0
        tmp = self.indices['paired']
        # print 'Length of all paired indices: {0}'.format(len(tmp[0]) + len(tmp[1]))
        if tmp is not None:
            for k in range(len(self.outliers)):
                if '(set 1)' in self.outliers[k][2]:
                    # print 'removed outlier'
                    try:
                        tmp[0].remove(self.outliers[k][0] - 1)
                        # a += 1
                        self.nppts -= 1
                    except:
                        pass
                elif '(set 2)' in self.outliers[k][2]:
                    # print 'removed outlier'
                    try:
                        tmp[1].remove(self.outliers[k][0] - 1)
                        # a += 1
                        self.nppts -= 1
                    except:
                        pass

        # print 'Number of paired indices removed: {0}'.format(a)
        # print len(self.pts)
        self.indices['paired'] = copy.copy(tmp)
        # print len(self.indices['paired'][0]) + len(self.indices['paired'][0])

        tmp = copy.copy(self.indices['unpaired'])
        if tmp is not None:
            for k in range(len(self.outliers)):
                if 'Unpaired' in self.outliers[k][2]:
                    try:
                        tmp[self.outliers[k][-1]].remove(self.outliers[k][0] - 1)
                        self.nuppts -= 1
                    except:
                        pass

        self.indices['unpaired'] = tmp

        print('\nRunning again with outliers removed...')
        sys.stdout.flush()
        self.fix()
        self.showGraph()
    
    def exitLoop(self):
        if self.grapher.isVisible():
            self.grapher.close()

class OutlierWindow(QtWidgets.QWidget):
    def __init__(self, my_app, key, nppts, nuppts, scale, refBool, indices, ncams, npframes, nupframes=None, name=None, temp=None,
                 display=True, uvs=None, nRef=0, order=None, report=True, cams=[], reference_type='Axis points', recording_frequency=100):
        super().__init__()
        
        self.my_app = my_app                
        self.nppts = nppts
        self.nuppts = nuppts
        self.scale = scale
        self.refBool = refBool
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
        
        # make run the graph which also finds outliers, errors, wandscore
        self.outliers, self.index = self.buildData()
        
        # self.init_UI()
        
    def init_UI(self):
        # Create a double panewindow
        # Create a main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        # Create a splitter
        splitter = QtWidgets.QSplitter(Qt.Horizontal)
        # Create left pane (3D view)
        left_pane = QtWidgets.QFrame()
        left_layout = QtWidgets.QVBoxLayout()
        left_pane.setLayout(left_layout)
        
        # Create a GL View widget for displaying 3D data with grid and axes (data will come later)
        self.view = gl.GLViewWidget()
        self.view.setWindowTitle('3D Graph')
        self.view.setCameraPosition(distance=20)
        # Create grid items for better visualization
        self.grid = gl.GLGridItem()
        self.grid.scale(2, 2, 1)
        self.view.addItem(self.grid)
        
        # Add x, y, z axes lines
        axis_length = 10
        self.x_axis = gl.GLLinePlotItem(pos=np.array([[0, 0, 0], [axis_length, 0, 0]]), color=(1, 0, 0, 1), width=2)  # Red line for x-axis
        self.y_axis = gl.GLLinePlotItem(pos=np.array([[0, 0, 0], [0, axis_length, 0]]), color=(0, 1, 0, 1), width=2)  # Green line for y-axis
        self.z_axis = gl.GLLinePlotItem(pos=np.array([[0, 0, 0], [0, 0, axis_length]]), color=(0, 0, 1, 1), width=2)  # Blue line for z-axis
        self.view.addItem(self.x_axis)
        self.view.addItem(self.y_axis)
        self.view.addItem(self.z_axis)
        
        left_layout.addWidget(self.view)
        
        # Create right pane (for other content, e.g., labels)
        right_pane = QtWidgets.QFrame()
        right_layout = QtWidgets.QVBoxLayout()
        right_pane.setLayout(right_layout)

        # Add right pane
        errslabel = QtWidgets.QLabel(f"DLT errors: {self.dlterrors}")
        wslabel = QtWidgets.QLabel(f"Wand score: {self.wandscore}")
        label = QtWidgets.QLabel("Outliers")
        # Create a table widget
        self.table = QtWidgets.QTableWidget(1, 4)
        # Set the column headers
        self.table.setHorizontalHeaderLabels(['Frame', 'Undistorted Pixel Coordinate', 'Point Type', 'Error'])
        right_layout.addWidget(errslabel)
        right_layout.addWidget(wslabel)
        right_layout.addWidget(label)
        right_layout.addWidget(self.table)
        # Create a label and add it to the layout - will contain text on number of outliers found
        self.label = QtWidgets.QLabel("")
        right_layout.addWidget(self.label)

        # Create two buttons and add them to the layout
        try_again_button = QtWidgets.QPushButton("Remove these and try again")
        try_again_button.clicked.connect(self.redo)
        right_layout.addWidget(try_again_button)

        im_happy_button = QtWidgets.QPushButton("I'm happy, don't remove outliers")
        im_happy_button.clicked.connect(self.exitLoop)
        right_layout.addWidget(im_happy_button)
        
        #build the splitter view
        splitter.addWidget(left_pane)
        splitter.addWidget(right_pane)
        splitter.setSizes([int(self.width() * .7), int(self.width() * .3)])
        
        # Add the splitter to the main layout
        main_layout.addWidget(splitter)
        self.resize(1000, 600)
        
        # build the rest of the graph
        self.updateGraph()
        # get the data for the Table
        self.updateTable()
        
        
    def updateGraph(self):
        # Clear existing items
        self.view.clear()

        # Re-add grid and axes
        self.view.addItem(self.grid)
        self.view.addItem(self.x_axis)
        self.view.addItem(self.y_axis)
        self.view.addItem(self.z_axis)
        
        # Plot unpaired points
        if self.nuppts != 0:
            # up = xyzs[self.nppts:, :]
            if self.display:
                # x = self.up[:, 0]
                # y = self.up[:, 1]
                # z = self.up[:, 2]
                plotup = np.array(self.up).reshape(-1, 3)  # Ensure a 2D array of shape (n_points, 3)
                # print(f"uppts: {plotup.shape}")
                scatter = gl.GLScatterPlotItem(pos = plotup, color=(0, 1, 1, 1), size=20)  # Cyan color, larger markers
                scatter.setGLOptions('translucent')
                self.view.addItem(scatter)

        # Plot paired points and draw lines between each paired set
        if self.nppts != 0 and self.display:
            for k in range(len(self.pairedSet1)):
                points = np.vstack((self.pairedSet1[k], self.pairedSet2[k]))
                x = points[:, 0]
                y = points[:, 1]
                z = points[:, 2]
                line = gl.GLLinePlotItem(pos=np.array([x, y, z]).T, color=(1, 0, 1, 1), width=5, antialias=True)  # Magenta color
                self.view.addItem(line)

        # Plot reference points
        if self.nRef != 0 and self.display:
            plotref = np.array(self.ref).reshape(-1, 3)  # Ensure ref is a 2D array of shape (n_points, 3)
            # print(f"ref: {plotref.shape}")
            scatter = gl.GLScatterPlotItem(pos=plotref, color=(1, 0, 0, 1), size=20)  # Red color, larger markers
            scatter.setGLOptions('translucent')
            self.view.addItem(scatter)

        # Get the camera locations as expressed in the DLT coefficients
        camXYZ = DLTtoCamXYZ(self.dlts)
        plotcamXYZ = np.array(camXYZ).reshape(-1, 3)  # Ensure camXYZ is a 2D array of shape (n_points, 3)
        # print(f"cams: {plotcamXYZ.shape}")
        scatter = gl.GLScatterPlotItem(pos=plotcamXYZ, color=(0, 1, 0, 1), size=10)  # Green color, larger markers
        scatter.setGLOptions('translucent')
        self.view.addItem(scatter)
       
    
    def buildData(self): 
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
        
        if self.refBool:
            print('Using reference points')
            xyzs = self.transform(xyzs, xyzs[:self.nRef, :])
            self.ref = xyzs[:self.nRef, :] # transformed reference points

        else:
            print('No reference points available - centering the calibration on the mean point location.')
            ref = None
            t = np.mean(xyzs, axis=0)
            for k in range(xyzs.shape[0]):
                xyzs[k] = xyzs[k] - t # changed by Ty from + to - to center an unaligned calibration 2020-05-26 version 2.1.2
        # now that we've applied the scale and alignment, re-extract the paired points for proper display
        # print(self.nRef, self.nppts, self.nuppts)
        if self.nppts != 0:
            paired = xyzs[self.nRef:self.nppts + self.nRef]
            p1, p2, pairedSet1, pairedSet2 = self.pairedIsomorphism(paired)
        # get unpaired points
        if self.nuppts != 0:
            self.up = xyzs[self.nRef + self.nppts:, :]
            
        # save to class variables for use in graph
        self.xyzs = xyzs
        self.paired = paired
        self.pairedSet1 = pairedSet1
        self.pairedSet2 = pairedSet2
        
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

        self.dlts = np.asarray(dlts)
        errs = np.asarray(errs)
        self.dlterrors = errs
        #print errors and wand score to the log
        self.outputDLT(self.dlts, errs)
        sys.stdout.flush()
        
        if self.nppts != 0:
            self.wandscore = 100. * (std / dist)
            print('\nWand score: ' + str(self.wandscore))
            sys.stdout.flush()
        else:
            print('\nWand score: not applicable')
        sys.stdout.flush()
        outputter = WandOutputter(self.name, self.ncams, self.npframes, p1, p2, self.indices['paired'], self.up, self.indices['unpaired'], self.nupframes)
        outputter.output()
        return outliers, ptsi

    def updateTable(self):
        self.table.setRowCount(len(self.outliers))
        for row, row_data in enumerate(self.outliers):
            if len(row_data) > 4:
                row_data = row_data[0:4]
            row_data[1] = np.array2string(row_data[1], separator=', ', formatter={'float_kind': lambda x: f"{x:.2f}"})
            # format and convert to strings
            items = [f"{x:.2f}" if isinstance(x, float) else str(x) for x in row_data]
            items = [QtWidgets.QTableWidgetItem(str(cell)) for cell in items]

            for column, item in enumerate(items):
                self.table.setItem(row, column, item)
        self.label.setText(f"Found {len(self.outliers)} possible outliers.\n Removing them may improve the DLT errors and wand score.")

    def exitLoop(self):
        self.close()

    def redo(self):
        self.my_app.redo()

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
            
            # print(ref) # debug
            
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


# gets data from CSVs. Expects a header.
def parseCSVs(csv):
    if csv.split('.')[-1] == 'csv':
        dataf = pandas.read_csv(csv, index_col=False)
        return dataf.values()
    # else check if we have sparse data representation
    elif csv.split('.')[-1] == 'tsv':
        fo = open(csv)
        # expect a header
        line = fo.readline()
        # next line has shape information for the sparse matrix
        line = fo.readline()
        shape = list(map(int, line.split('\t')))
        # ret = lil_matrix((shape[0], shape[1]))
        ret = lil_matrix((shape[0], shape[1]))
        ret[:, :] = np.nan
        line = fo.readline()
        while line != '':
            val = list(map(float, line.split('\t')))
            ret[int(val[0]) - 1, int(val[1]) - 1] = val[2]
            line = fo.readline()
        return ret

    """
    fo = open(csv)
    line = fo.readline()
    header = False
    try:
        float(line.split(',')[0])
    except:
        header = True
        pass
    if not header:
        ret = map(float, line.split(','))
    else:
        line = fo.readline()
        ret = map(float, line.split(','))
    line = fo.readline()
    while line != '':
        ret = np.vstack((ret, map(float, line.split(','))))
        line = fo.readline()
    return ret
    """

# calculate camera xyz position from DLT coefficients
def DLTtoCamXYZ(dlts):
    camXYZ = []
    for i in range(len(dlts)):
        m1=np.hstack([dlts[i,0:3],dlts[i,4:7],dlts[i,8:11]]).T
        m2=np.vstack([-dlts[i,3],-dlts[i,7],-1])
        camXYZ.append(np.dot(np.linalg.inv(m1),m2))
        
    camXYZa = np.array(camXYZ)
    return camXYZa

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
    camXYZ = []
    for i in range(len(dlts)):
        m1=np.hstack([dlts[i,0:3],dlts[i,4:7],dlts[i,8:11]]).T
        m2=np.vstack([-dlts[i,3],-dlts[i,7],-1])
        camXYZ.append(np.dot(np.linalg.inv(m1),m2))
        
    camXYZa = np.array(camXYZ)
    return camXYZa

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




