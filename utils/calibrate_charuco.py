#!/usr/bin/env python3
"""
Charuco Board Camera Calibration Script

This script loads multiple synchronized videos of a Charuco board, detects corners
with visual display and numbering, and outputs camera intrinsic and extrinsic
properties for 3D calibration.

"""

import cv2
import numpy as np
import toml
import glob
import os
import csv
from typing import List, Tuple, Dict
import argparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CharucoCalibrator:
    """
    A class to handle Charuco board detection and camera calibration
    from multiple synchronized video sources.
    """
    
    def __init__(self, config_path: str):
        """
        Initialize the calibrator with configuration parameters.
        
        Args:
            config_path: Path to the config.toml file containing calibration parameters
        """
        self.config_path = config_path
        self.config = self.load_config()
        self.setup_charuco_board()
        
        # Storage for calibration data
        self.all_charuco_corners = []
        self.all_charuco_ids = []
        self.all_image_points = []
        self.all_object_points = []
        self.image_sizes = {}
        
        # Expected number of corners for a full board detection
        board_size = tuple(self.config['calibration']['board_size'])
        self.expected_full_board_corners = (board_size[0] - 1) * (board_size[1] - 1)
        
        # Storage for debug visualization
        self.debug_frames = {}  # Store one frame per camera for debug
        
        # Storage for paired points information
        self.paired_points_info = {'corner_ids': None, 'physical_distance_mm': 0.0, 'detection_count': 0}
        
        # Track actual video frame indices for all-frames CSV export
        self.video_frame_indices = []  # Maps calibration frame index to actual video frame number
        self.total_video_frames = 0    # Total number of frames in the video
        
    def load_config(self) -> Dict:
        """Load configuration from TOML file."""
        try:
            with open(self.config_path, 'r') as f:
                config = toml.load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def setup_charuco_board(self):
        """Set up the Charuco board based on configuration parameters."""
        cal_config = self.config['calibration']
        
        # Get Charuco board parameters
        board_size = tuple(cal_config['board_size'])
        marker_length = cal_config['board_marker_length']
        square_length = cal_config['board_square_side_length']
        dict_number = cal_config['board_marker_dict_number']
        
        # Create ArUco dictionary and Charuco board (OpenCV 4.7+)
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(dict_number)
        self.charuco_board = cv2.aruco.CharucoBoard(
            board_size, square_length, marker_length, self.aruco_dict
        )
        
        # Create Charuco detector with parameters
        charuco_params = cv2.aruco.CharucoParameters()
        detector_params = cv2.aruco.DetectorParameters()
        self.charuco_detector = cv2.aruco.CharucoDetector(
            self.charuco_board, charuco_params, detector_params
        )
        
        logger.info(f"Created Charuco board: {board_size[0]}x{board_size[1]}, "
                   f"square_length={square_length}mm, marker_length={marker_length}mm")
    
    def find_video_files(self, calibration_dir: str) -> List[str]:
        """
        Find all video files in the calibration directory.
        
        Args:
            calibration_dir: Directory containing calibration videos
            
        Returns:
            List of video file paths
        """
        video_extensions = ['*.mp4', '*.avi', '*.mov', '*.mkv']
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(glob.glob(os.path.join(calibration_dir, ext)))
        
        video_files.sort()  # Ensure consistent ordering
        logger.info(f"Found {len(video_files)} video files: {[os.path.basename(f) for f in video_files]}")
        
        return video_files
    
    def group_videos_by_timestamp(self, video_files: List[str]) -> List[List[str]]:
        """
        Group video files by matching timestamps in filenames.
        
        Videos with the same timestamp (everything after cam1/cam2/cam3 prefix)
        are grouped together as one set.
        
        Args:
            video_files: List of video file paths
            
        Returns:
            List of video file groups, where each group contains videos from the same recording session
            
        Example:
            Input: ['cam1_07-Oct-25_13-46-11.mov', 'cam2_07-Oct-25_13-46-11.mov', 'cam3_07-Oct-25_13-46-11.mov',
                    'cam1_07-Oct-25_14-42-38.mov', 'cam2_07-Oct-25_14-42-38.mov', 'cam3_07-Oct-25_14-42-38.mov']
            Output: [['cam1_07-Oct-25_13-46-11.mov', 'cam2_07-Oct-25_13-46-11.mov', 'cam3_07-Oct-25_13-46-11.mov'],
                     ['cam1_07-Oct-25_14-42-38.mov', 'cam2_07-Oct-25_14-42-38.mov', 'cam3_07-Oct-25_14-42-38.mov']]
        """
        import re
        
        # Dictionary to group videos by timestamp: {timestamp: [video_files]}
        timestamp_groups = {}
        
        for video_file in video_files:
            basename = os.path.basename(video_file)
            
            # Try to extract camera prefix (cam1, cam2, cam3, CAM1, CAM2, etc.)
            match = re.match(r'^(cam\d+|CAM\d+)[_-](.+)$', basename, re.IGNORECASE)
            
            if match:
                timestamp_part = match.group(2)  # Everything after camera prefix
                
                # Use timestamp as the grouping key
                if timestamp_part not in timestamp_groups:
                    timestamp_groups[timestamp_part] = []
                
                timestamp_groups[timestamp_part].append(video_file)
                logger.debug(f"Video '{basename}' -> timestamp: '{timestamp_part}'")
            else:
                # If filename doesn't match expected pattern, put it in its own group
                logger.warning(f"Video '{basename}' doesn't match expected naming pattern 'camN_timestamp'. Creating separate group.")
                timestamp_groups[basename] = [video_file]
        
        # Convert dictionary to list of groups and sort
        video_groups = list(timestamp_groups.values())
        
        # Sort each group by filename to ensure cam1, cam2, cam3 order
        for group in video_groups:
            group.sort()
        
        # Sort groups by the first video in each group
        video_groups.sort(key=lambda g: g[0])
        
        # Log the grouping results
        logger.info(f"Grouped {len(video_files)} videos into {len(video_groups)} set(s):")
        for i, group in enumerate(video_groups, 1):
            logger.info(f"  Set {i}: {len(group)} videos - {[os.path.basename(f) for f in group]}")
        
        return video_groups
    
    def detect_charuco_corners(self, image: np.ndarray, camera_id: int, 
                              frame_num: int, visualize: bool = True) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Detect Charuco board corners in an image.
        
        Args:
            image: Input image
            camera_id: Camera identifier
            frame_num: Frame number
            visualize: Whether to display detection results
            
        Returns:
            Tuple of (charuco_corners, charuco_ids, display_image)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect Charuco board using the new detector API
        charuco_corners, charuco_ids, aruco_corners, aruco_ids = self.charuco_detector.detectBoard(gray)
        
        display_image = image.copy()
        ret = 0
        
        if charuco_corners is not None and charuco_ids is not None:
            ret = len(charuco_corners)
            
        if ret > 0:
            if visualize:
                # Draw detected ArUco markers if available
                if aruco_corners is not None and aruco_ids is not None:
                    cv2.aruco.drawDetectedMarkers(display_image, aruco_corners, aruco_ids)
                
                # Draw Charuco corners with numbering
                cv2.aruco.drawDetectedCornersCharuco(display_image, charuco_corners, charuco_ids)
                
                # Add corner numbers
                if charuco_corners is not None and charuco_ids is not None:
                    for i, corner_id in enumerate(charuco_ids.flatten()):
                        corner = charuco_corners[i][0]
                        cv2.putText(display_image, str(corner_id), 
                                  (int(corner[0]) + 5, int(corner[1]) - 5),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                # Add frame info
                cv2.putText(display_image, f"Cam {camera_id} Frame {frame_num}", 
                          (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(display_image, f"Corners detected: {ret}", 
                          (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            logger.debug(f"Camera {camera_id}, Frame {frame_num}: Detected {ret} corners")
        
        return charuco_corners, charuco_ids, display_image
    
    def process_videos(self, video_files: List[str], sample_frames: int = 50, 
                      display_detections: bool = True, display_delay_ms: int = 500) -> None:
        """
        Process multiple synchronized videos to collect calibration data.
        
        Args:
            video_files: List of video file paths
            sample_frames: Number of frames to sample from each video
            display_detections: Whether to display detection results
        """
        logger.info(f"Processing {len(video_files)} videos...")
        
        # Open all video captures
        caps = []
        for video_file in video_files:
            cap = cv2.VideoCapture(video_file)
            if not cap.isOpened():
                raise ValueError(f"Could not open video file: {video_file}")
            caps.append(cap)
        
        # Get video properties
        total_frames = int(caps[0].get(cv2.CAP_PROP_FRAME_COUNT))
        fps = caps[0].get(cv2.CAP_PROP_FPS)
        
        logger.info(f"Video properties: {total_frames} frames, {fps:.2f} FPS")
        
        # Store total video frames for all-frames export
        self.total_video_frames = total_frames
        
        # Sample frame indices
        frame_indices = np.linspace(0, total_frames - 1, sample_frames, dtype=int)
        
        for frame_idx in frame_indices:
            frames = []
            
            # Read synchronized frames from all cameras
            for i, cap in enumerate(caps):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if not ret:
                    logger.warning(f"Could not read frame {frame_idx} from camera {i}")
                    continue
                
                frames.append((frame, i))
                
                # Store image size for this camera
                if i not in self.image_sizes:
                    self.image_sizes[i] = (frame.shape[1], frame.shape[0])
            
            if len(frames) != len(caps):
                continue
            
            # Process each frame for corner detection
            valid_detections = []
            display_images = []
            
            for frame, camera_id in frames:
                charuco_corners, charuco_ids, display_img = self.detect_charuco_corners(
                    frame, camera_id, frame_idx, visualize=display_detections
                )
                
                if charuco_corners is not None and len(charuco_corners) >= 4:
                    valid_detections.append((charuco_corners, charuco_ids, camera_id))
                
                if display_detections:
                    display_images.append(display_img)
            
            # Only use frames where all cameras detected sufficient corners
            if len(valid_detections) == len(caps):
                for charuco_corners, charuco_ids, camera_id in valid_detections:
                    self.all_charuco_corners.append(charuco_corners)
                    self.all_charuco_ids.append(charuco_ids)
                
                # Store the actual video frame index for this calibration frame
                self.video_frame_indices.append(frame_idx)
                
                # Store debug frames - prioritize frames with full board in at least 2 cameras
                if len(self.debug_frames) == 0:  # Need to find a good debug frame
                    # Count how many cameras have full board detection
                    full_board_count = sum(1 for corners, ids, _ in valid_detections 
                                          if len(corners) >= self.expected_full_board_corners)
                    
                    # Save this frame if at least 2 cameras have full board, or if it's the first valid frame
                    should_save = (full_board_count >= 2) or (len(self.video_frame_indices) == 1)
                    
                    if should_save:
                        for i, (charuco_corners, charuco_ids, camera_id) in enumerate(valid_detections):
                            # Get the corresponding frame for this camera
                            caps[camera_id].set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                            ret, debug_frame = caps[camera_id].read()
                            if ret:
                                # Draw corners with numbering on debug frame
                                debug_img = debug_frame.copy()
                                cv2.aruco.drawDetectedCornersCharuco(debug_img, charuco_corners, charuco_ids)
                                
                                # Add corner ID numbers
                                for j in range(len(charuco_corners)):
                                    corner = charuco_corners[j][0]
                                    corner_id = charuco_ids[j][0]
                                    cv2.putText(debug_img, str(corner_id), 
                                               (int(corner[0]) + 10, int(corner[1]) - 10),
                                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                                
                                # Add camera info
                                cv2.putText(debug_img, f"Camera {camera_id}", (20, 40),
                                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
                                cv2.putText(debug_img, f"Corners: {len(charuco_corners)}/{self.expected_full_board_corners}", (20, 80),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                                cv2.putText(debug_img, f"Frame: {frame_idx}", (20, 120),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                                
                                # Mark if this is a full board detection
                                if len(charuco_corners) >= self.expected_full_board_corners:
                                    cv2.putText(debug_img, "FULL BOARD", (20, 160),
                                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                                
                                self.debug_frames[camera_id] = debug_img
                
                logger.info(f"Frame {frame_idx}: Valid detections from all cameras")
                
                # Display detections if requested
                if display_detections and display_images:
                    if not self.display_multi_camera_detections(display_images, frame_idx, display_delay_ms):
                        # User pressed quit, break out of frame processing
                        break
            
        # Clean up
        for cap in caps:
            cap.release()
        cv2.destroyAllWindows()
        
        logger.info(f"Collected {len(self.all_charuco_corners)} valid detection sets")
    
    def display_multi_camera_detections(self, display_images: List[np.ndarray], 
                                       frame_idx: int, delay_ms: int = 500) -> bool:
        """
        Display detections from multiple cameras in a grid with efficient window management.
        
        Args:
            display_images: List of images with drawn detections
            frame_idx: Current frame index
        """
        if not display_images:
            return True
        
        # Create a grid layout for multiple cameras
        n_cameras = len(display_images)
        
        if n_cameras == 1:
            combined = display_images[0]
        elif n_cameras == 2:
            # Side by side
            h1, w1 = display_images[0].shape[:2]
            h2, w2 = display_images[1].shape[:2]
            max_h = max(h1, h2)
            
            # Resize if needed
            img1 = cv2.resize(display_images[0], (w1, max_h)) if h1 != max_h else display_images[0]
            img2 = cv2.resize(display_images[1], (w2, max_h)) if h2 != max_h else display_images[1]
            
            combined = np.hstack([img1, img2])
        else:
            # Grid layout for 3+ cameras
            cols = 2 if n_cameras <= 4 else 3
            rows = (n_cameras + cols - 1) // cols
            
            # Resize all images to same size
            target_size = (640, 480)
            resized_imgs = [cv2.resize(img, target_size) for img in display_images]
            
            # Create grid
            grid_rows = []
            for r in range(rows):
                row_imgs = []
                for c in range(cols):
                    idx = r * cols + c
                    if idx < len(resized_imgs):
                        row_imgs.append(resized_imgs[idx])
                    else:
                        # Fill with black image
                        row_imgs.append(np.zeros((target_size[1], target_size[0], 3), dtype=np.uint8))
                grid_rows.append(np.hstack(row_imgs))
            
            combined = np.vstack(grid_rows)
        
        # Add instruction text overlay
        text_y_start = 30
        instructions = [
            f"Frame {frame_idx} - Press: SPACE=next, Q=quit, S=save, ESC=quit",
        ]
        
        for i, instruction in enumerate(instructions):
            cv2.putText(combined, instruction, (10, text_y_start + i*25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(combined, instruction, (10, text_y_start + i*25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
        
        # Use a consistent window name to reuse the same window
        window_name = 'Charuco Detection Progress'
        cv2.imshow(window_name, combined)
        
        # Wait for key press with configurable delay for better control
        key = cv2.waitKey(delay_ms) & 0xFF
        
        if key == ord('q') or key == 27:  # 'q' or ESC key
            cv2.destroyAllWindows()
            return False
        elif key == ord('s'):
            # Save current frame
            cv2.imwrite(f'charuco_detection_frame_{frame_idx}.jpg', combined)
            logger.info(f"Saved detection frame {frame_idx}")
        elif key == 32:  # Spacebar - continue to next frame
            pass  # Just continue
        
        return True
    
    def parse_focal_lengths(self, focal_length_str: str, num_cameras: int) -> List[float]:
        """
        Parse focal length string into per-camera values.
        
        Args:
            focal_length_str: String containing focal length(s)
            num_cameras: Number of cameras to calibrate
            
        Returns:
            List of focal lengths, one per camera
        """
        if ',' in focal_length_str:
            # Multiple values - one per camera
            values = [float(v.strip()) for v in focal_length_str.split(',')]
            if len(values) != num_cameras:
                raise ValueError(f"Expected {num_cameras} focal lengths, got {len(values)}: {values}")
            return values
        else:
            # Single value - apply to all cameras
            single_value = float(focal_length_str)
            return [single_value] * num_cameras
    
    def get_calibration_flags(self, args, num_cameras: int = 1):
        """
        Generate calibration flags based on which parameters to optimize.
        
        Args:
            args: Command line arguments with optimization flags
            num_cameras: Number of cameras (for focal length parsing)
            
        Returns:
            tuple: (calibration_flags, focal_lengths_list, info_str)
        """
        # Start with base flags
        calibration_flags = cv2.CALIB_USE_INTRINSIC_GUESS | cv2.CALIB_FIX_PRINCIPAL_POINT
        
        # Handle focal length and aspect ratio flags
        focal_info = []
        focal_lengths = None
        
        if args.fix_focal_length is not None:
            calibration_flags |= cv2.CALIB_FIX_FOCAL_LENGTH
            focal_lengths = self.parse_focal_lengths(args.fix_focal_length, num_cameras)
            
            if len(set(focal_lengths)) == 1:
                # All cameras have same focal length
                focal_info.append(f"focal length fixed at {focal_lengths[0]:.1f} (all cameras)")
            else:
                # Different focal lengths per camera
                focal_info.append(f"focal lengths: {[f'{f:.1f}' for f in focal_lengths]} (per camera)")
        else:
            focal_info.append("focal length optimized")
        
        if args.fix_aspect_ratio != 1.0:
            # Custom aspect ratio
            focal_info.append(f"aspect ratio fixed at {args.fix_aspect_ratio:.3f}")
        else:
            # Default square pixels
            calibration_flags |= cv2.CALIB_FIX_ASPECT_RATIO
            focal_info.append("square pixels (aspect ratio = 1.0)")
        
        # Handle distortion parameter flags
        calibration_flags, distortion_info = self.get_distortion_flags_only(args, calibration_flags)
        
        # Combine focal length and distortion information
        focal_str = ", ".join(focal_info)
        full_info = f"{focal_str}; {distortion_info}"
        
        return calibration_flags, focal_lengths, full_info
    
    def get_distortion_flags_only(self, args, calibration_flags):
        """
        Add distortion parameter flags to existing calibration flags.
        
        Args:
            args: Command line arguments with distortion optimization flags
            calibration_flags: Existing calibration flags to modify
            
        Returns:
            tuple: (modified_calibration_flags, description_string)
        """
        # Handle convenience flags first
        if args.fix_all_distortion:
            calibration_flags |= (cv2.CALIB_FIX_K1 | cv2.CALIB_FIX_K2 | cv2.CALIB_FIX_K3 | 
                                 cv2.CALIB_ZERO_TANGENT_DIST)
            return calibration_flags, "no distortion (all parameters fixed at 0)"
        
        if args.optimize_radial:
            if args.optimize_radial == 'k1':
                calibration_flags |= (cv2.CALIB_FIX_K2 | cv2.CALIB_FIX_K3 | 
                                     cv2.CALIB_ZERO_TANGENT_DIST)
                return calibration_flags, "optimizing k1 only"
            elif args.optimize_radial == 'k1k2':
                calibration_flags |= (cv2.CALIB_FIX_K3 | cv2.CALIB_ZERO_TANGENT_DIST)
                return calibration_flags, "optimizing k1 and k2"
            elif args.optimize_radial == 'k1k2k3':
                calibration_flags |= cv2.CALIB_ZERO_TANGENT_DIST
                return calibration_flags, "optimizing k1, k2, and k3 (radial only)"
            elif args.optimize_radial == 'all':
                return calibration_flags, "optimizing all distortion parameters (k1, k2, k3, p1, p2)"
        
        # Handle individual flags
        any_individual_flags = (args.optimize_k1 or args.optimize_k2 or args.optimize_k3 or 
                               args.optimize_p1 or args.optimize_p2)
        
        if not any_individual_flags:
            return calibration_flags, "optimizing all distortion parameters (k1, k2, k3, p1, p2) - default"
        
        optimized_params = []
        
        if not args.optimize_k1:
            calibration_flags |= cv2.CALIB_FIX_K1
        else:
            optimized_params.append('k1')
            
        if not args.optimize_k2:
            calibration_flags |= cv2.CALIB_FIX_K2
        else:
            optimized_params.append('k2')
            
        if not args.optimize_k3:
            calibration_flags |= cv2.CALIB_FIX_K3
        else:
            optimized_params.append('k3')
            
        if not (args.optimize_p1 and args.optimize_p2):
            calibration_flags |= cv2.CALIB_ZERO_TANGENT_DIST
        else:
            optimized_params.extend(['p1', 'p2'])
        
        if optimized_params:
            return calibration_flags, "optimizing: " + ", ".join(optimized_params)
        else:
            calibration_flags |= (cv2.CALIB_FIX_K1 | cv2.CALIB_FIX_K2 | cv2.CALIB_FIX_K3 | 
                                 cv2.CALIB_ZERO_TANGENT_DIST)
            return calibration_flags, "no distortion parameters optimized"
    
    def calibrate_cameras(self, calibration_flags=None, focal_lengths_list=None, optimization_info="", enable_stereo=False) -> Dict:
        """
        Perform camera calibration using collected Charuco board detections.
        
        Returns:
            Dictionary containing calibration results for all cameras
        """
        if not self.all_charuco_corners:
            raise ValueError("No calibration data collected. Run process_videos first.")
        
        logger.info("Starting camera calibration...")
        if optimization_info:
            logger.info(f"Optimization: {optimization_info}")
        
        # Organize data by camera
        cameras_data = {}
        n_cameras = len(self.image_sizes)
        
        # Group corners and IDs by camera
        for cam_id in range(n_cameras):
            cameras_data[cam_id] = {
                'corners': [],
                'ids': [],
                'object_points': [],
                'image_points': []
            }
        
        # Properly organize detection data by frame and camera
        # The current data structure stores detections sequentially for each frame where ALL cameras detected corners
        # We need to group them by frame first, then by camera
        
        total_detections = len(self.all_charuco_corners)
        frames_with_all_cameras = total_detections // n_cameras
        
        logger.info(f"Processing {frames_with_all_cameras} frames with detections from all {n_cameras} cameras")
        
        for frame_idx in range(frames_with_all_cameras):
            # For each frame, get detections from all cameras
            frame_detections = {}
            
            for cam_id in range(n_cameras):
                detection_idx = frame_idx * n_cameras + cam_id
                if detection_idx < total_detections:
                    corners = self.all_charuco_corners[detection_idx]
                    ids = self.all_charuco_ids[detection_idx]
                    
                    # Get object points for this set of corners
                    obj_pts = self.charuco_board.getChessboardCorners()[ids.flatten()]
                    
                    frame_detections[cam_id] = {
                        'corners': corners,
                        'ids': ids,
                        'object_points': obj_pts
                    }
            
            # Only use frames where we have detections from ALL cameras
            if len(frame_detections) == n_cameras:
                # Find common corner IDs across all cameras for this frame
                # This ensures stereo calibration uses matching points
                common_ids = set(frame_detections[0]['ids'].flatten())
                for cam_id in range(1, n_cameras):
                    common_ids &= set(frame_detections[cam_id]['ids'].flatten())
                
                if len(common_ids) >= 6:  # Need at least 6 matching corners for calibration (OpenCV requirement)
                    # Extract only the common corners for each camera
                    for cam_id in range(n_cameras):
                        detection = frame_detections[cam_id]
                        ids_flat = detection['ids'].flatten()
                        
                        # Find indices of common IDs in this camera's detection
                        common_indices = [i for i, id_val in enumerate(ids_flat) if id_val in common_ids]
                        
                        if len(common_indices) >= 6:
                            # Extract matching corners and object points
                            matching_corners = detection['corners'][common_indices]
                            matching_ids = detection['ids'][common_indices]
                            matching_obj_pts = self.charuco_board.getChessboardCorners()[matching_ids.flatten()]
                            
                            cameras_data[cam_id]['corners'].append(matching_corners)
                            cameras_data[cam_id]['ids'].append(matching_ids)
                            cameras_data[cam_id]['object_points'].append(matching_obj_pts)
                            cameras_data[cam_id]['image_points'].append(matching_corners)
                else:
                    logger.debug(f"Frame {frame_idx}: Only {len(common_ids)} common corners (need ≥6), skipping")
        
        # Calibrate each camera individually first
        calibration_results = {}
        
        for cam_id in range(n_cameras):
            logger.info(f"Calibrating camera {cam_id}...")
            
            image_size = self.image_sizes[cam_id]
            
            # Prepare calibration data
            object_points = cameras_data[cam_id]['object_points']
            image_points = cameras_data[cam_id]['image_points']
            
            if len(object_points) < 3:
                logger.warning(f"Insufficient data for camera {cam_id} calibration")
                continue
            
            # Limit calibration data to prevent numerical instability with too many frames
            # OpenCV can become unstable with hundreds of frames
            max_calibration_frames = 100  # Reasonable limit for stable calibration
            if len(object_points) > max_calibration_frames:
                logger.info(f"Camera {cam_id}: Selecting best {max_calibration_frames} frames from {len(object_points)} available")
                
                # Quality-based frame selection instead of evenly spaced
                frame_qualities = []
                for i in range(len(object_points)):
                    obj_pts = object_points[i]
                    img_pts = image_points[i]
                    
                    # Primary quality metric: number of detected corners (more is better)
                    num_corners = len(obj_pts)
                    
                    # Secondary quality metric: corner distribution across image
                    # Calculate spread of corners to prefer frames with well-distributed points
                    if len(img_pts) > 0:
                        corners_2d = img_pts.reshape(-1, 2)
                        x_spread = np.std(corners_2d[:, 0]) / image_size[0]  # Normalized by image width
                        y_spread = np.std(corners_2d[:, 1]) / image_size[1]  # Normalized by image height
                        distribution_score = (x_spread + y_spread) / 2.0  # Average spread
                    else:
                        distribution_score = 0.0
                    
                    # Combined quality score (prioritize corner count, bonus for good distribution)
                    quality_score = num_corners + (distribution_score * 10.0)  # Weight distribution less than count
                    frame_qualities.append((i, quality_score, num_corners, distribution_score))
                
                # Sort by quality score (descending) and take the best frames
                frame_qualities.sort(key=lambda x: x[1], reverse=True)
                best_frames = frame_qualities[:max_calibration_frames]
                
                # Extract the frame indices and sort them to maintain temporal order
                selected_indices = sorted([frame[0] for frame in best_frames])
                
                # Update the calibration data with selected high-quality frames
                object_points = [object_points[i] for i in selected_indices]
                image_points = [image_points[i] for i in selected_indices]
                
                # Log quality selection statistics
                avg_corners = np.mean([frame[2] for frame in best_frames])
                avg_distribution = np.mean([frame[3] for frame in best_frames])
                logger.info(f"Camera {cam_id}: Selected frames with avg {avg_corners:.1f} corners, "
                           f"avg distribution {avg_distribution:.3f}")
                logger.info(f"Camera {cam_id}: Using {len(object_points)} high-quality frames for calibration")
            
            # Initial camera matrix - use fixed focal length if specified
            if focal_lengths_list is not None and len(focal_lengths_list) > cam_id:
                camera_focal_length = focal_lengths_list[cam_id]
                initial_camera_matrix = np.array([
                    [camera_focal_length, 0, image_size[0] / 2],
                    [0, camera_focal_length, image_size[1] / 2],
                    [0, 0, 1]
                ], dtype=np.float32)
            else:
                # Better initial guess based on typical camera parameters
                # Most cameras have focal lengths between 2-10x the image width
                # Use 4x width as a reasonable middle-ground estimate
                estimated_focal_length = image_size[0] * 4.0  # 4x width is common for many cameras
                initial_camera_matrix = np.array([
                    [estimated_focal_length, 0, image_size[0] / 2],
                    [0, estimated_focal_length, image_size[1] / 2],
                    [0, 0, 1]
                ], dtype=np.float32)
                logger.info(f"Camera {cam_id}: Using estimated focal length {estimated_focal_length:.1f} (4x image width)")
            
            logger.info(f"Camera {cam_id}: Image size {image_size}, using {len(object_points)} frames for calibration")
            
            # Use provided calibration flags or default
            if calibration_flags is not None:
                calib_flags = calibration_flags
            else:
                # Default: optimize all parameters
                calib_flags = (
                    cv2.CALIB_USE_INTRINSIC_GUESS |
                    cv2.CALIB_FIX_ASPECT_RATIO |
                    cv2.CALIB_FIX_PRINCIPAL_POINT
                )
            
            # Perform calibration
            ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
                object_points, image_points, image_size,
                initial_camera_matrix, None, flags=calib_flags
            )
            
            # Store results
            calibration_results[cam_id] = {
                'name': str(cam_id + 1),
                'size': list(image_size),
                'matrix': camera_matrix.tolist(),
                'distortions': dist_coeffs.flatten().tolist(),
                'rotation': rvecs[0].flatten().tolist() if rvecs else [0, 0, 0],
                'translation': tvecs[0].flatten().tolist() if tvecs else [0, 0, 0],
                'reprojection_error': ret
            }
            
            logger.info(f"Camera {cam_id} calibrated with reprojection error: {ret:.4f}")
        
        # Perform stereo calibration if requested and we have multiple cameras
        if enable_stereo and n_cameras >= 2:
            logger.info("Performing stereo calibration...")
            self.perform_stereo_calibration(calibration_results, cameras_data)
        elif n_cameras >= 2:
            logger.info("Multiple cameras detected, but stereo calibration disabled (use --stereo flag to enable)")
        elif enable_stereo:
            logger.warning("Stereo calibration requested but only one camera detected")
        
        return calibration_results
    
    def perform_stereo_calibration(self, calibration_results: Dict, cameras_data: Dict):
        """
        Perform stereo calibration between camera pairs to get relative poses.
        
        Args:
            calibration_results: Individual camera calibration results
            cameras_data: Organized calibration data by camera
        """
        n_cameras = len(calibration_results)
        
        # Perform pairwise stereo calibrations
        for cam1_id in range(n_cameras):
            for cam2_id in range(cam1_id + 1, n_cameras):
                logger.info(f"Stereo calibrating cameras {cam1_id} and {cam2_id}...")
                
                # Get calibration data for both cameras
                cam1_data = cameras_data[cam1_id]
                cam2_data = cameras_data[cam2_id]
                
                # Use the properly matched points from the organized data
                # Since we already ensured matching corners in the data organization step,
                # we can directly use the corresponding frames
                common_object_points = []
                common_image_points1 = []
                common_image_points2 = []
                
                min_frames = min(len(cam1_data['object_points']), len(cam2_data['object_points']))
                
                for i in range(min_frames):
                    # Verify that we have the same number of points for both cameras
                    obj_pts1 = cam1_data['object_points'][i]
                    obj_pts2 = cam2_data['object_points'][i]
                    img_pts1 = cam1_data['image_points'][i]
                    img_pts2 = cam2_data['image_points'][i]
                    
                    # Ensure equal number of points
                    if (len(obj_pts1) == len(obj_pts2) and 
                        len(img_pts1) == len(img_pts2) and 
                        len(obj_pts1) == len(img_pts1) and 
                        len(obj_pts2) == len(img_pts2)):
                        
                        common_object_points.append(obj_pts1)  # Both cameras should have same object points
                        common_image_points1.append(img_pts1)
                        common_image_points2.append(img_pts2)
                    else:
                        logger.warning(f"Frame {i}: Mismatched point counts - "
                                     f"cam{cam1_id}: obj={len(obj_pts1)}, img={len(img_pts1)}, "
                                     f"cam{cam2_id}: obj={len(obj_pts2)}, img={len(img_pts2)}")
                
                logger.info(f"Using {len(common_object_points)} frames for stereo calibration "
                           f"between cameras {cam1_id} and {cam2_id}")
                
                if len(common_object_points) < 3:
                    continue
                
                # Get camera matrices and distortion coefficients
                camera_matrix1 = np.array(calibration_results[cam1_id]['matrix'])
                camera_matrix2 = np.array(calibration_results[cam2_id]['matrix'])
                dist_coeffs1 = np.array(calibration_results[cam1_id]['distortions'])
                dist_coeffs2 = np.array(calibration_results[cam2_id]['distortions'])
                image_size1 = tuple(calibration_results[cam1_id]['size'])
                
                # Perform stereo calibration
                stereo_flags = cv2.CALIB_FIX_INTRINSIC
                
                ret, _, _, _, _, R, T, E, F = cv2.stereoCalibrate(
                    common_object_points, common_image_points1, common_image_points2,
                    camera_matrix1, dist_coeffs1,
                    camera_matrix2, dist_coeffs2,
                    image_size1, flags=stereo_flags
                )
                
                # Convert rotation matrix to rotation vector
                rvec, _ = cv2.Rodrigues(R)
                
                # Update the second camera's extrinsic parameters relative to the first
                if cam1_id == 0:  # Use first camera as reference
                    calibration_results[cam2_id]['rotation'] = rvec.flatten().tolist()
                    calibration_results[cam2_id]['translation'] = T.flatten().tolist()
                
                logger.info(f"Stereo calibration between cameras {cam1_id} and {cam2_id} "
                           f"completed with error: {ret:.4f}")
    
    def export_detections_to_csv(self, output_dir: str = '.', flip_y: bool = False, all_frames: bool = False):
        """
        Export corner detections to CSV files in the specified formats.
        
        Args:
            output_dir: Directory to save CSV files
            flip_y: If True, flip Y coordinates (subtract from image height) for bottom-left origin systems
        """
        if not self.all_charuco_corners:
            logger.warning("No detections to export")
            return
        
        # Get number of cameras
        n_cameras = len(self.image_sizes)
        total_detections = len(self.all_charuco_corners)
        frames_with_all_cameras = total_detections // n_cameras
        
        logger.info(f"Exporting detections from {frames_with_all_cameras} frames with {n_cameras} cameras")
        if flip_y:
            logger.info("Y-coordinate flipping enabled - coordinates will be flipped for bottom-left origin systems")
        
        # Adaptive corner selection for two corners along the same long side
        # Get board dimensions from config
        board_size = self.config['calibration']['board_size']  # [cols, rows]
        cols, rows = board_size[0], board_size[1]
        
        # Determine which is the long side
        if rows > cols:
            # Vertical is longer - long sides are left and right edges
            long_side_length = rows - 1  # Number of internal corners along long side
            corners_per_row = cols - 1   # Number of internal corners per row
            is_vertical_long = True
        else:
            # Horizontal is longer - long sides are top and bottom edges  
            long_side_length = cols - 1  # Number of internal corners along long side
            corners_per_row = rows - 1   # Number of internal corners per row
            is_vertical_long = False
        
        logger.info(f"Board: {cols}x{rows}, Long side: {long_side_length} corners, Vertical long: {is_vertical_long}")
        
        # First, find all detected corner IDs across all frames
        all_detected_ids = set()
        for frame_idx in range(frames_with_all_cameras):
            for cam_id in range(n_cameras):
                detection_idx = frame_idx * n_cameras + cam_id
                if detection_idx < total_detections:
                    ids = self.all_charuco_ids[detection_idx]
                    all_detected_ids.update(ids.flatten())
        
        # Generate candidate corner pairs along the same long side
        candidate_pairs = []
        
        if is_vertical_long:
            # Long sides are vertical (left and right edges)
            # Left edge corners: 0, corners_per_row, 2*corners_per_row, ..., (long_side_length-1)*corners_per_row
            # Right edge corners: (corners_per_row-1), 2*corners_per_row-1, 3*corners_per_row-1, ..., long_side_length*corners_per_row-1
            
            # Left edge pairs - use outermost corners (first and last)
            left_edge_corners = [i * corners_per_row for i in range(long_side_length)]
            if len(left_edge_corners) >= 2:
                pt1, pt2 = left_edge_corners[0], left_edge_corners[-1]  # First and last corners
                if pt1 in all_detected_ids and pt2 in all_detected_ids:
                    candidate_pairs.append((pt1, pt2, 'left_edge'))
            
            # Right edge pairs - use outermost corners (first and last)  
            right_edge_corners = [(i + 1) * corners_per_row - 1 for i in range(long_side_length)]
            if len(right_edge_corners) >= 2:
                pt1, pt2 = right_edge_corners[0], right_edge_corners[-1]  # First and last corners
                if pt1 in all_detected_ids and pt2 in all_detected_ids:
                    candidate_pairs.append((pt1, pt2, 'right_edge'))
        
        else:
            # Long sides are horizontal (top and bottom edges)
            # Top edge corners: 0, 1, 2, ..., corners_per_row-1
            # Bottom edge corners: (long_side_length-1)*corners_per_row, ..., long_side_length*corners_per_row-1
            
            # Top edge pairs - use outermost corners (first and last)
            top_edge_corners = list(range(corners_per_row))
            if len(top_edge_corners) >= 2:
                pt1, pt2 = top_edge_corners[0], top_edge_corners[-1]  # First and last corners
                if pt1 in all_detected_ids and pt2 in all_detected_ids:
                    candidate_pairs.append((pt1, pt2, 'top_edge'))
            
            # Bottom edge pairs - use outermost corners (first and last)
            bottom_start = (long_side_length - 1) * corners_per_row
            bottom_edge_corners = list(range(bottom_start, bottom_start + corners_per_row))
            if len(bottom_edge_corners) >= 2:
                pt1, pt2 = bottom_edge_corners[0], bottom_edge_corners[-1]  # First and last corners
                if pt1 in all_detected_ids and pt2 in all_detected_ids:
                    candidate_pairs.append((pt1, pt2, 'bottom_edge'))
        
        logger.info(f"Found {len(candidate_pairs)} candidate corner pairs along long sides")
        logger.info("Using frame-by-frame adaptive pair selection")
        
        # Storage for CSV data
        paired_data = []
        unpaired_data = []
        pair_usage_stats = {}  # Track which corner pairs are used in each frame
        paired_data_by_frame = {}  # For all_frames mode, track which frames have valid detections (frame_idx -> row data)
        
        for frame_idx in range(frames_with_all_cameras):
            # Collect detections for this frame from all cameras
            frame_detections = {}
            
            for cam_id in range(n_cameras):
                detection_idx = frame_idx * n_cameras + cam_id
                if detection_idx < total_detections:
                    corners = self.all_charuco_corners[detection_idx]
                    ids = self.all_charuco_ids[detection_idx]
                    
                    # Convert to flat arrays for easier processing
                    ids_flat = ids.flatten()
                    corners_flat = corners.reshape(-1, 2)  # Nx2 array of (x,y) coordinates
                    
                    # Create dictionary mapping ID -> (x, y)
                    corner_dict = {}
                    for i, corner_id in enumerate(ids_flat):
                        x, y = corners_flat[i]
                        
                        # Apply Y-coordinate flipping if requested
                        if flip_y:
                            if cam_id in self.image_sizes:
                                image_height = self.image_sizes[cam_id][1]  # Height is second element (w, h)
                                y = image_height - y
                            else:
                                logger.warning(f"Cannot flip Y coordinate: no image size stored for camera {cam_id}")
                        
                        corner_dict[corner_id] = (x, y)
                    
                    frame_detections[cam_id] = corner_dict
            
            # Process frames where we have detections from any cameras (minimum 2 for meaningful analysis)
            if len(frame_detections) >= 2:
                # Frame-by-frame pair selection: check all candidate pairs for this frame
                best_frame_pair = None
                
                for pt1_candidate, pt2_candidate, edge_name in candidate_pairs:
                    # Check if both corners are detected in at least 2 cameras for this frame
                    cameras_with_both = [cam_id for cam_id in frame_detections 
                                       if pt1_candidate in frame_detections[cam_id] and pt2_candidate in frame_detections[cam_id]]
                    
                    if len(cameras_with_both) >= 2:
                        best_frame_pair = (pt1_candidate, pt2_candidate, edge_name)
                        break  # Use first available pair (pairs are already sorted by preference)
                
                # Export paired points if we found a valid pair for this frame
                if best_frame_pair:
                    pt1_frame, pt2_frame, edge_name = best_frame_pair
                    paired_row = []
                    
                    # Add pt1 coordinates for all cameras (NaN if not detected)
                    for cam_id in range(n_cameras):
                        if cam_id in frame_detections and pt1_frame in frame_detections[cam_id]:
                            x, y = frame_detections[cam_id][pt1_frame]
                            paired_row.extend([x, y])
                        else:
                            paired_row.extend([float('nan'), float('nan')])
                    
                    # Add pt2 coordinates for all cameras (NaN if not detected)
                    for cam_id in range(n_cameras):
                        if cam_id in frame_detections and pt2_frame in frame_detections[cam_id]:
                            x, y = frame_detections[cam_id][pt2_frame]
                            paired_row.extend([x, y])
                        else:
                            paired_row.extend([float('nan'), float('nan')])
                    
                    if all_frames:
                        paired_data_by_frame[frame_idx] = paired_row
                    else:
                        paired_data.append(paired_row)
                    
                    # Track which pairs are being used (for statistics)
                    pair_key = (pt1_frame, pt2_frame)
                    if pair_key not in pair_usage_stats:
                        pair_usage_stats[pair_key] = {'count': 0, 'edge': edge_name}
                    pair_usage_stats[pair_key]['count'] += 1
                
                # Export all other corners as unpaired data
                # Find all corner IDs present in at least one camera
                all_ids = set()
                for cam_id in frame_detections:
                    all_ids.update(frame_detections[cam_id].keys())
                
                # Remove corners used in paired data for this frame (if any)
                if best_frame_pair:
                    pt1_frame, pt2_frame, _ = best_frame_pair
                    unpaired_ids = all_ids - {pt1_frame, pt2_frame}
                else:
                    unpaired_ids = all_ids
                
                for corner_id in sorted(unpaired_ids):
                    # Check if this corner is present in at least 2 cameras
                    cameras_with_corner = [cam_id for cam_id in frame_detections 
                                         if corner_id in frame_detections[cam_id]]
                    
                    if len(cameras_with_corner) >= 2:
                        unpaired_row = []
                        for cam_id in range(n_cameras):
                            if cam_id in frame_detections and corner_id in frame_detections[cam_id]:
                                x, y = frame_detections[cam_id][corner_id]
                                unpaired_row.extend([x, y])
                            else:
                                unpaired_row.extend([float('nan'), float('nan')])
                        unpaired_data.append(unpaired_row)
        
        # After processing all frames, calculate statistics and distance info
        physical_distance_mm = 0.0
        most_used_pair = None
        
        if pair_usage_stats:
            # Find the most frequently used pair
            most_used_pair = max(pair_usage_stats.items(), key=lambda x: x[1]['count'])
            pair_ids, pair_info = most_used_pair
            pt1_id, pt2_id = pair_ids
            
            # Calculate physical distance for the most used pair
            square_size = self.config['calibration']['board_square_side_length']
            
            if is_vertical_long:
                pt1_row = pt1_id // corners_per_row
                pt2_row = pt2_id // corners_per_row
                row_difference = abs(pt2_row - pt1_row)
                physical_distance_mm = row_difference * square_size
            else:
                pt1_col = pt1_id % corners_per_row
                pt2_col = pt2_id % corners_per_row
                col_difference = abs(pt2_col - pt1_col)
                physical_distance_mm = col_difference * square_size
            
            logger.info(f"Frame-by-frame pair selection used {len(pair_usage_stats)} different corner pairs")
            for (p1, p2), stats in sorted(pair_usage_stats.items(), key=lambda x: x[1]['count'], reverse=True):
                logger.info(f"  Corners ({p1}, {p2}) from {stats['edge']}: {stats['count']} frames")
            logger.info(f"Most used pair: ({pt1_id}, {pt2_id}) with distance {physical_distance_mm}mm")
        
        # Write paired points CSV (no distance metadata in CSV anymore)
        paired_csv_path = os.path.join(output_dir, "paired_pts-xypts.csv")
        
        # Determine which data to use based on all_frames mode
        if all_frames:
            # Use frame-by-frame data with NaN filling for ALL video frames
            final_paired_data = []
            nan_row = [float('nan')] * (n_cameras * 4)  # 2 points * 2 coords * n_cameras
            
            # Create mapping from actual video frame index to calibration frame index
            video_frame_to_cal_frame = {}
            for cal_frame_idx in range(frames_with_all_cameras):
                if cal_frame_idx < len(self.video_frame_indices):
                    video_frame_idx = self.video_frame_indices[cal_frame_idx]
                    video_frame_to_cal_frame[video_frame_idx] = cal_frame_idx
            
            # Create one row per video frame
            for video_frame_idx in range(self.total_video_frames):
                if video_frame_idx in video_frame_to_cal_frame:
                    cal_frame_idx = video_frame_to_cal_frame[video_frame_idx]
                    if cal_frame_idx in paired_data_by_frame:
                        final_paired_data.append(paired_data_by_frame[cal_frame_idx])
                    else:
                        final_paired_data.append(nan_row)
                else:
                    final_paired_data.append(nan_row)
            
            data_to_write = final_paired_data
            detection_count = len(paired_data_by_frame)
            logger.info(f"All-frames mode: {detection_count}/{self.total_video_frames} frames have valid paired detections")
        else:
            # Use regular paired_data list
            data_to_write = paired_data
            detection_count = len(paired_data)
        
        if data_to_write and (not all_frames or detection_count > 0):
            with open(paired_csv_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Create header: pt1_cam1_x, pt1_cam1_y, pt1_cam2_x, pt1_cam2_y, ..., pt2_cam1_x, pt2_cam1_y, ...
                header = []
                for cam_id in range(n_cameras):
                    header.extend([f'pt1_cam{cam_id+1}_x', f'pt1_cam{cam_id+1}_y'])
                for cam_id in range(n_cameras):
                    header.extend([f'pt2_cam{cam_id+1}_x', f'pt2_cam{cam_id+1}_y'])
                
                writer.writerow(header)
                writer.writerows(data_to_write)
            
            if all_frames:
                logger.info(f"Exported {len(data_to_write)} rows (all frames) with {detection_count} valid paired detections to {paired_csv_path}")
            else:
                logger.info(f"Exported {detection_count} paired detections to {paired_csv_path}")
            
            if physical_distance_mm > 0:
                logger.info(f"Paired points distance: {physical_distance_mm}mm")
        else:
            logger.warning("No paired detections found (pt1 and pt2 not detected in all cameras)")
        
        # Store distance info for TOML output
        if most_used_pair:
            pair_ids, pair_info = most_used_pair
            self.paired_points_info = {
                'corner_ids': list(pair_ids),
                'physical_distance_mm': physical_distance_mm,
                'detection_count': pair_info['count'],
                'total_pairs_used': len(pair_usage_stats),
                'pair_statistics': {f"{p1}_{p2}": {'count': stats['count'], 'edge': stats['edge']} 
                                   for (p1, p2), stats in pair_usage_stats.items()}
            }
        else:
            self.paired_points_info = {
                'corner_ids': None,
                'physical_distance_mm': 0.0,
                'detection_count': 0
            }
        
        # Write unpaired points CSV
        unpaired_csv_path = os.path.join(output_dir, "unpaired_pts-xypts.csv")
        if unpaired_data:
            with open(unpaired_csv_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Create header: pt1_cam1_x, pt1_cam1_y, pt1_cam2_x, pt1_cam2_y, ...
                header = []
                for cam_id in range(n_cameras):
                    header.extend([f'pt1_cam{cam_id+1}_x', f'pt1_cam{cam_id+1}_y'])
                
                writer.writerow(header)
                writer.writerows(unpaired_data)
            
            logger.info(f"Exported {len(unpaired_data)} unpaired detections to {unpaired_csv_path}")
        else:
            logger.warning("No unpaired detections found")
    
    def save_debug_frame(self, output_dir: str = '.'):
        """
        Save a debug frame showing corner detections with numbering for visual verification.
        
        Args:
            output_dir: Directory to save debug image
        """
        if not self.debug_frames:
            logger.warning("No debug frames available for visualization")
            return
        
        logger.info("Saving debug frames showing corner detections with numbering...")
        
        # Save individual camera debug images
        detection_images = []
        for cam_id in sorted(self.debug_frames.keys()):
            img = self.debug_frames[cam_id]
            debug_path = os.path.join(output_dir, f"debug_corners_cam{cam_id}.png")
            cv2.imwrite(debug_path, img)
            logger.info(f"Saved debug image for camera {cam_id}: {debug_path}")
            detection_images.append(img)
        
        # Create a combined debug image if multiple cameras
        if len(detection_images) > 1:
            # Resize images to same height for side-by-side display
            target_height = 600
            resized_images = []
            
            for img in detection_images:
                h, w = img.shape[:2]
                aspect_ratio = w / h
                target_width = int(target_height * aspect_ratio)
                resized_img = cv2.resize(img, (target_width, target_height))
                resized_images.append(resized_img)
            
            # Combine horizontally
            combined_img = np.hstack(resized_images)
            
            # Save combined image
            combined_path = os.path.join(output_dir, "debug_corners_all_cameras.png")
            cv2.imwrite(combined_path, combined_img)
            logger.info(f"Saved combined debug image: {combined_path}")
            
        logger.info("Debug frame visualization complete! Check the generated PNG files to verify corner numbering.")
    
    def export_camera_profile(self, calibration_results: Dict, output_dir: str = '.', flip_y: bool = False):
        """
        Export camera profile file with intrinsic parameters and distortion coefficients.
        
        Args:
            calibration_results: Calibration results dictionary
            output_dir: Directory to save the camera profile file
            flip_y: If True, apply Y-coordinate flipping to intrinsic parameters
        """
        n_cameras = len(calibration_results)
        logger.info(f"Exporting camera profile for {n_cameras} cameras")
        if flip_y:
            logger.info("Y-coordinate flipping enabled for camera profile - coordinates will be flipped for bottom-left origin systems")
        
        # Camera profile data
        profile_data = []
        
        for cam_id in range(n_cameras):
            # Get calibration parameters from results dictionary
            cam_result = calibration_results[cam_id]
            K = np.array(cam_result['matrix'])              # Intrinsic matrix
            dist = np.array(cam_result['distortions'])      # Distortion coefficients
            image_size = self.image_sizes[cam_id]           # (width, height)
            
            # Apply Y-coordinate flipping to intrinsic matrix if requested
            if flip_y:
                width, height = image_size
                # Create transformation matrix for Y-flip: T = [1 0 0; 0 -1 height; 0 0 1]
                T_flip = np.array([[1, 0, 0],
                                  [0, -1, height],
                                  [0, 0, 1]], dtype=float)
                # Transform intrinsic matrix: K_flipped = T_flip * K
                K = T_flip @ K
            
            # Extract intrinsic parameters (possibly flipped)
            fx = K[0, 0]
            fy = K[1, 1]
            cx = K[0, 2] 
            cy = K[1, 2]
            width, height = image_size
            aspect_ratio = fy / fx
            
            # Extract distortion coefficients (OpenCV format: k1, k2, p1, p2, k3)
            k1 = dist[0] if len(dist) > 0 else 0.0  # r2 in Bourguet notation
            k2 = dist[1] if len(dist) > 1 else 0.0  # r4 in Bourguet notation  
            p1 = dist[2] if len(dist) > 2 else 0.0  # t1 tangential
            p2 = dist[3] if len(dist) > 3 else 0.0  # t2 tangential
            k3 = dist[4] if len(dist) > 4 else 0.0  # r6 in Bourguet notation
            
            # Create camera profile row: camera_num, fx, width, height, cx, cy, AR, r2, r4, t1, t2, r6
            profile_row = [
                cam_id + 1,    # Camera number (1-based)
                fx,            # Focal length x in pixels
                width,         # Image width
                height,        # Image height  
                cx,            # Principal point x
                cy,            # Principal point y
                aspect_ratio,  # Aspect ratio (fy/fx)
                k1,            # r2 (k1 in OpenCV)
                k2,            # r4 (k2 in OpenCV)
                p1,            # t1 tangential distortion
                p2,            # t2 tangential distortion
                k3             # r6 (k3 in OpenCV)
            ]
            profile_data.append(profile_row)
        
        # Save camera profile file (no headers)
        profile_path = os.path.join(output_dir, "camera_profile.txt")
        with open(profile_path, 'w') as f:
            # Write data rows without header
            for row in profile_data:
                formatted_row = [f"{val:.6f}" if isinstance(val, float) else str(val) for val in row]
                f.write("\t".join(formatted_row) + "\n")
        
        logger.info(f"Camera profile saved to {profile_path}")

    def save_calibration_results(self, results: Dict, output_path: str, 
                                overall_error: float = 0.0):
        """
        Save calibration results to a TOML file in human-readable format.
        
        Args:
            results: Calibration results dictionary
            output_path: Output file path
            overall_error: Overall calibration error
        """
        logger.info(f"Saving calibration results to {output_path}")
        
        # Prepare output data structure
        output_data = {}
        
        # Add camera calibration data
        for cam_id, cam_data in results.items():
            cam_key = f"cam_{cam_id}"
            output_data[cam_key] = cam_data
        
        # Add metadata
        output_data['metadata'] = {
            'adjusted': True,
            'error': overall_error,
            'calibration_date': '2025-09-25',  # Current date
            'board_type': 'charuco',
            'board_size': self.config['calibration']['board_size'],
            'square_length': self.config['calibration']['board_square_side_length'],
            'marker_length': self.config['calibration']['board_marker_length']
        }
        
        # Add paired points information if available
        if hasattr(self, 'paired_points_info') and self.paired_points_info['corner_ids']:
            paired_points_data = {
                'corner_ids': list(self.paired_points_info['corner_ids']),
                'physical_distance_mm': self.paired_points_info['physical_distance_mm'],
                'detection_count': self.paired_points_info['detection_count']
            }
            
            # Add multi-pair statistics if available
            if 'total_pairs_used' in self.paired_points_info:
                paired_points_data['total_pairs_used'] = self.paired_points_info['total_pairs_used']
            
            if 'pair_statistics' in self.paired_points_info:
                paired_points_data['pair_statistics'] = self.paired_points_info['pair_statistics']
            
            output_data['metadata']['paired_points'] = paired_points_data
        
        # Calculate overall error if not provided
        if overall_error == 0.0:
            errors = [cam_data.get('reprojection_error', 0) for cam_data in results.values()]
            overall_error = float(np.mean(errors)) if errors else 0.0
            output_data['metadata']['error'] = overall_error
        
        # Save to TOML file
        try:
            with open(output_path, 'w') as f:
                toml.dump(output_data, f)
            
            logger.info("Calibration results saved successfully!")
            logger.info(f"Overall reprojection error: {overall_error:.4f}")
            
        except Exception as e:
            logger.error(f"Error saving calibration results: {e}")
            raise


def main():
    """Main function to run the calibration process."""
    parser = argparse.ArgumentParser(description='Charuco Board Camera Calibration')
    parser.add_argument('--config', '-c', 
                       default='config.toml',
                       help='Path to configuration file (default: config.toml)')
    parser.add_argument('--calibration-dir', '-d',
                       default='.',
                       help='Directory containing calibration videos (default: current directory)')
    parser.add_argument('--output', '-o',
                       default='calibration_output.toml',
                       help='Output calibration file (default: calibration_output.toml)')
    parser.add_argument('--frames', '-f', type=int,
                       default=50,
                       help='Number of frames to sample (default: 50)')
    parser.add_argument('--no-display', action='store_true',
                       help='Disable visual display of detections')
    
    # Distortion parameter optimization flags
    parser.add_argument('--optimize-k1', action='store_true',
                       help='Optimize k1 radial distortion coefficient')
    parser.add_argument('--optimize-k2', action='store_true',
                       help='Optimize k2 radial distortion coefficient')
    parser.add_argument('--optimize-k3', action='store_true',
                       help='Optimize k3 radial distortion coefficient')
    parser.add_argument('--optimize-p1', action='store_true',
                       help='Optimize p1 tangential distortion coefficient')
    parser.add_argument('--optimize-p2', action='store_true',
                       help='Optimize p2 tangential distortion coefficient')
    
    # Convenience flags for common combinations
    parser.add_argument('--optimize-radial', choices=['k1', 'k1k2', 'k1k2k3', 'all'], 
                       help='Convenience flag - optimize radial distortion: k1 only, k1+k2, k1+k2+k3, or all parameters')
    parser.add_argument('--fix-all-distortion', action='store_true',
                       help='Fix all distortion parameters at zero (assume no lens distortion)')
    
    # Focal length control flags
    parser.add_argument('--fix-focal-length', type=str,
                       help='Fix focal length(s) - single value for all cameras (e.g., "8600") or comma-separated list per camera (e.g., "8600,8700,8550")')
    parser.add_argument('--fix-aspect-ratio', type=float, default=1.0,
                       help='Fix aspect ratio (fy/fx) at specified value (default: 1.0 for square pixels)')
    parser.add_argument('--optimize-focal-length', action='store_true', default=True,
                       help='Allow focal length optimization (default behavior)')
    
    # CSV export flag
    parser.add_argument('--export-detections', action='store_true', default=True,
                       help='Export corner detections to CSV files (paired_pts-xypts.csv and unpaired_pts_xypts.csv) (default: True)')
    parser.add_argument('--no-export-detections', dest='export_detections', action='store_false',
                       help='Disable export of corner detections to CSV files')
    parser.add_argument('--flip-y', action='store_true', default=True,
                       help='Flip Y coordinates in CSV export (subtract from image height) for bottom-left origin coordinate systems (default: True)')
    parser.add_argument('--no-flip-y', dest='flip_y', action='store_false',
                       help='Disable Y-coordinate flipping in CSV export')
    parser.add_argument('--all-frames', action='store_true',
                       help='Export one row per video frame in paired CSV, using NaN for frames without detections')
    
    parser.add_argument('--camera-profile', action='store_true', default=True,
                       help='Export camera profile file (camera_profile.txt) with intrinsic parameters and distortion coefficients (default: True)')
    parser.add_argument('--no-camera-profile', dest='camera_profile', action='store_false',
                       help='Disable export of camera profile file')
    
    parser.add_argument('--stereo', action='store_true',
                       help='Perform stereo calibration between camera pairs (default: individual camera calibration only)')
    
    parser.add_argument('--display-delay', type=int, default=1,
                       help='Delay between frames in milliseconds when displaying detections (default: 1ms)')
    
    parser.add_argument('--match-timestamps', action='store_true',
                       help='Group videos by matching timestamps (e.g., cam1_timestamp.mov, cam2_timestamp.mov, cam3_timestamp.mov) and only use the first matching set for calibration')

    args = parser.parse_args()
    
    try:
        # Initialize calibrator
        calibrator = CharucoCalibrator(args.config)
        
        # Find video files
        video_files = calibrator.find_video_files(args.calibration_dir)
        
        if not video_files:
            logger.error("No video files found in the specified directory")
            return
        
        # Group videos by timestamp if requested
        if args.match_timestamps:
            video_groups = calibrator.group_videos_by_timestamp(video_files)
            if not video_groups:
                logger.error("No video groups found after timestamp matching")
                return
            
            # Use only the first group for calibration
            video_files = video_groups[0]
            logger.info(f"Using first video set with {len(video_files)} cameras for calibration")
        
        # Process videos to collect calibration data
        calibrator.process_videos(
            video_files, 
            sample_frames=args.frames,
            display_detections=not args.no_display,
            display_delay_ms=args.display_delay
        )
        
        logger.info("Calibration data collection completed successfully!")
        
        # Get calibration flags including focal length and distortion control
        num_cameras = len(video_files)
        calibration_flags, focal_lengths_list, optimization_info = calibrator.get_calibration_flags(args, num_cameras)
        logger.info(f"Calibration parameters: {optimization_info}")
        
        # Perform camera calibration
        calibration_results = calibrator.calibrate_cameras(
            calibration_flags=calibration_flags,
            focal_lengths_list=focal_lengths_list,
            optimization_info=optimization_info,
            enable_stereo=args.stereo
        )
        
        # Calculate overall error
        errors = [cam_data.get('reprojection_error', 0) for cam_data in calibration_results.values()]
        overall_error = float(np.mean(errors)) if errors else 0.0
        
        # Determine output directory - use calibration directory if output path is just a filename
        if os.path.dirname(args.output):
            # User specified a full path
            output_dir = os.path.dirname(args.output)
            output_file = args.output
        else:
            # User specified just a filename, use calibration directory
            output_dir = args.calibration_dir
            output_file = os.path.join(args.calibration_dir, args.output)
        
        logger.info(f"Output directory: {output_dir}")
        
        # Export detections to CSV if requested (do this first to populate paired_points_info)
        if args.export_detections:
            calibrator.export_detections_to_csv(output_dir, flip_y=args.flip_y, all_frames=args.all_frames)
            # Also save a debug frame showing corner numbering
            calibrator.save_debug_frame(output_dir)
        
        # Export camera profile if requested
        if args.camera_profile:
            calibrator.export_camera_profile(calibration_results, output_dir, flip_y=args.flip_y)
        
        # Save calibration results (includes paired points info if CSV export was done)
        calibrator.save_calibration_results(
            calibration_results, 
            output_file, 
            overall_error
        )
        
        logger.info(f"Camera calibration completed! Results saved to {output_file}")
        logger.info(f"Number of cameras calibrated: {len(calibration_results)}")
        logger.info(f"Overall reprojection error: {overall_error:.4f} pixels")
        
    except Exception as e:
        logger.error(f"Calibration failed: {e}")
        raise


if __name__ == "__main__":
    main()