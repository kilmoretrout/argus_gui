from PySide6 import QtGui, QtWidgets, QtCore

class OptionsPopupWindow(QtWidgets.QDialog):
    """# popup window for the options dialog
    """

    def __init__(self, sync, auto, track_list, track, disp, bstrap, o_sparse, rgb, parent=None):

        super().__init__(parent)
        self.setWindowTitle("Options")

        self.o_sparse = o_sparse
        self.rgb = rgb
        self.track_list = track_list

        self.cam_entry = QtWidgets.QLineEdit()
        self.lc = QtWidgets.QPushButton('Load camera profile')
        self.lc.clicked.connect(self.load_camera)
        
        self.dlt = QtWidgets.QLineEdit()
        self.ld = QtWidgets.QPushButton('Load DLT coefficients')
        self.ld.clicked.connect(self.load_DLT)

        self.tracks = QtWidgets.QComboBox()
        self.tracks.addItems(track_list)
        self.track = track
        self.tracks.setCurrentText(self.track)

        self.add_button = QtWidgets.QPushButton("Add a new track")
        self.add_button.clicked.connect(self.newTrack)

        self.disp = QtWidgets.QCheckBox("Display all tracks")
        self.disp.setChecked(disp)

        self.sync = QtWidgets.QCheckBox("Keep all videos in same frame")
        self.sync.setChecked(sync)

        self.auto = QtWidgets.QCheckBox("Automatically advance frames")
        self.auto.setChecked(auto)

        self.bstrap = QtWidgets.QCheckBox("Save 95% CIs, spline filtering weights,\nand error tolerance")
        self.bstrap.setChecked(bstrap)

        self.formatlabel = QtWidgets.QLabel("Save format: ")
        self.formatbox = QtWidgets.QComboBox()
        self.formatbox.addItems(["Dense .csv", "Sparse .tsv"])
        self.formatbox.currentIndexChanged.connect(self.sparse_toggle)
        if self.o_sparse:
            self.formatbox.setCurrentText("Sparse .tsv")
        else:
            self.formatbox.setCurrentText("Dense .csv")

        self.colorlabel = QtWidgets.QLabel("Display: ")
        self.colorbox = QtWidgets.QComboBox()
        self.colorbox.addItems(['RGB color', 'grayscale'])
        self.colorbox.currentIndexChanged.connect(self.color_toggle)
        if self.rgb:
            self.colorbox.setCurrentText('RGB color')
        else:
            self.colorbox.setCurrentText('grayscale')

        self.savelabel = QtWidgets.QLabel("Save location/tag: ")
        self.fnam = QtWidgets.QLineEdit()
        self.save_button = QtWidgets.QPushButton('Specify')
        self.save_button.clicked.connect(self.save_as)

        self.okbutton = QtWidgets.QPushButton("Ok")
        self.okbutton.clicked.connect(self.accept)
        
        # set values to globals if they are already set
        self.cam_entry.setText(camera_filename)
        self.dlt.setText(dlt_filename)
        self.fnam.setText(global_filename)
        
        # GUI structure
        genlabel = QtWidgets.QLabel("General Settings")
        displabel = QtWidgets.QLabel("Display options")
        outlabel = QtWidgets.QLabel("Save Settings")
        divider1 = QtWidgets.QFrame()
        divider1.setFrameShape(QtWidgets.QFrame.HLine)
        divider1.setFrameShadow(QtWidgets.QFrame.Sunken)
        divider2 = QtWidgets.QFrame()
        divider2.setFrameShape(QtWidgets.QFrame.HLine)
        divider2.setFrameShadow(QtWidgets.QFrame.Sunken)        

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(genlabel, 0, 0)
        layout.addWidget(self.cam_entry, 1, 0, 1, 2)
        layout.addWidget(self.lc, 1, 2)
        layout.addWidget(self.dlt, 2, 0, 1, 2)
        layout.addWidget(self.ld, 2, 2)
        layout.addWidget(self.tracks, 3, 0)
        layout.addWidget(self.add_button, 3, 1)

        layout.addWidget(divider1, 4, 0, 1, 3)
        layout.addWidget(displabel, 5, 0, 1, 3)
        layout.addWidget(self.disp, 6, 0)
        layout.addWidget(self.auto, 7, 0)
        layout.addWidget(self.sync, 8, 0)
        layout.addWidget(self.colorlabel, 9, 0)
        layout.addWidget(self.colorbox, 9, 0, QtCore.Qt.AlignRight)
        
        layout.addWidget(divider2, 10, 0, 1, 3)
        layout.addWidget(outlabel, 11, 0, 1, 3)
        layout.addWidget(self.bstrap, 12, 0)
        layout.addWidget(self.formatlabel, 13, 0)
        layout.addWidget(self.formatbox, 13, 0, QtCore.Qt.AlignRight)
        layout.addWidget(self.savelabel, 14, 0)
        layout.addWidget(self.fnam, 15, 0, 1, 2)
        layout.addWidget(self.save_button, 15, 2)
        layout.addWidget(self.okbutton, 16, 2)

        # self.track_list = track_list
        # self.dlts = list()

    # close with Return key
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Return:
            self.accept()

    # popup window for inputting track name
    def newTrack(self):
        track_name_window = newTrackPopup(self)
        if track_name_window.exec_() == QtWidgets.QDialog.Accepted:
            new_name = track_name_window.line_edit.text()

        # check to make sure the track name is not empty and does not already exist
        if new_name != '' and new_name not in self.track_list:
            self.track_list.append(new_name)
            self.tracks.addItem(new_name)
            self.tracks.setCurrentText(new_name)

        else:
            QtWidgets.QMessageBox.warning(None,
                "Error",
                "Track names must be unique and non-empty"
            )

    def load_camera(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose camera profile", filter="Text files (*.txt)")
        try:
            if filename:
                load_camera(filename)
                self.cam_entry.setText(filename)
        except:
            QtWidgets.QMessageBox.warning(None,
                "Error",
                "Could not load Camera profile!"
            )

    def load_DLT(self):
        global DLTCoefficients
        global dlt_filename
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose DLT coefficients file", filter="CSV files (*.csv)")

        if filename:
            try:
                DLTCoefficients = np.loadtxt(filename, delimiter=',')
                DLTCoefficients = DLTCoefficients.T
                self.dlt.setText(filename)
                dlt_filename = filename
            # TODO: Better Exception Handling
            except:
                QtWidgets.QMessageBox.warning(None,
                    "Error",
                    "Could not load DLT coefficients!"
                )
            
    def sparse_toggle(self):
        if self.formatbox.currentText() == "Sparse .tsv":
            self.o_sparse = True
        elif self.formatbox.currentText() == "Dense .csv":
            self.o_sparse = False

    def color_toggle(self):
        if self.colorbox.currentText() == "RGB color":
            self.rgb == True
        elif self.colorbox.currentText() == "grayscale":
            self.rgb == False

    def save_as(self):
        global global_filename
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Select location and enter file name prefix")
        if filename != '':
            self.fnam.setText(filename)
            global_filename = filename

class newTrackPopup(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Name the new track")
        layout = QtWidgets.QVBoxLayout(self)
        self.line_edit = QtWidgets.QLineEdit()
        layout.addWidget(self.line_edit)
        button = QtWidgets.QPushButton("Ok")
        button.clicked.connect(self.accept)
        layout.addWidget(button)

class GoToPopupWindow(QtWidgets.QDialog):
    """Popup window for skipping to specified frame
    """
    def __init__(self, number_of_frames, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter frame number")
        layout = QtWidgets.QVBoxLayout(self)
        self.go_to_frame = QtWidgets.QSpinBox()
        self.go_to_frame.setValue(current_frame)
        layout.addWidget(self.go_to_frame)
        self.label = QtWidgets.QLabel(f'out of {number_of_frames}')
        layout.addWidget(self.label)
        button = QtWidgets.QPushButton("Ok")
        button.clicked.connect(self.accept)
        layout.addWidget(button)
    
    def showEvent(self, event):
        super().showEvent(event)
        self.go_to_frame.setFocus()
        self.go_to_frame.selectAll()

sync = False
auto_advance=False
track_list_global = ['track 1', 'track 2']
current_track_global = 'track 2'
displaying_all_tracks = True
bstrap = False
outputSparse = True
rgb = True
global camera_filename
camera_filename = 'profile name'
global dlt_filename
dlt_filename = 'dlt name'
global global_filename
global_filename = 'save here'
global current_frame
current_frame = 52

app = QtWidgets.QApplication.instance()
if app is None:
    app = QtWidgets.QApplication([])
#w = OptionsPopupWindow(sync, auto_advance, track_list_global, current_track_global, displaying_all_tracks, bstrap, outputSparse, rgb)
w = GoToPopupWindow(2032)

w.exec_()
