# User Guide

Welcome to the comprehensive user guide for Argus GUI. This guide covers all aspects of using the software for 3D camera calibration and reconstruction.

## Table of Contents

1. [Interface Overview](#interface-overview)
2. [Clicker](#clicker)
3. [Sync](#syncp)
4. [Wand](#wand)
5. [Patterns](#patterns)
6. [Calibrate](#calibrate)
7. [Dwarp](#dwarp)

## Interface Overview

The Argus GUI displays tabs for each module, allowing you to switch between different functionalities easily. The left side of the GUI allows you to select files and change settings, while the right side displays some important text outputs of all of the modules. Each tab is independent, so you can load different files or settings in each tab without affecting the others. However you should only have one process running at a time. You can use the `Cancel running process` button to stop any currently running process, such as calibration or reconstruction.

## Clicker

Several imporant steps of the 3D reconstruction process are performed by marking and tracking individual points in multiple videos. Clicker is where you can view and navigate through videos while placing markers. 

### Main GUI Elements

![Clicker Tab](/docs/images/clicker_img.png)

1. Video List: Displays loaded videos and frame offsets. The first camera has an offset of 0. 
2. `+` Button: Add a new video to the list. After selecting a video, you will be prompted to set the frame offset for that camera. You can edit that offset by double-clicking the offset value in the table, and by using the ⬆ and ⬇ keys while viewing the video.
3. `-` Button will remove the selected video from the list.
4. `Clear` button will clear all videos from the list.
5. `Display Resolution`: Select `Half` resolution for large videos if you are working on a small screen (e.g. laptop) or if you want faster processing. Otherwise, select `Full` resolution for best quality. Video windows can be resized once displayed. All coordinates will be converted to the original resolution when saving no matter what resolution you select.
6. `Load Config`: Load a configuration file that is saved from a previous session. If you use this, you do **not** need to add videos to the list. After selecting your config file the tracking interface will load.

### Clicker Video Interface

![Clicker Video Interface](/docs/images/clicker_vids.png)

Each video will open in a separate window. The window title has several important pieces of information:
1. Video file name
2. Displayed frame number
3. Frame offset (relative to the first camera)
4. Current track name

Markers from all frames of the current Track will be displayed by default. Lines connect makers from consecutive frames. You can change the size of the markers in the options dialog.

The marker representing the current current track in the current frame is highlighted in a larger pink circle.

Light blue lines display the epipolar lines that show a predicted position based on marker positions in the current frame in other cameras and the 3D reconstruction (so they only display if you have loaded a camera profile and DLT coefficients, and placed markers in other cameras).

### Video Controls

- `Left click`: Place a marker at the current frame position. If a marker already exists, it will be updated to the new position.
- `Right click` or `d`: Delete the marker at the current frame position in the active camera.
-  `shift-d`: Delete the current track (with confirmation dialog). You cannot delete the only track, so you may need to add a new track first.
- `=`: Zoom in on the video. `-`: Zoom out. You can also use the mouse wheel to zoom in and out. Zooming will center on the current mouse cursor position.
- `r`: Reset the zoom level to the default.
- `Shift + Left Click and drag`: Pan in the image
- `f`: Move forward one frame. `F`: Move forward 50 frames.
- `b`: Move backward one frame. `B`: Move backward 50 frames.
- `g`: Go to a specific frame number. A dialog will open to enter the frame number.
- `,`: switch to the previous track.
- `.`: switch to the next track.
- `➡`: Go to the next frame with a marked position in the current track.
- `⬅`: Go to the previous frame with a marked position in the current track.
- `⬆`: Increase the frame offset for the current camera by 1. This will move the video forward in time.
- `⬇`: Decrease the frame offset for the current camera by 1. This will move the video backward in time.
- `shift-C`: set directory to save captured images to
- `alt-C`: capture the current frame to the specified directory (not currently functional)
- `o`: Open the options dialog to change settings for the current project.
- `s`: Save the project data. Will prompt for a file name and location if not already set.
- `ctrl-s`: Save as... will prompt for a file name and location to save the current project data.
- `v`: toggle the display of the view finder in the lower right corner.
- `x`: toggle the 'sync' option which keeps all videos on the same frame. Can also be set in the options dialog.
- `7`: Grow the view-finder vertically by a pixel
- `U`: Shrink the view-finder vertically by a pixel
- `Y`: Grow the view-finder horizontally by a pixel
- `I`: Shrink the view-finder horizontally by a pixel
- `P`: Plot 3D positions (requires DLT coefficients and a camera profile)
- `L`: Load saved points (from .csv or .tsv file)

### Clicker Options Dialog

With any video window active, you can open the options dialog by typing `o` . This dialog allows you to configure various settings for the Clicker module that affect the current project rather than specific videos. All settings shown are saved to the project configuration file when you save the project.

![Clicker Options Dialog](/docs/images/clicker_options.png)

1. Navigate to and select a camera profile that contains the camera intrinsics for your specific camera. You can use one of the included profiles or build your own using **Patterns** and **Calibrate**. This is required for 3D reconstruction.
2. Navigate to and select a DLT coefficients file that contains the camera extrinsics for your specific camera. You can use **Wand** to determine the DLT coefficients for a camera set up based on points tracked in **Clicker**. This is required for 3D reconstruction.
3. Currently active track name. Use the dropdown to select a different track, or use the `,` and `.` keys to switch tracks in the video window instead of opening this dialog.
4. To add a new track, click this button and enter a name for the new track.
5. `Display all tracks` checkbox: If checked, all tracks will be displayed in the video window. If unchecked, only the current track will be displayed. This may slow down the video display if there are many tracks and points.
6. `Automatically advance frames` when placing markers. If checked, the video will automatically advance to the next frame after placing a marker. If unchecked, you will need to manually advance frames using the `f` key.
7. `Keep all videos on the same frame` checkbox: If checked, all videos will be synchronized to the same frame when placing markers. If unchecked, each video can be advanced independently. Keeping this checked may slow down the video display on some computers.
8. Change the marker size and track line thickness display. This is display only, and does not affect the saved data.
9. `Display`: Select `RGB color` or `grayscale` for the video display. Grayscale may be faster for large videos.
10. ` Save 95% CI...` checkbox. If checked, a bootstrapping algorithm based on the 3d reconstruction error will be used to compute a 95% confidence interval for the 3D position of each marker in each frame. This will slow down the saving process, but will provide a more accurate estimate of the uncertainty in the 3D positions.
11. Save format: Select `Dense .csv` or `Sparse .tsv` for saving the tracked points. Dense format saves all frames with and without markers, while sparse format only saves frames where markers are present. Dense format is more generally useful for analysis, while sparse format is more compact for very long videos espeically with many frames without markers.
12. `Save location/tag`: Click to select the directory where the project data will be saved. The dialog will require you to enter a file "tag" (on windows you will also need to add a file extension, which will be removed. This will be used for saving the tracked points and other project data. Depending on options above, this will save muliple files all starting with the same tag, appended with additional information and the file extension. For example, if you enter "trial01" as the tag, and have entered a camera profile and dlt coefficients the following files will be saved:
   - `trial01-xypts.csv` (or .tsv)
   - `trial01-xyzpts.csv` (or .tsv)
   - `trial01-offsets.csv` 
   - `trial01-res.csv` (or .tsv) - the 3D reconstruction errors for each marker for each frame
   - `trial01-config.yaml` - the project configuration file containing all settings and metadata
   - other files will be saved in the 95% CI option is selected

## Sync

Before analyzing videos in **Clicker**, you need to determine the synchronization offsets between cameras. The **Sync** module provides tools to synchronize multiple video files based on their audio tracks. We suggest repeated loud sounds delivered directly to each camera. See [the paper](/docs/citation.md) for some details on how to synchronize cameras using sound. 

![Sync Tab](/docs/images/sync_img.png)

1. **Add Video**: Click the `+` button to add a video file to the list. You should add all videos from your cameras for a specific trial. Make sure you load them in the same order you will load them in **Clicker**. 
2. **Remove Video**: Select a video and click the `-` button to remove it from the list.
3. **Clear List**: Click the `Clear` button to remove all videos from the list.
4. **Show Waves**: Click the `Show Waves` button to display the audio waveforms for all loaded videos. This will open a new window showing the audio waveforms for each video, which can help you visually identify synchronization points.

![Sync Waves](/docs/images/sync_waves_img.png)

5. **Specify Time Range**: Long videos, especially with low sync-signal-to-noise-ratios may not syncrhonize accurately if the full video is used. Use the waveform display to determine the approximate start and end time (in decimal minutes) of your synchronization sequence, and enter those values in `Start Time` and `End Time` fields.
6. **Output filename**: Specify the output filename for the synchronization results. By default this will be named based on the first video loaded in the list, with `_offsets.csv` appended, saved to the same directory as the first video. You can change this to any valid filename, but it must end with `.csv`. This file will contain the time and frame offsets for each camera, plus an confidence score for the synchronization. The confidence score is based on the correlation between the audio waveforms of the cameras.
7. **Write Log**: If checked, a log file will be created with the output that is printed to the right side of the window. 
8. **Go**: Click this button to start the synchronization process. The software will analyze the audio tracks of the loaded videos and attempt to find the best synchronization offsets based on the specified time range. 

## Wand

Camera extrinsics (location and orientation relative to a common coordinate system) are determined by waving a "wand" with two markers in front of the cameras to provide a known distance calibration. **Wand** uses the wand (or "paired") points, and other unpaired points (these can be static objects in the background, or moving subjects), tracked in **Clicker**, along with camera intrinsics, and processed through sparse bundle adjustment to optimize camera extrinsics. It can also further optimize camera intrinsics. The output is a DLT coeffients file than can be loaded into **Clicker** for 3D reconstruction of tracks. 

![Wand Tab](/docs/images/wand_img.png)

1. **Select paired points file**: This should be a `-xypts.csv` file saved from **Clicker** containing two tracks that mark two points a constant distance apart. The distance between these two points will be used to determine the scale of the 3D reconstruction.


## Project Management

### Creating a New Project

1. **File → New Project** or click the "New Project" button
2. Choose a project directory (will create subfolder structure)
3. Enter project name and description
4. Configure default settings

### Suggested Project Structure

A lot of files will be tracked and created in the process of using Argus, so it is important to keep them organized. The following structure is one recommended for your project directory:

```
MyProject/
├── date/          # one folder per day, or camera setup/session
    └── calibration  # to contain camera intrinsics and extrinsics
        ├── camera1.yaml  # Camera 1 calibration data
        ├── camera2.yaml  # Camera 2 calibration data
        └── ...
├── config.yaml    # Project configuration file
├── cameras/              # Camera calibration data
├── videos/              # Video files (or links)
├── images/              # Image sequences
├── points/              # Detected/manual points
├── calibration/         # Calibration results
├── reconstruction/      # 3D reconstruction data
└── exports/             # Exported results
```

### Saving and Loading

- **Auto-save**: Projects are saved automatically every 5 minutes
- **Manual save**: Ctrl+S or File → Save
- **Load project**: File → Open Project (select .yaml config file)

## Camera Setup

### Adding Cameras

1. Click "Add Camera" in the cameras panel
2. Configure camera properties:
   - **Name**: Descriptive camera name
   - **Type**: Video file, image sequence, or live camera
   - **Source**: File path or device ID
   - **Properties**: Resolution, frame rate, etc.

### Camera Types

#### Video Files
- Supported formats: MP4, AVI, MOV, MKV
- Should be synchronized across cameras
- Can specify start/end frames

#### Image Sequences
- Supported formats: JPG, PNG, TIFF, BMP
- Images should be numbered consistently
- Example: cam1_001.jpg, cam1_002.jpg, etc.

#### Live Cameras
- USB cameras, IP cameras, or capture devices
- Real-time preview and capture
- Adjustable camera parameters

### Synchronization

For accurate 3D reconstruction, cameras must be synchronized:

- **Hardware sync**: Use external trigger or sync signal
- **Software sync**: Manual alignment using common events
- **Audio sync**: Use audio tracks to align video files
- **Visual sync**: Use flashes or other visual cues

## Data Import

### Video Import

1. **File → Import → Videos**
2. Select video files for each camera
3. Configure import settings:
   - Frame range to import
   - Downsampling factor
   - Quality settings

### Image Import

1. **File → Import → Images**
2. Select folders containing image sequences
3. Map folders to cameras
4. Verify image ordering and timing

### Batch Import

For large datasets:
1. **File → Import → Batch Import**
2. Select parent directory containing organized subdirectories
3. Configure automatic camera detection and mapping
4. Review and confirm import settings

## Point Detection

### Detection Methods

#### Checkerboard Detection
- Automatic detection of checkerboard patterns
- Configure board size (internal corners)
- Adjust detection sensitivity
- Sub-pixel accuracy refinement

#### Circle Grid Detection
- Detects circular patterns
- More robust to lighting variations
- Symmetric or asymmetric grids supported
- Higher accuracy than checkerboards

#### LED/Marker Detection
- Detects bright spots or markers
- Adjustable intensity threshold
- Blob detection algorithms
- Good for large volumes or specific markers

#### Manual Point Selection
- Click to manually select points
- Useful for custom calibration objects
- Supports multiple point types
- Can combine with automatic detection

### Detection Settings

#### Sensitivity Settings
- **Threshold**: Detection sensitivity (0-100)
- **Min/Max Size**: Size constraints for detected features
- **Aspect Ratio**: Expected shape constraints
- **Clustering**: Group nearby detections

#### Quality Filters
- **Sharpness**: Remove blurry detections
- **Contrast**: Minimum contrast requirements
- **Symmetry**: Geometric consistency checks
- **Temporal**: Consistency across frames

### Manual Editing

After automatic detection:
1. **Review Results**: Check detected points in all views
2. **Delete Bad Points**: Right-click → Delete on poor detections
3. **Add Missing Points**: Manual click to add missed points
4. **Refine Positions**: Drag points for fine adjustments

## Calibration Process

### Calibration Methods

#### Standard Calibration
- Uses detected calibration points
- Estimates intrinsic and extrinsic parameters
- Includes distortion correction
- Good for most applications

#### Self-Calibration
- Uses feature matches between views
- No calibration object required
- Requires sufficient camera motion
- Less accurate than standard methods

#### Hybrid Calibration
- Combines calibration object and feature matching
- Improved accuracy and robustness
- Handles sparse calibration data
- Recommended for challenging scenarios

### Calibration Parameters

#### Intrinsic Parameters
- **Focal Length**: Camera focal length in pixels
- **Principal Point**: Image center offset
- **Distortion**: Radial and tangential distortion coefficients
- **Aspect Ratio**: Pixel aspect ratio

#### Extrinsic Parameters
- **Rotation**: Camera orientation in 3D space
- **Translation**: Camera position in 3D space
- **Scale**: Overall scale of the coordinate system

### Quality Assessment

#### Reprojection Error
- Average pixel error across all points
- Should be < 1 pixel for good calibration
- Check for outliers or systematic errors

#### Calibration Plots
- Error distribution plots
- Camera position visualization
- Calibration point coverage maps
- Parameter uncertainty estimates

### Refinement

If calibration quality is poor:
1. **Add More Data**: Capture additional calibration images
2. **Improve Coverage**: Ensure calibration object fills entire field of view
3. **Remove Outliers**: Delete poor quality detections
4. **Adjust Parameters**: Modify calibration settings
5. **Re-run Calibration**: Iterate until satisfactory results

## 3D Reconstruction

### Point Reconstruction

1. **Select Points**: Click corresponding points in multiple camera views
2. **Triangulate**: Calculate 3D coordinates using camera calibration
3. **Refine**: Optimize 3D positions using all available views
4. **Validate**: Check reconstruction errors and geometry

### Batch Reconstruction

For large datasets:
1. **Feature Detection**: Automatically detect features to track
2. **Feature Matching**: Match features across camera views
3. **Trajectory Reconstruction**: Calculate 3D trajectories over time
4. **Smoothing**: Apply temporal smoothing to reduce noise

### Reconstruction Quality

#### Geometric Validation
- **Triangulation Angle**: Angle between rays from different cameras
- **Reprojection Error**: Back-projection error in each camera
- **3D Residuals**: Distance between rays in 3D space
- **Temporal Consistency**: Smoothness of trajectories

#### Statistical Analysis
- **Point Clouds**: Visualize 3D point distributions
- **Measurement Tools**: Distance and angle measurements
- **Coordinate Transformations**: Convert between coordinate systems
- **Export Options**: Various 3D file formats

## Data Export

### Export Formats

#### 3D Points
- **CSV**: Simple comma-separated values
- **JSON**: Structured data with metadata
- **PLY**: 3D point cloud format
- **MAT**: MATLAB data format
- **HDF5**: Hierarchical data format

#### Camera Data
- **Calibration Files**: Camera parameters and distortion
- **Projection Matrices**: Direct projection matrices
- **OpenCV Format**: Compatible with OpenCV library
- **Blender**: Import into Blender for visualization

#### Videos and Images
- **Undistorted**: Remove lens distortion
- **Synchronized**: Align timing across cameras
- **Annotated**: Overlay detected points and tracks
- **Cropped**: Extract regions of interest

### Export Settings

- **Coordinate System**: Choose world coordinate frame
- **Units**: Specify measurement units
- **Precision**: Number of decimal places
- **Metadata**: Include calibration information
- **Compression**: Data compression options

### Integration

#### MATLAB/Python
- Direct data loading functions
- Example analysis scripts
- Visualization tools
- Further processing pipelines

#### Other Software
- **DLTdv**: Direct export compatibility
- **OpenCV**: Standard calibration format
- **Blender**: 3D visualization and animation
- **CAD Software**: Engineering analysis tools

## Tips and Best Practices

### Camera Setup
- Use high-quality cameras with global shutters
- Ensure adequate lighting and contrast
- Minimize camera vibration and movement
- Plan camera positions for good triangulation angles

### Calibration
- Use high-quality calibration objects
- Cover entire field of view during calibration
- Capture calibration data at multiple distances and angles
- Check calibration quality before proceeding

### Reconstruction
- Ensure good lighting and contrast for tracking
- Use appropriate frame rates for motion being captured
- Validate 3D results against known measurements
- Apply appropriate smoothing for noisy data

### Troubleshooting
- Check camera synchronization if 3D results look wrong
- Verify calibration quality if reconstruction is poor
- Ensure sufficient baseline between cameras
- Check for and remove systematic errors
