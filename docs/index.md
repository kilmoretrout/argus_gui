# Argus GUI Documentation

Welcome to the official documentation for the **Argus** project - a comprehensive Python package for 3D camera calibration and reconstruction.

Most Argus users want to track either whole or specific parts of animals in 3D space from video. This requires at least two cameras, but Argus can handle many more. Those cameras must be synchronized; Argus **Sync** provides tools for using sound for synchronization. You must know the camera intrinsics like lens distortion, which Argus **Patterns** and **Calibrate** will find. You also need the camera extrinics (camera location and orientation), which are found in **Wand**. And for tracking positions of objects in the video, you have Argus **Clicker**.  Argus also includes a bonus module **DWarp** which can be used to correct lens distortion in videos based on the camera intrinsics to produce undistorted videos for presentation or analysis in other software.

![Argus GUI](https://img.shields.io/badge/version-3.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-GPL%20v3-green)

Argus packages together a suite of open-source, freely available software tools including OpenCV and SBA with an easy to use graphical interface designed for performing multi-camera 3D data acquisition using consumer-grade cameras such as the GoPro Hero series. With Argus you can:

+ Quantify and remove lens distortion
+ Synchronize cameras by matching their audio streams
+ Perform structure-from-motion (i.e. wand-wave) camera calibration
+ Automatically and manually track points or markers in video files
+ Triangulate markers among cameras to compute 3D position information

## Quick Start

Get up and running with Argus GUI in just a few steps:

1. **[Installation](installation.md)** - Choose from pip or conda installation
2. **[Quick Start Guide](quick-start.md)** 
3. **[User Guide](user-guide.md)** - Comprehensive usage instructions


## Documentation Sections

### Getting Started
- [Installation](installation.md)
- [Quick Start Guide](quick-start.md)
- [System Requirements](requirements.md)

### User Guide
- [User Interface Overview](user-guide.md)
- [Camera Calibration](calibration.md)
- [3D Reconstruction](reconstruction.md)
- [Working with Videos](video-processing.md)

### Advanced Topics
- [Configuration Files](configuration.md)
- [Batch Processing](batch-processing.md)
- [Troubleshooting](troubleshooting.md)
- [FAQ](faq.md)

### Developer Resources
- [API Reference](api-reference.md)
- [Contributing](contributing.md)
- [Building from Source](building.md)

## Citation

If you use Argus in your research, please cite:

**Jackson, B.E., Evangelista, D.J., Ray, D.D., and Hedrick, T.L.** (2016). 3D for the people: multi-camera motion capture in the field with consumer-grade cameras and open source software. *Biology Open*, 5(9), 1334-1342. [https://doi.org/10.1242/bio.018713](https://doi.org/10.1242/bio.018713)

[Full citation details and BibTeX →](citation.md)

## Support

- 📧 **Email**: jacksonbe3@longwood.edu or ddray@email.unc.edu
- 🐛 **Issues**: [GitHub Issues](https://github.com/backyardbiomech/argus_gui/issues)


## License

Argus GUI is licensed under the [GNU General Public License v3.0](https://github.com/backyardbiomech/argus_gui/blob/main/LICENSE).

---

*Last updated: June 30, 2025*
