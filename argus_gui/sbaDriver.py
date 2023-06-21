#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import os

import pkg_resources

cwd = os.getcwd()
os.chdir(pkg_resources.resource_filename('argus_gui.resources', ''))

import sba

os.chdir(cwd)
from PySide6 import QtWidgets
from .triangulate import *
from .graphers import *
import pandas
from texttable import *
# import six.moves.tkinter_messagebox
# from six.moves.tkinter import *
import copy
# import six.moves.tkinter_filedialog
# import matplotlib.backends.backend_tkagg as tkagg
from scipy.sparse import lil_matrix
import string
import random
from .tools import undistort_pts


# driver for SBA operations, graphing, and writing output
class sbaArgusDriver():
    def __init__(self, ppts, uppts, cams, display=True, scale=None, modeString=None, ref=None, name=None, temp=None,
                 report=True, outputCPs=True, reorder=True, reference_type='Axis points', recording_frequency=100):
        self.ppts = ppts
        self.uppts = uppts
        self.cams = cams
        self.ncams = cams.shape[0]
        self.display = display  # deprecated option, always display graph
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
        grapher = wandGrapher(key, self.nppts, self.nuppts, self.scale, refBool, self.indices, self.ncams, npframes,
                              nupframes, self.name, self.temp, self.display, uvs, nRef, self.order, self.report,
                              self.cams, self.reference_type, self.recording_frequency)
        if self.display:
            print('Graphing and writing output files...')
            sys.stdout.flush()
            # if self.report:
                # root = Tk()

        self.outliers, self.index = grapher.graph()
        sys.stdout.flush()
        # outliers = sorted(outliers)

        nps = np.loadtxt(self.name + '-sba-profile.txt')

        if self.outputCameraProfiles:
            for k in range(len(nps)):
                l = nps[k]
                l = np.insert(l, 0, 1.)
                l = np.delete(l, [5] + list(np.arange(11, 18)), axis=0)
                np.savetxt(self.name + '-camera-' + str(self.order[k] + 1) + '-profile.txt', np.asarray([l]),
                           fmt='%-1.5g')

        if self.report:
            if len(self.outliers) == 0:
                QtWidgets.QMessageBox.warning(None,
                    "No outliers",
                    "No outliers were found! Exiting..."
                )
                if self.outwindow.isVisible():
                    self.outwindow.close()
            else:
                app = QtWidgets.QApplication.instance()
                self.running = True
                if app is None:
                    self.running = False
                    app = QtWidgets.QApplication(sys.argv)
                self.outwindow = OutlierWindow(self, self.outliers) 

                if self.display:
                    if not self.outwindow.isVisible():
                        # Show the window
                        self.outwindow.show()

                        if not self.running:
                            app.exec()      
                    else:
                        self.outwindow.outliers = self.outliers
                        self.outwindow.updateTable()
                    # log.insert(END, table.draw())
                    # root.mainloop()
                else:
                    print('Found ' + str(len(self.outliers)) + ' possible outliers:')
                    # print(table.draw())
                    go_again = input('Try again without these outliers? (Y/n): ')
                    if go_again == 'y' or go_again == 'Y':
                        self.redo()
                    else:
                        self.exitLoop()
        else:
            self.exitLoop()

    def redo(self):
        sys.stdout.flush()
        # if self.display and self.report:
        #     # Clear the contents of the window
        #     for widget in outwindow.findChildren(QtWidgets.QWidget):
        #         widget.deleteLater()
        #     outwindow.close()
            # root.destroy()
        self.pts = np.delete(self.pts, self.index, axis=0)

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
    
    def exitLoop(self):
        if self.display and self.outwindow.isVisible():
            self.outwindow.close()

class OutlierWindow(QtWidgets.QWidget):
    def __init__(self, my_app, outliers):
        super().__init__()
        self.my_app = my_app
        self.outliers = outliers
        # Create a window
        self.setWindowTitle("Argus - Outlier Report")
        self.resize(500, 500)
        layout = QtWidgets.QVBoxLayout(self)

        # Create a table widget and add it to the layout
        self.table = QtWidgets.QTableWidget(1, 4)
        # Set the column headers
        self.table.setHorizontalHeaderLabels(['Frame', 'Undistorted Pixel Coordinate', 'Point Type', 'Error'])
        layout.addWidget(self.table)
        # Create a label and add it to the layout
        self.label = QtWidgets.QLabel("")
        self.label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.label)

        # Create two buttons and add them to the layout
        try_again_button = QtWidgets.QPushButton("Remove these and try again")
        try_again_button.clicked.connect(self.redo)
        layout.addWidget(try_again_button)

        im_happy_button = QtWidgets.QPushButton("I'm happy, don't remove outliers")
        im_happy_button.clicked.connect(self.exitLoop)
        layout.addWidget(im_happy_button)
        self.updateTable()

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
        self.label.setText(f"Found {len(self.outliers)} possible outliers")

    def exitLoop(self):
        self.close()

    def redo(self):
        self.my_app.redo()

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
