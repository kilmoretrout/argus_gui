import sys
import subprocess
from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QPlainTextEdit, QCheckBox

# class Worker(QtCore.QRunnable):
#     def __init__(self, command, log_display):
#         super().__init__()
#         self.command = command
#         self.log_display = log_display

#     def run(self):
#         process = QtCore.QProcess()
#         process.setProgram(sys.executable)
#         process.setArguments(self.command)
#         process.setReadChannel(QtCore.QProcess.StandardOutput)
#         process.readyReadStandardOutput.connect(lambda: self.log_display.appendPlainText(process.readAllStandardOutput().data().decode().strip()))
#         process.start()
#         print('process started')
#         process.waitForFinished()
        
class Worker(QtCore.QRunnable):
    def __init__(self, command, log_display):
        super().__init__()
        self.command = command
        self.log_display = log_display
    
    def run(self):
        process = subprocess.Popen(self.command, 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.STDOUT, 
                                   shell=True, 
                                    text=True)
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                process.kill()
                print('killing process')
                break
            if output:
                self.log_display.appendPlainText(output.strip())

class LogWindow(QWidget):
    def __init__(self, parent=None):
        super(LogWindow, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.log_display = QPlainTextEdit()
        self.log_display.setReadOnly(True)
        self.layout.addWidget(self.log_display)
        self.cancel_button = QPushButton('Cancel')
        self.cancel_button.clicked.connect(self.cancel)
        self.layout.addWidget(self.cancel_button)
        self.process = None
        self.show()
        # self.log_thread = QtCore.QThread()

    def cancel(self):
        if self.process:
            self.process.kill()
            self.cancel_button.setText('Done')
            self.cancel_button.clicked.disconnect()
            self.cancel_button.clicked.connect(self.close)

    def closeEvent(self, event):
        if self.process:
            self.process.kill()
        # self.log_thread.wait()
        event.accept()

    def update_log(self, command):
        worker = Worker(command, self.log_display)
        QtCore.QThreadPool.globalInstance().start(worker)
        # worker.output_signal.connect(self.log_display.appendPlainText)
        # worker.moveToThread(self.log_thread)
        # self.log_thread.started.connect(worker.run)
        # print('starting thread')
        # self.log_thread.start()
        # print('after the start')

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        go_button = QPushButton('Go')
        go_button.clicked.connect(self.go)
        layout.addWidget(go_button)
        self.wLog_checkbox = QCheckBox('wLog')
        layout.addWidget(self.wLog_checkbox)
        self.setLayout(layout)
        self.log_window = None

    def go(self):
        command = [sys.executable, 'external_function.py']
        self.log_window = LogWindow()
        self.log_window.update_log(command)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
