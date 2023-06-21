#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
logger.py - Takes a command, executes it, and displays its live stderr and stdout in a Qt window.
Has options for writing output to txt, and can be told of any temproary directory that the command
uses for proper cleanup.
"""

from __future__ import absolute_import
from __future__ import print_function

import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
from PySide6 import QtGui, QtWidgets, QtCore
# from six.moves.queue import Queue
# from six.moves.tkinter import *

# Takes a command and displays its stdout and stderr as its running.  Used by most of the Argus programs to display progress.

class WorkerSignals(QtCore.QObject):
    finished = QtCore.Signal()

class Worker(QtCore.QRunnable):
    """
    run a command in its own thread
    """

    def __init__(self, cmd, log_display, logfile):
        super().__init__()
        self.cmd = cmd
        self.cmd = cmd
        self.log_display = log_display
        self.logfile = logfile
        self.running = True
        self.signals = WorkerSignals()

    def run(self):
        startupinfo = None
        if sys.platform == "win32" or sys.platform == "win64":  # Make it so subprocess brings up no console window
            # Set up the startupinfo to suppress the console window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        # Start the process
        self.process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, text=True, startupinfo=startupinfo)


        while self.running:
            line = self.process.stdout.readline()
            if line == '' and self.process.poll() is not None:
                self.process.kill()
                self.update_log('Process complete')
                self.running = False
                self.logfile.close()
                break
            if line:
                self.update_log(line.strip())
                # self.log_display.appendPlainText(line.strip())
        self.signals.finished.emit()

    def update_log(self, text):
        bad_phrases = ['iters',
                        'it/s',
                        'InsecureRequestWarning',
                        'axes3d.py',
                        'Python',
                        '_createMenuRef',
                        '0x',
                        'ApplePersistenceIgnoreState',
                        'self._edgecolors',
                        'objc',
                        'warnings.warn',
                        'UserWarning',
                        ]
         
        if not any(bad_phrase in text for bad_phrase in bad_phrases):
            self.log_display.appendPlainText(text)
            
            if self.logfile:
                text = "\n" + text
                self.logfile.write(text.encode('utf-8'))
            # self.linecount += 1
            
    def cancel(self):
        self.running = False
        if self.process:
            self.process.kill()
            self.update_log("Canceled process")
            self.logfile.close()
            self.process = None

class Logger(QtWidgets.QDialog):
    def __init__(self, cmd, tmp='', wLog=True, doneButton=True, parent=None):
        super().__init__(parent)
        self.cmd = cmd
        self.tmp = tmp
        self.wLog = wLog
        self.doneButton = doneButton

        # Create a QPlainTextEdit to display the output
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        font = self.log.font()
        font.setFamily("Courier New")
        self.log.setFont(font)
        
        # Create a "Done" button
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel)

        self.id = None

        # Create a layout and add the widgets to it
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.log)
        layout.addWidget(self.cancel_button)
        self.setLayout(layout)

        # Set the window titleand size
        self.setWindowTitle("Argus ouput")
        self.resize(800, 600)

        if wLog:
            self.fo = open("Log--" + time.strftime("%Y-%m-%d-%H-%M") + ".txt", "wb")
        else:
            self.fo = None
        self.linecount = 0
        self.show()

    @QtCore.Slot()
    def update_log(self):
        #start the thread
        self.worker = Worker(self.cmd, self.log, self.fo)
        QtCore.QThreadPool.globalInstance().start(self.worker)

    # def guifinished(self, returncode):
    #     self.append_output(f"\nProcess finished with exit code {returncode}")
    #     self.cancel_button.setText("Done")
    @QtCore.Slot()
    def cancel(self):
        QtCore.QThreadPool.globalInstance().clear()
        self.cancel_button.setText('Done')
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.close)
        
    @QtCore.Slot()
    def task_finished(self):
        self.cancel_button.setText('Done')
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.close)
    
    def closeEvent(self, event):
        if self.tmp != '':
            if os.path.isdir(self.tmp):
                shutil.rmtree(self.tmp)
        if self.wLog:
            self.fo.close()

        if self.worker.process:
            self.worker.cancel()
            self.worker.kill
            self.worker_thread.wait()
        super().closeEvent(event)

    def flush(self):
        pass
