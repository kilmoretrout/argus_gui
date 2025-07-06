# Quick Start Guide

Get up and running with your first tracking effort! This guide assumes you have already [installed Argus GUI](https://backyardbiomech.github.io/argus_gui/installation.html).

## Your First Track

### What You'll Need

- Video from at least one camera.
- Argus installed and working

### Step 1: Launch Argus GUI

Open your terminal/command prompt, activate your environment, and launch the GUI:

```bash
# If using pip installation
source argus_env/bin/activate  # macOS/Linux
argus_env\Scripts\activate     # Windows
argus-gui

# If using conda installation
conda activate argus
argus-gui
```

### Select Video Files

1. The **Clicker** tab will be active by default.
2. Click the `+` button to add a video.
3. Select the video size (use `half` on a laptop screen or for faster processing).
4. Click `Go`. You should see a window open showing the first frame of your video.

### Track Points

1. Click the mouse on the point you want to track in the video. The video will automatically advance to the next frame.
2. Click the point again in the next frame to continue tracking.
3. To add a new track, type the `o` key to open the options dialog. Click on `Add Track` and enter a name. Ok out of the options window and click to track a new point.
4. Use `f` and `b` keys to move forward and backward through the video frames. `shift + f` and `shift + b` will move 50 frames at a time.
5. The marker in the current frame will be highlighted in a larger pink circle. Right click will delete the mark in the current frame. 
6. Use `=` to zoom in, and `-` to zoom out. Scolling the mouse wheel will also zoom in and out. Type `r` to reset the zoom level.

### Saving the data

1. You can type `o` to open the options dialog and select a save location and name. `Ok` to close the dialog.
2. With a video window active, type `s` to save the current video data. This will overwrite without warning, so be careful!




## Quick Tips

- **Lighting**: Ensure even, bright lighting for better detection
- **Coverage**: Move calibration object to cover entire camera field of view
- **Angles**: Capture the calibration object at various angles and distances
- **Synchronization**: Ensure cameras are properly synchronized
- **Quality**: Delete poor quality frames/detections before calibration

## What's Next?

- Read the full [User Guide](https://backyardbiomech.github.io/argus_gui/user-guide.html) for detailed instructions
- Learn about [advanced calibration techniques](https://backyardbiomech.github.io/argus_gui/calibration.html)
- Explore [3D reconstruction workflows](https://backyardbiomech.github.io/argus_gui/reconstruction.html)
- Check out [video processing features](https://backyardbiomech.github.io/argus_gui/video-processing.html)

## Need Help?

- Check the [Troubleshooting Guide](https://backyardbiomech.github.io/argus_gui/troubleshooting.html)
- Review the [FAQ](https://backyardbiomech.github.io/argus_gui/faq.html)

