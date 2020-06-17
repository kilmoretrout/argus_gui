#!C:\Users\thedrick\Miniconda3\python.exe
# -*- coding: utf-8 -*-

# Author: Dylan Ray
# I HAVE ADDED SOMETHING!
from __future__ import absolute_import

import os
import subprocess

import pkg_resources
from six.moves.tkinter import *
import six.moves.tkinter_ttk as ttk

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
    if sys.platform == "win32" or sys.platform == "win64":  # Make it so subprocess brings up no console window
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
        gui.ClickerGUI()


    def wand():
        gui.WandGUI()


    # Make Tkinter image objects for the icons
    dwarpim = PhotoImage(file=os.path.join(RESOURCE_PATH, 'icons/eye-8x.gif'))
    syncim = PhotoImage(file=os.path.join(RESOURCE_PATH, 'icons/pulse-8x.gif'))
    patternsim = PhotoImage(file=os.path.join(RESOURCE_PATH, 'icons/grid-four-up-8x.gif'))
    calibim = PhotoImage(file=os.path.join(RESOURCE_PATH, 'icons/calculator-8x.gif'))
    clickim = PhotoImage(file=os.path.join(RESOURCE_PATH, 'icons/location-8x.gif'))
    wandim = PhotoImage(file=os.path.join(RESOURCE_PATH, 'icons/wand.gif'))

    DWARP = ttk.Button(root, command=dwarp, image=dwarpim)
    DWARP.grid(row=0, column=0, padx=20, pady=10)
    Label(text="DWarp").grid(row=1, column=0, padx=10, pady=10)

    SYNC = ttk.Button(root, command=sync, image=syncim)
    SYNC.grid(row=0, column=1, padx=20, pady=10)
    Label(text="Sync").grid(row=1, column=1, padx=10, pady=10)

    PATTERNS = ttk.Button(root, command=patterns, image=patternsim)
    PATTERNS.grid(row=0, column=2, padx=20, pady=10)
    Label(text="Patterns").grid(row=1, column=2, padx=10, pady=10)

    CALIBRATE = ttk.Button(root, command=calibrate, image=calibim)
    CALIBRATE.grid(row=0, column=3, padx=20, pady=10)
    Label(text="Calibrate").grid(row=1, column=3, padx=10, pady=10)

    CLICKER = ttk.Button(root, command=clicker, image=clickim)
    CLICKER.grid(row=0, column=4, padx=20, pady=10)
    Label(text="Clicker").grid(row=1, column=4, padx=10, pady=10)

    WAND = ttk.Button(root, command=wand, image=wandim)
    WAND.grid(row=0, column=5, padx=20, pady=10)
    Label(text="Wand").grid(row=1, column=5, padx=10, pady=10)

    import argus_gui as gui
    root.mainloop()
