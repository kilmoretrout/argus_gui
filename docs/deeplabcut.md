# Working with DeepLabCut
Argus GUI can be integrated with [DeepLabCut](https://github.com/DeepLabCut/DeepLabCut), a popular tool for animal pose estimation, to enhance your 3D tracking capabilities. This section provides guidance on how to set up and use Argus with DeepLabCut.

## 3D in DeepLabCut
DeepLabCut natively supports 3D tracking with several significant limitations that Argus can help overcome:
1. **Number of Cameras**: DeepLabCut is limited to two cameras for 3D tracking, while Argus can handle multiple cameras.
2. **Camera Synchronization**: Argus provides robust synchronization tools using audio, while DeepLabCut requires that video files are synchronized before importing.
3. **Filming Volume Calibration**: Argus can calibrate the filming volume using a wand, which is not supported in DeepLabCut, which requires filming of checkerboard patterns to simultaneous determine camera instrinsics and extrinsics. The wand calibration (structure-from-motion) allows for 3D tracking in difficult to access filming volumes by separating the camera intrinsics and extrinsics calibration steps.

For a robust 2-camera setup in a controlled envinroment, we strongly recommend using DeepLabCut directly for the simplest workflow. However, for more complex setups or when using more than two cameras, Argus provides a more flexible and powerful solution, and can take advantage of DeepLabCut's pose estimation capabilities.

## Installation
We do not recommend trying to install Argus and DeepLabCut in the same Python environment. It might work, but both have a number of dependencies that may conflict. Instead, we recommend using a separate environment for Argus and DeepLabCut.

## Using Argus with DeepLabCut
Of all of the modules in Argus, the **Clicker** module is the manual analog of DeepLabCut pose estimation; and it can both import and export DeepLabCut data. This provides several possible uses and workflows:

### 1. Using Argus Clicker to manually clean up DeepLabCut data
Even for single-camera setups, DeepLabCut may not produce perfect tracking data. The ideal fix would be to iterate through extracting outliers, refining the model, retraining the model, and then re-tracking. Where that timeline isn't practical, you can use Argus Clicker to manually clean up the tracking data.
1. Track your video in DeepLabCut as normal. This should produce a .h5 file with the tracking data.
2. Open Argus Clicker and load the video in question.
3. Once the video window is open, type `O` for the options window and click the `Load DeepLabCut data` button to import the DeepLabCut tracking data.
4. You can now use Argus Clicker to manually edit the tracking data, deleting or correcting points as needed. 
5. When you are done, type `O` again to open the options window. You can either save it as a dense or spare Argus file, or select the `DeepLabCut .h5` option to save the data back to a DeepLabCut .h5 file. If you use this option, the likelihood values for any points you edited will be set to 1.0.
6. Note that to use this edited file in DeepLabCut functions (like `create_labeled_video`), you will need to rename the file to match the original DeepLabCut file name, so make a copy of the original file and put in a new folder before renaming the edited file.

### 2. Using Argus Clicker to export DeepLabCut data for training
If you have previously used Argus Clicker to manually track points in a video, and you wan to use that data to train a DeepLabCut model, you can export the data in the correct format.
A function to do that is available in [DLCconverterDLT](https://github.com/backyardbiomech/DLCconverterDLT), and will be included in a future version of Argus.

### 3. Using Argus Clicker to import DeepLabCut data for 3D tracking
If you have a DeepLabCut model trained for 3D tracking, you can use Argus **Wand** for 3D calibration and **Clicker** to import the tracking data and use it for 3D triangulation.
1. Train your DeepLabCut model to track each video. Ignore DeepLabCut's 3D tracking capabilities, as Argus will handle that. This might be one model per camera, or if all cameras have similar enough views you might make a single model for all cameras.
2. Track your animals in each camera using DeepLabCut. This should produce a .h5 file with the tracking data for each camera.
3. You can train a separate model to track a wand with DeepLabCut. However, since only about 60 wand points are needed, it may be faster for single set-ups to manually track the wand using Argus **Clicker**. If you used DeepLabCut to track the wand, open all of the wand videos in Argus **Clicker** with the appropriate offsets. Once the video windows are open, type `O` for the options window and click the `Load DeepLabCut data` button to import the DeepLabCut tracking data. You will be asked for one tracking file per video, so make sure you open them in the same order as you loaded the videos. Clean up the wand tracks and save the data as an Argus file.
4. Re-open the videos and manually digitized some unpaired points and reference points if needed (see the [Wand module documentation](user-guide.md#wand) for details).
5. Open the **Wand** module and load the wand tracking data (paired points), unpaired points, and reference points, and camera profiles. Run wand, remove outliers if needed, and save the results.
6. Open the **Clicker** module and load the animal tracking videos with appropriate offsets.
7. Once the video windows are open, type `O` for the options window and click the `Load DeepLabCut data` button to import the DeepLabCut tracking data for each camera. You will be asked for one tracking file per video, so make sure you open them in the same order as you loaded the videos.
8. Load the DLT coefficients file generated by the **Wand** module and the camera profile. 
9. Saving as an Argus file will now produce an `xyzpts.csv` file with the 3D triangulated points for each camera.
10. There are additional funcitons to streamline the triangulation availabel at [DLCconverterDLT](https://github.com/backyardbiomech/DLCconverterDLT), and will be included in a future version of Argus.