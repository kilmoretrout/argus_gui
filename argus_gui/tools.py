from __future__ import absolute_import
from __future__ import print_function

import cv2
import numpy as np
import scipy as sp
from scipy import interpolate
from argus.ocam import PointUndistorter, ocam_model
from six.moves import range
from tqdm import *


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class ArgusError(Error):
    """Exception raised for errors in the input.

    Attributes:
        expr -- input expression in which the error occurred
        msg  -- explanation of the error
    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


# project a 3D-coordinate into the image plane using DLT coefficients
# courtesy of Dr. Ty Hedrick
"""
Takes:
    - xyz: Nx3 array of 3D points
    - L: 1 dimensional array with 11 DLT coefficients
Returns:
    - Nx2 array of image coordinates with the origin at the bottom left
"""


def dlt_inverse(L, xyz):
    if not hasattr(L, '__iter__'):
        raise ArgusError('DLT coefficients must be iterable')
    elif np.array(L).shape[0] != 11 or len(np.array(L).shape) != 1:
        raise ArgusError('There must be exaclty 11 DLT coefficients in a 1d iterable')

    if type(xyz) != np.ndarray:
        raise ArgusError('XYZ must be an Nx3 numpy array')
    elif len(xyz.shape) != 2:
        raise ArgusError('XYZ must be an Nx3 numpy array')
    elif xyz.shape[1] != 3:
        raise ArgusError('XYZ must be an Nx3 numpy array')
    uv = np.zeros((len(xyz), 2))
    for k in range(uv.shape[0]):
        u = (np.dot(L[:3].T, xyz[k]) + L[3]) / (np.dot(L[-3:].T, xyz[k]) + 1.)
        v = (np.dot(L[4:7].T, xyz[k]) + L[7]) / (np.dot(L[-3:].T, xyz[k]) + 1.)
        uv[k] = [u, v]
    return uv


# like the above function but for single xyz value
def reconstruct_uv(L, xyz):
    if not hasattr(L, '__iter__'):
        raise ArgusError('DLT coefficients must be iterable')
    elif np.array(L).shape[0] != 11 and len(np.array(L).shape) != 1:
        raise ArgusError('There must be exaclty 11 DLT coefficients in a 1d array or list')

    if type(xyz) != np.ndarray:
        raise ArgusError('XYZ must be a numpy array')
    elif len(xyz) != 3 and len(xyz.shape) != 1:
        raise ArgusError('XYZ must be of shape (3,)')
    u = (np.dot(L[:3].T, xyz) + L[3]) / (np.dot(L[-3:].T, xyz) + 1.)
    v = (np.dot(L[4:7].T, xyz) + L[7]) / (np.dot(L[-3:].T, xyz) + 1.)
    return np.array([u, v])


# Get a line in the pixel coordinate system with the origin in the lower left using DLT coefficients
# courtesy of Dr. Ty Hedrick
"""
Takes:
    - u: x coordinate in the image plane
    - v: y coordinate in the image plane
    - c1: DLT coefficients for camera 1
    - c2: DLT coefficients for camera 2
Returns:
    - m, b: slope and intercept respectively for the epipolar line in camera 2 given u,v coordinate in camera 1
"""


def getDLTLine(u, v, c1, c2):
    z = [500., -500.]
    y = np.zeros(2)
    x = np.zeros(2)
    for i in range(len(z)):
        Z = z[i]

        y[i] = -(u * c1[8] * c1[6] * Z + u * c1[8] * c1[7] - u * c1[10] * Z * c1[4] - u * c1[4] + c1[0] * v * c1[
            10] * Z + c1[0] * v - c1[0] * c1[6] * Z - c1[0] * c1[7] - c1[2] * Z * v * c1[8] + c1[2] * Z * c1[4] - c1[
                     3] * v * c1[8] + c1[3] * c1[4]) / (
                           u * c1[8] * c1[5] - u * c1[9] * c1[4] + c1[0] * v * c1[9] - c1[0] * c1[5] - c1[1] * v * c1[
                       8] + c1[1] * c1[4])

        Y = y[i]

        x[i] = -(v * c1[9] * Y + v * c1[10] * Z + v - c1[5] * Y - c1[6] * Z - c1[7]) / (v * c1[8] - c1[4])

    xy = np.zeros((2, 2))

    for i in range(2):
        xy[i, :] = reconstruct_uv(c2, np.asarray([x[i], y[i], z[i]]))

    m = (xy[1, 1] - xy[0, 1]) / (xy[1, 0] - xy[0, 0])
    b = xy[0, 1] - m * xy[0, 0]
    return m, b


# undistort using OpenCV
"""
Takes:
    - pts: Nx2 array of pixel coordinates
    - prof: either an array of pinhole distortion coefficients or a Omnidirectional distortion object from Argus
Returns:
    - Nx2 array of undistorted pixel coordinates
"""


def undistort_pts(pts, prof):
    if (type(prof) == list) or (type(prof) == np.ndarray):
        prof = np.array(prof)

        # try block to discern whether or not we are using the omnidirectional model
        # define the camera matrix
        K = np.asarray([[prof[0], 0., prof[1]],
                        [0., prof[0], prof[2]],
                        [0., 0., 1.]])
        src = np.zeros((1, pts.shape[0], 2), dtype=np.float32)
        src[0] = pts
        ret = cv2.undistortPoints(src, K, prof[-5:], P=K)
        return ret[0]

    else:
        # return prof.undistort_points(pts.T).T # broken due to numpy 1d transpose no-op
        return prof.undistort_points(pts.reshape((-1, 1))).T


"""
Takes:
    - pts: Nx2 array of pixel coordinates
    - prof: either an array of pinhole distortion coefficients or a Omnidirectional distortion object from Argus
Returns:
    - Nx2 array of distorted pixel coordinates
"""

# redistort by projecting a 3D point with arbitrary depth back into the image plane using OpenCV
def redistort_pts(pts, prof):
    # try block to discern the use of omnidirectional model
    if (type(prof) == list) or (type(prof) == np.ndarray):
        prof = np.array(prof)
        if len(prof) == 8:
            # rotaion is the identity matrix
            # translation is zero
            prof = np.array(prof)
            rvec = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], np.float)  # rotation vector
            tvec = np.array([0, 0, 0], np.float)  # translation vector

            # define K, the camera matrix
            cameraMatrix = np.asarray([[prof[0], 0., prof[1]],
                                       [0., prof[0], prof[2]],
                                       [0., 0., 1.]])

            p = np.hstack((normalize(pts, prof), np.tile(1, (pts.shape[0], 1))))
            return np.reshape(cv2.projectPoints(p, rvec, tvec, cameraMatrix, prof[-5:])[0], pts.shape)
        else:
            raise ArgusError('pinhole distortion profile must contain exactly 8 coefficients')
    else:
        return prof.distort_points(pts.T).T


"""
Takes:
    - pts: Nx2 array of pixel coordinates
    - prof: either an array of pinhole distortion coefficients or a Omnidirectional distortion object from Argus
Returns:
    - Nx2 array of normalized pixel coordinates
"""


# normalize pixel coordinates based on focal length and optical center
def normalize(pts, prof):
    if type(pts) == np.ndarray:
        if len(pts.shape) != 2:
            raise ArgusError('pts must be a two dimensional array')
        if pts.shape[1] != 2:
            raise ArgusError('pts must be an Nx2 array')
    else:
        raise ArgusError('pts must be a numpy array')
    for k in range(len(pts)):
        pts[k][0] = (pts[k][0] - prof[1]) / prof[0]
        pts[k][1] = (pts[k][1] - prof[2]) / prof[0]
    return pts


# solves an overdetermined linear system for DLT coefficients constructed via
# these instructions: http://kwon3d.com/theory/dlt/dlt.html
"""
Takes:
    - xyz: Nx3 array of 3d coordinates
    - uv: Nx2 array of pixel coordinates
Returns:
    - L: 11 DLT coefficients mapping the transform between image plane and 3d space
    - rmse: Root mean squared error of the mapping in pixels
"""


def solve_dlt(xyz, uv):
    if type(xyz) == np.ndarray and type(uv) == np.ndarray:
        if len(xyz.shape) != 2 or len(uv.shape) != 2:
            raise ArgusError('xyz and uv must be 2-d arrays')
        if xyz.shape[0] != uv.shape[0]:
            raise ArgusError('xyz and uv must have the same number of rows')
        if xyz.shape[1] != 3:
            raise ArgusError('xyz must be an Nx3 array')
        if uv.shape[1] != 2:
            raise ArgusError('uv must be an Nx2 array')
    else:
        raise ArgusError('uv and xyz must be numpy arrays')

    # delete rows which have nans
    toDel = list()
    for k in range(uv.shape[0]):
        if True in np.isnan(uv[k]):
            toDel.append(k)

    xyz = np.delete(xyz, toDel, axis=0)
    uv = np.delete(uv, toDel, axis=0)

    A = np.zeros((xyz.shape[0] * 2, 11))

    # construct matrix based on uv pairs and xyz coordinates
    for k in range(xyz.shape[0]):
        A[2 * k, :3] = xyz[k]
        A[2 * k, 3] = 1
        A[2 * k, 8:] = xyz[k] * -uv[k, 0]
        A[2 * k + 1, 4:7] = xyz[k]
        A[2 * k + 1, 7] = 1
        A[2 * k + 1, 8:] = xyz[k] * -uv[k, 1]

    B = np.zeros((uv.shape[0] * 2, 1))

    for k in range(uv.shape[0]):
        B[2 * k] = uv[k, 0]
        B[2 * k + 1] = uv[k, 1]

    # solve using numpy's least squared algorithm
    L = np.linalg.lstsq(A, B)[0]

    # reproject to calculate rmse
    reconsted = np.zeros((uv.shape[0], 2))
    for k in range(uv.shape[0]):
        u = (np.dot(L[:3].T, xyz[k]) + L[3]) / (np.dot(L[-3:].T, xyz[k]) + 1.)
        v = (np.dot(L[4:7].T, xyz[k]) + L[7]) / (np.dot(L[-3:].T, xyz[k]) + 1.)
        reconsted[k] = [u, v]

    errors = list()
    # dof = float(self.ncams*2 - 3)

    error = 0
    for k in range(uv.shape[0]):
        s = np.sqrt((reconsted[k, 0] - uv[k, 0]) ** 2 + (reconsted[k, 1] - uv[k, 1]) ** 2)
        errors.append(s)
        error += s

    rmse = error / float(uv.shape[0])

    return L, rmse


# solves an overdetermined linear system for xyz coordinates given uv coordinates from n cameras in a given frame
# takes pts from all frames in a given track (pts) and DLT coefficients for the n cameras (dlt)
# math from kwon3d.com/theory/dlt/dlt.html
"""
Takes:
    - pts: Nx(2*number of cameras) array of points
    - profs: iterable of distortion profiles, must have number of cameras elements
    - dlt: (number of cameras)x11 array of DLT coefficients
Returns:
    - XYZ: Nx3 array of 3d coordinates
"""


#def uv_to_xyz(pts, profs, dlt):
def uv_to_xyz(pts, dlt, profs=None):
    if profs is not None:
        if (int(pts.shape[1] / 2) != len(profs)) or (int(pts.shape[1] / 2) != len(dlt)):
            raise ArgusError(
                'the length of the profile list and DLT coefficients should match the number of cameras present')
    else:
        print("No camera profile loaded, proceding with potentially distorted reconstruction")
        if (int(pts.shape[1] / 2) != len(dlt)):
            raise ArgusError(
                'the length of the DLT coefficients should match the number of cameras present')

    # pts = pts.toarray()

    xyzs = np.zeros((len(pts), 3))
    # for each frame
    for i in range(len(pts)):
        uvs = list()
        # for each uv pair
        for j in range(int(len(pts[i]) / 2)):
            # do we have a NaN pair?
            if not True in np.isnan(pts[i, 2 * j:2 * (j + 1)]):
                # if not append the undistorted point and its camera number to the list
                if profs is None:
                    uvs.append([pts[i, 2 * j:2 * (j + 1)], j])
                else:
                    uvs.append([undistort_pts(pts[i, 2 * j:2 * (j + 1)], profs[j])[0], j])

        if len(uvs) > 1:
            # if we have at least 2 uv coordinates, setup the linear system
            A = np.zeros((2 * len(uvs), 3))

            for k in range(len(uvs)):
                A[2*k] = np.asarray([uvs[k][0][0] * dlt[uvs[k][1]][8] - dlt[uvs[k][1]][0],
                                   uvs[k][0][0] * dlt[uvs[k][1]][9] - dlt[uvs[k][1]][1],
                                   uvs[k][0][0] * dlt[uvs[k][1]][10] - dlt[uvs[k][1]][2]])
                A[2*k + 1] = np.asarray([uvs[k][0][1] * dlt[uvs[k][1]][8] - dlt[uvs[k][1]][4],
                                       uvs[k][0][1] * dlt[uvs[k][1]][9] - dlt[uvs[k][1]][5],
                                       uvs[k][0][1] * dlt[uvs[k][1]][10] - dlt[uvs[k][1]][6]])

            B = np.zeros((2 * len(uvs), 1))
            for k in range(len(uvs)):
                B[2*k] = dlt[uvs[k][1]][3] - uvs[k][0][0]
                B[2*k + 1] = dlt[uvs[k][1]][7] - uvs[k][0][1]

            # solve it
            xyz = np.linalg.lstsq(A, B, rcond=None)[0]
            # place in the proper frame
            xyzs[i] = xyz[:, 0]

    # replace everything else with NaNs
    xyzs[xyzs == 0] = np.nan
    return xyzs


# gets reprojection errors for all 3D points in an array
"""
    get_repo_errors:
    ====================================
    Takes 3D coordinates, uv pixel coordinates, and a camera profile.  Finds the RMSE for each frame in each track.
    RMSEs for two camera situations are replaced by the average RMSE for all two camera situations, as they are viewed
    an unreliable estimate for error.  Uses the function above, xyz_to_uv to project into the image plane and then calculate
    squared error for each frame in each track.

Takes:
    - xyzs: Nx(3*k) array of 3d points where k = number of individual tracks
    - pts: Nx(2*n*k) array of pixel coordinates where n is the number of cameras
    - prof: iterable of camera intrinsic information
    - dlt: nx11 array of DLT coefficients or list of Ocam undistorter objects
    
Returns:
    - k*N array of reprojection errors
"""


def get_repo_errors(xyzs, pts, prof, dlt):
    # error catching non-sensical inputs
    if prof is not None:
        if ((not hasattr(prof, '__iter__')) or (not hasattr(dlt, '__iter__'))):
            raise ArgusError('camera profile and dlt coefficients must be iterables')
    else:
        if (not hasattr(dlt, '__iter__')):
            raise ArgusError('dlt coefficients must be iterables')

    if type(xyzs) != np.ndarray:
        raise ArgusError('xyz values must be an N*(3*k) array, where k is the number of tracks')
    elif len(xyzs.shape) == 2:
        if (xyzs.shape[1] % 3) != 0:
            raise ArgusError('xyz values must be an N*(3*k) array, where k is the number of tracks')
    else:
        raise ArgusError('xyz values must be an N*(3*k) array, where k is the number of tracks')

    # pts = pts.toarray()
    errorss = list()
    # how many tracks, for each track
    for k in range(int(xyzs.shape[1] / 3)):
        xyz = xyzs[:, 3 * k:3 * (k + 1)]
        uv = pts[:, k * (2 * len(dlt)):(k + 1) * (2 * len(dlt))]
        errors = np.zeros(xyz.shape[0])

        twos = list()
        s = 0

        # for each point in track
        for j in range(xyz.shape[0]):
            if not True in np.isnan(xyz[j]):
                toSum = list()
                for i in range(int(uv.shape[1] / 2)):
                    if not np.isnan(uv[j, i * 2]):
                        if prof is not None:
                            ob = undistort_pts(np.array([uv[j, i * 2:(i + 1) * 2]]), prof[i])[0]
                        else:
                            ob = np.array([uv[j, i * 2:(i + 1) * 2]])[0]
                        re = reconstruct_uv(dlt[i], xyz[j])
                        toSum.append(((ob[0] - re[0]) ** 2 + (ob[1] - re[1]) ** 2))
                epsilon = sum(toSum)
                errors[j] = np.sqrt(epsilon / float(len(toSum) * 2 - 3))
                if len(toSum) == 2:
                    twos.append(j)
                    s += errors[j]
                if errors[j] == np.nan or errors[j] == 0:
                    print('Somethings wrong!', uv[j], xyz[j])
        # rmse error from two cameras unreliable, replace with the average rmse over all two camera situations
        # if len(twos) > 1:
        #     s = s / float(len(twos))
        #     errors[twos] = s
        errorss.append(errors)
    ret = np.asarray(errorss)
    ret[ret == 0] = np.nan
    return ret


# Based on Tys code in Matlab for producing 95% CI
"""
    bootStrapXYZs:
    ===========================
    Uses bootstrapping to estimate (1-2*alpha)% confidence intervals for XYZ points, spline weights, and error tolerances to 1 dimensional
    splines used to estimate continuous 3d trajectories.  Bootstrapping is accomplished by taking the original marked uv pixel coordinate
    perturbing it randomly according to a standard normal distribution with a variance defined by pre-calculated rmses. A perturbed point
    is projected into 3D coordinates bsIter times, and then the using the standard deviation we arrive at 3D CIs.

Takes:
    - pts: an N*(2*k*n) array where n is the number of cameras, k is the number of tracks, and N is the number of frames
    - rmses: a N*k array that contains pre-computed rmses for the N frames.
    - prof: an iterable with coefficients of Ocam undistorter objects, len(prof) == n
    - dlt: an iterable with DLT coefficients, len(dlt) == n
    
Returns:
    CIs: an N*(6*k) array of 3D confidence intervals.  If k == 1, columns would be x_lower, y_lower, z_lower, x_upper, y_upper, z_upper
    weights: spline weights
    tols: spline error tolerances
"""


def bootstrapXYZs(pts, rmses, prof, dlt, bsIter=250, display_progress=False, subframeinterp=True):
    #do subframe interpolation of xypoint data based on cam1; overwrite pts input
    camlist = list(range(len(dlt)))
    numcams = len(dlt)
    numpts = int(pts.shape[1] / (2 * len(dlt)))
    if subframeinterp and len(camlist)>2:
        print('Checking subframe interpolation')
        redormse=False
        xs = np.arange(len(pts))
        step = list(np.linspace(-1, 1, 21))
        # for each camera after the first
        for c in range(1,len(dlt)):
            steprmses = np.zeros((21, numpts))*np.nan
            # for each point
            for k in range(numpts):
                c1pts = pts[:, k * 2 * len(dlt):(k * 2 * len(dlt))+2]
                cpts_clean = pts[:, k * 2 * len(dlt) + c*2 : k * 2 * len(dlt) + c*2 + 2]
                #need other cam (ocam) pts to make erros work well, always use cam2, except when cam2 is being tested, then use cam 3
                ocam = 1 if c > 1 else 2
                ocpts = pts[:, k * 2 * len(dlt) + ocam*2 : k * 2 * len(dlt) + ocam*2 + 2]
                fin = np.where(np.isfinite(cpts_clean[:,0]))[0]
                if not np.any(fin):
                    continue
                # interp from -1 to 1 by 0.1
                for id in range(len(step)):
                    s = step[id]
                    cpts=cpts_clean.copy()
                    cpts[fin] = interpolate.interp1d(fin, cpts[fin], axis=0, kind='linear', fill_value='extrapolate')(fin + s)
                    # reconstruct
                    spts = np.hstack([c1pts, ocpts, cpts])
                    threecam = np.where(np.sum(np.isfinite(spts), axis=1)>4)[0]
                    spts=spts[threecam]
                    sprof = np.vstack([prof[0], prof[ocam], prof[c]])
                    sdlt = np.vstack([dlt[0], dlt[ocam], dlt[c]])
                    sxyzs = uv_to_xyz(spts, sdlt, sprof)
                    srms = get_repo_errors(sxyzs, spts, sprof, sdlt)
                    # capture rmse
                    steprmses[id,k]= np.nanmedian(srms)
            # sum rmse for all points for each step, find the min index, and get the offset
            poff = step[np.nanargmin(np.nanmedian(steprmses, axis=1))]
            if poff !=0:
                redormse=True
                print('partial offset of {} frames found for cam {}, remaking pts'.format(poff, c+1))
                # reconstruct the new values, and overwrite in pts and rmse
                for k in range(int(pts.shape[1] / (2 * len(dlt)))):
                    cpts = pts[:, k * 2 * len(dlt) + c * 2: k * 2 * len(dlt) + c * 2 + 2]
                    fin = np.where(np.isfinite(cpts_clean[:,0]))[0]
                    cpts[fin] = interpolate.interp1d(fin, cpts[fin], axis=0, kind='linear', fill_value='extrapolate')(fin + poff)
                    pts[:, k * 2 * len(dlt) + c * 2: k * 2 * len(dlt) + c * 2 + 2] = cpts
        #get new rmses since partial offsets were found
        if redormse:
            xyzs = np.zeros((pts.shape[0], int(3 * pts.shape[1] / (2 * len(dlt))))) * np.nan
            for k in range(int(pts.shape[1] / (2 * len(dlt)))):
                track = pts[:, k * 2 * len(dlt):(k + 1) * 2 * len(dlt)]
                txyzs = uv_to_xyz(track, dlt, prof)
                xyzs[:,k*3:(k+1)*3]=txyzs
            rmses = get_repo_errors(xyzs, pts, prof, dlt).T
    ret = np.zeros((pts.shape[0], int(3 * pts.shape[1] / (2 * len(dlt)))))

    # for each track
    for k in range(numpts):
        print('processing point {} of {}'.format(k+1, numpts))
        # bootstrap matrix 
        xyzBS = np.zeros((pts.shape[0], 3, bsIter))
        xyzBS[xyzBS == 0] = np.nan
        # standard deviation matrix
        xyzSD = np.zeros((pts.shape[0], 3))
        xyzSD[xyzSD == 0] = np.nan
        # track (k+1)
        track = pts[:, k * 2 * len(dlt):(k + 1) * 2 * len(dlt)]
        # find the number of cameras with digitized points at eah row of pts
        camSum = np.nansum(np.isfinite(track), axis=1)/2
        # for each bootstrap
        if not display_progress:
            for j in range(bsIter):
                ran = np.random.randn(track.shape[0], track.shape[1])
                per = ran * np.tile((rmses[:,k]*2**0.5/camSum).reshape((-1,1)), (1, 2*numcams)) + track
                xyzBS[:, :, j] = uv_to_xyz(per, dlt, prof)
        else:
            for j in tqdm(list(range(bsIter))):
                ran = np.random.randn(track.shape[0], track.shape[1])
                per = ran * np.tile((rmses[:, k] * 2 ** 0.5 / camSum).reshape((-1, 1)), (1, 2 * numcams)) + track
                xyzBS[:, :, j] = uv_to_xyz(per, dlt, prof)
        xyzSD = np.nanstd(xyzBS, axis=2, ddof=1)
        xyzSD[xyzSD==0] = np.nan
        ret[:, k * 3:(k + 1) * 3] = xyzSD

    weights=1/(ret/np.tile(np.nanmin(ret, axis=0),(ret.shape[0],1)))
    tols = np.nansum(np.multiply(weights, np.power(ret,2)), axis=0)
    # tols = np.zeros(weights.shape[1])
    # for j in range(len(tols)):
    #     tols[j] = np.nansum(np.multiply(weights[:, j], np.power(ret[:, j], 2)))

    return ret * 1.96, weights, tols
