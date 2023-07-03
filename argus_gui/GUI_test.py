from PySide6 import QtWidgets

class MyWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Create central widget
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)

        # Create left panel
        self.left_panel = QtWidgets.QTabWidget()
        self.left_panel.addTab(QtWidgets.QWidget(), 'Tab 1')
        self.left_panel.addTab(QtWidgets.QWidget(), 'Tab 2')
        self.left_panel.addTab(QtWidgets.QWidget(), 'Tab 3')

        # Create right panel
        self.right_panel = QtWidgets.QWidget()
        self.right_layout = QtWidgets.QVBoxLayout()
        self.text_field = QtWidgets.QLineEdit()
        self.cancel_button = QtWidgets.QPushButton('Cancel')
        self.about_button = QtWidgets.QPushButton('About')
        self.quit_button = QtWidgets.QPushButton('Quit')
        self.right_layout.addWidget(self.text_field)
        self.right_layout.addWidget(self.cancel_button)
        self.right_layout.addWidget(self.about_button)
        self.right_layout.addWidget(self.quit_button)
        self.right_panel.setLayout(self.right_layout)

        # Create main layout
        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addWidget(self.left_panel)
        self.main_layout.addWidget(self.right_panel)
        self.central_widget.setLayout(self.main_layout)

app = QtWidgets.QApplication([])
window = MyWindow()
window.show()
app.exec_()
