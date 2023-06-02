from PySide6 import QtCore, QtWidgets

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Set up the user interface
        self.file_list = QtWidgets.QListWidget()
        self.add_button = QtWidgets.QPushButton("Add")
        self.add_button.clicked.connect(self.add_file)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.file_list)
        layout.addWidget(self.add_button)

        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def add_file(self):
        # Open a file dialog to select a file
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select File")

        # Check if the file is already in the list
        if file_name and not self.file_list.findItems(file_name, QtCore.Qt.MatchExactly):
            # Add the file to the list
            self.file_list.addItem(file_name)

if __name__ == "__main__":
    app = QtWidgets.QApplication()
    window = MainWindow()
    window.show()
    app.exec_()
