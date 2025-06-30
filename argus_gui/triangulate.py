#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
import numpy as np
import cv2
import sba.quaternions as quaternions
from .tools import ArgusError


# Gram-Schmidt column orthonormalization
def gs(X, row_vecs=False, norm=True):
    if not row_vecs:
        X = X.T
    Y = X[0:1, :].copy()
    for i in range(1, X.shape[0]):
        proj = np.diag((X[i, :].dot(Y.T) / np.linalg.norm(Y, axis=1) ** 2).flat).dot(Y)
        Y = np.vstack((Y, X[i, :] - proj.sum(0)))
    if norm:
        Y = np.diag(1 / np.linalg.norm(Y, axis=1)).dot(Y)
    if row_vecs:
        return Y
    else:
        return Y.T


class Triangulator():
    def __init__(self, p1, p2, f1, f2, c1, c2, dist1, dist2):
        self.p1 = p1  # p1 is a np.array of shape (n,2)
        self.p2 = p2  # p2 is same shape (should be same length)
        self.f1 = f1  # float
        self.f2 = f2
        self.c1 = c1  # np arrays of shape (1,2)
        self.c2 = c2
        self.R = None
        self.t = None
        self.dist1 = dist1
        self.dist2 = dist2
        self.normalize()

    # Normalize by subtracting out the optical center and dividing by the focal length
    def normalize(self):
        src1 = np.zeros((1, self.p1.shape[0], self.p1.shape[1]), dtype=np.float32)
        src2 = np.zeros((1, self.p1.shape[0], self.p1.shape[1]), dtype=np.float32)

        src1[0] = self.p1
        src2[0] = self.p2

        # make some camera matrices
        K1 = np.asarray([[self.f1, 0., self.c1[0]],
                         [0., self.f1, self.c1[1]],
                         [0., 0., 1.]])
        K2 = np.asarray([[self.f2, 0., self.c2[0]],
                         [0., self.f2, self.c2[1]],
                         [0., 0., 1.]])

        d1 = cv2.undistortPoints(src1, K1, np.asarray(self.dist1), P=None).squeeze()
        d2 = cv2.undistortPoints(src2, K2, np.asarray(self.dist2), P=None).squeeze()

        self.p1 = d1
        self.p2 = d2

    def getQuaternion(self):
        if self.R.any():
            Q = quaternions.quatFromRotationMatrix(gs(self.R))
            return Q.asVector()

    def triangulate(self):
        # get the essential matrix from OpenCV
        F = self.getFundamentalMat()
        # decompose
        U, D, V = np.linalg.svd(F)
        # print(U) # similar but not identical to MATLAB

        # V comes out inverted as compared to MATLAB & even after inversion has
        # opposite sign in last column, but this is not important
        V = V.T

        W = np.asarray([[0., -1., 0.],
                        [1., 0., 0.],
                        [0., 0., 1.]])

        t = U[:, 2].T  # as per easyWand / MATLAB

        # Four possible orientations (rotation matrices) * two possible translations (forward or backward) = 8 possibilites
        Rs = [U.dot(W.T).dot(V.T), U.dot(W).dot(V.T), U.dot(W.T).dot(-V.T), U.dot(W).dot(-V.T)]

        # Reduce Rs to the 2 good rotation matrices
        cnt = 0
        Rs2 = Rs[:2]
        for R in Rs:
            if np.round(np.linalg.det(R)) != -1:
                Rs2[cnt] = R
                cnt += 1

        # make lists for the triangulated points for all 4 cases, and the count of net Z sign for each
        outs = list()
        plusses = list()

        # Put the points in a format OpenCV likes
        ps1 = np.zeros((2, len(self.p1)))
        ps2 = np.zeros((2, len(self.p1)))
        for k in range(len(self.p1)):
            ps1[:, k] = self.p1[k].T
            ps2[:, k] = self.p2[k].T

        # Check each of the 2 possible rotations
        for R in Rs2:
            # projection matrix for last camera
            P1 = np.asarray([[1., 0., 0., 0.],
                             [0., 1., 0., 0.],
                             [0., 0., 1, 0.]])

            # Positive view
            P = np.zeros((3, 4))
            P[:, :3] = R
            P[:, 3] = t.T

            # Inverse view
            P_ = np.zeros((3, 4))
            P_[:, :3] = np.linalg.inv(R)
            P_[:, 3] = np.asmatrix(-t.T) * np.asmatrix(R)

            # Make arrays for triangulated points from base & inverse camera view
            out = np.zeros((3, len(self.p1)))
            out_ = np.zeros((3, len(self.p1)))

            # Count variables for getting the net sign of the Z of the points resulting
            # from triangulating with the base & inverse views
            p = 0
            p_ = 0

            # Triangulate one at a time so that homogenous coefficient doesn't get too small
            for k in range(len(self.p1)):
                tmp = np.zeros((4, 1))
                tmp_ = np.zeros((4, 1))

                cv2.triangulatePoints(P, P1, ps1[:, k], ps2[:, k], tmp)

                # inverse view: different camera matrices but same points
                cv2.triangulatePoints(P1, P_, ps1[:, k], ps2[:, k], tmp_)

                tmp = tmp * (1. / tmp[3, 0])
                tmp_ = tmp_ * (1. / tmp_[3, 0])

                out[:, k] = tmp[:3, 0]
                out_[:, k] = tmp_[:3, 0]

            # Transpose for easier to work with format
            out = out.T
            out_ = out_.T

            # add up sign of the Z value for each point
            for k in range(len(out[:, 0])):
                if out[k, 2] > 0:
                    p += 1
                else:
                    p -= 1
                if out_[k, 2] > 0:
                    p_ += 1
                else:
                    p_ -= 1

            # outs and plusses end up with 4 entries: [R0,inverse(R0),R1,inverse(R1)]
            outs.append(out)
            outs.append(out_)

            plusses.append(p)
            plusses.append(p_)

        # Decision logic: we are looking for the Rotation & translation option with the
        # largest net plusses score, i.e. the most asymmetrical distribution of points on
        # one side or the other of the base camera.  In most cases, both options will be
        # equal in this regard

        # compare R0 and R1
        if np.absolute(plusses[0]) > np.absolute(plusses[2]):
            zdx = 0
            self.R = Rs2[0]
        elif np.absolute(plusses[0]) < np.absolute(plusses[2]):
            zdx = 2
            self.R = Rs2[1]

        # if both options from above are equal then we look for the case where the base and
        # inverse views have the same sign, i.e. will sum to the larger absolute value. In
        # most cases one option will sum & the other option will cancel to zero; this happens
        # because the rotations imply that you can triangulate xyz points in front of camera 0
        # by looking out the back of camera 1, but when you switch to camera 1 as the base it is
        # clear that the points are behind it instead of in front of it, thus the net plusses
        # sums to zero

        # compare R0+inverse(R0) and R1+inverse(R1)
        else:
            if np.absolute(plusses[0] + plusses[1]) > np.absolute(plusses[2] + plusses[3]):
                zdx = 0
                self.R = Rs2[0]
            else:
                zdx = 2
                self.R = Rs2[1]

        # set the sign of the translation vector to give the desired (i.e. negative) sign for
        # the xyz points
        if plusses[zdx] < 0:
            self.t = U[:, 2].T
        else:
            self.t = -U[:, 2].T

        # Grab the right xyz points and set their sign
        return outs[zdx] * -1 * np.sign(plusses[zdx])

    def getFundamentalMat(self):
        return cv2.findFundamentalMat(self.p2, self.p1, method=cv2.FM_8POINT)[0]


# class for calling triangulate with multiple pixel coordinate pairs. Always passes the last camera
# as the reference frame camera. Afterwards, normalizes the other xyz coordinates based on the average distance for the
# origin camera xyzs and averages everything together for the final estimate of 3D coordinates.
class multiTriangulator():
    def __init__(self, pts, intrins):
        if type(pts) != np.ndarray:
            raise ArgusError('points passed must be a numpy array')
        else:
            if len(pts.shape) != 2:
                raise ArgusError('points must be a 2d array')
        self.pts = pts
        self.ncams = int(pts.shape[1] / 2)
        self.intrins = intrins
        self.ext = None
        if self.ncams != len(self.intrins):
            raise ArgusError('length of intrinsics does not match the number of cameras supplied')

    def triangulate(self):
        # Last camera points
        origincam = self.pts[:, -2:]

        othercams = list()
        xyzs = list()
        # Other camera points
        for k in range(self.ncams - 1):
            othercams.append(self.pts[:, 2 * k: 2 * (k + 1)])

        transrots = list()
        for k in range(len(othercams)):
            # List for the triangulatable point set indices
            goodindices = list()
            cam = othercams[k]

            # Populate goodindices
            for j in range(len(cam[:, 0])):
                if not True in np.isnan(cam[j]) and not True in np.isnan(origincam[j]):
                    goodindices.append(j)

            dest = list()
            source = list()
            for j in range(len(cam[:, 0])):
                if j in goodindices:
                    dest.append(np.asarray(cam[j]))
                    source.append(np.asarray(origincam[j]))

            dest = np.asarray(dest)
            source = np.asarray(source)

            tring = Triangulator(dest, source,
                                 self.intrins[k, 0], self.intrins[-1, 0],
                                 self.intrins[k, 1:3], self.intrins[-1, 1:3],
                                 self.intrins[k, -5:],
                                 self.intrins[-1, -5:])
            tri = tring.triangulate()

            transrots.append(np.hstack((tring.getQuaternion(), tring.t)))

            xyz = np.zeros((len(self.pts[:, 0]), 3))

            for j in range(len(goodindices)):
                xyz[goodindices[j]] = tri[j]

            xyz[xyz == 0] = np.nan
            xyzs.append(xyz)

        # Cleanup
        othercams, origincam = None, None

        _ = transrots[0]
        for k in range(1, len(transrots)):
            _ = np.vstack((_, transrots[k]))
        _ = np.vstack((_, [1, 0, 0, 0, 0, 0, 0]))

        self.ext = _

        return self.normalizeAndAverage(xyzs)

    def normalizeAndAverage(self, xyzs):
        averdists = list()

        for xyz in xyzs:
            dists = list()
            for j in range(len(xyz[:, ])):
                if not True in np.isnan(xyz[j]):
                    dists.append(np.linalg.norm(xyz[j]))
            averdists.append(np.nanmean(dists))
        ret = np.zeros((len(xyzs), len(xyzs[0]), 3))
        ret[0] = xyzs[0]

        for k in range(1, len(xyzs)):
            ret[k] = xyzs[k] * (averdists[0] / averdists[k])

        return np.nanmean(ret, axis=0)
