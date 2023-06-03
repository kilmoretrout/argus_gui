from PySide6 import QtWidgets
from PySide6.QtWidgets import QApplication, QLabel, QRadioButton, QVBoxLayout

class Window(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.o_sparse = None

        layout = QVBoxLayout(self)

        label = QLabel("Save format:")
        layout.addWidget(label)

        self.sparse_radio = QRadioButton("Sparse .tsv")
        self.sparse_radio.toggled.connect(self.on_radio_toggled)
        layout.addWidget(self.sparse_radio)

        self.dense_radio = QRadioButton("Dense .csv")
        self.dense_radio.toggled.connect(self.on_radio_toggled)
        layout.addWidget(self.dense_radio)

    def on_radio_toggled(self):
        if self.sender() == self.sparse_radio:
            self.o_sparse = True
        elif self.sender() == self.dense_radio:
            self.o_sparse = False

if __name__ == "__main__":
    app = QApplication()
    window = Window()
    window.show()
    app.exec_()
