ReadMe
=======

argus_gui is a python package with multiple tools for 3D camera calibration and reconstruction. Argus Panoptes had thousands of eyes, but you may only have two or more cameras.  Hopefully this will help.

Version: 3.0.0 
Updated: 2025-06-30, tested on Windows 11 and MacOS 15.5

### How do I get set up?

Visit https://argus.web.unc.edu for detailed instructions

### Quick installation instructions

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
   
   
### Who do I talk to?

Any questions or comments can be emailed to:
jacksonbe3@longwood.edu or ddray@email.unc.edu
