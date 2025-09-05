# Troubleshooting Guide

This guide helps you solve common issues when using Argus GUI. If you can't find a solution here, please check our [FAQ](docs/faq.md) or contact support.

## Installation Issues


### Package Installation Failures

**Problem**: Installation fails with dependency errors
```
ERROR: Could not find a version that satisfies the requirement
```

**Solutions**:
1. Update pip first:
   ```bash
   pip install --upgrade pip
   ```

2. Try installing with verbose output to see specific errors:
   ```bash
   pip install -v git+https://github.com/backyardbiomech/argus_gui.git
   ```

3. Install dependencies manually:
   ```bash
   pip install numpy pandas matplotlib opencv-python
   pip install git+https://github.com/backyardbiomech/argus_gui.git
   ```

### Virtual Environment Issues

**Problem**: Cannot activate virtual environment

**macOS/Linux Solution**:
```bash
source argus_env/bin/activate
```

**Windows Solution**:
```bash
argus_env\Scripts\activate.bat
```

**Alternative for Windows PowerShell**:
```bash
argus_env\Scripts\Activate.ps1
```

## Startup Issues

### GUI Won't Launch

**Problem**: Command `argus-gui` not found or GUI doesn't open

**Solutions**:
1. Verify installation:
   ```bash
   python -c "import argus_gui; print('Installation OK')"
   ```

2. Try launching directly:
   ```bash
   python -m argus_gui
   ```

3. Check if GUI packages are installed:
   ```bash
   pip install pyside6 pyqtgraph
   ```

### Graphics/OpenGL Errors

**Problem**: OpenGL or graphics-related error messages

**Solutions**:
1. Update graphics drivers
2. Try software rendering:
   ```bash
   export PYOPENGL_PLATFORM=osmesa  # Linux/macOS
   set PYOPENGL_PLATFORM=osmesa     # Windows
   ```
3. Install additional OpenGL packages:
   ```bash
   pip install PyOpenGL PyOpenGL_accelerate
   ```

## Camera and Video Issues

### Cannot Load Video Files

**Problem**: "Unable to open video file" or codec errors

**Solutions**:
1. Install FFmpeg:
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org) and add to PATH
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg`

2. Convert videos to compatible format:
   ```bash
   ffmpeg -i input.mov -c:v libx264 -c:a aac output.mp4
   ```

3. Install additional codecs:
   ```bash
   pip install imageio-ffmpeg
   ```

## Synchronization Issues

**Problem**: Cameras are not synchronized, may result in low correlations in **Sync** and/or poor 3D reconstruction 

**Solutions**:
1. Check video frame rates match
2. For existing videos, limit the time range to just the sound sync period
3. For future videos, maximize the sync signal to background noise ratio

## Instrincs Calibration Problems

### Poor Calibration Quality

**Problem**: Patterns not being detected

**Solutions**:
1. **Improve video quality**:
   - Ensure good lighting
   - Avoid motion blur

2. **Check calibration object**:
   - Verify pattern dimensions
   - Ensure pattern is flat and rigid
   - Use high-contrast patterns

**Problem**: High calibration errors

**Solutions**:
1. **Improve patterns data**:
   - Cover entire field of view
   - Use multiple distances and angles
   - Ensure sharp, well-lit images

3. **Calibration settings**:
   - Try "Invert coordinates" option
   - Increase sample size and iterations

## Wand Calibration and 3D Reconstruction Issues

**Problem**: File format or structure errors when loading wand data

**Solutions**:
1. **Check input data**:
   - paired points `-xypts.csv` should have 4 columns per camera (2 per track)
   - unpaired points and reference points `-xypts.csv` files should have 2 columns per camera (a single track)

**Problem**: Many error messages or high reprojection errors or wandscore

**Solutions**:
1. **Check sync**: 
   - Ensure cameras in calibration videos are properly synchronized - especially important if using moving objects.
   - Use visual cues to verify audio sync
2. **Improve wand data**:
   - Aim to start with 30-60 frames where the wand is digitized in the all cameras
   - Ensure that the same wand end is marked as the same track in all cameras in the same frame

   - Use consistent point selection across cameras
   - Avoid occlusions and reflections

## 3D Reconstruction Issues



## Performance Issues

### Slow Processing

## Data Import/Export Issues

### File Format Problems



### Encoding Issues


## Getting Help

### Diagnostic Information

When reporting issues, please include:

1. **System information**:
   ```bash
   python --version
   pip list | grep argus
   ```

2. **Error messages**: Full error traceback
3. **Steps to reproduce**: Detailed description
4. **Data description**: Camera setup, video formats, etc.

### Log Files

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check log files in project directory for detailed error information.

### Contact Support

- **Email**: jacksonbe3@longwood.edu or ddray@email.unc.edu
- **GitHub Issues**: [Submit a bug report](https://github.com/backyardbiomech/argus_gui/issues)
- **Include**: System info, error messages, and steps to reproduce

### Community Resources

- **GitHub Discussions**: [Community forum](https://github.com/backyardbiomech/argus_gui/discussions)
- **Documentation**: [Full documentation](index.md)
- **Examples**: Check the test files and example projects
