# Installation Guide

This guide will help you install Argus GUI on your system. We provide multiple installation methods to suit different user preferences and environments.

## Installing Python (First Time Users)
<details>
<summary>👈 Click here if you need to install Python</summary>
If you don't have Python installed or are unsure, you can use any instructions for installing Python on your system. The steps below are one of the simplest options for beginners.

### For Mac Users

1. **Python may already be installed:**
   - Open Terminal (Applications > Utilities > Terminal, or press `Cmd + Space`, type "Terminal", and press Enter)
   - Type `python --version` and press Enter
   - If you see something like "Python 3.10.x" or higher, you can skip to [System Requirements](#system-requirements)

2. **Install Python using the official installer:**
   - Go to [python.org/downloads](https://www.python.org/downloads/)
   - Click the yellow "Download Python 3.x.x" button (it will show the latest version). Argus is tested on Python 3.10 through 3.13.
   - Once downloaded, double-click the `.pkg` file
   - Follow the installation wizard (keep all default settings)
   - When prompted, check the box "Add Python to PATH"

3. **Verify installation:**
   - Open a new Terminal window
   - Type `python --version` and press Enter
   - You should see the Python version number you downloaded

### For Windows Users

1. **Check if Python is already installed:**
   - Press `Windows + R`, type "cmd", and press Enter
   - Type `python --version` and press Enter
   - If you see something like "Python 3.10.x" or higher, you can skip to [System Requirements](#system-requirements)

2. **Install Python using the official installer:**
   - Go to [python.org/downloads](https://www.python.org/downloads/)
   - Click the yellow "Download Python 3.x.x" button (it will show the latest version). Argus is tested on Python 3.10 through 3.13.
   - Once downloaded, double-click the `.exe` file
   - **IMPORTANT:** Check the box "Add Python to PATH" at the bottom of the first screen
   - Click "Install Now"
   - Wait for installation to complete

3. **Verify installation:**
   - Press `Windows + R`, type "cmd", and press Enter
   - Type `python --version` and press Enter
   - You should see the Python version number

### Troubleshooting Python Installation

**If "python" command is not recognized:**
- **Mac:** Try using `python3` instead of `python`
- **Windows:** Make sure you checked "Add Python to PATH" during installation. If not, reinstall Python and check this box.

**If you see an older Python version (like 2.7):**
- Download and install the latest Python 3.x from python.org
- On Mac, use `python3` command instead of `python`

## System Requirements

- **Python**: tested on 3.10 through 3.13
- **Operating System**: Tested on Windows 11, macOS 15.5+, or Linux
- **Graphics**: OpenGL 3.0+ compatible graphics card - this includes all macs and most standard PCs

</details>

## Option 1: Install with pip (Recommended)

This is the easiest method for most users.

### Step 1: Create a Virtual Environment

A virtual environment keeps your Argus GUI installation separate from other Python packages on your system.

1. Open a terminal (macOS/Linux) or Command Prompt (Windows)
2. Create a new virtual environment:
   + This will create a folder named `argus_env` in the folder you run this command from (probably your Home or User directory).
   ```bash
   python -m venv argus_env
   ```
3. Activate the virtual environment:

   **macOS/Linux:**
   ```bash
   source argus_env/bin/activate
   ```
   
   **Windows:**
   ```bash
   argus_env\Scripts\activate
   ```
   
   You should see `(argus_env)` at the beginning of your command prompt when the environment is active.

### Step 2: Install Argus GUI

This will download and install the latest version of Argus GUI from GitHub, along with its dependencies. It may take a few minutes depending on your internet speed.

```bash
pip install git+https://github.com/backyardbiomech/argus_gui.git
```

### Step 3: Run the GUI

```bash
argus-gui
```

### Daily Usage

For future use, remember to activate your virtual environment each time before launching the Argus GUI:

**macOS/Linux:**
```bash
source argus_env/bin/activate
argus-gui
```

**Windows:**
```bash
argus_env\Scripts\activate
argus-gui
```

## Option 2: Install with Conda

<details>
<summary> 👈 click here if you prefer using conda for package management:</summary>

### Step 1: Download Environment File

1. Right-click this link and select "Save Link As..." or "Download Linked File As...": [Argus.yaml](https://raw.githubusercontent.com/backyardbiomech/argus_gui/main/Argus.yaml)
2. Save it as `Argus.yaml` (not `Argus.yaml.txt`)

### Step 2: Install Miniconda

If you don't have conda installed, download and install [Miniconda](https://www.anaconda.com/docs/getting-started/miniconda/install) or Anaconda.

### Step 3: Create Environment

1. Open a terminal (macOS/Linux) or Anaconda Prompt (Windows)
2. Navigate to the directory where you downloaded `Argus.yaml`:
   ```bash
   cd ~/Downloads  # macOS/Linux
   cd C:\Users\<YourUsername>\Downloads  # Windows
   ```
3. Create the environment:
   ```bash
   conda env create -f Argus.yaml
   ```

### Step 4: Activate and Run

```bash
conda activate argus
argus-gui
```
</details>

### Daily Usage with Conda

To start the GUI in the future:
```bash
conda activate argus
argus-gui
```

## Troubleshooting

### Common Issues

#### OpenCV Error
If you encounter an error related to `cv2` or `opencv`:
```bash
pip install opencv-contrib-python
```

#### FFmpeg Error (Windows)
If you encounter an error related to `ffmpeg` or `ffplay`, or an error reporting something like a file cannot be found:
1. In your command line, activate your virtual environment:
   ```bash
   argus_env\Scripts\activate  # Windows
   source argus_env/bin/activate  # macOS/Linux
   ```
2. Check if `ffmpeg` is installed:
   ```bash
   ffmpeg -version
   ```
   If you see an error like "command not found", follow these steps:
3. Download the latest version of [FFmpeg](https://ffmpeg.org/download.html)
4. Add it to your system's PATH using [these instructions](https://www.wikihow.com/Install-FFmpeg-on-Windows)
5. Note that you may need to restart your terminal or computer for the changes to take effect.

#### Permission Errors (macOS/Linux)
If you get permission errors, try:
```bash
pip install --user git+https://github.com/backyardbiomech/argus_gui.git
```

#### Graphics Issues
If you experience graphics-related problems:
- Ensure your graphics drivers are up to date
- Try running with software rendering:
  ```bash
  export PYOPENGL_PLATFORM=osmesa  # Linux/macOS
  set PYOPENGL_PLATFORM=osmesa     # Windows
  argus-gui
  ```

## Verifying Installation

To verify that Argus GUI is installed correctly:

1. Activate your environment
2. Run the following command:
   ```bash
   python -c "import argus_gui; print(argus_gui.__version__)"
   ```
   This should print the version number (e.g., "3.0.0")

3. Launch the GUI:
   ```bash
   argus-gui
   ```

## Updating Argus GUI

To update to the latest version:

**With pip:**
```bash
source argus_env/bin/activate  # macOS/Linux
argus_env\Scripts\activate     # Windows
pip install --upgrade git+https://github.com/backyardbiomech/argus_gui.git
```

**With conda:**
```bash
conda activate argus
pip install --upgrade git+https://github.com/backyardbiomech/argus_gui.git
```

## Uninstalling

To remove Argus from the virtual environment:

**With pip:**
```bash
pip uninstall argus-gui argus sba
```

**With conda:**
```bash
conda remove --name argus --all
```

You can also delete the `argus_env` folder if you no longer need it.

## Next Steps

Once installed, proceed to the [Quick Start Guide](quick-start.md) to begin using Argus GUI.
