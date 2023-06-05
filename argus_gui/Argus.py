from PySide6 import QtGui, QtWidgets, QtCore
import pkg_resources
import os.path
import shutil
import subprocess
import cv2
import numpy as np
import sys
import yaml
import string
import random
import tempfile
import psutil

RESOURCE_PATH = os.path.abspath(pkg_resources.resource_filename('argus_gui.resources', ''))

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        # Set the window title
        self.setWindowTitle("Argus")

        # Set the window icon
        self.setWindowIcon(QtGui.QIcon(os.path.join(RESOURCE_PATH,'icons/eye-8x.gif')))

        # Set up the user interface
        self.tab_widget = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # Set up some variables
        # general
        self.tmps = []
        self.pids = []

        # clicker
        self.offsets = []
        self.drivers = []
        
        self.tmps.append(tempfile.mkdtemp())
        # dictionary of cached files, relating random key to movie location
        self.cached = dict()

        # Add tabs with different widgets
        self.add_clicker_tab()
        self.add_sync_tab()
        self.add_wand_tab()
        self.add_patterns_tab()
        self.add_calibrate_tab()
        self.add_dwarp_tab()

    def add_clicker_tab(self):
        # Create the Clicker tab
        # Create file list
        self.file_list = QtWidgets.QListWidget()
        self.file_list.setToolTip("List of movies to click through for\nPress '+' button to add movie")
        # Create add button
        self.add_button = QtWidgets.QPushButton(' + ')
        self.add_button.setToolTip('Add a movie to the list')
        self.add_button.clicked.connect(self.add)
        # Create clear button
        self.clear_button = QtWidgets.QPushButton('Clear')
        self.clear_button.setToolTip('Clear the list of movies')
        self.clear_button.clicked.connect(self.clear)
        # Create remove button
        self.remove_button = QtWidgets.QPushButton(' - ')
        self.remove_button.setToolTip('Remove the selected movie from the list')
        self.remove_button.clicked.connect(self.delete)
        # Create resolution dropdown
        self.resolution_label = QtWidgets.QLabel('Resolution: ')
        self.resolution_var = QtWidgets.QComboBox()
        self.resolution_var.addItems(['Half', 'Full'])
        # Create about button
        self.about_button = QtWidgets.QPushButton('About')
        self.about_button.setToolTip('Show information about this software')
        self.about_button.clicked.connect(self.about)
        # Create load config button
        self.load_button = QtWidgets.QPushButton('Load Config')
        self.load_button.setToolTip('Load configuration from a file')
        self.load_button.clicked.connect(self.load)
        # Create go button
        self.go_button = QtWidgets.QPushButton('Go')
        self.go_button.setToolTip('Start clicking through the movies')
        self.go_button.clicked.connect(self.clicker_go)
        # Create quit button
        self.quit_button = QtWidgets.QPushButton('Quit')
        self.quit_button.setToolTip('Quit the program')
        self.quit_button.clicked.connect(self.quit_all)
        # Layout
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.file_list, 0, 0, 3, 2)
        layout.addWidget(self.add_button, 0, 2)
        layout.addWidget(self.clear_button, 2, 2)
        layout.addWidget(self.remove_button, 1, 2)
        layout.addWidget(self.resolution_label, 3, 0)
        layout.addWidget(self.resolution_var, 3, 1)
        layout.addWidget(self.load_button, 5, 0)
        layout.addWidget(self.go_button, 4, 0)
        layout.addWidget(self.about_button, 6, 2)
        layout.addWidget(self.quit_button, 6, 0)

        tab = QtWidgets.QWidget()
        tab.setLayout(layout)

        self.tab_widget.addTab(tab, QtGui.QIcon(os.path.join(RESOURCE_PATH,'icons/location-8x.gif')), "Clicker")

    def add_sync_tab(self):
        # Create the Sync tab
        # Create file list
        self.sync_file_list = QtWidgets.QListWidget()
        self.sync_file_list.setToolTip("List of movies to syncronize\nPress '+' button to add movie")
        # Create add button
        self.sync_add_button = QtWidgets.QPushButton(' + ')
        self.sync_add_button.setToolTip('Add a movie to the list')
        self.sync_add_button.clicked.connect(self.add)
        # Create clear button
        self.sync_clear_button = QtWidgets.QPushButton('Clear')
        self.sync_clear_button.setToolTip('Clear the list of movies')
        self.clear_button.clicked.connect(self.clear)
        # Create remove button
        self.sync_remove_button = QtWidgets.QPushButton(' - ')
        self.sync_remove_button.setToolTip('Remove the selected movie from the list')
        self.sync_remove_button.clicked.connect(self.delete)
        # Create go button
        self.sync_go_button = QtWidgets.QPushButton('Go')
        self.sync_go_button.setToolTip('Synchronize the videos')
        self.sync_go_button.clicked.connect(self.sync_go)
        # Create quit button
        self.sync_quit_button = QtWidgets.QPushButton('Quit')
        self.sync_quit_button.setToolTip('Quit the program')
        self.sync_quit_button.clicked.connect(self.quit_all)
        # Create about button
        self.sync_about_button = QtWidgets.QPushButton('About')
        self.sync_about_button.setToolTip('Show information about this software')
        self.sync_about_button.clicked.connect(self.about)
        # creat log check box
        self.sync_log = QtWidgets.QCheckBox("Write Log")


        # Sync specific
        self.show_waves_button = QtWidgets.QPushButton("Show waves")
        self.show_waves_button.clicked.connect(self.sync_show)
        self.crop = QtWidgets.QCheckBox("Specify time range")
        self.crop.stateChanged.connect(self.updateCropOptions)
        self.time_label = QtWidgets.QLabel("Time range containing sync sounds")
        self.start_crop = QtWidgets.QLineEdit()
        self.start_crop.setValidator(QtGui.QDoubleValidator())
        self.start_crop.setText("0.0")
        self.start_crop.setEnabled(False)
        self.start_label = QtWidgets.QLabel("Start time (decimal minutes)")
        self.end_crop = QtWidgets.QLineEdit()
        self.end_crop.setValidator(QtGui.QDoubleValidator())
        self.end_crop.setText("4.0")
        self.end_crop.setEnabled(False)
        self.end_label = QtWidgets.QLabel("End time  (decimal minutes)")

        self.sync_onam_label = QtWidgets.QLabel("Output filename")
        self.sync_onam = QtWidgets.QLineEdit()
        self.sync_onam_button = QtWidgets.QPushButton("Specify")
        self.sync_onam_button.clicked.connect(self.save_loc)

        # Layout
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.sync_file_list, 0, 0, 3, 2)
        layout.addWidget(self.sync_add_button, 0, 2)
        layout.addWidget(self.sync_clear_button, 2, 2)
        layout.addWidget(self.sync_remove_button, 1, 2)
        layout.addWidget(self.show_waves_button, 3, 1)
        layout.addWidget(self.crop, 4, 0)
        layout.addWidget(self.time_label, 5, 0)
        layout.addWidget(self.start_label, 6, 0)
        layout.addWidget(self.start_crop, 6, 1)
        layout.addWidget(self.end_label, 7, 0)
        layout.addWidget(self.end_crop, 7, 1)
        layout.addWidget(self.sync_log, 8, 0)
        layout.addWidget(self.sync_onam_label, 9, 0)
        layout.addWidget(self.sync_onam_button, 10, 0)
        layout.addWidget(self.sync_onam, 10, 1, 1, 2)
        layout.addWidget(self.sync_go_button, 11, 0)
        layout.addWidget(self.sync_about_button, 12, 2)
        layout.addWidget(self.sync_quit_button, 12, 0)
        tab = QtWidgets.QWidget()
        tab.setLayout(layout)

        self.tab_widget.addTab(tab, QtGui.QIcon(os.path.join(RESOURCE_PATH,'icons/pulse-8x.gif')), "Sync")

    def add_wand_tab(self):
        # Create the Wand tab

        self.intModeDict = {
            "Optimize none": '0',
            "Optimize focal length": '1',
            "Optimize focal length and principal point": '2'
        }

        self.disModeDict = {
            "Optimize none": '0',
            "Optimize r2": '1',
            "Optimize r2, r4": '2',
            "Optimize all distortion coefficients": '3'
        }

        self.refModeDict = {
            "Axis points": '0',
            "Gravity": '1',
            "Plane": '2'
        }

        # Create go button
        self.wand_go_button = QtWidgets.QPushButton('Go')
        self.wand_go_button.setToolTip('wandhronize the videos')
        self.wand_go_button.clicked.connect(self.wand_go)
        # Create quit button
        self.wand_quit_button = QtWidgets.QPushButton('Quit')
        self.wand_quit_button.setToolTip('Quit the program')
        self.wand_quit_button.clicked.connect(self.quit_all)
        # Create about button
        self.wand_about_button = QtWidgets.QPushButton('About')
        self.wand_about_button.setToolTip('Show information about this software')
        self.wand_about_button.clicked.connect(self.about)

        ops_label = QtWidgets.QLabel("Options")

        self.ppts = QtWidgets.QLineEdit()
        self.ppts_button = QtWidgets.QPushButton("Select paired points file")
        self.ppts_button.setToolTip('Open a CSV file with paired (wand) pixel coordinates')
        self.ppts_button.clicked.connect(self.add)
        self.uppts = QtWidgets.QLineEdit()
        self.uppts_button = QtWidgets.QPushButton("Select unpaired points file")
        self.uppts_button.setToolTip('Open a CSV file with unpaired (background) pixel coordinates')
        self.uppts_button.clicked.connect(self.add)
        self.wand_cams = QtWidgets.QLineEdit()
        self.wand_cams_button = QtWidgets.QPushButton("Select camera profile")
        self.wand_cams_button.setToolTip('Open a CSV or TXT file with camera intrinsic and extrinsics')
        self.wand_cams_button.clicked.connect(self.add)
        self.wand_refs = QtWidgets.QLineEdit()
        self.wand_refs_button = QtWidgets.QPushButton("Select reference points")
        self.wand_refs_button.setToolTip('Open a CSV file with axes pixel coordinates')
        self.wand_refs_button.clicked.connect(self.add)

        #reference point options
        self.wand_reftype_label = QtWidgets.QLabel("Reference point type:")
        self.wand_reftype = QtWidgets.QComboBox()
        for key in self.refModeDict.keys():
            self.wand_reftype.addItem(key)
        self.wand_reftype.currentIndexChanged.connect(self.updateFreqBoxState)
        self.wand_reftype.setToolTip('Set the reference type. \nAxis points are 1-4 points defining the origin and axes, \nGravity is an object accelerating due to gravity, \nPlane are 3+ points that define the X-Y plane')
        #recording frequency
        self.wand_freq_label = QtWidgets.QLabel("Recording frequency (fps)")
        self.wand_freq = QtWidgets.QLineEdit()
        self.wand_freq.setValidator(QtGui.QDoubleValidator())
        self.updateFreqBoxState()

        self.wand_scale_label = QtWidgets.QLabel("Wand length")
        self.wand_scale = QtWidgets.QLineEdit()
        self.wand_scale.setValidator(QtGui.QDoubleValidator())
        self.wand_scale.setText("1.0")
        self.wand_scale.setToolTip("Enter the distance between paired points (wand length).\nxyz coordinate outputs will have the same units as used here.")

        self.wand_instrics_label = QtWidgets.QLabel("Intriniscs: ")
        self.wand_intrinsics = QtWidgets.QComboBox()
        for key in self.intModeDict.keys():
            self.wand_intrinsics.addItem(key)
        
        self.wand_dist_label = QtWidgets.QLabel("Distortion: ")
        self.wand_dist = QtWidgets.QComboBox()
        for key in self.disModeDict.keys():
            self.wand_dist.addItem(key)
        #options boxes
        self.wand_outliers = QtWidgets.QCheckBox("Report on outliers")
        self.wand_chooseRef = QtWidgets.QCheckBox("Choose reference cameras")
        self.wand_outputProf = QtWidgets.QCheckBox("Output camera profiles")
        self.wand_display = QtWidgets.QCheckBox("Display results")
        self.wand_display.setChecked(True)
        self.wand_log = QtWidgets.QCheckBox("Write log")

        self.wand_onam_label = QtWidgets.QLabel("Output file prefix and location")
        self.wand_onam_button = QtWidgets.QPushButton("Specify")
        self.wand_onam_button.clicked.connect(self.save_loc)
        self.wand_onam = QtWidgets.QLineEdit()

        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.ppts_button, 1, 0)
        layout.addWidget(self.ppts, 1, 1, 1, 3)
        layout.addWidget(self.uppts_button, 2, 0)
        layout.addWidget(self.uppts, 2, 1, 1, 3)
        layout.addWidget(self.wand_refs_button, 3, 0)
        layout.addWidget(self.wand_refs, 3, 1, 1, 3)
        layout.addWidget(self.wand_cams_button, 4, 0)
        layout.addWidget(self.wand_cams, 4, 1, 1, 3)
        layout.addWidget(self.wand_reftype_label, 3, 4)
        layout.addWidget(self.wand_reftype, 3, 5)
        layout.addWidget(self.wand_freq_label, 3, 6)
        layout.addWidget(self.wand_freq, 3, 7)
        layout.addWidget(self.wand_scale_label, 1, 4)
        layout.addWidget(self.wand_scale, 1, 5)
        layout.addWidget(ops_label, 6, 1)
        layout.addWidget(self.wand_instrics_label, 7, 0)
        layout.addWidget(self.wand_intrinsics, 7, 1)
        layout.addWidget(self.wand_dist_label, 8, 0)
        layout.addWidget(self.wand_dist, 8, 1)
        layout.addWidget(self.wand_outliers, 9, 0)
        layout.addWidget(self.wand_chooseRef, 9, 1)
        layout.addWidget(self.wand_outputProf, 9, 2)
        layout.addWidget(self.wand_display, 9, 3)
        layout.addWidget(self.wand_onam_label, 10, 0)
        layout.addWidget(self.wand_onam_button, 11, 0)
        layout.addWidget(self.wand_onam, 11, 1, 1, 3)
        layout.addWidget(self.wand_log, 12, 0)
        layout.addWidget(self.wand_go_button, 13, 0)
        layout.addWidget(self.wand_quit_button, 14, 0)
        layout.addWidget(self.wand_about_button, 14, 6)
        
        layout.setColumnMinimumWidth(1, 400)

        tab = QtWidgets.QWidget()
        tab.setLayout(layout)

        self.tab_widget.addTab(tab, QtGui.QIcon(os.path.join(RESOURCE_PATH,'icons/wand.gif')),"Wand")

    def add_patterns_tab(self):
        # Create the Patterns tab
        # Create go button
        self.patt_go_button = QtWidgets.QPushButton('Go')
        self.patt_go_button.setToolTip('Detect patterns')
        self.patt_go_button.clicked.connect(self.pattern_go)
        # Create quit button
        self.patt_quit_button = QtWidgets.QPushButton('Quit')
        self.patt_quit_button.setToolTip('Quit the program')
        self.patt_quit_button.clicked.connect(self.quit_all)
        # Create about button
        self.patt_about_button = QtWidgets.QPushButton('About')
        self.patt_about_button.setToolTip('Show information about this software')
        self.patt_about_button.clicked.connect(self.about)

        self.patt_file_button = QtWidgets.QPushButton('Select calibration video')
        self.patt_file_button.clicked.connect(self.add)
        self.patt_file = QtWidgets.QLineEdit()
        
        # settings options
        self.patt_display = QtWidgets.QCheckBox("Display pattern recognition in progress")
        self.patt_type_label = QtWidgets.QLabel("Pattern type: ")
        self.patt_dots = QtWidgets.QRadioButton("Dots")
        self.patt_chess = QtWidgets.QRadioButton("Chess board")
        self.patt_flip = QtWidgets.QCheckBox("Inverse dimensions")
        set_layout = QtWidgets.QGridLayout()
        set_layout.addWidget(self.patt_display, 0, 0)
        set_layout.addWidget(self.patt_type_label, 1, 0)
        set_layout.addWidget(self.patt_dots, 1, 1)
        set_layout.addWidget(self.patt_chess, 1, 2)
        set_layout.addWidget(self.patt_flip, 2, 0)

        #settings box
        sett_box = QtWidgets.QGroupBox("Settings")
        sett_box.setLayout(set_layout)

        #Parameters
        param_box = QtWidgets.QGroupBox("Parameters")
        #pattern box
        patt_box = QtWidgets.QGroupBox("Pattern")
        self.patt_rows_label = QtWidgets.QLabel("Marks per row:")
        self.patt_rows = QtWidgets.QSpinBox()
        self.patt_rows.setValue(12)
        self.patt_cols_label = QtWidgets.QLabel("Marks per column:")
        self.patt_cols = QtWidgets.QSpinBox()
        self.patt_cols.setValue(9)
        self.patt_space_label = QtWidgets.QLabel("Spacing (m)")
        self.patt_space = QtWidgets.QLineEdit()
        self.patt_space.setValidator(QtGui.QDoubleValidator())
        patt_layout = QtWidgets.QGridLayout()
        patt_layout.addWidget(self.patt_rows_label, 0, 0)
        patt_layout.addWidget(self.patt_rows, 0, 1)
        patt_layout.addWidget(self.patt_cols_label, 1, 0)
        patt_layout.addWidget(self.patt_cols, 1, 1)
        patt_layout.addWidget(self.patt_space_label, 2, 0)
        patt_layout.addWidget(self.patt_space, 2, 1)
        patt_box.setLayout(patt_layout)
        #movie box
        mov_box = QtWidgets.QGroupBox("Movie")
        self.patt_start_label = QtWidgets.QLabel("Start time:")
        self.patt_start = QtWidgets.QLineEdit()
        self.patt_start.setValidator(QtGui.QDoubleValidator())
        self.patt_end_label = QtWidgets.QLabel("End time:")
        self.patt_end = QtWidgets.QLineEdit()
        self.patt_end.setValidator(QtGui.QDoubleValidator())
        mov_layout = QtWidgets.QGridLayout()
        mov_layout.addWidget(self.patt_start_label, 0, 0)
        mov_layout.addWidget(self.patt_start, 0, 1)
        mov_layout.addWidget(self.patt_end_label, 1, 0)
        mov_layout.addWidget(self.patt_end, 1, 1)
        mov_box.setLayout(mov_layout)
        param_layout = QtWidgets.QGridLayout()
        param_layout.addWidget(patt_box, 0, 0)
        param_layout.addWidget(mov_box, 0, 1)
        param_box.setLayout(param_layout)

        self.patt_log = QtWidgets.QCheckBox("Write log")
        # Create about button
        self.patt_about_button = QtWidgets.QPushButton('About')
        self.patt_about_button.setToolTip('Show information about this software')
        self.patt_about_button.clicked.connect(self.about)
        self.patt_onam_label = QtWidgets.QLabel("Output file prefix and location")
        self.patt_onam_button = QtWidgets.QPushButton("Specify")
        self.patt_onam_button.clicked.connect(self.save_loc)
        self.patt_onam = QtWidgets.QLineEdit()

        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.patt_file_button, 1, 0)
        layout.addWidget(self.patt_file, 1, 1, 1, 3)
        layout.addWidget(sett_box, 2, 0, 1, 6)
        layout.addWidget(param_box, 3, 0, 2, 6)
        layout.addWidget(self.patt_onam_label, 5, 0)
        layout.addWidget(self.patt_onam_button, 6, 0)
        layout.addWidget(self.patt_onam, 6, 1, 1, 3)
        layout.addWidget(self.patt_log, 7, 0)
        layout.addWidget(self.patt_go_button, 8, 0)
        layout.addWidget(self.patt_quit_button, 9, 0)
        layout.addWidget(self.patt_about_button, 9, 6)
        tab = QtWidgets.QWidget()
        tab.setLayout(layout)

        self.tab_widget.addTab(tab, QtGui.QIcon(os.path.join(RESOURCE_PATH,'icons/grid-four-up-8x.gif')), "Patterns")

    def add_calibrate_tab(self):
        # Create the Calibrate tab with a spin box
        spin_box = QtWidgets.QSpinBox()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(spin_box)

        tab = QtWidgets.QWidget()
        tab.setLayout(layout)

        self.tab_widget.addTab(tab, QtGui.QIcon(os.path.join(RESOURCE_PATH,'icons/calculator-8x.gif')), "Calibrate")

    def add_dwarp_tab(self):
        # Create the Dwarp tab with a combo box
        combo_box = QtWidgets.QComboBox()
        combo_box.addItems(["Option 1", "Option 2", "Option 3"])
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(combo_box)

        tab = QtWidgets.QWidget()
        tab.setLayout(layout)

        self.tab_widget.addTab(tab, QtGui.QIcon(os.path.join(RESOURCE_PATH,'icons/eye-8x.gif')), "Dwarp")
    
    ## General Functions
    def closeEvent(self, event):
        # Call the quit_all function when the window is closed
        self.quit_all()

    def about(self):
        w = QtWidgets.QDialog(self)
        license_text = QtWidgets.QPlainTextEdit()

        with open(os.path.join(RESOURCE_PATH, 'LICENSE.txt'), 'r') as f:
            text = f.read()
        license_text.setPlainText(text)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(license_text)
        w.setLayout(layout)
        w.exec_()


    def quit_all(self):
        self.close()
        self.kill_pids()
        for tmp in self.tmps:
            # Delete temporary directory in use if it still exists
            if os.path.isdir(tmp):
                shutil.rmtree(tmp)

    def kill_proc_tree(self, pid, including_parent=True):
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            child.kill()
        if including_parent:
            parent.kill()
            parent.wait(5)

    def kill_pids(self):
        for pid in self.pids:
            try:
                self.kill_proc_tree(pid)
            except:
                pass


    # def go(self, cmd, wlog=False, mode='DEBUG'):
    #     cmd = [str(wlog), ''] + cmd
    #     rcmd = [sys.executable, os.path.join(RESOURCE_PATH, 'scripts/argus-log')]

    #     rcmd = rcmd + cmd

    #     startupinfo = None
    #     if sys.platform == "win32" or sys.platform == "win64":  # Make it so subprocess brings up no console window
    #         startupinfo = subprocess.STARTUPINFO()
    #         startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    #     print(type(rcmd), rcmd)
    #     print(type(subprocess.PIPE))
    #     print(type(startupinfo))

    #     proc = subprocess.Popen(rcmd, stdout=subprocess.PIPE, shell=False, startupinfo=startupinfo)
    #     self.pids.append(proc.pid)

    def set_in_filename(self, var, filetypes=None):
        # Define the set_in_filename function
        options = QtWidgets.QFileDialog.Options()
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Select File', '', filetypes, options=options)
        if filename:
            var.set(filename)

    def set_out_filename(self, var, filetypes=None):
        options = QtWidgets.QFileDialog.Options()
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Select File', '', filetypes, options=options)
        if filename:
            var.set(filename)

    
    # Function for bringing up file dialogs; adds selected file to listbox
    def add(self):
        """
        Adds files to various tabs
        """
        # This function is used on several tabs, so get the tab name
        current_tab_name = self.tab_widget.tabText(self.tab_widget.currentIndex())

        # Depending on tab name and/or button pushed, call the window something different, filter for different files, and save to different locations

        # Clicker
        if current_tab_name == "Clicker":
            title = "Select Movie File"
            filter = 'All files (*)'
            target = self.file_list
        
        if current_tab_name == "Sync":
            title = "Select Movie File"
            filter = 'All files (*)'
            target = self.sync_file_list

        if current_tab_name == "Wand":
            button = self.sender()
            # paired
            if button == self.ppts_button:
                title = "Select paired points file"
                filter = "Wand points file (*xypts.csv);;All files (*)"
                target = self.ppts
            # unpaired
            if button == self.uppts_button:
                title = "Select unpaired points file"
                filter = "Wand points file (*xypts.csv);;All files (*)"
                target = self.uppts
            #camera profile
            if button == self.wand_cams_button:
                title = "Select camera profile"
                filter = "TXT (*.txt);;CSV (*.csv);;All files (*)"
                target = self.wand_cams
            #reference points
            if button == self.wand_refs_button:
                title = "Select reference points"
                filter = "reference points (*xypts.csv);;All files (*)"
                target = self.wand_refs
        if current_tab_name == "Patterns":
            title = "Select pattern video"
            filter = "All files (*)"
            target = self.patt_file
        # Create a file dialog with the specified title and filter
        file_dialog = QtWidgets.QFileDialog(self)
        file_dialog.setWindowTitle(title)
        file_dialog.setNameFilter(filter)

        # Show the file dialog and get the selected file path
        if file_dialog.exec_():
            file_name = file_dialog.selectedFiles()[0]

        if file_name:
            # Clicker
            if current_tab_name == "Clicker":
                if not self.file_list.findItems(file_name, QtCore.Qt.MatchExactly):
                    print(f'adding {file_name}')
                    self.file_list.addItem(file_name)
                    
                    if len(self.offsets) != 0:
                        offset, ok = QtWidgets.QInputDialog.getInt(self, 'Enter Offset', "Frame offset: ", value=0)
                    else:
                        offset = 0

                    try:
                        self.offsets.append(int(offset))
                    except ValueError:
                        QtWidgets.QMessageBox.warning(None, 'Error', 'Frame offset must be an integer')
                        return
                else:
                # if file_name in set(self.file_list):
                    QtWidgets.QMessageBox.warning(None,
                        "Error",
                        "You cannot click through two of the same movies"
                    )
        
            # Sync
            if current_tab_name == "Sync":
                if not self.sync_file_list.findItems(file_name, QtCore.Qt.MatchExactly):
                    print(f'adding {file_name}')
                    self.sync_file_list.addItem(file_name)
                    self.cached[file_name] = self.id_generator() + '-' + file_name.split('/')[-1].split('.')[0] + '.wav'
                else:
                    QtWidgets.QMessageBox.warning(None,
                        "Error",
                        "You cannot click through two of the same movies"
                    )

            # Wand
            if current_tab_name == "Wand":
                target.setText(file_name)

            # Pattern
            if current_tab_name == "Patterns":
                target.setText(file_name)


    def delete(self):
        """
        Removes videos from various tabs
        """
        # This function is used on several tabs, so get the tab name
        current_tab_name = self.tab_widget.tabText(self.tab_widget.currentIndex())
        
        #for Clicker
        if current_tab_name == "Clicker":
            # Get the selected item
            selected_items = self.file_list.selectedItems()

            if selected_items:
                # If an item is selected, delete it
                for item in selected_items:
                    self.file_list.takeItem(self.file_list.row(item))
                    del self.offsets[self.file_list.row(item)]
            else:
                # If no item is selected, delete the last item in the list
                if self.file_list.count() > 0:
                    self.file_list.takeItem(self.file_list.count() - 1)
                    del self.offsets[-1]
        #for Sync
        if current_tab_name == "Sync":
            # Get the selected item
            selected_items = self.sync_file_list.selectedItems()

            if selected_items:
                # If item(s) selected, delete it from list
                for item in selected_items:
                    self.sync_file_list.takeItem(self.sync_file_list.row(item))
                    # check if there is a cached wav, and delete it
                    if os.path.isfile(self.tmps[0] + '/' + self.cached[item]):
                        os.remove(self.tmps[0] + '/' + self.cached[item])
                    del self.cached[item]
            else:
                # If no item is selected, delete the last item in the list
                if self.sync_file_list.count() > 0:
                    item = self.sync_file_list[self.sync_file_list.count()-1]
                    if os.path.isfile(self.tmps[0] + '/' + self.cached[item]):
                        os.remove(self.tmps[0] + '/' + self.cached[item])
                    del self.cached[item]
                    self.sync_file_list.takeItem(self.sync_file_list.count() - 1)

    def clear(self):

        # This function is used on several tabs, so get the tab name
        current_tab_name = self.tab_widget.tabText(self.tab_widget.currentIndex())
        
        #for Clicker
        if current_tab_name == "Clicker":
            self.file_list.selectAll()
            self.delete()

        #for Sync
        if current_tab_name == "Sync":
            self.sync_file_list.selectAll()
            self.delete()
    
    # general function to select save location
    def save_loc(self):
        # This function is used on several tabs, so get the tab name
        current_tab_name = self.tab_widget.tabText(self.tab_widget.currentIndex())
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self,
         caption="Select save location")#, dir = init, filter = filt)
        if filename:
            #for Sync
            if current_tab_name == "Sync":
                self.sync_onam.setText(filename)
            if current_tab_name == "Wand":
                self.wand_onam.setText(filename)
            if current_tab_name == "Patterns":
                self.patt_onam.setText(filename)
    
    ## Clicker Functions
    def load(self):
        """
        Loads config file on clicker window
        """
        options = QtWidgets.QFileDialog.Options()
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Select an Argus clicker config file', '', 'Argus clicker config files (*.yaml)', options=options)
        if filename:
            cmd = [sys.executable, os.path.join(RESOURCE_PATH, 'scripts/argus-click')]
            args = [f"configload@{filename}"]
            cmd = cmd + args
            if hasattr(sys, 'frozen'):
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False,
                                        startupinfo=None)
            else:
                proc = subprocess.Popen(cmd)            

    def clicker_go(self):
        if self.resolution_var == "Full":
            res_var = 1
        else:
            res_var = 2

        movies = [str(self.file_list.item(x).text()) for x in range(self.file_list.count())]

        if len(movies) != 0:
            driver = PygletDriver(movies, self.offsets, res=str(res_var))
            driver.run()
            self.drivers.append(driver)
        else:
            QtWidgets.QMessageBox.warning(None,
                "Error",
                "No movies to click through!"
            )
            return   

    ## Sync Functions

    # Gets seconds from 'hours:minutes:seconds' string
    def getSec(self, s):
        return 60. * float(s)

    def updateCropOptions(self):
        self.start_crop.setEnabled(self.crop.isChecked())
        self.end_crop.setEnabled(self.crop.isChecked())

    def sync_go(self):
        cropArg = ''
        files = [str(self.sync_file_list.item(x).text()) for x in range(self.sync_file_list.count())]
        if len(files) <= 1:
            QtWidgets.QMessageBox.warning(None,
                "Error",
                "Need at least two videos to sync"
            )
            return 
        for k in range(len(files)):
            try:
                open(files[k])
            except:
                QtWidgets.QMessageBox.warning(None,
                "Error",
                "Could not find one or more of the specified videos"
                )
                return 
        if self.crop.isChecked():
            try:
                float(self.start_crop)
                float(self.end_crop)
            except:
                QtWidgets.QMessageBox.warning(None,
                "Error",
                "Start and end time must be floats"
                )
                return
            for k in range(len(files)):
                    cap = cv2.VideoCapture(files[k])
                    length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    dur = length * float(cap.get(cv2.CAP_PROP_FPS))
                    # dur = VideoFileClip(files[k]).duration
                    if self.getSec(self.start_crop.text()) >= dur or self.getSec(self.end_crop.text()) > dur:
                        QtWidgets.QMessageBox.warning(None,
                            "Error",
                            "Time range does not exist for one or more of the specified videos"
                        )
                        return
                    elif self.getSec(self.start_crop.text()) >= self.getSec(self.end_crop.text()):
                        QtWidgets.QMessageBox.warning(None,
                            "Error",
                            "Start time is further along than end time"
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

        logBool = self.sync_log

        # check for properly named output file (if it exists) & fix it if appropriate
        of = self.sync_onam.text()
        if of:
            ofs = of.split('.')
            if ofs[-1].lower() != 'csv':
                of = of + '.csv'
                self.sync_onam.setText(of)

        file_str = ','.join(files)
        out_str = ','.join(out)

        cmd = [sys.executable, os.path.join(RESOURCE_PATH, 'scripts/argus-sync')]
        # Create args list, order is important
        args = [file_str, '--tmp', self.tmps[0], '--start', self.start_crop.text(), '--end', self.end_crop.text(), '--ofile',
                self.sync_onam.text(), '--out', out_str]

        if self.crop:
            args = args + ['--crop']
        cmd = cmd + args
        self.go(cmd, logBool)

# Graph the wave files with matplotlib
    def sync_show(self):
        files = [str(self.sync_file_list.item(x).text()) for x in range(self.sync_file_list.count())]
        for k in range(len(files)):
            try:
                self.cached[files[k]]
            except:
                self.cached[files[k]] = self.id_generator() + '-' + files[k].split('/')[-1].split('.')[0] + '.wav'
        out = list()
        for k in range(len(files)):
            out.append(self.cached[files[k]])

        cmd = [sys.executable, os.path.join(RESOURCE_PATH, 'scripts/argus-show')]
        if isinstance(files, str):
            args = [self.tmps[0], files] + out
        else:
            args = [self.tmps[0]] + list(files) + out

        cmd = cmd + args

        self.go(cmd)

    def id_generator(self, size=12, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))
    
## Wand specific
    def updateFreqBoxState(self):
        if self.wand_reftype.currentText() == "Gravity":
            self.wand_freq.setEnabled(True)
            self.wand_freq_label.setEnabled(True)
        else:
            self.wand_freq.setEnabled(False)
            self.wand_freq_label.setEnabled(False)

    def wand_go(self):
        cmd = [sys.executable, os.path.join(RESOURCE_PATH, 'scripts/argus-wand')]
        tmp = tempfile.mkdtemp()
        write_bool = False

        args = [self.wand_cams.text(), '--intrinsics_opt', self.intModeDict[self.wand_intrinsics.currentText()], '--distortion_opt',
                self.disModeDict[self.wand_dist.currentText()], self.wand_onam.text(), '--paired_points', self.ppts.text(),
                '--unpaired_points', self.uppts.text(), '--scale', self.wand_scale.text(), '--reference_points',
                self.wand_refs.text(), '--reference_type', self.wand_reftype.currentText(), '--recording_frequency', self.wand_freq.text(), 
                '--tmp', tmp]

        if self.wand_log:
            write_bool = True

        if self.wand_display:
            args = args + ['--graph']

        if self.wand_outliers:
            args = args + ['--outliers']

        if self.wand_outputProf:
            args = args + ['--output_camera_profiles']

        if self.wand_chooseRef:
            args = args + ['--choose_reference']

        cmd = cmd + args
        print(cmd)
        self.go(cmd, wlog=write_bool)

    def pattern_go(self):
        # check and fix the output filename
        if self.patt_onam.text() == '':  # no name at all
            self.patt_onam.setText(self.patt_file.text().split('.')[0] + 'pkl')
        of = self.patt_onam.text()
        if of:  # check extension
            ofs = of.split('.')
            if ofs[-1].lower() != 'pkl':
                of = of + '.pkl'
                self.patt_onam.setText(of)

        cmd = [sys.executable, os.path.join(RESOURCE_PATH, 'scripts/argus-patterns')]
        writeBool = False

        if self.patt_log:
            writeBool = True
        args = [self.patt_file.text(), self.patt_onam.text(), '--rows', self.patt_rows.text(), '--cols', self.patt_cols.text(), '--spacing',
                self.patt_space.text(), '--start', self.patt_start.text(), '--stop', self.patt_end.text()]
        if self.dots:
            args = args + ['--dots']
        if self.disp:
            args = args + ['--display']
        cmd = cmd + args

        self.go(cmd, writeBool)

    # main command caller used by all but clicker
    def go(self, cmd, wlog=False, mode='DEBUG'):
        cmd = [str(wlog), ''] + cmd
        rcmd = [sys.executable, os.path.join(RESOURCE_PATH, 'scripts/argus-log')]

        rcmd = rcmd + cmd

        startupinfo = None
        if sys.platform == "win32" or sys.platform == "win64":  # Make it so subprocess brings up no console window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        print(type(rcmd), rcmd)
        print(type(subprocess.PIPE))
        print(type(startupinfo))

        proc = subprocess.Popen(rcmd, stdout=subprocess.PIPE, shell=False, startupinfo=startupinfo)
        self.pids.append(proc.pid)

# Makes a subprocess with Pyglet windows for all camera views
class PygletDriver:
    def __init__(self, movies, offsets, res=None):
        self.movies = movies
        self.offsets = offsets
        self.res = res
        starts = []
        for k in range(len(offsets)):
            starts.append(np.max(offsets) - offsets[k])
        self.processes = []
        self.end = int(cv2.VideoCapture(movies[0]).get(cv2.CAP_PROP_FRAME_COUNT))

    def run(self):
        movie_string = ''
        for index, movie in enumerate(self.movies):
            if index != len(self.movies) - 1:
                movie_string = movie_string + movie + '@'
            else:
                movie_string = movie_string + movie

        offset_string = ''
        for k in range(len(self.offsets)):
            if k != len(self.offsets) - 1:
                offset_string = offset_string + str(self.offsets[k]) + '@'
            else:
                offset_string = offset_string + str(self.offsets[k])

        cmd = [sys.executable, os.path.join(RESOURCE_PATH, 'scripts/argus-click')]
        args = [movie_string, str(self.end), offset_string, self.res]
        cmd = cmd + args
        if hasattr(sys, 'frozen'):
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False,
                                    startupinfo=None)
        else:
            proc = subprocess.Popen(cmd)

        self.processes.append(proc)

    def kill(self):
        for proc in self.processes:
            proc.kill()

class ClickerProject:
    @staticmethod
    def create(proj_path, video_paths, points, resolution, last_frame, offsets,
               dlt_coefficents=None, camera_profile=None, settings=None, window_positions=None):
        project = [{"videos": video_paths}, {"points": points}, {"resolution": resolution},
                   {"last_frame": last_frame}, {"offsets": offsets}, {"dlt_coefficents": dlt_coefficents},
                   {"camera_profile": camera_profile}, {"settings": settings}]
        with open(f"{proj_path}-config.yaml", "w") as f:
            f.write(yaml.dump(project))

if __name__ == "__main__":
    app = QtWidgets.QApplication()
    window = MainWindow()
    window.show()
    app.exec_()
