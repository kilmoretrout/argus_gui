"""
Entry point for running argus_gui as a module.
This allows the package to be run with: python -m argus_gui
"""

# Fix Qt platform plugin path for Windows - MUST be done before any Qt imports
import sys
import os
if sys.platform.startswith('win'):
    print("__main__.py: Setting up Windows Qt environment variables...")
    try:
        import PySide6
        pyside6_path = os.path.dirname(PySide6.__file__)
        
        # Try multiple possible plugin directory structures
        possible_plugin_paths = [
            os.path.join(pyside6_path, 'Qt6', 'plugins'),
            os.path.join(pyside6_path, 'Qt', 'plugins'),
            os.path.join(pyside6_path, 'plugins'),
            os.path.join(pyside6_path, '..', 'Library', 'plugins'),  # conda structure
            os.path.join(pyside6_path, '..', 'Lib', 'site-packages', 'PySide6', 'Qt6', 'plugins')  # pip structure
        ]
        
        qt_plugin_path = None
        for path in possible_plugin_paths:
            if os.path.exists(path):
                qt_plugin_path = path
                print(f"  Found Qt plugins at: {path}")
                break
        
        if qt_plugin_path:
            os.environ['QT_PLUGIN_PATH'] = qt_plugin_path
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_plugin_path
            print(f"  Set QT_PLUGIN_PATH to: {qt_plugin_path}")
            
            # Check if the windows platform plugin specifically exists
            windows_plugin = os.path.join(qt_plugin_path, 'platforms', 'qwindows.dll')
            if os.path.exists(windows_plugin):
                print(f"  ✓ Windows platform plugin found: {windows_plugin}")
            else:
                print(f"  ⚠ Windows platform plugin NOT found at: {windows_plugin}")
                # List what's actually in the platforms directory
                platforms_dir = os.path.join(qt_plugin_path, 'platforms')
                if os.path.exists(platforms_dir):
                    plugins_found = os.listdir(platforms_dir)
                    print(f"  Available platform plugins: {plugins_found}")
        else:
            print("  ⚠ Could not find Qt plugins directory in any expected location")
            
        # Additional Qt environment variables for Windows
        os.environ['QT_QPA_PLATFORM'] = 'windows'
        print("  Set QT_QPA_PLATFORM=windows")
        
    except Exception as e:
        print(f"  Qt plugin path setup error: {e}")

from argus_gui.Argus import main

if __name__ == "__main__":
    main()
