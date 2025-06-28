#!/usr/bin/env python
"""
Test script to verify OpenGL fallback functionality on Windows.
This script tests the same OpenGL configuration approach used in argus-click.
"""

import sys
import os

# Windows OpenGL compatibility settings - MUST be set before pyglet import
if sys.platform.startswith('win'):
    # Force software rendering if hardware acceleration is problematic
    os.environ['PYGLET_GL_DISABLE_MULTISAMPLING'] = '1'
    os.environ['PYGLET_GL_FALLBACK'] = '1'
    os.environ['PYGLET_SHADOW_WINDOW'] = '0'
    # Force OpenGL software rendering as fallback
    os.environ['MESA_GL_VERSION_OVERRIDE'] = '3.3'
    # Disable advanced OpenGL features that might not be supported
    os.environ['PYGLET_GL_DISABLE_WGL'] = '1'

try:
    import pyglet
    from pyglet.gl import Config
    print("Successfully imported pyglet")
except ImportError as e:
    print(f"Failed to import pyglet: {e}")
    sys.exit(1)

def test_opengl_configurations():
    """Test various OpenGL configurations to see which ones work."""
    
    configs_to_try = []
    
    if sys.platform.startswith('win'):
        print("Testing Windows OpenGL configurations...")
        
        # Try with multisampling first (if driver supports it)
        try:
            config_ms = Config(double_buffer=True)
            config_ms.sample_buffers = 1
            config_ms.samples = 4
            configs_to_try.append(("Multisampling 4x", config_ms))
        except Exception as e:
            print(f"Failed to create multisampling config: {e}")
        
        # Fallback: basic double buffering without multisampling
        try:
            config_basic = Config(double_buffer=True)
            configs_to_try.append(("Basic double buffer", config_basic))
        except Exception as e:
            print(f"Failed to create basic double buffer config: {e}")
        
        # Fallback: single buffer
        try:
            config_single = Config(double_buffer=False)
            configs_to_try.append(("Single buffer", config_single))
        except Exception as e:
            print(f"Failed to create single buffer config: {e}")
        
        # Software rendering fallback
        try:
            config_software = Config()
            config_software.double_buffer = False
            config_software.depth_size = 0
            config_software.stencil_size = 0
            config_software.aux_buffers = 0
            config_software.sample_buffers = 0
            config_software.samples = 0
            configs_to_try.append(("Software rendering", config_software))
        except Exception as e:
            print(f"Failed to create software config: {e}")
        
        # Minimal configuration
        try:
            config_minimal = Config()
            configs_to_try.append(("Minimal", config_minimal))
        except Exception as e:
            print(f"Failed to create minimal config: {e}")
        
        # None (let pyglet choose)
        configs_to_try.append(("Default (None)", None))
    
    else:
        # On macOS/Linux
        try:
            config = Config(double_buffer=True)
            configs_to_try.append(("Standard", config))
        except Exception as e:
            print(f"Failed to create standard config: {e}")
    
    print(f"Testing {len(configs_to_try)} configurations...")
    
    successful_configs = []
    
    for name, config in configs_to_try:
        try:
            print(f"Testing {name} configuration...")
            
            if config is None:
                window = pyglet.window.Window(
                    width=400, height=300,
                    visible=False,
                    resizable=True)
            else:
                window = pyglet.window.Window(
                    width=400, height=300,
                    visible=False,
                    resizable=True,
                    config=config)
            
            # Test basic OpenGL functionality
            window.switch_to()
            window.clear()
            window.close()
            
            print(f"✓ {name} configuration SUCCESSFUL")
            successful_configs.append(name)
            
        except Exception as e:
            print(f"✗ {name} configuration FAILED: {e}")
            if "wglChoosePixelFormatARB" in str(e):
                print("  → This is the specific error argus-click was encountering")
    
    return successful_configs

def main():
    print("OpenGL Fallback Test for argus-click")
    print("=" * 50)
    
    print(f"Platform: {sys.platform}")
    print(f"Python version: {sys.version}")
    
    try:
        print(f"Pyglet version: {pyglet.version}")
    except:
        print("Could not determine pyglet version")
    
    print()
    
    # Test configurations
    successful = test_opengl_configurations()
    
    print()
    print("RESULTS:")
    print("=" * 20)
    
    if successful:
        print(f"✓ {len(successful)} configuration(s) worked:")
        for config in successful:
            print(f"  - {config}")
        print()
        print("✓ argus-click should work with these fixes!")
    else:
        print("✗ No configurations worked.")
        print("This indicates a serious OpenGL driver issue.")
        print("Suggestions:")
        print("1. Update your graphics drivers")
        print("2. Install Mesa3D software renderer")
        print("3. Check Windows graphics settings")
    
    return len(successful) > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
