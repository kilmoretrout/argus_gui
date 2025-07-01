# Troubleshooting Guide

This guide helps you solve common issues when using Argus GUI. If you can't find a solution here, please check our [FAQ](faq.md) or contact support.

## Installation Issues

### Python Version Errors

**Problem**: Error messages about Python version compatibility
```
ERROR: Python 3.9 is not supported
```

**Solution**: 
- Argus GUI requires Python 3.10 or higher
- Install a newer Python version or use conda to create an environment:
```bash
conda create -n argus python=3.11
conda activate argus
```

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

### Camera Not Detected

**Problem**: USB or IP cameras not showing up

**Solutions**:
1. Check camera permissions (especially on macOS)
2. Test camera access:
   ```python
   import cv2
   cap = cv2.VideoCapture(0)  # Try different numbers: 0, 1, 2...
   print(cap.isOpened())
   ```
3. Install camera drivers
4. Try different USB ports or cables

### Synchronization Issues

**Problem**: Cameras are not synchronized, 3D reconstruction is poor

**Solutions**:
1. Check video frame rates match
2. Use external sync signal during recording
3. Manually align videos using audio tracks or visual cues
4. Use hardware-triggered cameras for critical applications

## Calibration Problems

### Poor Calibration Quality

**Problem**: High reprojection errors (> 1 pixel)

**Solutions**:
1. **Improve calibration data**:
   - Cover entire field of view
   - Use multiple distances and angles
   - Ensure sharp, well-lit images

2. **Check calibration object**:
   - Verify pattern dimensions
   - Ensure pattern is flat and rigid
   - Use high-contrast patterns

3. **Detection settings**:
   - Adjust detection thresholds
   - Remove poor quality detections
   - Use sub-pixel refinement

### Calibration Fails to Converge

**Problem**: Calibration process fails or produces unrealistic results

**Solutions**:
1. **Check input data**:
   - Ensure sufficient calibration points
   - Verify point correspondences
   - Remove outlier detections

2. **Adjust calibration parameters**:
   - Use different optimization methods
   - Modify initial parameter estimates
   - Enable/disable distortion parameters

3. **Camera setup issues**:
   - Check for camera movement during calibration
   - Verify image quality and focus
   - Ensure adequate lighting

### Detection Failures

**Problem**: Calibration pattern not detected or poor detection

**Solutions**:
1. **Lighting conditions**:
   - Ensure even, bright lighting
   - Avoid shadows and reflections
   - Use diffuse lighting sources

2. **Pattern quality**:
   - Print patterns at high resolution
   - Use thick, black lines on white background
   - Ensure pattern is flat and undamaged

3. **Detection settings**:
   - Adjust sensitivity thresholds
   - Modify size constraints
   - Try different detection algorithms

## 3D Reconstruction Issues

### Poor 3D Accuracy

**Problem**: 3D coordinates are inaccurate or inconsistent

**Solutions**:
1. **Improve calibration**:
   - Re-calibrate cameras with better data
   - Check reprojection errors
   - Validate calibration with known measurements

2. **Camera geometry**:
   - Ensure good triangulation angles (> 30°)
   - Avoid cameras that are too close together
   - Check for camera movement during capture

3. **Point selection**:
   - Use consistent point selection across views
   - Ensure points are visible in multiple cameras
   - Remove ambiguous or poor-quality points

### Reconstruction Fails

**Problem**: Cannot triangulate 3D points or process fails

**Solutions**:
1. **Check point correspondences**:
   - Verify same points are selected in all views
   - Ensure points are correctly matched
   - Remove points visible in only one camera

2. **Camera calibration**:
   - Verify calibration quality
   - Check that all cameras are calibrated
   - Ensure cameras have valid extrinsic parameters

3. **Geometric constraints**:
   - Check for sufficient camera separation
   - Ensure points are within calibrated volume
   - Verify camera orientations are reasonable

## Performance Issues

### Slow Processing

**Problem**: Operations take very long or system becomes unresponsive

**Solutions**:
1. **Reduce data size**:
   - Lower video resolution
   - Process fewer frames
   - Use region of interest cropping

2. **Hardware optimization**:
   - Close other applications
   - Increase available RAM
   - Use SSD storage for data

3. **Processing settings**:
   - Adjust quality settings
   - Use batch processing for large datasets
   - Enable multi-threading

### Memory Errors

**Problem**: "Out of memory" errors during processing

**Solutions**:
1. **Reduce memory usage**:
   - Process data in smaller chunks
   - Lower image/video resolution
   - Close unnecessary applications

2. **System optimization**:
   - Increase virtual memory/swap space
   - Add more RAM if possible
   - Use 64-bit Python installation

## Data Import/Export Issues

### File Format Problems

**Problem**: Cannot read/write specific file formats

**Solutions**:
1. **Install format-specific packages**:
   ```bash
   pip install openpyxl xlrd  # Excel files
   pip install h5py           # HDF5 files
   pip install scipy         # MATLAB files
   ```

2. **Convert to supported formats**:
   - Use CSV for point data
   - Convert videos to MP4
   - Use standard image formats (JPG, PNG)

### Encoding Issues

**Problem**: Special characters or non-ASCII filenames cause errors

**Solutions**:
1. Use ASCII-only filenames and paths
2. Avoid spaces in filenames
3. Check file encoding settings
4. Use forward slashes in file paths

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
