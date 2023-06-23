#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
logger.py - Takes a command, executes it, and displays its live stderr and stdout in a Qt window.
Has options for writing output to txt, and can be told of any temproary directory that the command
uses for proper cleanup.
"""

# from __future__ import absolute_import
# from __future__ import print_function

import sys
import subprocess
from PySide6.QtCore import QRunnable, QThreadPool, Signal, Slot
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QTextEdit
import time

class LogWindowTask(QRunnable):
    """
    run a command in its own thread
    """
    
    def __init__(self, cmd, logWindow):
        super().__init__()
        self.cmd = cmd
        self.logWindow = logWindow

    def run(self):
        startupinfo = None
        # if sys.platform == "win32" or sys.platform == "win64":  # Make it so subprocess brings up no console window
        #     # Set up the startupinfo to suppress the console window
        #     startupinfo = subprocess.STARTUPINFO()
        #     startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        # Start the process
        self.process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, text=True, startupinfo=startupinfo)

        while True:
            output = self.process.stdout.readline()
            if output == '' and self.process.poll() is not None:
                self.logWindow.onFinished()
                break
            if output:
                self.logWindow.onOutput(output.strip())

class Logger(QMainWindow):
    def __init__(self, cmd, tmp='', wLog=True, doneButton=True, parent=None):
        super().__init__(parent)
        self.cmd = cmd
        self.tmp = tmp
        self.wLog = wLog
        if self.wLog:
            self.fo = open("Log--" + time.strftime("%Y-%m-%d-%H-%M") + ".txt", "wb")
        else:
            self.fo = None
        self.initUI()
    
    def initUI(self):
        # Create a QPlainTextEdit to display the output
        self.logwindow = QTextEdit()
        self.logwindow.setReadOnly(True)
        font = self.logwindow.font()
        font.setFamily("Courier New")
        self.logwindow.setFont(font)
        self.setCentralWidget(self.logwindow)
        
        # Create a "cancel/done" button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.onCancel)
        self.statusBar().addPermanentWidget(self.cancel_button)
        self.id = None

        # Set the window titleand size
        self.setWindowTitle("Argus ouput")
        self.resize(600, 600)

        self.logTask = LogWindowTask(self.cmd, self)
        # self.logTask.output.connect(self.onOutput)
        # self.logTask.finished.connect(self.onFinished)
        QThreadPool.globalInstance().start(self.logTask)
        
    @Slot()
    def onOutput(self, text):
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
            self.logwindow.append(text)
            
            if self.fo:
                text = "\n" + text
                self.fo.write(text.encode('utf-8'))

            # self.linecount += 1

    # def guifinished(self, returncode):
    #     self.append_output(f"\nProcess finished with exit code {returncode}")
    #     self.cancel_button.setText("Done")
    
    @Slot()
    def onCancel(self):
        print('canceled')
        self.onOutput('Process cancelled by user')
        QThreadPool.globalInstance().clear()
        QThreadPool.globalInstance().waitForDone()
        QApplication.processEvents()
        self.cancel_button.setText('Done')
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.close)
        
    @Slot()
    def onFinished(self):
        print('finished')
        self.onOutput('Process completed!')
        QApplication.processEvents()
        self.cancel_button.setText('Done')
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.close)
        if self.wLog:
            self.fo.close()
        
    # def closeEvent(self, event):
    #     print('closing')
    #     if self.tmp != '':
    #         if os.path.isdir(self.tmp):
    #             shutil.rmtree(self.tmp)
    #     if self.wLog:
    #         self.fo.close()

    #     if self.worker.process:
    #         self.worker.cancel()
    #         self.worker.kill()
    #         self.worker_thread.wait()
            
        # super().closeEvent(event)
