#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
logger.py - Takes a command, executes it, and displays its live stderr and stdout in a Tkinter window.
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
from six.moves.queue import Queue
from six.moves.tkinter import *

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
        self.worker.finished.connect(self.finished)
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


    def finished(self, returncode):
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

    def finished(self, returncode):
        if returncode is not None:
            self.append_output(f"\nProcess finished with exit code {returncode}")
            self.cancel_button.setText("Done")

class LoggerTK(Tk):
    def __init__(self, cmd, tmp='', wLog=False, doneButton=True):
        print('Changing stuff...')
        Tk.__init__(self)
        self.cmd = cmd
        self.tmp = tmp
        self.wLog = wLog
        self.doneButton = doneButton
        # create a done button and connect the close window command to its command to ensure cleanup
        self.dButton = Button(self, text='Cancel', command=self.wereDoneHere)
        self.q = Queue()
        self.id = None

        scrollbar = Scrollbar(self, width=20)
        scrollbar.pack(side=RIGHT, fill=Y, padx=10, pady=10)
        self.log = Text(self, yscrollcommand=scrollbar.set, bg="black", fg="green")
        scrollbar.config(command=self.log.yview)
        self.t = ThreadCommand(self.q, command=self.cmd)

        # start thread that will wait for data
        self.t.daemon = True
        self.t.start()

        # make text updater class which is called every 100 ms to make sure everything can be seen in the log
        self.T = TextUpdater(self.t, self.q, self, self.log, self.wLog)

    # Kill everything, if were done that is
    def wereDoneHere(self):
        self.t.kill()
        if self.tmp != '':
            if os.path.isdir(self.tmp):
                shutil.rmtree(self.tmp)
        if self.wLog:
            self.T.fo.close()
        self.cancel()
        self.destroy()

    def cancel(self):
        if self.id is not None:
            print('Canceling...')
            self.after_cancel(self.id)

    # if the subprocess is done, change the label of the exit button from 'cancel' to 'done'
    def checkButton(self):
        if self.t.getStatus() is not None:
            self.dButton.configure(text='Done')
            self.update_idletasks()
            self.t.timeToChill = True
        else:
            try:
                self.id = self.after(100, self.checkButton)
            except:
                pass

    # start the subprocess and begin monitoring its stdout
    def start(self):
        self.resizable(width=FALSE, height=FALSE)
        self.wm_title('Log')

        # pack the log and tell the user where we're writing the log file if it's being written
        self.log.pack()
        if self.wLog:
            self.log.insert(END, 'Writing log file to: ' + os.getcwd() + '\n')

        self.log.insert(END, 'Build info: \n' + platform.platform() + " " + platform.machine() + '\n')

        if self.doneButton:
            self.dButton.pack()
        self.protocol('WM_DELETE_WINDOW', self.wereDoneHere)
        self.update_idletasks()
        self.after(100, self.T.update_text)
        self.after(100, self.checkButton)
        self.mainloop()


class ThreadCommand(threading.Thread):
    """
    run a command in its own thread
    """

    def __init__(self, queue, fetchfn=None, command=None):
        threading.Thread.__init__(self)
        self.queue = queue
        self.command = command
        self.fetchfn = self.read_buffer
        self.running = False
        self.proc = None
        self.timeToChill = False

    # read the stdout one character at a time
    def read_buffer(self, master):
        last_part = b""
        nl = re.compile(b'(\n)')
        while self.running:
            s = last_part
            try:
                s += os.read(master, 1)
                s = s.replace(b'\r', b'')  # \r shows up as music notes in tk (at least on linux)
                lines = nl.split(s)
                last_part = lines[-1]
                if not last_part:
                    data = b''.join(lines)
                else:
                    data = b''.join(lines[:-1])
                yield (True, data)
            except Exception as e:
                yield (False, b'')
                traceback.print_exc()
            if self.timeToChill:
                time.sleep(0.01)

    def getStatus(self):
        if self.proc is not None:
            return self.proc.poll()

    def run(self):
        self.running = True
        startupinfo = None
        if sys.platform == "win32" or sys.platform == "win64":  # Make it so subprocess brings up no console window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        # Start the process
        self.proc = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False,
                                     startupinfo=startupinfo)
        # Start getting data from the pipe and putting each line in a queue
        more_data = True
        for more_data, lines in self.fetchfn(self.proc.stdout.fileno()):
            if lines:
                # send the received data into the queue
                self.queue.put(lines)
            if not more_data:
                # time to close ourselves down
                print('We closed')
                self.running = False
                break

    def kill(self):
        try:
            self.proc.kill()
        except:
            print('Could not kill!')
            pass
        self.running = False
        return


# these classes were pulled from the internet under MIT license and modified to make them Windows friendly and freezable
class TextUpdater(object):
    def __init__(self, the_thread, the_queue, root, textwidget, wLog):
        self.the_thread = the_thread
        self.the_queue = the_queue
        self.textwidget = textwidget
        self.root = root
        if wLog:
            self.fo = open("Log--" + time.strftime("%Y-%m-%d-%H-%M") + ".txt", "wb")
        else:
            self.fo = None
        self.linecount = 0

    def update_text(self):
        while self.the_thread.running:
            # Argus specific stuff we don't want to show
            bad_phrases = ['iters', 'it/s', 'InsecureRequestWarning', 'axes3d.py', 'Python', '_createMenuRef', '0x',
                           'ApplePersistenceIgnoreState', 'self._edgecolors', 'objc', 'warnings.warn', 'UserWarning']
            try:
                self.root.update()
            except:
                pass
            try:
                # try to get data from the queue and write it to the text widget
                line = self.the_queue.get(timeout=0.2)
                # Delete line with bad phrase as they pop up
                for phrase in bad_phrases:
                    if phrase in line.encode('utf-8'):
                        self.textwidget.delete(str(self.linecount), str(self.linecount + 1))

                self.textwidget.insert(END, line.decode('utf-8'))
                if self.fo:
                    self.fo.write(line.decode('utf-8'))
                self.linecount += 1
                self.textwidget.see(END)
                self.textwidget.update_idletasks()
                self.root.update()
            except:
                pass
