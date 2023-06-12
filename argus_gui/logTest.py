import sys
import subprocess
from PySide6 import QtCore, QtWidgets, QtGui

class Worker(QtCore.QObject):
    output = QtCore.Signal(str)
    finished = QtCore.Signal(int)

    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd
        self.process = None

    def run(self):
        self.process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        while True:
            line = self.process.stdout.readline()
            if not line:
                break
            self.output.emit(line)

        self.process.wait()
        self.finished.emit(self.process.returncode)

    def cancel(self):
        if self.process:
            self.process.terminate()
            self.process = None

class OutputWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Argus output")
        self.resize(600, 400)

        self.output_text = QtWidgets.QPlainTextEdit()
        self.output_text.setReadOnly(True)
        font = self.output_text.font()
        font.setFamily("Courier New")
        self.output_text.setFont(font)

        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.output_text)
        layout.addWidget(self.cancel_button)

        cmd = ["ping", "google.com"]
        self.worker = Worker(cmd)
        self.worker_thread = QtCore.QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker.output.connect(self.append_output)
        self.worker.finished.connect(self.finished)
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.start()

    def append_output(self, text):
        self.output_text.moveCursor(QtGui.QTextCursor.End)
        self.output_text.insertPlainText(text)

    def finished(self, returncode):
        self.append_output(f"\nProcess finished with exit code {returncode}")
        self.cancel_button.setText("Done")

    def cancel(self):
        if not self.worker_thread.isFinished():
            self.worker.cancel()
            self.cancel_button.setText("Done")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = OutputWindow()
    window.show()
    sys.exit(app.exec())
