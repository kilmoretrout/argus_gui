from setuptools import setup
import os
import sys
#from distutils.core import setup # distutils no longer recommended

setup(
    name='argus_gui',
    version='2.2',
    packages=['argus_gui', 'argus_gui.resources'],
    scripts=[
        'argus_gui/resources/scripts/argus-dwarp', 
        'argus_gui/resources/scripts/argus-click', 
        'argus_gui/resources/scripts/Argus', 
        #'argus_gui/Argus.py',
        'argus_gui/resources/scripts/Argus_win.py', 
        'argus_gui/resources/scripts/argus-sync', 
        'argus_gui/resources/scripts/argus-patterns', 
        'argus_gui/resources/scripts/argus-calibrate', 
        'argus_gui/resources/scripts/argus-log', 
        'argus_gui/resources/scripts/argus-wand', 
        'argus_gui/resources/scripts/argus-show'],
    # dependencies
    install_requires=[
        "numpy >= 1.9.1",
        "pandas >= 0.15.2",
        "pyglet",
        "moviepy >= 0.2.2.11",
        "Pmw >= 1.3.3",
        "texttable >= 0.8.3",
        "sba >= 1.6.5.1",
        "audioread >= 2.1.1",
        "psutil >= 3.4.1",
        "argus >= 0.0.6",
        "pykalman",
        "future >= 0.16.0",
        "PyYAML >= 5.0",
        "pyside6 >= 6.4",
        "pyqtgraph >= 0.13.7",
        ],
    dependency_links=[
        #'http://opencv.org/downloads.html',
        'http://sourceforge.net/projects/opencvlibrary/files/opencv-unix/2.4.9/opencv-2.4.9.zip/download',
        # should add avconv or ffmpeg to this list depending
    ],
    package_data = {'argus_gui.resources':['*.*', 'scripts/*.*', 'icons/*.*','calibrations/*.*']},
    include_package_data = True,

    zip_safe = False,

    author='Dylan Ray and Dennis Evangelista',
    author_email='ddray1993@gmail.com',
    description='Tools for 3D camera calibration and reconstruction with graphical user interfaces',
    license = 'GNU GPLv3',
    keywords = 'calibration, camera, camera calibration, photogrammetry',
    url = 'http://argus.web.unc.edu',
    classifiers=['Development Status :: 3 - Alpha',
                 'Intended Audience :: Science/Research',
                 'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
                 'Operating System :: OS Independent',
                 'Operating System :: POSIX :: Linux',
                 'Programming Language :: Python :: 2.7',
                 'Topic :: Multimedia :: Graphics',
                 'Topic :: Multimedia :: Graphics :: 3D Modeling',
                 'Topic :: Multimedia :: Graphics :: Capture :: Digital Camera',
                 'Topic :: Multimedia :: Video',
                 'Topic :: Scientific/Engineering'],
)
    
if 'linux' in sys.platform:
    print("Copying SBA shared objects to /usr/local/lib/ \n")
    try:
        os.system("cp argus_gui/resources/libsba.so /usr/local/lib/libsba.so")
        os.system("cp argus_gui/resources/libsbaprojs.so /usr/local/lib/libsbaprojs.so")
    except:
        print("Install successful but could not copy SBA shared objects to /usr/local/lib.  Wand may not work...")
        sys.exit()
        
    print("Copy successful.  Install OK")

