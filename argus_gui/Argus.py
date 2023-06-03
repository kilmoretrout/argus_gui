from PySide6 import QtGui, QtWidgets, QtCore
import pkg_resources
import os.path
import shutil
import subprocess
import cv2
import numpy as np
import sys
import yaml

RESOURCE_PATH = os.path.abspath(pkg_resources.resource_filename('argus_gui.resources', ''))

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

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
        layout.addWidget(self.load_button, 4, 2)
        layout.addWidget(self.go_button, 4, 0)
        layout.addWidget(self.about_button, 5, 2)
        layout.addWidget(self.quit_button, 5, 0)

        tab = QtWidgets.QWidget()
        tab.setLayout(layout)

        self.tab_widget.addTab(tab, QtGui.QIcon(os.path.join(RESOURCE_PATH,'icons/location-8x.gif')), "Clicker")

    def add_sync_tab(self):
        # Create the Sync tab with a checkbox
        checkbox = QtWidgets.QCheckBox("Sync Checkbox")
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(checkbox)

        tab = QtWidgets.QWidget()
        tab.setLayout(layout)

        self.tab_widget.addTab(tab, QtGui.QIcon(os.path.join(RESOURCE_PATH,'icons/pulse-8x.gif')), "Sync")


    def add_wand_tab(self):
        # Create the Wand tab with a radio button
        radio_button = QtWidgets.QRadioButton("Wand Radio Button")
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(radio_button)

        tab = QtWidgets.QWidget()
        tab.setLayout(layout)

        self.tab_widget.addTab(tab, QtGui.QIcon(os.path.join(RESOURCE_PATH,'icons/wand.gif')),"Wand")

    def add_patterns_tab(self):
        # Create the Patterns tab with a line edit
        line_edit = QtWidgets.QLineEdit()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(line_edit)

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

    @staticmethod
    def about():
        with open(os.path.join(RESOURCE_PATH, 'LICENSE.txt'), 'r') as f:
            license_text = f.read()
        QtWidgets.QMessageBox.about(None, 'License', license_text)

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

    ## Clicker Functions
    # Function for bringing up file dialogs; adds selected file to listbox
    def add(self):
        options = QtWidgets.QFileDialog.Options()
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Select Movie File', '', 'All Files (*)', options=options)

        if file_name and not self.file_list.findItems(file_name, QtCore.Qt.MatchExactly):
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
    def delete(self):
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

    def clear(self):
        self.file_list.clear()
        self.offsets = list()

    def load(self):
        print('load pressed')
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
