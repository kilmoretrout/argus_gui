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

![Clicker Tab](images/clicker_img.png)

1. Video List: Displays loaded videos and frame offsets. The first camera has an offset of 0. 
2. `+` Button: Add a new video to the list. After selecting a video, you will be prompted to set the frame offset for that camera. You can edit that offset by double-clicking the offset value in the table, and by using the ⬆ and ⬇ keys while viewing the video.
3. `-` Button will remove the selected video from the list.
4. `Clear` button will clear all videos from the list.
5. `Display Resolution`: Select `Half` resolution for large videos if you are working on a small screen (e.g. laptop) or if you want faster processing. Otherwise, select `Full` resolution for best quality. Video windows can be resized once displayed. All coordinates will be converted to the original resolution when saving no matter what resolution you select.
6. `Load Config`: Load a configuration file that is saved from a previous session. If you use this, you do **not** need to add videos to the list. After selecting your config file the tracking interface will load.

### Clicker Video Interface

![Clicker Video Interface](images/clicker_vids.png)

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

![Clicker Options Dialog](images/clicker_options.png)

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

![Sync Tab](images/sync_img.png)

1. **Add Video**: Click the `+` button to add a video file to the list. You should add all videos from your cameras for a specific trial. Make sure you load them in the same order you will load them in **Clicker**. 
2. **Remove Video**: Select a video and click the `-` button to remove it from the list.
3. **Clear List**: Click the `Clear` button to remove all videos from the list.
4. **Show Waves**: Click the `Show Waves` button to display the audio waveforms for all loaded videos. This will open a new window showing the audio waveforms for each video, which can help you visually identify synchronization points.

![Sync Waves](images/sync_waves_img.png)

5. **Specify Time Range**: Long videos, especially with low sync-signal-to-noise-ratios may not syncrhonize accurately if the full video is used. Use the waveform display to determine the approximate start and end time (in decimal minutes) of your synchronization sequence, and enter those values in `Start Time` and `End Time` fields.
6. **Output filename**: Specify the output filename for the synchronization results. By default this will be named based on the first video loaded in the list, with `_offsets.csv` appended, saved to the same directory as the first video. You can change this to any valid filename, but it must end with `.csv`. This file will contain the time and frame offsets for each camera, plus an confidence score for the synchronization. The confidence score is based on the correlation between the audio waveforms of the cameras.
7. **Write Log**: If checked, a log file will be created with the output that is printed to the right side of the window. 
8. **Go**: Click this button to start the synchronization process. The software will analyze the audio tracks of the loaded videos and attempt to find the best synchronization offsets based on the specified time range. 

## Wand

Camera extrinsics (location and orientation relative to a common coordinate system) are determined by waving a "wand" with two markers in front of the cameras to provide a known distance calibration. **Wand** uses the wand (or "paired") points, and other unpaired points (these can be static objects in the background, or moving subjects), tracked in **Clicker**, along with camera intrinsics, and processed through sparse bundle adjustment to optimize camera extrinsics. It can also further optimize camera intrinsics. The output is a DLT coeffients file than can be loaded into **Clicker** for 3D reconstruction of tracks. 

![Wand Tab](images/wand_img.png)

1. **Select paired points file**: This should be a `-xypts.csv` file saved from **Clicker** containing two tracks that mark two points a constant distance apart. The distance between these two points will be used to determine the scale of the 3D reconstruction.
2. **Select unpaired points file**: This should be a `-xypts.csv` file saved from **Clicker**. These can be static objects in the background, or moving subjects as long as the same actual object is accurately tracked in multiple cameras in the same time-synced frames. The more of the filming volume covered by unpaired points, the better the camera extrinsics will be estimated. These should all be in a single clicker track. 
3. **Select reference points file**: This should be a `-xypts.csv` file saved from **Clicker** containing a single track that marks 1-4 points in all cameras. This will be used to determine the origin and orientation of the coordinate system for the 3D reconstruction: 1 point will set the origin, 2 points will set the z-axis (plumb line), 3 points will set a horizontal plane with the z-axis calculated, and 4 points will set the origin, x, y, and z axes with the right-hand rule. You can also track a free-falling object in the filming volume, such as a ball, and select "Gravity" as the point type to calculate the z-axis. 
4. **Select camera profile**: This should be a camera profile file that contains the camera intrinsics for your specific camera. You can use one of the included profiles or build your own using **Patterns** and **Calibrate**.
5. **Wand Length**: Enter the length of the wand. The units used here will set the units for the 3D reconstruction.
6. **Referecne Point Type**: Select the type of reference points you are using. This will determine how the coordinate system is set up. Options for static objects include `Axis` (1, 2, or 4 poitns), or `Plane` (3 points). If you are using a free-falling object, select `Gravity`.
7. **Recording frequency**: This is the camera recording frequency for the free-falling object for a `Gravity` reference point type.
8. **Intrinsics** and **Distortion**: Specifiy which camera intrinsics and distortion parameters you would like to optimizein the sparse bundle adjustment based on the paired and unpaired points. You can also use the intrinsics from the camera profile (`Optimize none`).
10. **Report on outliers**: If checked, the software will report on outliers in the paired and unpaired points after the sparse bundle adjustment and give the option to remove the outliers and re-run the optimization. This is automatic if you also selsect **Display results**. 
11. **Choose reference camera**: Optimize the choice of reference camera such that there are the most 3D triangulatable points, i.e. camera with the most shared information.
12. **Output camera profiles**: Good to use if you optimized intrinsics and distortion as those new values will be saved in a new camera profile to be used in **Clicker**. 
13: **Display results**: If checked, the software will display the results of the sparse bundle adjustment in a new window. This will show the 3D positions of the paired and unpaired points, the reference points, and allow you to visualize the camera extrinsics. This will also include an outlier detection and removal step.
14. **Output file prefix and location**: The default is the same directory as the paired points file, with `_cal` added. This will save a number of files depending on the options selected, all starting with the file prefix. 

15. **Write log**: If checked, a log file will be created with the output that is printed to the right side of the window.
16. **Go**: Click this button to start the sparse bundle adjustment process. If `Display results` is checked, the window below will open showing the results of the sparse bundle adjustment. 

![Wand Results](images/wand_report.png)

The 3D plot of the calibration scene can be navigated using the mouse:
- Left click and drag to rotate the view
- Cmd-click (macOS) or Ctrl-click (Windows/Linux) and drag to pan the view
- Scroll wheel to zoom in and out

Colors are as follows:
- **Paired points**: magenta lines
- **Unpaired points**: cyan dots
- **Reference points**: red dots
- **Cameras**: green dots

- The `DLT errors` shows the rmse reconstruction error for each camera, which is the average distance between the marked 2D position in the video and the 3D position projected back to the 2D camera using the DLT coefficients.  Very good calibrations will have DLT errors of less than 1 pixel.
- The `Wand Score` is calculated as $100 * \frac{std_{wand}}{mean_{wand}}$, where `std_wand` is the standard deviation of the calculated wand length across all cameras, and `mean_wand` is the mean calculated wand length across all cameras. Good calibrations generally have a wand score of approximately 1.0 or less. 

### Output Files
Depending on the options selected, the following files will be saved to the output directory with the specified prefix:
- `*_dlt-coefficients.csv` - DLT coefficients file for use in **Clicker** (camera extriniscs)
- `*_-sba-profile.txt` - Camera profile file with optimized intrinsics and extrinsics. This is for compatibility with DLTdv and easyWand, and should not be used in **Clicker**. Each row represents a camera with the following columns:
     - fx - focal length for x in pixels
     - cx, cy - principal point in pixels, typically in middle of image
     - AR - aspect ratio, typically 1.
     - s - skew, typically 0.
     - r2,r4 - radial distortion coeffs according to Bourguet (dimensionless)
     - t1,t2 - tangential distortion coeffs (dimensionless)
     - r6 - radial distortion coeff according to Bourguet (dimensionless)
     - q0,qi,qj,qk - unit quaternion rotation of camera (dimensionless)
     - tx,ty,tz - translation of camera in real world units
- `*_-sba-profile-orig.txt` - a the same profile above before full optimization
- `*-clicker_profile.txt` - a version of `sba-profile.txt` formatted for use in **Clicker** with the following columns:
     - camera number
     - fx - focal length for x in pixels
     - image width, height
     - cx, cy - principal point in pixels, typically in middle of image
     - AR - aspect ratio, typically 1.
     - r2,r4- radial distortion coeffs according to Bourguet (dimensionless)
     - t1,t2 - tangential distortion coeffs (dimensionless)
     - r6 - radial distortion coeff according to Bourguet (dimensionless)
 
- `*_unpaired-points-xyz.csv` - The 3D positions of the unpaired points after the sparse bundle adjustment
- `*_paired-points-xyz.csv` - The 3D positions of the paired points after the sparse bundle adjustment

## Patterns

## Calibrate

## Dwarp