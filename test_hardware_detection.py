#!/usr/bin/env python3
"""
Test script for hardware detection and encoder selection.
Run this to verify VA-API support is working correctly.
"""

import sys
import os
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')

# Add the plugin directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import just the hardware detection module directly
try:
    # Try direct import
    from octoprint_obico.hardware_detection import HardwareCapabilities
except ImportError:
    # If that fails, import the module file directly
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "hardware_detection", 
        os.path.join(os.path.dirname(__file__), "octoprint_obico", "hardware_detection.py")
    )
    hardware_detection = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hardware_detection)
    HardwareCapabilities = hardware_detection.HardwareCapabilities

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def main():
    print_section("OctoPrint-Obico Hardware Detection Test")
    
    hw_caps = HardwareCapabilities()
    
    # Test platform detection
    print_section("Platform Detection")
    platform = hw_caps.detect_platform()
    print(f"Detected Platform: {platform}")
    
    # Test GPU vendor detection
    print_section("GPU Vendor Detection")
    gpu_vendor = hw_caps.detect_gpu_vendor()
    if gpu_vendor:
        print(f"GPU Vendor: {gpu_vendor}")
    else:
        print("No GPU vendor detected (expected for RPi or systems without GPU)")
    
    # Test VA-API support
    print_section("VA-API Support Check")
    vaapi_device = hw_caps.get_vaapi_device()
    if vaapi_device:
        print(f"VA-API Device: {vaapi_device}")
        vaapi_supported = hw_caps.has_vaapi_support()
        print(f"VA-API Supported: {'✓ Yes' if vaapi_supported else '✗ No (device exists but driver check failed)'}")
    else:
        print("VA-API Device: Not found")
        print("VA-API Supported: ✗ No")
    
    # Get full capabilities info
    print_section("Full Hardware Capabilities")
    caps = hw_caps.get_capabilities_info()
    for key, value in caps.items():
        print(f"{key:25s}: {value}")
    
    # Recommended encoder
    print_section("Recommended Configuration")
    print(f"Recommended Encoder: {hw_caps.get_recommended_encoder()}")
    
    # Platform-specific advice
    print_section("Next Steps")
    if platform == 'rpi':
        print("✓ Raspberry Pi detected - hardware acceleration already supported!")
        print("  The plugin will use h264_omx or h264_v4l2m2m automatically.")
    elif platform in ['intel', 'amd']:
        if vaapi_device and hw_caps.has_vaapi_support():
            print(f"✓ {platform.upper()} GPU with VA-API detected!")
            print("  Hardware acceleration should work automatically.")
            print("  Check OctoPrint logs after restart to verify encoder detection.")
        else:
            print(f"⚠ {platform.upper()} GPU detected but VA-API not available.")
            print("  Install VA-API drivers:")
            if platform == 'intel':
                print("    sudo apt-get install intel-media-va-driver vainfo  # modern Intel")
                print("    sudo apt-get install i965-va-driver vainfo          # legacy Intel")
            else:
                print("    sudo apt-get install mesa-va-drivers vainfo")
            print("\n  See docs/VAAPI_SETUP.md for detailed instructions.")
    else:
        print("ℹ Generic platform detected (no GPU or unknown hardware)")
        print("  The plugin will fall back to software MJPEG streaming.")
        print("  This is expected for systems without compatible GPUs.")
    
    print_section("Test Complete")
    print()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n✗ Error during test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
