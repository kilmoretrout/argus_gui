from setuptools import setup
import os
import sys
#from distutils.core import setup # distutils no longer recommended

setup(
    name='argus_gui',
    version='3.0.0',
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
        "numpy >= 1.19.0",
        "pandas >= 1.0.0",
        "matplotlib >= 3.0.0",
        "opencv-python >= 4.0.0",
        "pyopengl",
        "pyglet >= 2.0.16, < 2.1",  # Pin to compatible version range
        "moviepy >= 1.0.0",
        "Pmw >= 1.3.3",
        "texttable >= 0.8.3",
        "sba @ git+https://github.com/backyardbiomech/python-sba.git@python310",
        "audioread >= 2.1.1",
        "psutil >= 5.0.0",
        "argus @ git+https://github.com/backyardbiomech/argus.git@python310",
        "pykalman",
        "future >= 0.16.0",
        "PyYAML >= 5.0",
        "pyside6 >= 6.4",
        "pyqtgraph >= 0.13.7",
        "imageio >= 2.0.0",
        "imageio-ffmpeg",
        ],
    # Note: dependency_links is deprecated, use modern dependency management
    # dependency_links=[
    #     'http://sourceforge.net/projects/opencvlibrary/files/opencv-unix/2.4.9/opencv-2.4.9.zip/download',
    # ],
    package_data = {'argus_gui.resources':['*.*', 'scripts/*.*', 'icons/*.*','calibrations/*.*']},
    include_package_data = True,
    
    # Add console script entry points
    entry_points={
        'console_scripts': [
            'argus-gui=argus_gui.Argus:main',
        ],
    },

    zip_safe = False,

    author='Dylan Ray and Dennis Evangelista',
    author_email='ddray1993@gmail.com',
    description='Tools for 3D camera calibration and reconstruction with graphical user interfaces',
    license = 'GNU GPLv3',
    keywords = 'calibration, camera, camera calibration, photogrammetry',
    url = 'http://argus.web.unc.edu',
    python_requires='>=3.10',
    classifiers=['Development Status :: 4 - Beta',
                 'Intended Audience :: Science/Research',
                 'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
                 'Operating System :: OS Independent',
                 'Operating System :: POSIX :: Linux',
                 'Operating System :: MacOS',
                 'Operating System :: Microsoft :: Windows',
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.10',
                 'Programming Language :: Python :: 3.11',
                 'Programming Language :: Python :: 3.12',
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
    except Exception as e:
        print(f"Install successful but could not copy SBA shared objects to /usr/local/lib: {e}")
        print("Wand may not work...")
        sys.exit()
        
    print("Copy successful.  Install OK")

