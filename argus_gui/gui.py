#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import sys
import subprocess
from Tkinter import *
import tkFileDialog
import tkMessageBox
import Pmw
import os
import pandas
import tempfile
import shutil
import cv2
import time
import copy
from moviepy.editor import *
import string
import psutil
import random
import argus_gui.resources
import pkg_resources

RESOURCE_PATH = os.path.abspath(pkg_resources.resource_filename('argus_gui.resources', ''))

# popup window for getting track names and offsets.
class popupWindow(object):
    def __init__(self, master, title):
        top=self.top=Toplevel(master)
        top.resizable(width=FALSE, height=FALSE)
        top.bind('<Return>', self.cleanup)
        self.l=Label(top,text=title)
        self.l.pack(padx = 10, pady = 10)
        self.e=Entry(top)
        self.e.focus_set()
        self.e.pack(padx = 10, pady = 5)
        self.b=Button(top,text='Ok', padx = 10, pady = 10)
        self.b.bind('<Button-1>', self.cleanup)
        self.b.pack(padx = 5, pady = 5)
    def cleanup(self, event):
        self.value=self.e.get()
        self.top.destroy()

# Makes a subprocess with Pyglet windows for all camera views
class pygletDriver():
    def __init__(self, movies, offsets, res):
        self.movies = movies
        self.offsets = offsets
        
        starts = list()
        for k in range(len(offsets)):
            starts.append(np.max(offsets) - offsets[k])
        self.processes = list()
        self.end = int(cv2.VideoCapture(movies[0]).get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))
        self.res = res

    def run(self):
        movieString = ''
        for movie in self.movies:
            if self.movies.index(movie) != len(self.movies) - 1:
                movieString = movieString + movie + '@'
            else:
                movieString = movieString + movie

        offsetString = ''
        for k in range(len(self.offsets)):
            if k != len(self.offsets) - 1:
                offsetString = offsetString + str(self.offsets[k]) + '@'
            else:
                offsetString = offsetString + str(self.offsets[k])

        cmd = [sys.executable, os.path.join(RESOURCE_PATH, 'scripts/argus-click')]
        args = [movieString, str(self.end), offsetString, self.res]
        cmd = cmd + args
        if hasattr(sys, 'frozen'):
            proc = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.STDOUT, shell = False, startupinfo = None)
        else:
            proc = subprocess.Popen(cmd, stdout = sys.stdout, stderr = sys.stdout, shell = False, startupinfo = None)
        self.processes.append(proc)

    def kill(self):
        for proc in self.processes:
            proc.kill()

"""
Base class for all Argus GUI objects.
Methods:
    - __init __ : makes a Tkinter window called root for subclass to populate, also makes list to keep track of temporary directories
    - about : bring up a Tkinter window that displays the license and authorship information of this Python package
    - quit_all : kills all subprocesses and this process, destroys all temporary directories, and obliterates the Tkinter window
    - kill_proc_tree : closs platform way to ensure death of all child processes with psutil
    - go : takes a cmd from a subclass and executes in a way such that the output is either piped to the console (debug) or routed nowhere (release)
    - set_in_file_name : used by subclasses to set filenames for readables
    - set_out_file_name : used by subclasses to set filenames for writables
    
"""

class GUI(object):
    def __init__(self):
        self.root = Tk()
        self.root.resizable(width=False, height=False)
        self.root.protocol('WM_DELETE_WINDOW', self.quit_all)

        self.tmps = list()
        self.pids = list()

        self.root.wm_title("Argus")

    def about(self):
        lic = Tk()
        scrollbar = Scrollbar(lic)
        scrollbar.pack(side=RIGHT, fill=Y, padx = 10, pady = 10)
        log = Text(lic, yscrollcommand = scrollbar.set, bg = "black", fg = "green", width = 100)
        scrollbar.config(command=log.yview)
        log.pack()

        lic.resizable(width=FALSE, height=FALSE)
        lic.wm_title('License')

        fo = open(os.path.join(RESOURCE_PATH, 'LICENSE.txt'))
        line = fo.readline()
        while line != '':
            log.insert(END, line)
            line = fo.readline()

    def quit_all(self):
        # Destroy the GUI and get out of dodge
        self.root.quit()
        self.root.destroy()
        self.kill_pids()

        for tmp in self.tmps:
            # Delete temporary directory in use if it still exists
            if os.path.isdir(tmp):
                shutil.rmtree(tmp)
        #me = os.getpid()
        #self.kill_proc_tree(me)
    
    def kill_proc_tree(self, pid, including_parent=True):    
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            child.kill()
        #psutil.wait_procs(children, timeout=5)
        if including_parent:
            parent.kill()
            parent.wait(5)

    def kill_pids(self):
        for pid in self.pids:
            try:
                self.kill_proc_tree(pid)
            except:
                pass

    def go(self, cmd, wlog = False, mode = 'DEBUG'):
        cmd = [str(wlog),''] + cmd

        rcmd = [sys.executable, os.path.join(RESOURCE_PATH, 'scripts/argus-log')]

        rcmd = rcmd + cmd
            
        startupinfo = None
        if sys.platform == "win32" or sys.platform == "win64": # Make it so subprocess brings up no console window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        proc = subprocess.Popen(rcmd, stdout = subprocess.PIPE, shell = False, startupinfo = startupinfo)
        self.pids.append(proc.pid)

    def set_in_filename(self, var, filetypes = None):
        # linux needs another window
        if sys.platform == 'linux2':
            root = Tk()
            root.withdraw()
        filename = tkFileDialog.askopenfilename()
        var.set(filename)

    def set_out_filename(self, var, filetypes = None):
        if sys.platform == 'linux2':
            root = Tk()
            root.withdraw()
        filename = tkFileDialog.asksaveasfilename()
        var.set(filename)

# Takes a list of videos and offsets and allows users to mark pixel locations.  Given DLT coefficients and camera profile, also capable of:
# Plotting 3D positions
# Saving 3D positions
# Outputting 95% Confidence Intervals, spline weights, and error tolerances
# Plotting epipolar lines to aid in tracking common objects
class clickerGUI(GUI):
    def __init__(self):
        super(clickerGUI, self).__init__()

        self.offsets = list()
        self.drivers = list()

        tooltips = Pmw.Balloon(self.root)
        self.res = StringVar(self.root)
        self.res.set("Medium")

        self.root.wm_title("Argus")
        self.filelist = Listbox(self.root, width = 50, height = 10)
        self.filelist.grid(row = 2, column = 0, padx = 5, pady = 5, sticky = EW)
        tooltips.bind(self.filelist, "List of movies to click through for\nPress '+' button to add movie")

        findInFile = Button(self.root, text = " + ", command = self.add, padx = 10, pady = 10)
        findInFile.grid(row = 1, column = 0, sticky = E, padx = 5, pady = 5)
        tooltips.bind(findInFile, "Open file dialog and browse for movie")

        clearButton = Button(self.root, text = "Clear all", command = self.clear, padx = 10, pady = 5)
        clearButton.grid(row = 1, column = 0, padx = 5, pady = 5)

        Label(self.root, text = "Argus-Clicker", font = ("Helvetica", 20), fg = '#56A0D3').grid(row = 0, column = 0, padx = 15, pady = 15, sticky = S)

        aboutButton = Button(self.root, text = "About", command = self.about, padx = 10, pady = 10)
        aboutButton.grid(row = 0, column = 0, sticky = E, padx = 5, pady = 5)

        delButton = Button(self.root, text = " - ",
                   command=self.delete, padx = 10, pady = 10)
        delButton.grid(row = 1, column = 0, sticky = W, padx = 5, pady = 5)
        tooltips.bind(delButton, "Remove movie from list")

        Label(self.root, text = "Resolution:").grid(row = 3, column = 0, padx = 5, pady = 5, sticky = W)
        resCheck = OptionMenu(self.root, self.res, "Low", "Medium", "High")
        resCheck.grid(row = 3, column = 0, pady = 5, padx = 100, sticky = W)
        tooltips.bind(resCheck, "Refers to window size\n Low - 1/4 * original image size, Medium - 1/2, High - 1")

        go = Button(self.root, text="Go", command=self.go, width = 6, height = 3)
        go.grid(row = 11, column = 0, padx = 5, pady = 5, sticky = W)

        quitB = Button(self.root, text="Quit", command=self.quit_all, width = 6, height = 3)
        quitB.grid(row = 11, column = 0, padx = 5, pady = 5, sticky = E)

        self.root.mainloop()

    # Clear the file list and delete all offsets
    def clear(self):
        self.filelist.delete(0,END)
        self.offsets = list()

    def quit_all(self):
        if len(self.drivers) != 0:
            for driver in self.drivers:
                driver.kill()
        self.root.destroy()

    # Function for bringing up file dialogs; adds selected file to listbox
    def add(self):
        filename = tkFileDialog.askopenfilename()

        if filename != '':
            if len(self.offsets) != 0:
                self.w=popupWindow(self.root, "Frame offset:")
                self.root.wait_window(self.w.top)
                value = self.w.value
            else:
                value = 0

            try:
                self.offsets.append(int(value))
            except:
                tkMessageBox.showwarning(
                "Error",
                "Frame offset must be an integer"
                )
                return
            self.filelist.insert(END, filename)

    def delete(self):
        if self.filelist.get(ANCHOR) != '':
            del self.offsets[self.filelist.get(0,END).index(self.filelist.get(ANCHOR))]
            self.filelist.delete(ANCHOR)
        elif self.filelist.get(END) != '':
            del self.offsets[-1]
            self.filelist.delete(END)

    def go(self):
        movies = list(self.filelist.get(0,END))
        for movie in movies:
            _ = copy.copy(movies)
            _.remove(movie)
            for m in _:
                if movie == m:
                    tkMessageBox.showwarning(
                    "Error",
                    "You cannot click through two of the same movies"
                    )
                    return
        if len(movies) != 0:
            driver = pygletDriver(movies, self.offsets, self.res.get())
            driver.run()
            self.drivers.append(driver)
        else:
            tkMessageBox.showwarning(
            "Error",
            "No movies to click through!"
            )
            return

class dwarpGUI(GUI):
    def __init__(self):
        super(dwarpGUI, self).__init__()
        # Load system specific integers for Tkinter drawing differences
        pads = np.loadtxt(os.path.join(RESOURCE_PATH,'dwarp-gui-paddings.txt'))
        if sys.platform == 'linux2':
            pads = pads[0]
        elif sys.platform == 'darwin':
            pads = pads[1]
        elif sys.platform == 'win32' or sys.platform == 'win64':
            pads = pads[2]
        pads = int(pads)

        tooltips = Pmw.Balloon(self.root)

        group = LabelFrame(self.root, text="Lens Parameters", padx=5, pady=5,  fg = '#56A0D3')
        group2 = LabelFrame(self.root, text="Output movie options", padx=5, pady=5,  fg = '#56A0D3')
        group3 = LabelFrame(self.root, text="Output type options", padx=5, pady=5,  fg = '#56A0D3')

        # Variables which store information for the undistort process, including
        # Input file name, calibrations file name, output file name, frame interval, compression quality level, camera model, shooting mode, run mode (Display, write, or both), and the undistortion coefficients
        self.fnam = StringVar(self.root)
        self.cfnam = StringVar(self.root)
        self.ofnam = StringVar(self.root)
        self.frameint = StringVar(self.root)
        self.sModeStr = StringVar(self.root)
        self.camStr = StringVar(self.root)
        self.crf = StringVar(self.root)
        self.wrdispboth = IntVar(self.root)
        self.k1 = StringVar(self.root)
        self.k2 = StringVar(self.root)
        self.k3 = StringVar(self.root)
        self.t1 = StringVar(self.root)
        self.t2 = StringVar(self.root)
        self.f = StringVar(self.root)
        self.cx = StringVar(self.root)
        self.cy = StringVar(self.root)
        self.wLog = StringVar(self.root)
        self.crop = StringVar(self.root)

        # Set defaults
        self.frameint.set("25")
        self.crf.set("12")
        self.wrdispboth.set(1)
        self.crop.set("0")
        self.wLog.set("0")

        # create and fill the camera model and shooting mode drop down menus from the calibrations files
        self.calibFiles = list()
        
        self.calibFolder = os.path.join(RESOURCE_PATH, 'calibrations/')
        for file in os.listdir(self.calibFolder):
            if file.endswith(".csv"):
                self.calibFiles.append(file)

        self.modes = list()
        self.models = list()

        for file in self.calibFiles:
            ifile = open(self.calibFolder + file)
            if file.split('.')[0] != '':
                self.models.append(file.split('.')[0])
            line = ifile.readline()
            mods = list()
            while line != '':
                line = ifile.readline().split(',')[0]
                if line != '':
                    mods.append(line)
            if len(mods) != 0:
                self.modes.append(mods)

        ifile.close()

        self.w = apply(OptionMenu, (group, self.camStr) + tuple(self.models))
        self.w2 = apply(OptionMenu, (group, self.sModeStr) + tuple(self.modes[0]))
        self.w.config(width = 16)
        self.w2.config(width = 22)

        # Set defaults for camera model and shooting mode
        self.camStr.set(self.models[0])
        self.sModeStr.set(self.modes[0][0])

        # make entry boxes for camera intrinsics including distortion coefficients
        self.fEntry = Entry(group,textvariable = self.f, width = 7, bd = 3)
        self.cxEntry = Entry(group,textvariable = self.cx, width = 7, bd = 3)
        self.cyEntry = Entry(group,textvariable = self.cy, width = 7, bd = 3)
        self.k1Entry = Entry(group, textvariable = self.k1, width = 7, bd = 3)
        self.k2Entry = Entry(group, textvariable = self.k2, width = 7, bd = 3)
        self.k3Entry = Entry(group, textvariable = self.k3, width = 7, bd = 3)
        self.t1Entry = Entry(group,textvariable = self.t1, width = 7, bd = 3)
        self.t2Entry = Entry(group, textvariable = self.t2, width = 7, bd = 3)

        self.cropCheck = Checkbutton(group2, text="Crop video to undistorted region", variable=self.crop)

        self.calibParse()

        # Make the elements of the GUI from Tkinter widgets added via the grid method
        # Elements include the title, in Carolina Blue, of the program and the following widgets all with labels:
        # Open-file-dialog button with manual entry field
        # Camera model drop-down menu with various GoPro models to choose from
        # Shooting model drop-down menu with various GoPro shooting modes to choose from
        # Editable boxes with all the relevant distortion parameters
        # Radiobutton for write and display options
        # Entry boxes for the interval between full frames and the compression quality level
        # Checkboxes for writing the log and cropping the video the undistorted region
        # Output-file manual-entry text box
        # Go button

        Label(self.root, text = "Argus-DWarp", font = ("Helvetica",40), fg = '#56A0D3').grid(row = 0, column = 0, padx = 20, pady = 20)

        aboutButton = Button(self.root, text = "About", command = self.about, padx = 15, pady = 15)
        aboutButton.grid(row = 0, column = 0, sticky = E, padx = 10, pady = 10)

        findInFile = Button(self.root, text="Open", command=lambda: self.set_in_filename(self.fnam), padx = 10, pady = 10, width = 10, height = 1)
        findInFile.grid(row = 1, column = 0, padx = 130, sticky = W)

        Label(self.root, text = "Input movie:").grid(row = 1, column = 0, padx = 35, sticky = W)

        inFileEntry =  Entry(self.root, textvariable=self.fnam, width = pads)
        inFileEntry.grid(row = 1, column = 0, padx = 10, sticky = E)

        group.grid(row = 2, padx=10, pady=10, sticky = EW)

        Label(group, text = "Camera Model:").grid(row = 0, column = 0, padx = 10)

        self.w.grid(row = 0, column = 1)

        self.camStr.trace('w', lambda *args: self.updateCam())
        self.sModeStr.trace('w', lambda *args: self.updateMode())

        Label(group, text = "Shooting Mode:").grid(row = 0, column = 2, padx = 10)

        self.w2.grid(row = 0, column = 3)

        Label(group, text = "Focal length (mm): ").grid(row = 1, column = 0, padx = 10, pady = 10)
        self.fEntry.grid(row = 1, column = 1, sticky = W)
        tooltips.bind(self.fEntry, 'Focal length (mm)')

        Label(group,text = "Horizontal center: ").grid(row = 1, column = 2, padx = 10, pady = 10)
        self.cxEntry.grid(row = 1, column = 3, sticky = W)
        tooltips.bind(self.cxEntry, 'x-coordinate of optical midpoint')

        Label(group,text = "Vertical center: ").grid(row = 1, column = 4, padx = 10, pady = 10)
        self.cyEntry.grid(row = 1, column = 5)
        tooltips.bind(self.cyEntry, 'y-coordinate of optical midpoint')

        Label(group, text = "Radial Distortion         k1: ").grid(row = 2, column = 0, padx = 5, pady = 10, sticky = W)
        self.k1Entry.grid(row = 2, column = 1, sticky = W)
        tooltips.bind(self.k1Entry, '2nd order radial\ndistortion coefficient')

        Label(group, text = "k2: ").grid(row = 2, column = 2, padx = 10, pady = 10, sticky = E)
        self.k2Entry.grid(row = 2, column = 3, sticky = W)
        tooltips.bind(self.k2Entry, '4th order radial\ndistortion coefficient')

        Label(group, text = "k3: ").grid(row = 2, column = 4, padx = 10, pady = 10, sticky = E)
        self.k3Entry.grid(row = 2, column = 5)
        tooltips.bind(self.k3Entry, '6th order radial\ndistortion coefficient')

        Label(group,text = "Tangential Distortion   t1: ").grid(row = 3, column = 0, padx = 5, pady = 10, sticky = W)
        self.t1Entry.grid(row = 3, column = 1, sticky = W)
        tooltips.bind(self.t1Entry, '1st decentering\ndistortion coefficient')

        Label(group, text = "t2: ").grid(row = 3, column = 2, padx = 10, pady = 10, sticky = E)
        self.t2Entry.grid(row = 3, column = 3, sticky = W)
        tooltips.bind(self.t2Entry, '2nd decentering\ndistortion coefficient')

        group3.grid(row = 3, sticky = W, padx = 10)

        Radiobutton(group3, text="Write and display video", variable= self.wrdispboth, value=1).grid(row = 0, column = 0, pady = 5, padx = 50, sticky = W)
        Radiobutton(group3, text="Display only", variable=self.wrdispboth, value=2).grid(row = 1, column = 0, pady = 10, padx = 50, sticky = W)
        Radiobutton(group3, text="Write only", variable=self.wrdispboth, value=3).grid(row = 2, column = 0, pady = 10, padx = 50, sticky = W)

        group2.grid(row = 3, sticky = E, padx = 280)

        Label(group2, text = "Compression quality level:").grid(row = 0, column = 0, sticky = W, padx = 20)

        bufferEntry = Entry(group2, textvariable=self.crf, bd = 3, width = 5)
        bufferEntry.grid(row = 0, column = 1, sticky = E)
        tooltips.bind(bufferEntry, 'Must be an integer between 0 and 63')

        Label(group2, text = "Full frame interval:").grid(row = 1, column = 0, sticky = W, padx = 20)

        frameintEntry = Entry(group2, textvariable=self.frameint, bd = 3, width = 5)
        frameintEntry.grid(row = 1, column = 1, pady = 5, )
        tooltips.bind(frameintEntry, 'Number of frames inbetween full frames\nHigher numbers mean larger file size but faster seek')

        self.cropCheck.grid(row = 2, pady = 5, sticky = W)

        writeLogCheck = Checkbutton(self.root, text="Write log", variable=self.wLog)
        writeLogCheck.grid(row = 4, column = 0, pady = 10, padx = 30, sticky = W)

        go = Button(self.root, text="Go", command=self.go, width = 6, height = 3)
        go.grid(row = 5, column = 0, padx = 10, pady = 5, sticky = W)

        Label(self.root, text = "Output file:").grid(row = 5, column = 0, padx = 180, sticky = W)

        outFileEntry = Entry(self.root, textvariable=self.ofnam, width = 50)
        outFileEntry.grid(row = 5, column = 0, sticky = E, padx = 100)

        specButton = Button(self.root, text = 'Specify', command =lambda: self.set_out_filename(self.ofnam), padx = 15, pady = 10)
        specButton.grid(row = 5, column = 0, sticky = W, padx = 285)

        quitButton = Button(self.root, text = "Quit", command = self.quit_all, width = 6, height = 3)
        quitButton.grid(row = 5, column = 0, sticky = E, padx = 10, pady = 10)

        self.root.mainloop()

    def disableEntries(self):
        self.crop.set('0')
        self.cropCheck.config(state = 'disabled')
        
        self.fEntry.config(state = 'disabled')
        self.cxEntry.config(state = 'disabled')
        self.cyEntry.config(state = 'disabled')
        self.k1Entry.config(state = 'disabled')
        self.k2Entry.config(state = 'disabled')
        self.k3Entry.config(state = 'disabled')
        self.t1Entry.config(state = 'disabled')
        self.t2Entry.config(state = 'disabled')

    def enableEntries(self):
        self.cropCheck.config(state = 'normal')
        self.fEntry.config(state = 'normal')
        self.cxEntry.config(state = 'normal')
        self.cyEntry.config(state = 'normal')
        self.k1Entry.config(state = 'normal')
        self.k2Entry.config(state = 'normal')
        self.k3Entry.config(state = 'normal')
        self.t1Entry.config(state = 'normal')
        self.t2Entry.config(state = 'normal')

    # Define function for filling the entry fields for the undistortion coefficients and other relevant numbers
    def calibParse(self):
        self.cfnam.set(self.calibFolder + self.camStr.get() + '.csv')

        ifile = open(self.cfnam.get(),"r")

        line = ifile.readline().split(',')
        while line[0] != self.sModeStr.get():
            line = ifile.readline().split(',')
        ifile.close()
        if not '(Fisheye)' in self.sModeStr.get():
            self.enableEntries()
            self.k1.set(line[7])
            self.k2.set(line[8])
            self.t1.set(line[9])
            self.t2.set(line[10])
            self.k3.set(line[11])
            self.f.set(line[1])
            self.cx.set(line[4])
            self.cy.set(line[5])
        else:
            self.disableEntries()

    def omniParse(self):
        self.cfnam.set(self.calibFolder + self.camStr.get() + '.csv')

        ifile = open(self.cfnam.get(),"r")

        line = ifile.readline()
        l = line.split(',')
        while l[0] != self.sModeStr.get():
            line = ifile.readline()
            l = line.split(',')
        ifile.close()

        return ','.join(l[1:])

    # Define function for returning an array of coefficients from the strings in the entry fields, call an error box from tkinter if they're not floats
    def getCoefficients(self):
        try:
            co = [self.f.get(), self.cx.get(), self.cy.get(), self.k1.get(), self.k2.get(), self.t1.get(), self.t2.get(), self.k3.get()]
            ret = ','.join(co)
            return ret
        except:
            tkMessageBox.showwarning(
            "Error",
            "Undistortion coefficients must all be floats"
            )
            return

    # This executes the undistort by wrapping it in a thread which then has its stdout and stderr monitored
    # by by tkinter text window with a scrollbar.  Closing the log or pressing 'Done' kills the process, deleting the temporary directory if one exists.
    def go(self):
        # make sure the crf and frame interval are integers
        try:
            int(self.crf.get())
            int(self.frameint.get())
        except:
            tkMessageBox.showwarning(
                "Error",
                "Compression quality level and frame interval must be positive integers"
                )
            return

        if int(self.crf.get()) > 63 or int(self.crf.get()) < 0:
            tkMessageBox.showwarning(
                "Error",
                "Compression quality level must be between 0 and 63"
                )
            return

        tmpName = ''
        # Extra bools and a string for passing temp dir, write option and display option to the undistorter object
        if self.getCoefficients():
            cmd = [sys.executable, os.path.join(RESOURCE_PATH, 'scripts/argus-dwarp')]
            if '(Fisheye)' in self.sModeStr.get():
                omni = self.omniParse()
            else:
                omni = ''
            args = [self.fnam.get(), '--ofile', self.ofnam.get(), '--frameint', self.frameint.get(), '--crf', self.crf.get()]
            
            if not '(Fisheye)' in self.sModeStr.get():
                args = args + ['--coefficients', self.getCoefficients()]
            else:
                args = args + ['--omni', omni]
                
            if self.wrdispboth.get() == 1 or self.wrdispboth.get() == 3:
                tmpName = tempfile.mkdtemp()
                args = args + ['--write', '--tmp', tmpName]
            if self.wrdispboth.get() == 1 or self.wrdispboth.get() == 2:
                disp = True
                args = args + ['--disp']
            if self.crop.get() == '1':
                args = args + ['--crop']
            cmd = cmd + args
        else:
            return

        if self.wLog.get() == '1':
            logBool = True
        else:
            logBool = False

        super(dwarpGUI, self).go(cmd, logBool)

    # Functions for updating the entry fields and drop down menus if needed
    def updateMode(self):
        self.calibParse()

    def updateCam(self):
        m = self.w2.children['menu']
        m.delete(0,END)
        a = 0
        for k in range(0, len(self.models)):
            if self.models[k] == self.camStr.get():
                a = k
                break
        newvalues = self.modes[a]
        for val in newvalues:
            m.add_command(label=val,command=lambda v=self.sModeStr,l=val:v.set(l))
        self.sModeStr.set(self.modes[a][0])
        self.calibParse()

class syncGUI(GUI):
    def __init__(self):
        super(syncGUI, self).__init__()
        
        # Load system specific integers for Tkinter drawing differences
        pads = np.loadtxt(os.path.join(RESOURCE_PATH,'sync-gui-paddings.txt'))
        if sys.platform == 'linux2':
            pads = pads[0]
        elif sys.platform == 'darwin':
            pads = pads[1]
        elif sys.platform == 'win32' or sys.platform == 'win64':
            pads = pads[2]
        pads = map(int, pads)

        tooltips = Pmw.Balloon(self.root)

        # Variables which store information to pass to the sync operation.
        self.filelist = Listbox(self.root, width = 50, height = 10)
        self.wLog = StringVar(self.root)
        self.start = StringVar(self.root)
        self.end = StringVar(self.root)
        self.crop = StringVar(self.root)
        self.onam = StringVar(self.root)

        # Defaults
        self.wLog.set('0')
        self.crop.set('1')
        self.start.set('0.0')
        self.end.set('4.0')

        self.startEntry = Entry(self.root, textvariable = self.start, bd = 3, width = 8)
        self.endEntry = Entry(self.root, textvariable = self.end, bd = 3, width = 8)

        self.tmps.append(tempfile.mkdtemp())

        # dictionary of cached files, relating random key to movie location
        self.cached = dict()

        self.crop.trace('w', lambda *args: self.checkEntries())

        self.filelist.grid(row = 2, column = 0, padx = 5, pady = 5, sticky = EW)
        tooltips.bind(self.filelist, "List of movies to find offsets for\nPress '+' button to add movie")

        findInFile = Button(self.root, text = " + ", command = self.add, padx = 10, pady = 10)
        findInFile.grid(row = 1, column = 0, sticky = E, padx = 5, pady = 5)
        tooltips.bind(findInFile, "Open file dialog and browse for movie")

        Label(self.root, text = "Argus-Sync", font = ("Helvetica", pads[1]), fg = '#56A0D3').grid(row = 0, column = 0, padx = 15, pady = 15, sticky = S)

        aboutButton = Button(self.root, text = "About", command = self.about, padx = 10, pady = 10)
        aboutButton.grid(row = 0, column = 0, sticky = E, padx = 5, pady = 5)

        delButton = Button(self.root, text = " - ",
                   command=self.delete, padx = 10, pady = 10)
        delButton.grid(row = 1, column = 0, sticky = W, padx = 5, pady = 5)
        tooltips.bind(delButton, "Remove movie from list")

        showButton = Button(self.root, text = "Show waves", command = self.show, padx = 15, pady = 5)
        showButton.grid(row = 3, column = 0, sticky = W, padx = 25, pady = 5)
        tooltips.bind(showButton, "Graph the audio tracks from the movies\nHelps better select a reasonable time range")

        f = Frame(self.root, height=1, width=350,bg="black")
        f.grid(row = 4, column = 0, pady = 5)

        clearButton = Button(self.root, text = "Clear all", command = self.clear, padx = 10, pady = 5)
        clearButton.grid(row = 1, column = 0, padx = 5, pady = 5)
        tooltips.bind(clearButton, "Clear all movies from the list and all cached audio tracks")

        rangeCheck = Checkbutton(self.root, text = 'Specify time range', variable = self.crop)
        rangeCheck.grid(row = 5, column = 0, sticky = W, padx = 25, pady = 5)

        Label(self.root, text = "Time range that beeps exists in (decimal minutes):").grid(row = 6, column = 0, sticky = W, padx = 20)

        Label(self.root, text = "Start:").grid(row = 7, sticky = W, padx = 45)
        self.startEntry.grid(row = 7, column = 0, sticky = W, padx = 100)

        f2 = Frame(self.root, height=1,width=350,bg="black")
        f2.grid(row = 9, column = 0, pady = 5)

        writeLogCheck = Checkbutton(self.root, text="Write log", variable=self.wLog)
        writeLogCheck.grid(row = 10, column = 0, padx = 25, pady = 5, sticky = W)

        Label(self.root, text = "End:").grid(row = 8, sticky = W, padx = 45)
        self.endEntry.grid(row = 8, column = 0, sticky = W, padx = 100)

        Label(self.root, text = "Output filename: ").grid(row = 11, column = 0, sticky = W, padx = 10)
        outEntry = Entry(self.root, textvariable = self.onam, width = 22)
        specButton = Button(self.root, text = 'Specify', command = lambda: self.set_out_filename(self.onam), padx = 15, pady = 10)
        specButton.grid(row = 11, column = 0, sticky = W, padx = pads[0])
        outEntry.grid(row = 11, column = 0, sticky = E, padx = 10, pady = 10)

        go = Button(self.root, text = "Go", command = self.go, width = 6, height = 3)
        go.grid(row = 12, column = 0, sticky = W, padx = 5, pady = 5)

        quitButton = Button(self.root, text = "Quit", command = self.quit_all, width = 6, height = 3)
        quitButton.grid(row = 12, column = 0, sticky = E, padx = 5, pady = 5)

        self.root.mainloop()

    # Gets seconds from 'hours:minutes:seconds' string
    def getSec(self, s):
        return 60.*float(s)

    def id_generator(self, size=12, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    # Function for bringing up file dialogs; adds selected file to listbox
    def add(self):
        if sys.platform == 'linux2':
            root = Tk()
            root.withdraw()
            #root.destroy()
        filename = tkFileDialog.askopenfilename()
        if filename != '':
            self.filelist.insert(END, filename)
            self.cached[filename] = self.id_generator() + '-' + filename.split('/')[-1].split('.')[0] + '.wav'
        root = None

    # Takes item off the list and deletes cached wave file if there is one
    def delete(self):
        if self.filelist.get(ANCHOR) != '':
            if os.path.isfile(self.tmps[0] + '/' + self.cached[self.filelist.get(ANCHOR)]):
                os.remove(self.tmps[0] + '/' + self.cached[self.filelist.get(ANCHOR)])
            del self.cached[self.filelist.get(ANCHOR)]
            self.filelist.delete(ANCHOR)
        elif self.filelist.get(END) != '':
            if os.path.isfile(self.tmps[0] + '/' + self.cached[self.filelist.get(END)]):
                os.remove(self.tmps[0] + '/' + self.cached[self.filelist.get(END)])
            del self.cached[self.filelist.get(END)]
            self.filelist.delete(END)

    # Do the sync operation
    def go(self):
        # Error checking and defining of bool to pass to the sync operation
        cropArg = ''
        files = self.filelist.get(0, END)
        if len(files) <= 1:
            tkMessageBox.showwarning(
            "Error",
            "Need at least two videos to sync"
            )
            return
        for k in range(len(files)):
            try:
                open(files[k])
            except:
                tkMessageBox.showwarning(
                "Error",
                "Could not find one or more of the specified videos"
                )
                return
        if self.crop.get() == '1':
            try:
                float(self.start.get())
                float(self.end.get())
            except:
                tkMessageBox.showwarning(
                "Error",
                "Start and end time must be floats"
                )
            for k in range(len(files)):
                dur = VideoFileClip(files[k]).duration
                if self.getSec(self.start.get()) >= dur or self.getSec(self.end.get()) > dur:
                    tkMessageBox.showwarning(
                    "Error",
                    "Time range does not exist for one or more of the specified videos"
                    )
                    return
            cropArg = '1'
        for k in range(len(files)):
            try:
                self.cached[files[k]]
            except:
                self.cached[files[k]] = self.id_generator() + '-' + files[k].split('/')[-1].split('.')[0] + '.wav'
        out = list()
        for k in range(len(files)):
            out.append(self.cached[files[k]])
        logBool = False
        if self.wLog.get() == '1':
            logBool = True

        file_str = ','.join(files)
        out_str = ','.join(out)
        
        cmd = [sys.executable, os.path.join(RESOURCE_PATH, 'scripts/argus-sync')]
        # Create args list, order is important
        args = [file_str, '--tmp', self.tmps[0], '--start', self.start.get(), '--end', self.end.get(), '--ofile', self.onam.get(), '--out', out_str]
        
        if self.crop.get() == '1':
            args = args + ['--crop']
        cmd = cmd + args

        super(syncGUI, self).go(cmd, logBool)

    # Graph the wave files with matplotlib
    def show(self):
        files = self.filelist.get(0, END)
        for k in range(len(files)):
            try:
                self.cached[files[k]]
            except:
                self.cached[files[k]] = self.id_generator() + '-' + files[k].split('/')[-1].split('.')[0] + '.wav'
        out = list()
        for k in range(len(files)):
            out.append(self.cached[files[k]])
        
        cmd = [sys.executable, os.path.join(RESOURCE_PATH, 'scripts/argus-show')]
        if isinstance(files,str):
            args = [self.tmps[0], files] + out
        else:
            args = [self.tmps[0]] + list(files) + out

        cmd = cmd + args

        super(syncGUI, self).go(cmd)
        
    # If a user does not want to specify a specific time range, make the entries inactive
    def checkEntries(self):
        if self.crop.get() == '1':
            self.startEntry.config(state = 'normal')
            self.endEntry.config(state = 'normal')
        else:
            self.startEntry.config(state = 'disabled')
            self.endEntry.config(state = 'disabled')

    # Clear the file list and delete all cached waves
    def clear(self):
        if os.path.isdir(self.tmps[0]):
            shutil.rmtree(self.tmps[0])
        self.tmps[0] = tempfile.mkdtemp()
        self.filelist.delete(0,END)
        self.cached = dict()

class wandGUI(GUI):
    def __init__(self):
        super(wandGUI, self).__init__()

        tooltips = Pmw.Balloon(self.root)

        group = LabelFrame(self.root, text="Options", padx=5, pady=5,  fg = '#56A0D3')

        intModes = ["Optimize none", "Optimize focal length", "Optimize focal length and principal point"]
        disModes = ["Optimize none", "Optimize r2", "Optimize r2, r4", "Optimize all distortion coefficients"]

        self.intModeDict = dict()
        self.disModeDict = dict()

        for k in range(len(intModes)):
            self.intModeDict[intModes[k]] = str(k)

        for k in range(len(disModes)):
            self.disModeDict[disModes[k]] = str(k)

        self.ppts = StringVar(self.root)
        self.uppts = StringVar(self.root)
        self.cams = StringVar(self.root)
        self.scale = StringVar(self.root)
        self.intfixes = StringVar(self.root)
        self.disfixes = StringVar(self.root)
        self.display = StringVar(self.root)
        self.ref = StringVar(self.root)
        self.tag = StringVar(self.root)
        self.report = StringVar(self.root)
        self.wLog = StringVar(self.root)
        self.ocps = StringVar(self.root)
        self.choose = StringVar(self.root)

        self.intfixes.set("Optimize none")
        self.disfixes.set("Optimize none")
        self.display.set('1')
        self.report.set('1')
        self.scale.set('1.0')
        self.wLog.set('0')
        self.ocps.set('0')
        self.choose.set('1')

        Label(self.root, text = "Argus-Wand", font = ("Helvetica",40), fg = '#56A0D3').grid(row = 0, column = 0, padx = 20, pady = 20, columnspan = 2)

        aboutButton = Button(self.root, text = "About", command = self.about, padx = 15, pady = 15)
        aboutButton.grid(row = 0, column = 1, sticky = E, padx = 5, pady = 5)

        findInFile = Button(self.root, text="Open", command=lambda: self.set_in_filename(self.cams), padx = 10, pady = 10, width = 10, height = 1)
        findInFile.grid(row = 1, column = 0, padx = 190, sticky = W)
        clearB = Button(self.root, text="Clear", command=lambda: self.clear(self.cams), padx = 10, pady = 10, width = 10, height = 1)
        clearB.grid(row = 1, column = 0, padx = 60, sticky = E)
        tooltips.bind(findInFile, 'Open a CSV file with camera intrinsic and extrinsics')
        Label(self.root, text = "Input cameras:").grid(row = 1, column = 0, padx = 35, sticky = W)

        inFileEntry = Entry(self.root, textvariable=self.cams, width = 20)
        inFileEntry.grid(row = 2, column = 0, padx = 10, pady = 10,  sticky = EW)
        tooltips.bind(inFileEntry, 'Path to CSV file with intrinsic and extrinsic estimates')

        findInFile = Button(self.root, text="Open", command=lambda: self.set_in_filename(self.ppts), padx = 10, pady = 10, width = 10, height = 1)
        findInFile.grid(row = 3, column = 0, padx = 190, sticky = W)
        clearB = Button(self.root, text="Clear", command=lambda: self.clear(self.ppts), padx = 10, pady = 10, width = 10, height = 1)
        clearB.grid(row = 3, column = 0, padx = 60, sticky = E)
        tooltips.bind(findInFile, 'Open a CSV file with paired pixel coordinates')

        Label(self.root, text = "Input paired points:").grid(row = 3, column = 0, padx = 35, sticky = W)

        inFileEntry =  Entry(self.root, textvariable=self.ppts, width = 20)
        inFileEntry.grid(row = 4, column = 0, padx = 10, pady = 10,  sticky = EW)
        tooltips.bind(inFileEntry, 'Path to paired points CSV file')

        findInFile = Button(self.root, text="Open", command=lambda: self.set_in_filename(self.uppts), padx = 10, pady = 10, width = 10, height = 1)
        findInFile.grid(row = 5, column = 0, padx = 190, sticky = W)
        clearB = Button(self.root, text="Clear", command=lambda: self.clear(self.uppts), padx = 10, pady = 10, width = 10, height = 1)
        clearB.grid(row = 5, column = 0, padx = 60, sticky = E)
        tooltips.bind(findInFile, 'Open a CSV file with unpaired pixel coordinates')

        Label(self.root, text = "Input unpaired points:").grid(row = 5, column = 0, padx = 35, sticky = W)

        inFileEntry =  Entry(self.root, textvariable=self.uppts, width = 20)
        inFileEntry.grid(row = 6, column = 0, padx = 10, pady = 10,  sticky = EW)
        tooltips.bind(inFileEntry, 'Path to unpaired points CSV file')

        findInFile = Button(self.root, text="Open", command=lambda: self.set_in_filename(self.ref), padx = 10, pady = 10, width = 10, height = 1)
        findInFile.grid(row = 5, column = 1, padx = 190, sticky = W)
        clearB = Button(self.root, text="Clear", command=lambda: self.clear(self.ref), padx = 10, pady = 10, width = 10, height = 1)
        clearB.grid(row = 5, column = 1, padx = 60, sticky = E)
        tooltips.bind(findInFile, 'Open a CSV file with axes pixel coordinates')

        Label(self.root, text = "Input reference points:").grid(row = 5, column = 1, padx = 35, sticky = W)

        inFileEntry =  Entry(self.root, textvariable=self.ref, width = 20)
        inFileEntry.grid(row = 6, column = 1, padx = 10, pady = 10,  sticky = EW)
        tooltips.bind(inFileEntry, 'Path to reference points text file')

        group.grid(row = 1, column = 1, rowspan = 3, padx = 5, sticky = EW)

        Label(group, text = "Scale (m): ").grid(row = 0, column = 0)
        rowEntry = Entry(group, textvariable = self.scale, width = 7, bd = 3)
        rowEntry.grid(row = 0, column = 1, sticky = W)
        tooltips.bind(rowEntry, 'Distance between paired points (Wand length)')

        Label(group, text = "Intrinsics: ").grid(row = 1, column = 0)
        w = OptionMenu(group, self.intfixes, "Optimize none", "Optimize focal length", "Optimize focal length and principal point")
        w.grid(row = 1, column = 1, sticky = W, pady = 10)

        Label(group, text = "Distortion: ").grid(row = 2, column = 0)
        w = OptionMenu(group, self.disfixes, "Optimize none", "Optimize r2", "Optimize r2, r4", "Optimize all distortion coefficients")
        w.grid(row = 2, column = 1, sticky = W)

        outliercheck = Checkbutton(group, text="Report on outliers", variable=self.report)
        outliercheck.grid(row = 3, column = 1, padx = 10, pady = 10, sticky = W)

        choosecheck = Checkbutton(group, text="Choose reference camera", variable=self.choose)
        choosecheck.grid(row = 3, column = 2, padx = 10, pady = 10, sticky = W)

        cameracheck = Checkbutton(group, text="Output camera profiles", variable=self.ocps)
        cameracheck.grid(row = 4, column = 1, padx = 10, sticky = W)

        findInFile = Button(self.root, text="Specify", command=lambda: self.set_out_filename(self.tag), padx = 10, pady = 10, width = 10, height = 1)
        findInFile.grid(row = 11, column = 0, padx = 10, pady = 10)

        Label(self.root, text = "Output tag and location:").grid(row = 11, column = 0, padx = 20, pady = 10, sticky = W)

        inFileEntry =  Entry(self.root, textvariable=self.tag, width = 40)
        inFileEntry.grid(row = 12, column = 0, columnspan = 2, padx = 10, pady = 5, sticky = EW)

        wLogCheck = Checkbutton(self.root, text = 'Write log', variable = self.wLog)
        wLogCheck.grid(row = 13, column = 0, padx = 20, pady = 5, sticky = W)

        go = Button(self.root, text="Go", command=self.go, width = 6, height = 3)
        go.grid(row = 14, column = 0, padx = 5, pady = 5, sticky = W)

        quitButton = Button(self.root, text = "Quit", command = self.quit_all, width = 6, height = 3)
        quitButton.grid(row = 14, column = 1, sticky = E, padx = 5, pady = 5)

        self.root.mainloop()

    def clear(self, var):
        var.set('')

    def go(self):
        try:
            float(self.scale.get())
        except:
            tkMessageBox.showwarning(
            "Error",
            "Scale must be a floating point number"
            )
            return
        
        cmd = [sys.executable, os.path.join(RESOURCE_PATH, 'scripts/argus-wand')]
            
        modeString = ''
        modeString = modeString + self.intModeDict[self.intfixes.get()]
        modeString = modeString + self.disModeDict[self.disfixes.get()]

        tmp = tempfile.mkdtemp()
        writeBool = False

        args = [self.cams.get(), '--intrinsics_opt', self.intModeDict[self.intfixes.get()], '--distortion_opt', self.disModeDict[self.disfixes.get()], self.tag.get(), '--paired_points', self.ppts.get(), '--unpaired_points', self.uppts.get(), '--scale', self.scale.get(), '--reference_points', self.ref.get(), '--tmp', tmp]

        if self.wLog.get() == '1':
            writeBool = True

        if self.display.get() == '1':
            args = args + ['--graph']

        if self.report.get() == '1':
            args = args + ['--outliers']

        if self.ocps.get() == '1':
            args = args + ['--output_camera_profiles']

        if self.choose.get() == '1':
            args = args + ['--choose_reference']

        cmd = cmd + args

        super(wandGUI, self).go(cmd, writeBool)


class calibrateGUI(GUI):
    def __init__(self):
        super(calibrateGUI, self).__init__()
        
        # Load system specific integers for Tkinter drawing differences
        pads = np.loadtxt(os.path.join(RESOURCE_PATH,'calib-gui-paddings.txt'))
        if sys.platform == 'linux2':
            pads = pads[0]
        elif sys.platform == 'darwin':
            pads = pads[1]
        elif sys.platform == 'win32' or sys.platform == 'win64':
            pads = pads[2]
        pads = map(int, pads)

        tooltips = Pmw.Balloon(self.root)

        group = LabelFrame(self.root, text="Options", padx=5, pady=5,  fg = '#56A0D3')

        # option variables:
        # fnam - input file name and location
        # inv - whether or not object points are inverted
        # replicates - number of passes through OpenCVs solver
        # ofnam - output file name and location
        # wLog - write a log?
        # option - what distortion coefficients to solve for
        self.fnam = StringVar(self.root)
        self.inv = StringVar(self.root)
        self.replicates = StringVar(self.root)
        self.patterns = StringVar(self.root)
        self.ofnam = StringVar(self.root)
        self.wLog = StringVar(self.root)
        self.option = StringVar(self.root)

        # set defaults:
        self.option.set("Optimize k1, k2")
        self.inv.set('0')
        self.wLog.set('0')
        self.replicates.set('100')
        self.patterns.set('20')

        Label(self.root, text = "Argus-Calibrate", font = ("Helvetica",23), fg = '#56A0D3').grid(row = 0, column = 0, padx = 20, pady = 20)
        #img = ImageTk.PhotoImage(Image.open("argus_panoptes.jpg").resize((96, 120), Image.ANTIALIAS))
        #panel = Label(root, image = img)

        #panel.grid(row = 0, column = 0, sticky = W)

        aboutButton = Button(self.root, text = "About", command = self.about, padx = 10, pady = 10)
        aboutButton.grid(row = 0, column = 0, sticky = E, padx = 5, pady = 5)

        findInFile = Button(self.root, text="Open", command=lambda: self.set_in_filename(self.fnam), padx = 10, pady = 10, width = 7, height = 1)
        findInFile.grid(row = 1, column = 0, padx = 180, sticky = W)
        tooltips.bind(findInFile, 'Find Pickle file with patterns')

        Label(self.root, text = "Input Patterns results:").grid(row = 1, column = 0, padx = 18, sticky = W)

        inFileEntry =  Entry(self.root, textvariable=self.fnam, width = 20)
        inFileEntry.grid(row = 2, column = 0, padx = 10, pady = 10,  sticky = EW)
        tooltips.bind(inFileEntry, 'Path to pickle')

        group.grid(row = 3, column = 0, sticky = EW, padx = 5)

        Label(group, text = "Number of replications:").grid(row = 0 ,column = 0, padx = 5, pady = 10)
        repEntry =  Entry(group, textvariable=self.replicates , width = 10, bd = 3)
        repEntry.grid(row = 0, column = 1, padx = 10, sticky = W)
        tooltips.bind(repEntry, 'Number of times to sample the frames and solve the distortion equations')

        invCheck = Checkbutton(group, text = 'Invert grid coordinates', variable = self.inv)
        invCheck.grid(row = 2, column = 0, padx = 20, pady = 5, sticky = W)
        tooltips.bind(invCheck, "If you're getting poor results, try checking this option")

        Label(group, text = "Sample size (frames):").grid(row = 1,column = 0, padx = 5, pady = 10)
        patEntry =  Entry(group, textvariable=self.patterns , width = 10, bd = 3)
        patEntry.grid(row = 1, column = 1, padx = 10, sticky = W)
        tooltips.bind(patEntry, 'Number of frames to use in each sample')

        w = OptionMenu(group, self.option, "Optimize k1, k2", "Optimize k1, k2, and k3", "Optimize all distortion coefficients")
        w.grid(row = 3, sticky = W, padx = 10, pady = 10)

        Label(self.root, text = "Output filename: ").grid(row = 4, column = 0, sticky = W, padx = pads[1])
        outEntry = Entry(self.root, textvariable = self.ofnam, width = pads[0])
        specButton = Button(self.root, text = 'Specify', command = lambda: self.set_out_filename(self.ofnam), padx = 15, pady = 10)
        specButton.grid(row = 4, column = 0, sticky = W, padx = 130, pady = 5)
        outEntry.grid(row = 4, column = 0, sticky = E, padx = 10, pady = 10)

        wLogCheck = Checkbutton(self.root, text = 'Write log', variable = self.wLog)
        wLogCheck.grid(row = 5, column = 0, padx = 20, pady = 5, sticky = W)

        go =Button(self.root, text="Go", command=self.go, width = 6, height = 3)
        go.grid(row = 6, column = 0, padx = 5, pady = 5, sticky = W)

        quitButton = Button(self.root, text = "Quit", command = self.quit_all, width = 6, height = 3)
        quitButton.grid(row = 6, column = 0, sticky = E, padx = 5, pady = 5)

        self.root.mainloop()

    # Start the subprocess and begin OpenCVs solving routine
    def go(self):
        if self.fnam.get().split('.')[-1] != 'pkl' and self.fnam.get().split('.')[-1] != 'PKL':
            tkMessageBox.showwarning(
            "Error",
            "Input file must be a Pickle"
            )
            return
        try:
            int(self.replicates.get())
            int(self.patterns.get())
        except:
            tkMessageBox.showwarning(
            "Error",
            "Number of samples and replicates must both be integers"
            )
            return
        if self.ofnam.get() == '':
            self.ofnam.set(self.fnam.get()[:-3] + 'csv')
        if self.ofnam.get().split('.')[-1] != 'csv' and self.ofnam.get().split('.')[-1] != 'CSV':
            tkMessageBox.showwarning(
            "Error",
            "Output file name must end with '.csv'"
            )
            return

        cmd = [sys.executable, os.path.join(RESOURCE_PATH, 'scripts/argus-calibrate')]
        writeBool = False
        args = [self.fnam.get(), self.ofnam.get(), '--replicates', self.replicates.get(), '--patterns', self.patterns.get()]
        if self.option.get() == "Optimize k1, k2, and k3":
            args = args + ['--k3']
        elif self.option.get() == "Optimize all distortion coefficients":
            args = args + ['--tangential']
        if self.wLog.get() == '1':
            writeBool = True

        if self.inv.get() == '1':
            args = args + ['--inverted']
        
        cmd = cmd + args

        super(calibrateGUI, self).go(cmd, writeBool)

class patternsGUI(GUI):
    def __init__(self):
        super(patternsGUI, self).__init__()
        # Load system specific integers for Tkinter drawing differences
        pads = np.loadtxt(os.path.join(RESOURCE_PATH,'patterns-gui-paddings.txt'))
        if sys.platform == 'linux2':
            pads = pads[0]
        elif sys.platform == 'darwin':
            pads = pads[1]
        elif sys.platform == 'win32' or sys.platform == 'win64':
            pads = pads[2]
        pads = map(int, pads)

        tooltips = Pmw.Balloon(self.root)

        group = LabelFrame(self.root, text="Settings", padx=5, pady=5,  fg = '#56A0D3')
        group2 = LabelFrame(self.root, text="Parameters", padx=5, pady=5,  fg = '#56A0D3')
        subgroup = LabelFrame(group2, text="Pattern", padx=5, pady=5,  fg = '#56A0D3')
        subgroup2 = LabelFrame(group2, text="Movie", padx=5, pady=5,  fg = '#56A0D3')

        self.fnam = StringVar(self.root)
        self.onam = StringVar(self.root)
        self.rows = StringVar(self.root)
        self.cols = StringVar(self.root)
        self.spacing = StringVar(self.root)
        self.start = StringVar(self.root)
        self.stop = StringVar(self.root)
        self.disp = StringVar(self.root)
        self.dots = IntVar(self.root)
        self.crop = StringVar(self.root)
        self.wLog = StringVar(self.root)

        self.wLog.set('0')
        self.disp.set('1')
        self.dots.set('1')
        self.crop.set('0')
        self.rows.set('12')
        self.cols.set('9')
        self.spacing.set('0.02')

        self.loggers = list()

        stopEntry = Entry(subgroup2, textvariable = self.stop, width = 10, bd = 3)
        startEntry = Entry(subgroup2, textvariable = self.start, width = 10, bd = 3)

        Label(self.root, text = "Argus-Patterns", font = ("Helvetica",25), fg = '#56A0D3').grid(row = 0, column = 0, padx = 20, pady = 20)
        #img = ImageTk.PhotoImage(Image.open("argus_panoptes.jpg").resize((96, 120), Image.ANTIALIAS))
        #panel = Label(root, image = img)

        #panel.grid(row = 0, column = 0, sticky = W)

        self.fnam.trace('w', lambda *args: self.setEntries())

        aboutButton = Button(self.root, text = "About", command = self.about, padx = 10, pady = 10)
        aboutButton.grid(row = 0, column = 0, sticky = E, padx = 5, pady = 5)

        findInFile = Button(self.root, text="Open", command=lambda: self.set_in_filename(self.fnam), padx = 10, pady = 10, width = 10, height = 1)
        findInFile.grid(row = 1, column = 0, padx = 180, sticky = W)
        tooltips.bind(findInFile, 'Open a video of a pattern')

        Label(self.root, text = "Input movie:").grid(row = 1, column = 0, padx = 35, sticky = W)

        inFileEntry =  Entry(self.root, textvariable=self.fnam, width = 20)
        inFileEntry.grid(row = 2, column = 0, padx = 10, pady = 10,  sticky = EW)
        tooltips.bind(inFileEntry, 'Path to video')

        group.grid(row = 3, column = 0, sticky = EW, padx = 5)

        dispCheck = Checkbutton(group, text="Display pattern recognition in progress", variable=self.disp)
        dispCheck.grid(row = 0, column = 0, sticky = W, padx = 5, pady = 5)
        tooltips.bind(dispCheck, 'Option to display video as patterns are found')

        Label(group, text = "Pattern type:").grid(row = 1, column = 0, sticky = W)

        Radiobutton(group, text="Dots", variable=self.dots, value=1).grid(row = 1, column = 0, pady = 5)
        Radiobutton(group, text="Chess board", variable=self.dots, value=2).grid(row = 1, column = 1, pady = 5)

        group2.grid(row = 4, column = 0, sticky = EW, padx = 5)
        subgroup.grid(row = 0, column = 0, padx = 5, pady = 5)
        subgroup2.grid(row = 0, column = 1, padx = 5, pady = 5)

        Label(subgroup, text = "Columns: ").grid(row = 0, column = 0)
        rowEntry = Entry(subgroup, textvariable = self.rows, width = 7, bd = 3)
        rowEntry.grid(row = 0, column = 1, sticky = W)
        tooltips.bind(rowEntry, 'Number of rows in the grid')

        Label(subgroup, text = "Rows: ").grid(row = 1, column = 0)
        colEntry = Entry(subgroup, textvariable = self.cols, width = 7, bd = 3)
        colEntry.grid(row = 1, column = 1, sticky = W)
        tooltips.bind(colEntry, 'Number of columns in the grid')

        Label(subgroup, text = "Spacing (m): ").grid(row = 2, column = 0)
        spacingEntry = Entry(subgroup, textvariable = self.spacing, width = 7, bd = 3)
        spacingEntry.grid(row = 2, column = 1, sticky = W)
        tooltips.bind(spacingEntry, 'Spacing between grid points')

        Label(subgroup2, text = "Start time: ").grid(row = 0, column = 0, sticky = W, padx = 5)
        startEntry.grid(row = 0, column = 1, pady = 10)

        Label(subgroup2, text = "Stop time: ").grid(row = 1, column = 0, sticky = W, padx = 5)
        stopEntry.grid(row = 1, column = 1, pady = 10)

        Label(self.root, text = "Output filename: ").grid(row = 5, column = 0, sticky = W, padx = pads[2])
        outEntry = Entry(self.root, textvariable = self.onam, width = pads[0])

        specButton = Button(self.root, text = 'Specify', command = lambda: self.set_out_filename(self.onam), padx = 15, pady = 10)
        specButton.grid(row = 5, column = 0, sticky = W, padx = pads[1], pady = 10)
        outEntry.grid(row = 5, column = 0, sticky = E, padx = 10, pady = 10)

        writeLogCheck = Checkbutton(self.root, text="Write log", variable=self.wLog)
        writeLogCheck.grid(row = 6, column = 0, pady = 5, padx = 30, sticky = W)

        go =Button(self.root, text="Go", command=self.go, width = 6, height = 3)
        go.grid(row = 7, column = 0, padx = 5, pady = 5, sticky = W)

        quitButton = Button(self.root, text = "Quit", command = self.quit_all, width = 6, height = 3)
        quitButton.grid(row = 7, column = 0, sticky = E, padx = 5, pady = 5)

        self.root.mainloop()

    def setEntries(self):
        if self.fnam.get() != '':
            try:
                clip = VideoFileClip(self.fnam.get())
                self.start.set('0.0')
                self.stop.set(clip.duration)
            except:
                tkMessageBox.showwarning(
                "Error",
                "Cannot read chosen video"
                )
                
    # Run the operation
    def go(self):
        try:
            int(self.rows.get())
            int(self.cols.get())
        except:
            tkMessageBox.showwarning(
            "Error",
            "Both rows and columns must be integers"
            )
            return
        try:
            float(self.spacing.get())
        except:
            tkMessageBox.showwarning(
            "Error",
            "Spacing must be a number"
            )
            return
        try:
            float(self.start.get())
            float(self.stop.get())
        except:
            tkMessageBox.showwarning(
            "Error",
            "Start and stop time must be floats"
            )
            return
        if self.onam.get() == '':
            self.onam.set(self.fnam.get()[:-3] + 'pkl')
        
        cmd = [sys.executable, os.path.join(RESOURCE_PATH, 'scripts/argus-patterns')]
        writeBool = False

        if self.wLog.get() == '1':
            writeBool = True
        args = [self.fnam.get(), self.onam.get(), '--rows', self.rows.get(), '--cols', self.cols.get(), '--spacing', self.spacing.get(), '--start' , self.start.get(), '--stop', self.stop.get()]
        if self.dots.get() == 1:
            args = args + ['--dots']
        if self.disp.get() == '1':
            args = args + ['--display']
        cmd = cmd + args

        super(patternsGUI, self).go(cmd, writeBool)

    
