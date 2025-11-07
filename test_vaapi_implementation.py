#!/usr/bin/env python3
"""
Test script for VA-API implementation
Run this inside Docker container to verify the implementation
"""

import sys
import os

# Add the plugin directory to path
sys.path.insert(0, '/app')

def test_hardware_detection():
    """Test hardware detection module"""
    print("=" * 60)
    print("Testing Hardware Detection Module")
    print("=" * 60)
    
    try:
        from octoprint_obico.hardware_detection import HardwareCapabilities
        
        hw = HardwareCapabilities()
        
        print("\n1. Platform Detection:")
        platform = hw.detect_platform()
        print(f"   Platform: {platform}")
        
        print("\n2. GPU Vendor Detection:")
        gpu_vendor = hw.detect_gpu_vendor()
        print(f"   GPU Vendor: {gpu_vendor if gpu_vendor else 'None detected'}")
        
        print("\n3. VA-API Support:")
        vaapi_supported = hw.has_vaapi_support()
        print(f"   VA-API Supported: {vaapi_supported}")
        
        print("\n4. VA-API Device:")
        vaapi_device = hw.get_vaapi_device()
        print(f"   VA-API Device: {vaapi_device if vaapi_device else 'Not found'}")
        
        print("\n5. Recommended Encoder:")
        recommended = hw.get_recommended_encoder()
        print(f"   Recommended: {recommended}")
        
        print("\n6. Full Capabilities Info:")
        capabilities = hw.get_capabilities_info()
        for key, value in capabilities.items():
            print(f"   {key}: {value}")
        
        print("\n✅ Hardware detection module working correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ Hardware detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_board_id():
    """Test updated board_id function"""
    print("\n" + "=" * 60)
    print("Testing board_id() Function")
    print("=" * 60)
    
    try:
        from octoprint_obico.utils import board_id
        
        board = board_id()
        print(f"\nBoard ID: {board}")
        print("Expected: One of 'rpi', 'intel', 'amd', 'nvidia', 'mks', or 'NA'")
        
        if board in ['rpi', 'intel', 'amd', 'nvidia', 'mks', 'NA']:
            print("✅ board_id() function working correctly")
            return True
        else:
            print(f"⚠️  Unexpected board_id value: {board}")
            return False
            
    except Exception as e:
        print(f"\n❌ board_id() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_encoder_detection():
    """Test encoder detection"""
    print("\n" + "=" * 60)
    print("Testing Encoder Detection")
    print("=" * 60)
    
    try:
        from octoprint_obico.webcam_stream import find_ffmpeg_h264_encoder
        
        print("\nAttempting to detect hardware encoder...")
        print("(This will test encoders and may take a few seconds)")
        
        encoder = find_ffmpeg_h264_encoder()
        
        if encoder:
            print(f"\n✅ Hardware encoder detected!")
            print(f"   Encoder flags: {encoder}")
        else:
            print("\n⚠️  No hardware encoder detected (will fallback to MJPEG)")
            print("   This is EXPECTED on systems without GPU/VA-API support")
            print("   On WSL or systems without GPU, this is normal behavior")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Encoder detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_environment_info():
    """Display environment information"""
    print("\n" + "=" * 60)
    print("Environment Information")
    print("=" * 60)
    
    # Check for /dev/dri
    print("\n1. DRM Devices:")
    if os.path.exists('/dev/dri'):
        try:
            devices = os.listdir('/dev/dri')
            print(f"   /dev/dri exists with devices: {devices}")
        except Exception as e:
            print(f"   /dev/dri exists but cannot list: {e}")
    else:
        print("   /dev/dri does NOT exist (no GPU/VA-API support)")
    
    # Check for lspci
    print("\n2. PCI Devices (lspci):")
    try:
        import subprocess
        result = subprocess.run(['lspci'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            # Filter for VGA/Display devices
            lines = [l for l in result.stdout.split('\n') if 'VGA' in l or 'Display' in l or '3D' in l]
            if lines:
                for line in lines:
                    print(f"   {line}")
            else:
                print("   No VGA/Display devices found")
        else:
            print("   lspci command failed")
    except FileNotFoundError:
        print("   lspci not available")
    except Exception as e:
        print(f"   lspci check failed: {e}")
    
    # Check for vainfo
    print("\n3. VA-API Info (vainfo):")
    try:
        import subprocess
        result = subprocess.run(['vainfo'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            # Show first few lines
            lines = result.stdout.split('\n')[:10]
            for line in lines:
                print(f"   {line}")
        else:
            print("   vainfo command failed (no VA-API support)")
    except FileNotFoundError:
        print("   vainfo not available (install with: apt-get install vainfo)")
    except Exception as e:
        print(f"   vainfo check failed: {e}")
    
    # Check FFmpeg encoders
    print("\n4. FFmpeg H.264 Encoders:")
    try:
        import subprocess
        result = subprocess.run(
            ['ffmpeg', '-encoders'], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        if result.returncode == 0:
            # Filter for h264 encoders
            lines = [l.strip() for l in result.stdout.split('\n') if 'h264' in l.lower()]
            if lines:
                for line in lines[:10]:  # Show first 10
                    print(f"   {line}")
            else:
                print("   No h264 encoders found")
        else:
            print("   ffmpeg command failed")
    except FileNotFoundError:
        print("   ffmpeg not available")
    except Exception as e:
        print(f"   ffmpeg check failed: {e}")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("VA-API Implementation Test Suite")
    print("Running inside Docker container")
    print("=" * 60)
    
    test_environment_info()
    
    results = []
    
    # Test hardware detection
    results.append(("Hardware Detection", test_hardware_detection()))
    
    # Test board_id
    results.append(("board_id() Function", test_board_id()))
    
    # Test encoder detection
    results.append(("Encoder Detection", test_encoder_detection()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✅ All tests passed!")
        print("\nNote: On WSL/systems without GPU:")
        print("  - Hardware detection should work")
        print("  - No encoder will be detected (expected)")
        print("  - System will fallback to MJPEG (expected)")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
