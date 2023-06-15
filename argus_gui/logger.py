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

class Worker(QtCore.QThread):
    """
    run a command in its own thread
    """
    output = QtCore.Signal(str)
    finished = QtCore.Signal(int)

    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd
        self.process = None
        self.running = True

    def run(self):
        self.process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        while self.running:
            line = self.process.stdout.readline()
            if not line:
                break
            self.output.emit(line)

        if self.process:
            self.process.terminate()
            self.process.wait()
            self.finished.emit(self.process.returncode)

    def cancel(self):
        self.running = False
        if self.process:
            self.process.terminate()
            self.process = None

class Logger(QtWidgets.QDialog):
    def __init__(self, cmd, tmp='', wLog=False, doneButton=True, parent=None):
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
        
        # Redirect stdout to the output widget
        self.original_stdout = sys.stdout
        sys.stdout = self
        
        # Set the window titleand size
        self.setWindowTitle("Argus ouput")
        self.resize(800, 600)

        if wLog:
            self.fo = open("Log--" + time.strftime("%Y-%m-%d-%H-%M") + ".txt", "wb")
        else:
            self.fo = None
        self.linecount = 0

        #start the thread
        self.worker = Worker(cmd)
        self.worker_thread = QtCore.QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker.output.connect(self.append_output)
        self.worker.finished.connect(self.guifinished)
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()
    
    def append_output(self, text):
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
                        'UserWarning']
        if not any(bad_phrase in text for bad_phrase in bad_phrases):
            self.log.moveCursor(QtGui.QTextCursor.End)
            self.log.insertPlainText(text)
            if self.fo:
                self.fo.write(text.encode('utf-8'))
            self.linecount += 1


    def guifinished(self, returncode):
        self.append_output(f"\nProcess finished with exit code {returncode}")
        self.cancel_button.setText("Done")

    def cancel(self):
        if not self.worker_thread.isFinished():
            self.worker.cancel()
            if not isinstance(self.sender(), QtWidgets.QPushButton):
                # If cancel is called from closeEvent
                # wait for worker thread to finish before closing window
                # otherwise just change button text
                # and let user decide when to close window
                # (and wait for worker thread to finish in closeEvent)
                # This prevents window from freezing while waiting for worker thread to finish
                # when user clicks on Cancel button
                return
            else:
                # If cancel is called from Cancel button click
                # just change button text and let user decide when to close window
                # (and wait for worker thread to finish in closeEvent)
                # This prevents window from freezing while waiting for worker thread to finish
                # when user clicks on Cancel button
                pass
            if isinstance(self.sender(), QtWidgets.QPushButton):
                if self.cancel_button.text() == "Done":
                    self.close()
                else:
                    self.cancel_button.setText("Done")
    
    def closeEvent(self, event):
        if self.tmp != '':
            if os.path.isdir(self.tmp):
                shutil.rmtree(self.tmp)
        if self.wLog:
            self.fo.close()

        if not self.worker_thread.isFinished():
            self.worker.cancel()
            self.worker_thread.quit()
            self.worker_thread.wait()
        super().closeEvent(event)

    def flush(self):
        pass
