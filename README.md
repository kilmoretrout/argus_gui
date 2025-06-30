ReadMe
=======

argus_gui is a python package with multiple tools for 3D camera calibration and reconstruction. Argus Panoptes had thousands of eyes, but you may only have two or more cameras.  Hopefully this will help.

Version: 3.0.0 
Updated: 2025-06-30, tested on Windows 11 and MacOS 15.5

### How do I get set up?

Visit https://argus.web.unc.edu for detailed instructions

### Quick installation instructions

#### Option 1: Install with pip (recommended for most users)

**Step 1: Create a virtual environment (recommended)**

A virtual environment keeps your argus_gui installation separate from other Python packages on your system.

1. Open a terminal (macOS/Linux) or Command Prompt (Windows)
2. Create a new virtual environment:
   ```bash
   python -m venv argus_env
   ```
3. Activate the virtual environment:
   - On macOS/Linux:
     ```bash
     source argus_env/bin/activate
     ```
   - On Windows:
     ```bash
     argus_env\Scripts\activate
     ```
   
   You should see `(argus_env)` at the beginning of your command prompt when the environment is active.

**Step 2: Install argus_gui**

```bash
pip install git+https://github.com/backyardbiomech/argus_gui.git
```

**Step 3: Run the GUI**

```bash
argus-gui
```

**For future use:** Remember to activate your virtual environment each time before using argus_gui:
- macOS/Linux: `source argus_env/bin/activate`
- Windows: `argus_env\Scripts\activate`

Then run: `argus-gui`

**Note:** The installation will automatically handle the `sba` and `argus` dependencies from GitHub.

**Troubleshooting:** 

- If during use you encounter an error related to `cv2` or `opencv`, you can try installing the contrib package:
  ```bash
  pip install opencv-contrib-python
  ```


<details>
<summary><strong>Option 2: Install with conda (if you prefer conda)</strong></summary>

1. Right-click this link and select "Save Link As..." or "Download Linked File As..." : <a href="https://raw.githubusercontent.com/backyardbiomech/argus_gui/main/Argus.yaml">Argus.yaml</a> (save it as `Argus.yaml`, not `Argus.yaml.txt`).
2. Install [miniconda](https://www.anaconda.com/docs/getting-started/miniconda/install) or anaconda on your computer. 
3. Open a terminal (macOS/Linux) or Anaconda Prompt (Windows).
4. Navigate to the directory where you downloaded `Argus.yaml` (probably your Downloads folder). You can use the `cd` command to change directories. For example:
   ```
   cd ~/Downloads
   ```
   or on Windows:
   ```   
   cd C:\Users\<YourUsername>\Downloads
   ```

5. Run the command:
   ```
   conda env create -f Argus.yaml
   ```
6. Activate the environment:
   ```
   conda activate argus
    ```
7. Open the gui with the command:
   ```
   argus-gui
   ```

8. To start the GUI in the the future, open a terminal or Anaconda Prompt, activate the environment with:
   ```
   conda activate argus
   ```
   and then run:
   ```
   argus-gui
   ```

</details>   
   
   
### Who do I talk to?

Any questions or comments can be emailed to:
jacksonbe3@longwood.edu or ddray@email.unc.edu
