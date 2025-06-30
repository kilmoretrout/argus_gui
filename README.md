ReadMe
=======

argus_gui is a python package with multiple tools for 3D camera calibration and reconstruction. Argus Panoptes had thousands of eyes, but you may only have two or more cameras.  Hopefully this will help.

Version: 3.0.0 

### How do I get set up?

Visit https://argus.web.unc.edu for detailed instructions

### Quick installation instructions

1. Download the `Argus.yaml` file.
2. Install miniconda or anaconda on your computer. 
3. Open a terminal (macOS/Linux) or Anaconda Prompt (Windows).
4. Navigate to the directory where you downloaded `Argus.yaml`.
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
