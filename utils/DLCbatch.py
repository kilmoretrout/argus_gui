#!/usr/bin/env python3
"""
DLC Batch Processing Script for Argus GUI
==========================================

This script processes DeepLabCut H5 files in batch mode, performing 3D reconstruction
and exporting results to CSV format.

Usage:
    python DLCbatch.py /path/to/data/directory --threshold 0.95

Directory structure expected:

    ├── videos-raw/          # Contains videos and DLC pose estimation H5 files named cam1_*, cam2_*, etc.
    ├── calibration/
    │   ├── *clicker-profile.txt     # Camera intrinsics
    │   └── *dlt-coefficients.csv    # DLT coefficients
    
Output:
    CSV files with columns: track_x, track_y, track_z, track_error, track_ncams, track_score

NOTES:
Currently in testing mode and not fully documented!
"""

import os
import sys
import argparse
import glob
import pandas as pd
import numpy as np
from collections import defaultdict
import re
import logging
from datetime import datetime

# Add argus_gui to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from argus_gui.tools import uv_to_xyz, get_repo_errors
try:
    import argus.ocam
    ARGUS_OCAM_AVAILABLE = True
except ImportError:
    ARGUS_OCAM_AVAILABLE = False


class DLCBatchProcessor:
    def __init__(self, data_dir, likelihood_threshold=0.95, optimize_cameras=True, 
                 use_filtered=True, shuffle=1):
        self.data_dir = data_dir
        self.likelihood_threshold = likelihood_threshold
        self.optimize_cameras = optimize_cameras
        self.use_filtered = use_filtered
        self.shuffle = shuffle
        self.camera_profile = None
        self.dlt_coefficients = None
        self.videos_dir = os.path.join(data_dir, 'videos-raw')
        self.calibration_dir = os.path.join(data_dir, 'calibration')
        
        # Set up logging
        self.log_file = os.path.join(data_dir, 'DLCBatch_log.txt')
        self._setup_logging()
        
        # Validate directory structure
        self._validate_directories()
        
        # Load calibration files
        self._load_calibration()
    
    def _setup_logging(self):
        """Set up logging to both file and console."""
        # Create logger
        self.logger = logging.getLogger('DLCBatch')
        self.logger.setLevel(logging.INFO)
        
        # Remove any existing handlers
        self.logger.handlers = []
        
        # Create file handler
        fh = logging.FileHandler(self.log_file, mode='w')
        fh.setLevel(logging.INFO)
        
        # Create console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
                                     datefmt='%Y-%m-%d %H:%M:%S')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
        # Log startup info
        self.logger.info("="*60)
        self.logger.info("DLC Batch Processing Started")
        self.logger.info(f"Data directory: {self.data_dir}")
        self.logger.info(f"Likelihood threshold: {self.likelihood_threshold}")
        self.logger.info(f"Camera optimization: {self.optimize_cameras}")
        self.logger.info(f"Use filtered files: {self.use_filtered}")
        self.logger.info(f"Shuffle number: {self.shuffle}")
        self.logger.info("="*60)
    
    def _validate_directories(self):
        """Check that required directories exist."""
        if not os.path.exists(self.videos_dir):
            raise FileNotFoundError(f"videos-raw directory not found: {self.videos_dir}")
        if not os.path.exists(self.calibration_dir):
            raise FileNotFoundError(f"calibration directory not found: {self.calibration_dir}")
    
    def _load_calibration(self):
        """Load camera profile and DLT coefficients."""
        # Find camera profile file
        profile_files = glob.glob(os.path.join(self.calibration_dir, '*clicker-profile.txt'))
        if not profile_files:
            raise FileNotFoundError("No clicker-profile.txt file found in calibration directory")
        profile_file = profile_files[0]
        # Load camera profile (similar to load_camera function in argus-click)
        camera_profile = np.loadtxt(profile_file)
        # Extract image dimensions before processing (needed for Y-coordinate flipping)
        if camera_profile.shape[1] == 12:
            # Columns: [cam_num, focal_len, width, height, cx, cy, skew, distortion_params...]
            self.image_heights = camera_profile[:, 3]  # Column 3 is image height
            self.image_widths = camera_profile[:, 2]   # Column 2 is image width for reference
        
        # Format camera profile based on type (from argus-click load_camera function)
        if camera_profile.shape[1] == 12:
            # Pinhole distortion - remove camera number, width, height, and skew columns
            self.camera_profile = np.delete(camera_profile, [0, 2, 3, 6], axis=1)
        elif camera_profile.shape[1] == 13:
            # CMei's omnidirectional distortion model
            new_list = []
            camera_number_checker = 1
            for profile in camera_profile:
                if profile[0] != camera_number_checker:
                    raise ValueError(f"Camera index mismatch in profile line {camera_number_checker}")
                # Remove camera index and create undistorter
                profile = np.delete(profile, [0])
                if ARGUS_OCAM_AVAILABLE:
                    new_list.append(argus.ocam.CMeiUndistorter(argus.ocam.ocam_model.from_array(profile)))
                else:
                    raise ImportError("argus.ocam module not available for omnidirectional cameras")
                camera_number_checker += 1
            self.camera_profile = new_list
        elif camera_profile.shape[1] == 19:
            # Scaramuzza's omnidirectional distortion model  
            new_list = []
            camera_number_checker = 1
            for profile in camera_profile:
                if profile[0] != camera_number_checker:
                    raise ValueError(f"Camera index mismatch in profile line {camera_number_checker}")
                # Remove camera index and create undistorter
                profile = np.delete(profile, [0])
                if ARGUS_OCAM_AVAILABLE:
                    new_list.append(argus.ocam.PointUndistorter(argus.ocam.ocam_model.from_array(profile)))
                else:
                    raise ImportError("argus.ocam module not available for omnidirectional cameras")
                camera_number_checker += 1
            self.camera_profile = new_list
        else:
            raise ValueError(f"Unsupported camera profile format: {camera_profile.shape[1]} columns")
        
        # Find DLT coefficients file
        dlt_files = glob.glob(os.path.join(self.calibration_dir, '*dlt-coefficients.csv'))
        if not dlt_files:
            raise FileNotFoundError("No dlt-coefficients.csv file found in calibration directory")
        dlt_file = dlt_files[0]
        # Load DLT coefficients (exact same as argus-click load_DLT function, lines 488-489)
        self.dlt_coefficients = np.loadtxt(dlt_file, delimiter=',')
        self.dlt_coefficients = self.dlt_coefficients.T  # Transpose like argus-click does
    
    def _find_trials(self):
        """Find all unique trials based on H5 file naming patterns."""
        all_h5_files = glob.glob(os.path.join(self.videos_dir, '*.h5'))
        if not all_h5_files:
            raise FileNotFoundError("No H5 files found in videos-raw directory")
        
        # Filter H5 files based on filtered and shuffle criteria
        h5_files = []
        filtered_pattern = 'filtered' if self.use_filtered else ''
        shuffle_pattern = f'shuffle{self.shuffle}'
        
        for h5_file in all_h5_files:
            basename = os.path.basename(h5_file)
            
            # Check filtered requirement
            if self.use_filtered and 'filtered' not in basename:
                continue
            elif not self.use_filtered and 'filtered' in basename:
                continue
            
            # Check shuffle requirement
            if shuffle_pattern not in basename:
                continue
            
            h5_files.append(h5_file)
        
        if not h5_files:
            filter_desc = f"{'filtered' if self.use_filtered else 'non-filtered'} with {shuffle_pattern}"
            raise FileNotFoundError(
                f"No H5 files found matching criteria: {filter_desc}\n"
                f"Found {len(all_h5_files)} total H5 files in {self.videos_dir}"
            )
        
        self.logger.info(f"Filtered {len(all_h5_files)} H5 files down to {len(h5_files)} files matching criteria")
        self.logger.info(f"  Criteria: {'filtered' if self.use_filtered else 'non-filtered'}, shuffle{self.shuffle}")
        
        # Group files by camera+trial (before scorer)
        # We need to handle multiple scorers for the same video
        cam_trial_files = defaultdict(list)
        
        for h5_file in h5_files:
            basename = os.path.basename(h5_file)
            # Extract camera number and everything after
            match = re.match(r'cam(\d+)(.+)\.h5$', basename)
            if match:
                cam_num = int(match.group(1))
                rest = match.group(2)
                
                # Try to separate trial from scorer
                # Common pattern: cam1_trialname_scorerDLC_resnet50_...
                # We'll use the part before the last underscore as trial key
                # and group all files with same cam+trial together
                cam_trial_files[(cam_num, rest)].append(h5_file)
            else:
                self.logger.warning(f"Could not parse camera number from {basename}")
        
        # For each cam+trial group, select the most recently created file
        trials = defaultdict(list)
        for (cam_num, trial_part), file_list in cam_trial_files.items():
            if len(file_list) > 1:
                # Multiple files for same camera+trial (different scorers)
                # Select most recently created file
                most_recent = max(file_list, key=lambda f: os.path.getmtime(f))
                self.logger.info(f"Found {len(file_list)} H5 files for cam{cam_num}{trial_part}")
                self.logger.info(f"  Using most recent: {os.path.basename(most_recent)}")
                selected_file = most_recent
            else:
                selected_file = file_list[0]
            
            # Group by trial (remove scorer-specific parts from trial_id)
            # Use trial_part as the key to group cameras together
            trials[trial_part].append((cam_num, selected_file))
        
        # Sort cameras within each trial
        for trial_id in trials:
            trials[trial_id].sort(key=lambda x: x[0])  # Sort by camera number
        
        self.logger.info(f"Found {len(trials)} trials")
        return trials
    
    def _load_dlc_data(self, h5_files, trial_id):
        """Load DLC data from H5 files for a single trial."""
        self.logger.info(f"Processing trial: {trial_id}")
        
        all_data = {}
        track_names = None
        max_frames = 0
        
        # h5_files is already sorted by camera number (see _find_trials). The
        # camera profile/DLT coefficients only have one row per camera actually
        # used in calibration, ordered positionally - the literal camera number
        # parsed from the filename (e.g. 3 for cam3) does NOT necessarily match
        # that row index (e.g. a 2-camera profile for cam1+cam3 has rows 0 and 1,
        # not 0 and 2). Use the position within h5_files for that indexing.
        for cam_pos, (cam_num, h5_file) in enumerate(h5_files):
            self.logger.info(f"  Loading camera {cam_num}: {os.path.basename(h5_file)}")
            
            try:
                # Load H5 file - try common DLC keys
                df = None
                common_keys = ['df_with_missing', 'df']  # Common DLC HDF5 keys
                
                for key in common_keys:
                    try:
                        df = pd.read_hdf(h5_file, key=key)
                        break  # Successfully loaded
                    except KeyError:
                        continue  # Try next key
                
                if df is None:
                    # No valid data found, skip this file silently
                    continue
                
                scorer_name = df.columns.get_level_values('scorer')[0]
                self.logger.info(f"    Using scorer: {scorer_name}")
                
                # Get track names from first file
                if track_names is None:
                    # Find bodypart level name
                    bodypart_level = None
                    for level_name in df.columns.names:
                        if level_name and isinstance(level_name, str) and 'bodypart' in level_name.lower():
                            bodypart_level = level_name
                            break
                    
                    if bodypart_level:
                        track_names = df.columns.get_level_values(bodypart_level).unique().tolist()
                    else:
                        raise ValueError("No bodypart level found in DLC data")
                
                # Determine if this is multi-animal DLC by checking MultiIndex structure
                is_multi_animal = hasattr(df.columns, 'nlevels') and df.columns.nlevels == 4
                
                if is_multi_animal:
                    # Multi-animal DLC - for now, just handle single animal case
                    self.logger.info("    Multi-animal DLC detected - using first individual")
                    
                    # Find the individual/animal level name (could be 'individual', 'individuals', or 'animal')
                    individual_level = None
                    for level_name in df.columns.names:
                        if level_name and isinstance(level_name, str) and level_name.lower() in ['individual', 'individuals', 'animal']:
                            individual_level = level_name
                            break
                    
                    if individual_level is None:
                        raise ValueError("Could not find individual/animal level in multi-animal DLC data")
                    
                    individuals = df.columns.get_level_values(individual_level).unique().tolist()
                    individual = individuals[0]
                    cam_data = df[scorer_name][individual]
                else:
                    # Single animal DLC
                    cam_data = df[scorer_name]
                
                # Apply likelihood threshold filtering
                for track in track_names:
                    if track in cam_data.columns.get_level_values(0):
                        likelihood = cam_data[track]['likelihood'].values.copy()
                        x_vals = cam_data[track]['x'].values.copy()
                        y_vals = cam_data[track]['y'].values.copy()
                        
                        # Flip Y coordinates from DeepLabCut (upper-left origin) to DLT (lower-left origin)
                        # Y_dlt = image_height - Y_dlc
                        # Use cam_pos (position among sorted cameras present), not the literal
                        # camera number, since the profile is indexed positionally.
                        if hasattr(self, 'image_heights') and cam_pos < len(self.image_heights):
                            image_height = self.image_heights[cam_pos]
                            y_vals = image_height - y_vals
                        
                        # Set coordinates to NaN where likelihood is below threshold
                        low_likelihood_mask = likelihood <= self.likelihood_threshold
                        x_vals[low_likelihood_mask] = np.nan
                        y_vals[low_likelihood_mask] = np.nan
                        
                        # Store the filtered data
                        if cam_num not in all_data:
                            all_data[cam_num] = {}
                        all_data[cam_num][track] = {
                            'x': x_vals,
                            'y': y_vals,
                            'likelihood': likelihood
                        }
                
                max_frames = max(max_frames, len(df))
                
            except Exception as e:
                self.logger.error(f"    Error loading {h5_file}: {e}")
                continue
        
        return all_data, track_names, max_frames
    
    def _format_data_for_reconstruction(self, all_data, track_names, max_frames):
        """Format loaded DLC data for 3D reconstruction."""
        n_cameras = len(all_data)
        n_tracks = len(track_names)
        
        # Create data array: frames x (2 * cameras * tracks)
        # IMPORTANT: Must match argus-click format which is:
        # [track1_cam1_x, track1_cam1_y, track1_cam2_x, track1_cam2_y, ..., track2_cam1_x, track2_cam1_y, ...]
        pts_data = np.full((max_frames, 2 * n_cameras * n_tracks), np.nan)
        
        camera_list = sorted(all_data.keys())  # e.g. [1, 3] -> positions 0, 1
        for track_idx, track in enumerate(track_names):
            for cam_pos, cam_num in enumerate(camera_list):
                if track in all_data[cam_num]:
                    cam_idx = cam_pos  # sequential position, not cam_num - 1
                    
                    # Calculate column indices for this camera and track
                    # argus-click format: each track gets (2 * n_cameras) columns
                    base_col = track_idx * (2 * n_cameras) + cam_idx * 2
                    
                    track_data = all_data[cam_num][track]
                    x_data = track_data['x']
                    y_data = track_data['y']
                    
                    # Ensure we don't exceed max_frames
                    data_len = min(len(x_data), max_frames)
                    
                    pts_data[:data_len, base_col] = x_data[:data_len]      # x coordinates
                    pts_data[:data_len, base_col + 1] = y_data[:data_len]  # y coordinates
        
        return pts_data
    
    def _calculate_scores_and_ncams(self, all_data, track_names, max_frames):
        """Calculate average likelihood scores and number of cameras per point."""
        n_tracks = len(track_names)
        
        scores = np.full((max_frames, n_tracks), np.nan)
        ncams = np.zeros((max_frames, n_tracks), dtype=int)
        
        for track_idx, track in enumerate(track_names):
            for frame in range(max_frames):
                valid_likelihoods = []
                n_valid_cams = 0
                
                for cam_num in sorted(all_data.keys()):
                    if (cam_num in all_data and track in all_data[cam_num] and 
                        frame < len(all_data[cam_num][track]['likelihood'])):
                        
                        likelihood = all_data[cam_num][track]['likelihood'][frame]
                        x_val = all_data[cam_num][track]['x'][frame]
                        y_val = all_data[cam_num][track]['y'][frame]
                        
                        # Check if this point passed the threshold (not NaN after filtering)
                        if not (np.isnan(x_val) or np.isnan(y_val)) and likelihood > self.likelihood_threshold:
                            valid_likelihoods.append(likelihood)
                            n_valid_cams += 1
                
                # Only record scores and ncams if we have at least 2 cameras
                # Single camera frames cannot be triangulated and will have NaN xyz
                if n_valid_cams >= 2:
                    scores[frame, track_idx] = np.mean(valid_likelihoods)
                    ncams[frame, track_idx] = n_valid_cams
        
        return scores, ncams
    
    def _reconstruct_with_camera_optimization(self, track_pts, track_name):
        """Reconstruct 3D coordinates with frame-by-frame outlier camera detection.
        
        For frames with 3+ cameras, detects cameras with significantly higher
        reprojection error (outliers) and excludes them from reconstruction.
        This handles cases where one camera has bad tracking despite passing
        the likelihood threshold.
        
        Args:
            track_pts: Frames x (2*n_cameras) array of pixel coordinates for one track
            track_name: Name of the track being processed
            
        Returns:
            xyz: Frames x 3 array of optimized 3D coordinates
            used_camera_mask: Frames x n_cameras boolean array, True where that
                camera's point was actually used to compute xyz for that frame.
                Cameras excluded as outliers (or unused/NaN) are False. This is
                needed so reprojection error calculations stay consistent with
                the cameras that contributed to each reconstruction - otherwise
                an excluded outlier camera's large disagreement still gets
                counted against the error even though it didn't inform xyz,
                which inflates reported errors relative to argus-click (which
                always uses every valid camera for both steps).
        """
        from argus_gui.tools import undistort_pts, reconstruct_uv
        
        n_cameras = len(self.camera_profile)
        n_frames = track_pts.shape[0]
        xyz_optimized = np.full((n_frames, 3), np.nan)
        used_camera_mask = np.zeros((n_frames, n_cameras), dtype=bool)
        
        # Track optimization statistics
        n_optimized = 0  # frames where outlier camera(s) were excluded
        
        # Process each frame independently
        for frame_idx in range(n_frames):
            frame_pts = track_pts[frame_idx, :]
            
            # Find which cameras have valid data for this frame
            valid_cameras = []
            for cam_idx in range(n_cameras):
                pt = frame_pts[cam_idx * 2:(cam_idx + 1) * 2]
                if not np.any(np.isnan(pt)):
                    valid_cameras.append(cam_idx)
            
            n_valid = len(valid_cameras)
            
            if n_valid < 2:
                # Can't triangulate with fewer than 2 cameras
                continue
            elif n_valid == 2:
                # Only one option, use these 2 cameras
                cam_subset = valid_cameras
                xyz_optimized[frame_idx] = self._reconstruct_single_frame(
                    frame_pts, cam_subset, track_pts[frame_idx:frame_idx+1, :]
                )
                used_camera_mask[frame_idx, cam_subset] = True
            else:
                # 3+ cameras: detect outlier cameras and exclude them
                # Default to using all cameras
                xyz_all = self._reconstruct_single_frame(frame_pts, valid_cameras, track_pts[frame_idx:frame_idx+1, :])
                
                if np.any(np.isnan(xyz_all)):
                    continue
                
                # Calculate per-camera reprojection errors for all-camera reconstruction
                per_cam_errors = self._get_per_camera_errors(xyz_all, frame_pts, valid_cameras)
                
                # Check if any camera is an outlier (significantly worse than others)
                # Use median absolute deviation to detect outliers
                if len(per_cam_errors) >= 3:
                    median_error = np.median(per_cam_errors)
                    mad = np.median(np.abs(per_cam_errors - median_error))
                    
                    # Identify outlier cameras (error > median + 2*MAD)
                    # Only exclude if the outlier is significantly bad
                    threshold = median_error + 2 * max(mad, 0.5)  # At least 0.5 pixel threshold
                    outlier_indices = [i for i, err in enumerate(per_cam_errors) if err > threshold]
                    
                    if outlier_indices and len(valid_cameras) - len(outlier_indices) >= 2:
                        # Exclude outlier camera(s) and reconstruct
                        good_cameras = [valid_cameras[i] for i in range(len(valid_cameras)) 
                                       if i not in outlier_indices]
                        xyz_optimized[frame_idx] = self._reconstruct_single_frame(
                            frame_pts, good_cameras, track_pts[frame_idx:frame_idx+1, :]
                        )
                        used_camera_mask[frame_idx, good_cameras] = True
                        n_optimized += 1
                    else:
                        # No significant outliers, use all cameras
                        xyz_optimized[frame_idx] = xyz_all
                        used_camera_mask[frame_idx, valid_cameras] = True
                else:
                    # Not enough cameras to detect outliers, use all
                    xyz_optimized[frame_idx] = xyz_all
                    used_camera_mask[frame_idx, valid_cameras] = True
        
        # Print optimization summary
        n_multi_cam = np.sum([len([c for c in range(n_cameras) 
                                    if not np.any(np.isnan(track_pts[i, c*2:(c+1)*2]))]) >= 3 
                              for i in range(n_frames)])
        if n_multi_cam > 0:
            self.logger.info(f"      {track_name}: {n_optimized}/{n_multi_cam} frames had outlier camera(s) excluded")
        
        return xyz_optimized, used_camera_mask
    
    def _get_per_camera_errors(self, xyz, frame_pts, cam_indices):
        """Calculate reprojection error for each camera individually.
        
        Args:
            xyz: (3,) array of 3D coordinates
            frame_pts: (2*n_cameras,) array of pixel coordinates
            cam_indices: List of camera indices to calculate errors for
            
        Returns:
            errors: List of reprojection errors (in pixels) for each camera
        """
        from argus_gui.tools import undistort_pts, reconstruct_uv
        
        errors = []
        for cam_idx in cam_indices:
            pt_observed = frame_pts[cam_idx * 2:(cam_idx + 1) * 2]
            if np.any(np.isnan(pt_observed)):
                errors.append(np.inf)  # Mark missing data as infinite error
                continue
            
            # Undistort observed point
            pt_undist = undistort_pts(np.array([pt_observed]), self.camera_profile[cam_idx])[0]
            
            # Reproject 3D point back to this camera
            pt_reproj = reconstruct_uv(self.dlt_coefficients[cam_idx], xyz)
            
            # Calculate reprojection error in pixels
            error = np.sqrt((pt_undist[0] - pt_reproj[0])**2 + (pt_undist[1] - pt_reproj[1])**2)
            errors.append(error)
        
        return np.array(errors)
    
    def _reconstruct_single_frame(self, frame_pts, cam_indices, pts_subset):
        """Reconstruct 3D point from a subset of cameras for a single frame.
        
        Args:
            frame_pts: (2*n_cameras,) array of pixel coordinates for one frame
            cam_indices: List of camera indices to use
            pts_subset: (1, 2*n_cameras) array (for compatibility)
            
        Returns:
            xyz: (3,) array of 3D coordinates
        """
        # Build subset of profiles and DLT coefficients
        if isinstance(self.camera_profile, list):
            prof_subset = [self.camera_profile[i] for i in cam_indices]
        else:
            prof_subset = self.camera_profile[cam_indices, :]
        dlt_subset = self.dlt_coefficients[cam_indices, :]
        
        # Build pts array for just these cameras
        pts_for_recon = np.full((1, 2 * len(cam_indices)), np.nan)
        for new_idx, cam_idx in enumerate(cam_indices):
            pts_for_recon[0, new_idx * 2:(new_idx + 1) * 2] = frame_pts[cam_idx * 2:(cam_idx + 1) * 2]
        
        # Reconstruct
        xyz = uv_to_xyz(pts_for_recon, prof_subset, dlt_subset)
        return xyz[0] if len(xyz) > 0 else np.full(3, np.nan)
    
    def _perform_3d_reconstruction(self, pts_data, track_names, optimize_camera_selection=True):
        """Perform 3D reconstruction using uv_to_xyz.
        
        Args:
            pts_data: Frame x (2*cameras*tracks) array of pixel coordinates
            track_names: List of track names
            optimize_camera_selection: If True, test 2-camera combinations when 3+ cameras available
                                      and use the combination with lowest reprojection error
        """
        n_tracks = len(track_names)
        max_frames = pts_data.shape[0]
        n_cameras = len(self.camera_profile)
        
        if self.camera_profile is None:
            raise ValueError("Camera profile is None")
        
        # Reconstruct each track separately
        xyz_results = []
        
        # pts_for_errors starts as a copy of the raw pixel data. When camera
        # optimization excludes an outlier camera from a frame's reconstruction,
        # that camera's point is also blanked out here so the reprojection error
        # calculation below only considers cameras that actually contributed to
        # xyz. Without this, an excluded outlier camera's large disagreement with
        # xyz still gets counted as error even though it was deliberately left out
        # of the triangulation, which inflates reported errors far above what
        # argus-click/Clicker would compute (Clicker always uses every valid
        # camera for both triangulation and error calculation, so there's never
        # a mismatch there).
        pts_for_errors = pts_data.copy()
        
        for track_idx in range(n_tracks):
            # Extract data for this track (all cameras) - exact argus-click pattern
            # argus-click: pts[:, j * 2 * len(camera_profile):(j + 1) * 2 * len(camera_profile)]
            track_pts = pts_data[:, track_idx * 2 * n_cameras:(track_idx + 1) * 2 * n_cameras]
            
            try:
                if optimize_camera_selection and n_cameras >= 3:
                    # Perform frame-by-frame camera optimization
                    xyz, used_camera_mask = self._reconstruct_with_camera_optimization(track_pts, track_names[track_idx])
                    
                    # Blank out excluded cameras' points for this track so error
                    # calculation matches the cameras actually used for xyz
                    track_base_col = track_idx * 2 * n_cameras
                    for cam_idx in range(n_cameras):
                        excluded_frames = ~used_camera_mask[:, cam_idx]
                        col = track_base_col + cam_idx * 2
                        pts_for_errors[excluded_frames, col:col + 2] = np.nan
                else:
                    # Standard reconstruction using all cameras
                    xyz = uv_to_xyz(track_pts, self.camera_profile, self.dlt_coefficients)
                xyz_results.append(xyz)
                
            except Exception as e:
                self.logger.error(f"    Error reconstructing {track_names[track_idx]}: {e}")
                # Fill with NaNs if reconstruction fails
                xyz_results.append(np.full((max_frames, 3), np.nan))
        
        # Calculate reprojection errors for all tracks at once (like argus-click does)
        try:
            # Concatenate all XYZ data horizontally like argus-click does
            if xyz_results:
                xyz_all = xyz_results[0]  # Start with first track
                for k in range(1, len(xyz_results)):
                    xyz_all = np.hstack((xyz_all, xyz_results[k]))
                # Calculate reprojection errors using exact same call as argus-click (line 2882),
                # but against pts_for_errors so excluded outlier cameras don't inflate the error
                all_errors = get_repo_errors(xyz_all, pts_for_errors, self.camera_profile, self.dlt_coefficients)
                
                # get_repo_errors returns (n_tracks, n_frames), so transpose like argus-click does
                all_errors = all_errors.T  # Now (n_frames, n_tracks)
                
                # Split errors back by track
                error_results = []
                for track_idx in range(n_tracks):
                    track_errors = all_errors[:, track_idx]  # Each column corresponds to a track
                    error_results.append(track_errors)
            else:
                # No valid reconstructions
                error_results = [np.full(max_frames, np.nan) for _ in range(n_tracks)]
                
        except Exception as e:
            self.logger.error(f"    Error calculating reprojection errors: {e}")
            # Fill with NaNs if error calculation fails
            error_results = [np.full(max_frames, np.nan) for _ in range(n_tracks)]
        
        return xyz_results, error_results
    
    def _extract_timestamp_from_trial_id(self, trial_id):
        """Extract timestamp from trial identifier for CSV filename."""
        # Look for datetime patterns in the trial ID
        # Common formats: _YYYY-MM-DD_HH-MM-SS, _YYYYMMDD_HHMMSS, etc.
        
        # Try different timestamp patterns
        patterns = [
            r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})',  # YYYY-MM-DD_HH-MM-SS
            r'(\d{4}\d{2}\d{2}_\d{2}\d{2}\d{2})',      # YYYYMMDD_HHMMSS
            r'(\d{8}_\d{6})',                           # YYYYMMDD_HHMMSS
            r'(\d{4}-\d{2}-\d{2})',                     # YYYY-MM-DD
            r'(\d{8})',                                 # YYYYMMDD
        ]
        
        for pattern in patterns:
            match = re.search(pattern, trial_id)
            if match:
                return match.group(1)
        
        # If no timestamp pattern found, use the trial_id itself (cleaned)
        # Remove leading/trailing underscores and replace problematic characters
        clean_id = trial_id.strip('_').replace('/', '-').replace('\\', '-').replace(' ', '_')
        return clean_id
    
    def _save_results(self, trial_id, track_names, xyz_results, error_results, scores, ncams):
        """Save results to CSV file."""
        # Create output directory if it doesn't exist
        output_dir = os.path.join(self.data_dir, 'pose-3d-argus')
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = self._extract_timestamp_from_trial_id(trial_id)
        output_file = os.path.join(output_dir, f"{timestamp}_3d_tracks.csv")
        
        max_frames = len(xyz_results[0])
        
        # Prepare data dictionary for DataFrame
        data_dict = {}
        
        # Add frame index
        data_dict['frame'] = range(max_frames)
        
        # Add data for each track
        for track_idx, track_name in enumerate(track_names):
            xyz = xyz_results[track_idx]
            errors = error_results[track_idx]
            track_scores = scores[:, track_idx]
            track_ncams = ncams[:, track_idx]
            
            # CRITICAL: Enforce that XYZ and errors are NaN when ncams < 2
            # Triangulation requires at least 2 cameras
            insufficient_cameras_mask = track_ncams < 2
            xyz_clean = xyz.copy()
            xyz_clean[insufficient_cameras_mask, :] = np.nan
            errors_clean = errors.copy()
            errors_clean[insufficient_cameras_mask] = np.nan
            
            # Add columns for this track
            data_dict[f'{track_name}_x'] = xyz_clean[:, 0]
            data_dict[f'{track_name}_y'] = xyz_clean[:, 1]
            data_dict[f'{track_name}_z'] = xyz_clean[:, 2]
            data_dict[f'{track_name}_error'] = errors_clean
            data_dict[f'{track_name}_ncams'] = track_ncams
            data_dict[f'{track_name}_score'] = track_scores
        
        # Create and save DataFrame
        df = pd.DataFrame(data_dict)
        df.to_csv(output_file, index=False, na_rep='NaN')
        
        self.logger.info(f"  Saved results to: {output_file}")
        return output_file
    
    def process_all_trials(self):
        """Process all trials in the data directory."""
        trials = self._find_trials()
        
        if self.optimize_cameras:
            self.logger.info("Camera optimization enabled: Detecting and excluding outlier cameras per frame")
        else:
            self.logger.info("Camera optimization disabled: Using all available cameras per frame")
        
        processed_files = []
        
        for trial_id, h5_files in trials.items():
            try:
                # Load DLC data
                all_data, track_names, max_frames = self._load_dlc_data(h5_files, trial_id)
                
                if not all_data or not track_names:
                    self.logger.warning(f"  No valid data found for trial {trial_id}")
                    continue
                
                # Format data for reconstruction
                pts_data = self._format_data_for_reconstruction(all_data, track_names, max_frames)
                
                # Calculate scores and camera counts
                scores, ncams = self._calculate_scores_and_ncams(all_data, track_names, max_frames)
                
                # Perform 3D reconstruction
                xyz_results, error_results = self._perform_3d_reconstruction(
                    pts_data, track_names, optimize_camera_selection=self.optimize_cameras
                )
                
                # Save results
                output_file = self._save_results(trial_id, track_names, xyz_results, error_results, scores, ncams)
                processed_files.append(output_file)
                
            except Exception as e:
                self.logger.error(f"  Error processing trial {trial_id}: {e}")
                continue
        
        self.logger.info(f"\nProcessing complete! Generated {len(processed_files)} files:")
        for file_path in processed_files:
            self.logger.info(f"  {file_path}")
        
        self.logger.info("="*60)
        self.logger.info("DLC Batch Processing Completed")
        self.logger.info(f"Log file saved to: {self.log_file}")
        self.logger.info("="*60)
        
        return processed_files


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Process DeepLabCut H5 files for 3D reconstruction',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Directory structure expected:
    data_directory/
    ├── videos-raw/          # Contains H5 files named cam1_*, cam2_*, etc.
    ├── calibration/
    │   ├── *clicker-profile.txt     # Camera intrinsics
    │   └── *dlt-coefficients.csv    # DLT coefficients

Output CSV columns for each track (example for 'L1hip'):
    L1hip_x, L1hip_y, L1hip_z, L1hip_error, L1hip_ncams, L1hip_score
        """
    )
    
    parser.add_argument('data_directory', 
                       help='Path to directory containing videos-raw and calibration folders')
    parser.add_argument('--threshold', '-t', type=float, default=0.95,
                       help='DLC likelihood threshold (default: 0.95)')
    parser.add_argument('--optimize-cameras', action='store_true', default=True,
                       help='Optimize camera selection per frame (default: enabled)')
    parser.add_argument('--no-optimize-cameras', dest='optimize_cameras', action='store_false',
                       help='Disable camera optimization, use all cameras for each frame')
    parser.add_argument('--filtered', action='store_true', default=True,
                       help='Use filtered H5 files (default: enabled)')
    parser.add_argument('--no-filtered', dest='filtered', action='store_false',
                       help='Use non-filtered H5 files')
    parser.add_argument('--shuffle', '-s', type=int, default=1,
                       help='Shuffle number to use (default: 1)')
    
    args = parser.parse_args()
    
    # Validate data directory
    if not os.path.exists(args.data_directory):
        # Can't use logger yet since it's created by the processor
        print(f"Error: Data directory does not exist: {args.data_directory}")
        sys.exit(1)
    
    try:
        # Create processor and run
        processor = DLCBatchProcessor(
            args.data_directory, 
            args.threshold, 
            optimize_cameras=args.optimize_cameras,
            use_filtered=args.filtered,
            shuffle=args.shuffle
        )
        processor.process_all_trials()
        
    except Exception as e:
        # Try to log to file if processor was created
        try:
            if 'processor' in locals() and hasattr(processor, 'logger'):
                processor.logger.error(f"Fatal error: {e}")
                processor.logger.exception("Exception details:")
        except:
            pass
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()