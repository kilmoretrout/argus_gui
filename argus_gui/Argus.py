from PySide6 import QtGui, QtWidgets, QtCore
import pkg_resources
import os.path

RESOURCE_PATH = os.path.abspath(pkg_resources.resource_filename('argus_gui.resources', ''))

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Set up the user interface
        self.tab_widget = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # Set up some variables
        #clicker
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
        self.add_button = QtWidgets.QPushButton('+')
        self.add_button.setToolTip('Add a movie to the list')
        self.add_button.clicked.connect(self.add)

        # Layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.file_list)
        layout.addWidget(self.add_button)

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

if __name__ == "__main__":
    app = QtWidgets.QApplication()
    window = MainWindow()
    window.show()
    app.exec_()
