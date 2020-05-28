#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import os

import pkg_resources
from six.moves import input
from six.moves import map

cwd = os.getcwd()
os.chdir(pkg_resources.resource_filename('argus_gui.resources', ''))

import sba

os.chdir(cwd)

# import multiTriangulator
# import wandGrapher
# import wandOutputter
from .triangulate import *
from .graphers import *
import pandas
from texttable import *
import six.moves.tkinter_messagebox
from six.moves.tkinter import *
import copy
import six.moves.tkinter_filedialog
# import matplotlib.backends.backend_tkagg as tkagg
from scipy.sparse import lil_matrix
import string
import random
from .tools import undistort_pts


# driver for SBA operations, graphing, and writing output
class sbaArgusDriver():
    def __init__(self, ppts, uppts, cams, display=True, scale=None, modeString=None, ref=None, name=None, temp=None,
                 report=True, outputCPs=True, reorder=True):
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
        print('Sending these points to multiTriangulator')
        print(pts) # debug
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
                              self.cams)
        if self.display:
            print('Graphing and writing output files...')
            sys.stdout.flush()
            if self.report:
                root = Tk()

        outliers, index = grapher.graph()
        # outliers = sorted(outliers)

        nps = np.loadtxt(self.name + '-sba-profile.txt')

        if self.outputCameraProfiles:
            for k in range(len(nps)):
                l = nps[k]
                l = np.insert(l, 0, 1.)
                l = np.delete(l, [5] + list(np.arange(11, 18)), axis=0)
                np.savetxt(self.name + '-camera-' + str(self.order[k] + 1) + '-profile.txt', np.asarray([l]),
                           fmt='%-1.5g')

        def redo():
            if self.display and self.report:
                root.destroy()
            self.pts = np.delete(self.pts, index, axis=0)

            # print 'Index length: {0}'.format(len(index))

            # a = 0
            tmp = self.indices['paired']
            # print 'Length of all paired indices: {0}'.format(len(tmp[0]) + len(tmp[1]))
            if tmp is not None:
                for k in range(len(outliers)):
                    if '(set 1)' in outliers[k][2]:
                        # print 'removed outlier'
                        try:
                            tmp[0].remove(outliers[k][0] - 1)
                            # a += 1
                            self.nppts -= 1
                        except:
                            pass
                    elif '(set 2)' in outliers[k][2]:
                        # print 'removed outlier'
                        try:
                            tmp[1].remove(outliers[k][0] - 1)
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
                for k in range(len(outliers)):
                    if 'Unpaired' in outliers[k][2]:
                        try:
                            tmp[outliers[k][-1]].remove(outliers[k][0] - 1)
                            self.nuppts -= 1
                        except:
                            pass

            self.indices['unpaired'] = tmp

            print('\nRunning again with outliers removed...')

            self.fix()

        def exitLoop():
            if self.display and self.report:
                root.destroy()
            # sys.exit()

        if self.report:
            if len(outliers) == 0:
                root.withdraw()
                six.moves.tkinter_messagebox.showwarning(
                    "No outliers",
                    "No outliers were found! Exiting..."
                )
                root.mainloop()
            else:
                table = Texttable()
                table.header(['Frame', 'Undistorted Pixel Coordinate', 'Point Type', 'Error'])
                for k in range(len(outliers)):
                    if len(outliers[k]) == 4:
                        table.add_row(outliers[k])
                    else:
                        table.add_row(outliers[k][:-1])

                if self.display:
                    root.resizable(width=FALSE, height=FALSE)

                    root.wm_title("Argus - Outlier report")

                    Label(root, text='Found ' + str(len(outliers)) + ' possible outliers:', font="-weight bold").grid(
                        row=0, column=0, sticky=W, padx=10, pady=10)

                    scrollbar = Scrollbar(root, width=20)
                    log = Text(root, yscrollcommand=scrollbar.set, bg="white", fg="black")
                    log.grid(row=1, column=0, padx=10, pady=5)
                    scrollbar.grid(row=1, column=1, padx=5, pady=5, sticky=NS)

                    scrollbar.configure(command=log.yview)

                    # Label(root, text = 'Try again without these outliers?').grid(row = 2,
                    # column = 0, padx = 10, pady = 10, sticky = W)

                    yes = Button(root, text='Try Again', command=redo, padx=5, pady=5)
                    yes.grid(row=2, column=0, padx=5, pady=10)

                    no = Button(root, text='Happy with calibration', command=exitLoop, padx=5, pady=5)
                    no.grid(row=2, column=0, padx=50, sticky=W)

                    log.insert(END, table.draw())
                    """
                    f = mplfig.Figure(figsize=(5,4), dpi=100)
                    a = f.add_subplot(111)

                    x = np.zeros(len(outliers))
                    y = np.zeros(len(outliers))

                    for k in range(len(outliers)):
                        x[k] = outliers[k][1][0]
                        y[k] = outliers[k][1][1]

                    a.plot(x, y, 'ro')

                    canvas = tkagg.FigureCanvasTkAgg(f, master=root)
                    canvas.show()
                    canvas.get_tk_widget().grid(row = 1, column = 2, padx = 5, pady = 5)
                    """
                    root.mainloop()
                else:
                    print('Found ' + str(len(outliers)) + ' possible outliers:')
                    print(table.draw())
                    go_again = input('Try again without these outliers? (Y/n): ')
                    if go_again == 'y' or go_again == 'Y':
                        redo()
                    else:
                        exitLoop()
        else:
            exitLoop()


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
