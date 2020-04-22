#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Dylan Ray
# I HAVE ADDED SOMETHING!
from Tkinter import *
import sys
import subprocess
import os
import pkg_resources

RESOURCE_PATH = os.path.abspath(pkg_resources.resource_filename('argus_gui.resources', ''))


# Launcher script. Has buttons for all programs in the Argus suite to be launched
if __name__ == '__main__':

    # Setup root window to put widgets in, and make it is unresizable
    root = Tk()
    root.resizable(width=FALSE, height=FALSE)

    # Set title for the window
    root.wm_title("Argus")
    root.protocol('WM_DELETE_WINDOW', root.destroy)

    startupinfo = None

    platform = sys.platform
    if sys.platform == "win32" or sys.platform == "win64": # Make it so subprocess brings up no console window
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    # Functions for starting all the Argus programs.
    def dwarp():
        gui.dwarpGUI()
    def sync():
        gui.syncGUI()
    def patterns():
        gui.patternsGUI()
    def calibrate():
        gui.calibrateGUI()
    def clicker():
        gui.clickerGUI()
    def wand():
        gui.wandGUI()
        
    # Make Tkinter image objects for the icons
    dwarpim = PhotoImage(file = os.path.join(RESOURCE_PATH, 'icons/eye-8x.gif'))
    syncim = PhotoImage(file = os.path.join(RESOURCE_PATH, 'icons/pulse-8x.gif'))
    patternsim = PhotoImage(file = os.path.join(RESOURCE_PATH, 'icons/grid-four-up-8x.gif'))
    calibim = PhotoImage(file = os.path.join(RESOURCE_PATH, 'icons/calculator-8x.gif'))
    clickim = PhotoImage(file = os.path.join(RESOURCE_PATH, 'icons/location-8x.gif'))
    wandim = PhotoImage(file = os.path.join(RESOURCE_PATH, 'icons/wand.gif'))

    DWARP = Button(root, command=dwarp, image = dwarpim, width = "100", height = "100")
    DWARP.grid(row = 0, column = 0, padx = 20, pady = 10)
    Label(text = "DWarp").grid(row = 1, column = 0, padx = 10, pady = 10)

    SYNC = Button(root, command=sync,image = syncim,  width = "100", height = "100")
    SYNC.grid(row = 0, column = 1, padx = 20, pady = 10)
    Label(text = "Sync").grid(row = 1, column = 1, padx = 10, pady = 10)

    PATTERNS = Button(root, command=patterns, image = patternsim, width = "100", height = "100")
    PATTERNS.grid(row = 0, column = 2, padx = 20, pady = 10)
    Label(text = "Patterns").grid(row = 1, column = 2, padx = 10, pady = 10)

    CALIBRATE = Button(root, command=calibrate, image = calibim, width = "100", height = "100")
    CALIBRATE.grid(row = 0, column = 3, padx = 20, pady = 10)
    Label(text = "Calibrate").grid(row = 1, column = 3, padx = 10, pady = 10)

    CLICKER = Button(root, command=clicker, image = clickim, width = "100", height = "100")
    CLICKER.grid(row = 0, column = 4, padx = 20, pady = 10)
    Label(text = "Clicker").grid(row = 1, column = 4, padx = 10, pady = 10)

    WAND = Button(root, command=wand, image = wandim, width = "100", height = "100")
    WAND.grid(row = 0, column = 5, padx = 20, pady = 10)
    Label(text = "Wand").grid(row = 1, column = 5, padx = 10, pady = 10)

    import argus_gui as gui   

    root.mainloop()
