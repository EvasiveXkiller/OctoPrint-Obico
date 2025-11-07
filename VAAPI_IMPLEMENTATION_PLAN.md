# VA-API Hardware Acceleration Implementation Plan
## OctoPrint-Obico Plugin Enhancement

**Created:** October 31, 2025  
**Target:** Add Intel/AMD VA-API hardware acceleration support for H.264 encoding

---

## 1. Executive Summary

This plan outlines the implementation of VA-API (Video Acceleration API) support for the OctoPrint-Obico plugin, enabling hardware-accelerated H.264 video encoding on Intel and AMD GPUs. This will significantly reduce CPU usage and improve streaming performance on x86/x64 systems.

### Current State
- **Supported:** Raspberry Pi hardware encoders only (`h264_omx`, `h264_v4l2m2m`)
- **Platform:** ARM-based Raspberry Pi devices
- **Fallback:** Software MJPEG streaming (no GPU acceleration)

### Proposed State
- **Add Support For:** Intel Quick Sync Video, AMD VCE/VCN via VA-API
- **Platform:** x86/x64 Linux systems with Intel/AMD GPUs
- **Compatibility:** Maintains backward compatibility with existing Raspberry Pi support

---

## 2. Technical Architecture Overview

### 2.1 Current Encoder Detection Flow
```
find_ffmpeg_h264_encoder()
├── Test h264_omx (Raspberry Pi OMX)
├── Test h264_v4l2m2m (Raspberry Pi V4L2)
├── Return encoder flags if successful
└── Return None (fallback to MJPEG)
```

### 2.2 Proposed Enhanced Flow
```
find_ffmpeg_h264_encoder()
├── Detect hardware platform (board_id)
│   ├── Raspberry Pi → Test h264_omx, h264_v4l2m2m
│   └── x86/x64 → Test h264_vaapi, h264_qsv
├── Test each encoder with actual video
├── Return encoder configuration with flags
└── Return None (fallback to MJPEG)
```

---

## 3. Implementation Components

### 3.1 Core Files to Modify

#### **A. `octoprint_obico/webcam_stream.py`**
**Location:** Lines 81-98  
**Function:** `find_ffmpeg_h264_encoder()`

**Changes Required:**
1. Expand encoder list to include VA-API variants
2. Add platform detection logic
3. Implement encoder-specific FFmpeg flags
4. Add VA-API device detection (`/dev/dri/renderD128`)
5. Enhanced error handling and logging

**New Encoder Tests:**
- `h264_vaapi` - VA-API encoder (Intel/AMD)
- `h264_qsv` - Intel Quick Sync (optional, uses VA-API backend)

#### **B. `octoprint_obico/utils.py`**
**Location:** Lines 363-375  
**Function:** `board_id()`

**Changes Required:**
1. Extend `board_id()` to detect x86/x64 platforms
2. Add GPU vendor detection (Intel/AMD)
3. Create helper function `detect_vaapi_support()`
4. Add function `get_gpu_info()`

#### **C. `octoprint_obico/bin/utils.sh`**
**Location:** Lines 12-24  
**Function:** `board_id()`

**Changes Required:**
1. Add x86/x64 detection logic
2. Add GPU vendor detection via `lspci` or `/sys/class/drm`
3. Return identifiers: `intel`, `amd`, `nvidia`, or `generic`

### 3.2 New Files to Create

#### **A. `octoprint_obico/hardware_detection.py`** (New)
**Purpose:** Centralized hardware detection and capabilities

```python
class HardwareCapabilities:
    - detect_platform()
    - detect_gpu_vendor()
    - has_vaapi_support()
    - has_drm_device()
    - get_vaapi_device_path()
    - get_recommended_encoder()
```

#### **B. `docs/VAAPI_SETUP.md`** (New)
**Purpose:** User documentation for VA-API setup and troubleshooting

---

## 4. Detailed Implementation Steps

### Phase 1: Hardware Detection (Week 1)

#### Step 1.1: Create Hardware Detection Module
- [ ] Create `octoprint_obico/hardware_detection.py`
- [ ] Implement platform detection (ARM vs x86/x64)
- [ ] Implement GPU vendor detection
- [ ] Add VA-API capability checking
- [ ] Unit tests for detection logic

**Key Functions:**
```python
def detect_platform() -> str:
    """Returns: 'rpi', 'intel', 'amd', 'nvidia', 'generic'"""
    
def detect_vaapi_support() -> bool:
    """Check for /dev/dri/renderD* devices"""
    
def get_vaapi_device() -> Optional[str]:
    """Returns: '/dev/dri/renderD128' or None"""
```

#### Step 1.2: Update Existing Detection Code
- [ ] Modify `utils.py::board_id()` to use new detection
- [ ] Update `bin/utils.sh::board_id()` for shell scripts
- [ ] Add fallback for systems without GPU

### Phase 2: Encoder Detection (Week 1-2)

#### Step 2.1: Expand Encoder Testing
- [ ] Modify `find_ffmpeg_h264_encoder()` in `webcam_stream.py`
- [ ] Add encoder priority list per platform
- [ ] Implement platform-specific encoder flags
- [ ] Add VA-API initialization parameters

**Encoder Priority by Platform:**
```python
ENCODER_PRIORITY = {
    'intel': ['h264_qsv', 'h264_vaapi'],
    'amd': ['h264_vaapi'],
    'rpi': ['h264_omx', 'h264_v4l2m2m'],
    'generic': ['h264_vaapi']  # Try anyway
}
```

**VA-API FFmpeg Flags:**
```python
# h264_vaapi encoder configuration
'-vaapi_device /dev/dri/renderD128 -vf format=nv12,hwupload -c:v h264_vaapi'

# Optional QSV configuration (uses VA-API backend)
'-init_hw_device qsv=hw -filter_hw_device hw -vf hwupload=extra_hw_frames=64 -c:v h264_qsv'
```

#### Step 2.2: Enhanced Error Handling
- [ ] Detailed logging for encoder test failures
- [ ] Specific error messages for missing drivers
- [ ] Fallback chain: VA-API → Software MJPEG
- [ ] Performance metrics logging

### Phase 3: Integration & Testing (Week 2)

#### Step 3.1: Update Streaming Pipeline
- [ ] Modify `h264_transcode()` to handle VA-API parameters
- [ ] Update `start_ffmpeg()` to pass device-specific flags
- [ ] Add VA-API device path to webcam streaming params
- [ ] Test with various resolutions and FPS settings

#### Step 3.2: Docker Development Environment
- [ ] Update `Dockerfile.python3` with VA-API dependencies
- [ ] Add GPU passthrough configuration to `docker-compose.yml`
- [ ] Create test environment with Intel/AMD GPU simulation
- [ ] Add VA-API drivers to Docker images

**Docker Changes Required:**
```dockerfile
# In Dockerfile.python3
RUN apt-get update && apt-get install -y \
    intel-media-va-driver \
    i965-va-driver \
    mesa-va-drivers \
    vainfo \
    && rm -rf /var/lib/apt/lists/*
```

```yaml
# In docker-compose.yml
services:
  op:
    devices:
      - /dev/dri:/dev/dri  # GPU passthrough
    environment:
      LIBVA_DRIVER_NAME: iHD  # or i965 for older Intel
```

### Phase 4: Documentation (Week 2-3)

#### Step 4.1: User Documentation
- [ ] Create `docs/VAAPI_SETUP.md` with setup instructions
- [ ] Add system requirements section
- [ ] Document driver installation per distro
- [ ] Add troubleshooting guide
- [ ] Create FAQ section

#### Step 4.2: Developer Documentation
- [ ] Update `README.md` with hardware requirements
- [ ] Document new functions in code comments
- [ ] Add architecture diagrams
- [ ] Update development setup instructions

#### Step 4.3: In-Plugin Help
- [ ] Add hardware detection status to settings UI
- [ ] Show detected encoder in troubleshooting section
- [ ] Display GPU info in diagnostic logs
- [ ] Add warning messages for missing drivers

### Phase 5: Testing & Validation (Week 3)

#### Step 5.1: Unit Tests
- [ ] Test hardware detection on various systems
- [ ] Test encoder selection logic
- [ ] Mock FFmpeg subprocess calls
- [ ] Test fallback mechanisms

#### Step 5.2: Integration Tests
- [ ] Test on Intel GPU system (if available)
- [ ] Test on AMD GPU system (if available)
- [ ] Test backward compatibility on Raspberry Pi
- [ ] Test fallback to MJPEG on unsupported hardware

#### Step 5.3: Performance Testing
- [ ] Measure CPU usage: VA-API vs Software
- [ ] Measure encoding latency
- [ ] Test various resolutions (480p, 720p, 1080p)
- [ ] Test various FPS settings (5, 15, 25, 30)
- [ ] Compare quality at same bitrate

---

## 5. Code Implementation Details

### 5.1 Enhanced `find_ffmpeg_h264_encoder()` Function

**File:** `octoprint_obico/webcam_stream.py`

```python
def find_ffmpeg_h264_encoder():
    """
    Detect available hardware H.264 encoders based on platform.
    
    Priority:
    1. Platform-specific hardware encoders (RPi, Intel, AMD)
    2. Generic VA-API (if available)
    3. None (falls back to MJPEG)
    
    Returns:
        str: FFmpeg encoder flags or None
    """
    from .hardware_detection import HardwareCapabilities
    
    test_video = os.path.join(FFMPEG_DIR, 'test-video.mp4')
    FNULL = open(os.devnull, 'w')
    
    hw_caps = HardwareCapabilities()
    platform = hw_caps.detect_platform()
    
    # Define encoder configurations per platform
    ENCODER_CONFIGS = {
        'rpi': [
            ('h264_omx', '-flags:v +global_header -c:v h264_omx -bsf dump_extra'),
            ('h264_v4l2m2m', '-c:v h264_v4l2m2m'),
        ],
        'intel': [
            ('h264_vaapi', '-vaapi_device /dev/dri/renderD128 -vf format=nv12,hwupload -c:v h264_vaapi'),
            ('h264_qsv', '-init_hw_device qsv=hw -filter_hw_device hw -vf hwupload=extra_hw_frames=64,format=qsv -c:v h264_qsv'),
        ],
        'amd': [
            ('h264_vaapi', '-vaapi_device /dev/dri/renderD128 -vf format=nv12,hwupload -c:v h264_vaapi'),
        ],
        'generic': [
            ('h264_vaapi', '-vaapi_device /dev/dri/renderD128 -vf format=nv12,hwupload -c:v h264_vaapi'),
        ]
    }
    
    encoders_to_test = ENCODER_CONFIGS.get(platform, [])
    
    # Test each encoder
    for encoder_name, encoder_flags in encoders_to_test:
        try:
            _logger.info(f'Testing {encoder_name} encoder for platform: {platform}')
            
            # Build test command
            ffmpeg_cmd = f'{FFMPEG} -re -i {test_video} -t 2 {encoder_flags} -an -f null -'
            
            _logger.debug(f'Popen: {ffmpeg_cmd}')
            ffmpeg_test_proc = subprocess.Popen(
                ffmpeg_cmd.split(' '), 
                stdout=FNULL, 
                stderr=subprocess.PIPE
            )
            
            returncode = ffmpeg_test_proc.wait(timeout=10)
            
            if returncode == 0:
                _logger.info(f'Successfully detected {encoder_name} encoder')
                return encoder_flags
            else:
                stderr = ffmpeg_test_proc.stderr.read().decode('utf-8', errors='ignore')
                _logger.debug(f'{encoder_name} test failed with code {returncode}: {stderr[:200]}')
                
        except subprocess.TimeoutExpired:
            _logger.warning(f'{encoder_name} test timed out')
            ffmpeg_test_proc.kill()
        except Exception as e:
            _logger.debug(f'Failed to test {encoder_name}: {str(e)}')
    
    _logger.warn(f'No hardware H.264 encoder found for platform: {platform}. Falling back to MJPEG.')
    return None
```

### 5.2 New Hardware Detection Module

**File:** `octoprint_obico/hardware_detection.py` (NEW)

```python
# coding=utf-8
"""
Hardware detection and capability checking for OctoPrint-Obico.
Detects platform, GPU vendor, and available hardware acceleration.
"""

import os
import re
import subprocess
import logging
from typing import Optional, Dict, List

_logger = logging.getLogger('octoprint.plugins.obico.hardware')


class HardwareCapabilities:
    """Detect and query hardware capabilities for video encoding."""
    
    def __init__(self):
        self._platform = None
        self._gpu_vendor = None
        self._vaapi_device = None
        self._capabilities_checked = False
    
    def detect_platform(self) -> str:
        """
        Detect the hardware platform.
        
        Returns:
            str: 'rpi', 'intel', 'amd', 'nvidia', or 'generic'
        """
        if self._platform:
            return self._platform
        
        # Check for Raspberry Pi
        if self._is_raspberry_pi():
            self._platform = 'rpi'
            return self._platform
        
        # Check for x86/x64 with GPU
        gpu_vendor = self.detect_gpu_vendor()
        if gpu_vendor:
            self._platform = gpu_vendor
        else:
            self._platform = 'generic'
        
        _logger.info(f'Detected platform: {self._platform}')
        return self._platform
    
    def detect_gpu_vendor(self) -> Optional[str]:
        """
        Detect GPU vendor on x86/x64 systems.
        
        Returns:
            str: 'intel', 'amd', 'nvidia', or None
        """
        if self._gpu_vendor:
            return self._gpu_vendor
        
        try:
            # Try lspci first
            result = subprocess.run(
                ['lspci'], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if result.returncode == 0:
                output = result.stdout.lower()
                
                if 'intel' in output and 'vga' in output:
                    self._gpu_vendor = 'intel'
                elif 'amd' in output or 'ati' in output:
                    if 'vga' in output or 'display' in output:
                        self._gpu_vendor = 'amd'
                elif 'nvidia' in output and 'vga' in output:
                    self._gpu_vendor = 'nvidia'
            
            # Fallback: check /sys/class/drm
            if not self._gpu_vendor:
                self._gpu_vendor = self._detect_gpu_from_drm()
            
        except Exception as e:
            _logger.debug(f'Failed to detect GPU vendor: {e}')
        
        _logger.info(f'Detected GPU vendor: {self._gpu_vendor}')
        return self._gpu_vendor
    
    def has_vaapi_support(self) -> bool:
        """
        Check if VA-API is available on the system.
        
        Returns:
            bool: True if VA-API devices are present
        """
        vaapi_device = self.get_vaapi_device()
        if not vaapi_device:
            return False
        
        # Try to run vainfo if available
        try:
            result = subprocess.run(
                ['vainfo', '--display', 'drm', '--device', vaapi_device],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                _logger.debug(f'VA-API supported. vainfo output: {result.stdout[:200]}')
                return True
            else:
                _logger.debug(f'VA-API check failed: {result.stderr[:200]}')
                
        except FileNotFoundError:
            _logger.debug('vainfo command not found, assuming VA-API may still work')
            return True  # Device exists, assume it works
        except Exception as e:
            _logger.debug(f'VA-API check error: {e}')
        
        return False
    
    def get_vaapi_device(self) -> Optional[str]:
        """
        Get the VA-API device path.
        
        Returns:
            str: Path like '/dev/dri/renderD128' or None
        """
        if self._vaapi_device:
            return self._vaapi_device
        
        # Check for DRM render devices
        drm_dir = '/dev/dri'
        if not os.path.exists(drm_dir):
            return None
        
        # Look for renderD* devices
        try:
            devices = os.listdir(drm_dir)
            render_devices = [d for d in devices if d.startswith('renderD')]
            
            if render_devices:
                # Use the first render device (usually renderD128)
                render_devices.sort()
                self._vaapi_device = os.path.join(drm_dir, render_devices[0])
                _logger.debug(f'Found VA-API device: {self._vaapi_device}')
                return self._vaapi_device
                
        except Exception as e:
            _logger.debug(f'Error checking DRM devices: {e}')
        
        return None
    
    def get_capabilities_info(self) -> Dict:
        """
        Get comprehensive hardware capabilities info.
        
        Returns:
            dict: Hardware capabilities and status
        """
        return {
            'platform': self.detect_platform(),
            'gpu_vendor': self.detect_gpu_vendor(),
            'vaapi_supported': self.has_vaapi_support(),
            'vaapi_device': self.get_vaapi_device(),
            'recommended_encoder': self.get_recommended_encoder(),
        }
    
    def get_recommended_encoder(self) -> Optional[str]:
        """
        Get the recommended encoder for this hardware.
        
        Returns:
            str: Encoder name or None
        """
        platform = self.detect_platform()
        
        RECOMMENDATIONS = {
            'intel': 'h264_vaapi or h264_qsv',
            'amd': 'h264_vaapi',
            'rpi': 'h264_omx or h264_v4l2m2m',
            'generic': 'h264_vaapi (if available)',
        }
        
        return RECOMMENDATIONS.get(platform, 'None available')
    
    # Private helper methods
    
    def _is_raspberry_pi(self) -> bool:
        """Check if running on Raspberry Pi."""
        try:
            with open('/sys/firmware/devicetree/base/model', 'r') as f:
                model = f.read()
                return 'Raspberry Pi' in model
        except:
            return False
    
    def _detect_gpu_from_drm(self) -> Optional[str]:
        """Detect GPU vendor from /sys/class/drm."""
        try:
            drm_path = '/sys/class/drm'
            if not os.path.exists(drm_path):
                return None
            
            for card in os.listdir(drm_path):
                if not card.startswith('card'):
                    continue
                
                device_path = os.path.join(drm_path, card, 'device', 'vendor')
                if not os.path.exists(device_path):
                    continue
                
                with open(device_path, 'r') as f:
                    vendor_id = f.read().strip()
                
                # PCI vendor IDs
                if vendor_id == '0x8086':
                    return 'intel'
                elif vendor_id in ['0x1002', '0x1022']:
                    return 'amd'
                elif vendor_id == '0x10de':
                    return 'nvidia'
        
        except Exception as e:
            _logger.debug(f'Failed to detect GPU from DRM: {e}')
        
        return None
```

### 5.3 Updated `board_id()` Function

**File:** `octoprint_obico/utils.py` (Lines ~363-375)

```python
def board_id():
    """
    Detect the board/platform identifier.
    
    Returns:
        str: 'rpi', 'intel', 'amd', 'mks', 'nvidia', or 'NA'
    """
    model_file = "/sys/firmware/devicetree/base/model"
    
    # Check ARM boards first
    if os.path.isfile(model_file):
        with open(model_file, 'r') as file:
            data = file.read()
            if "raspberry" in data.lower():
                return "rpi"
            elif "makerbase" in data.lower() or "roc-rk3328-cc" in data:
                return "mks"
    
    # Check for x86/x64 GPU
    try:
        from .hardware_detection import HardwareCapabilities
        hw_caps = HardwareCapabilities()
        gpu_vendor = hw_caps.detect_gpu_vendor()
        if gpu_vendor:
            return gpu_vendor
    except Exception:
        pass
    
    return "NA"
```

---

## 6. Dependencies & Requirements

### 6.1 System Requirements

**For VA-API Support (Intel/AMD):**
- Linux operating system
- Intel GPU (HD Graphics 2000+) OR AMD GPU (with AMDGPU driver)
- Mesa 20.0+ or proprietary drivers
- FFmpeg with VA-API support enabled

**Driver Requirements by Platform:**

| Platform | Driver Package | Notes |
|----------|---------------|-------|
| Intel (Broadwell+) | `intel-media-va-driver` | Recommended for newer GPUs (Gen 8+) |
| Intel (Legacy) | `i965-va-driver` | For Gen 5-7 GPUs |
| AMD | `mesa-va-drivers` | Open source AMDGPU driver |
| Generic | `libva2`, `libva-drm2` | Base VA-API libraries |

### 6.2 Python Dependencies

No new Python packages required. Uses existing:
- `subprocess` (standard library)
- `os` (standard library)
- `distro` (already required)

### 6.3 FFmpeg Requirements

**Minimum FFmpeg Version:** 4.0+  
**Required Codecs:** `h264_vaapi` encoder support

**Verify FFmpeg Support:**
```bash
ffmpeg -encoders | grep vaapi
# Should show: h264_vaapi
```

**Install FFmpeg with VA-API:**
```bash
# Debian/Ubuntu
sudo apt-get install ffmpeg libva-drm2

# Arch Linux
sudo pacman -S ffmpeg libva-mesa-driver

# Fedora
sudo dnf install ffmpeg libva
```

---

## 7. User Experience Improvements

### 7.1 Settings UI Enhancements

**Add Hardware Detection Panel to Settings:**

Location: `octoprint_obico/templates/obico_settings.jinja2`

```html
<section class="obico-settings-page__section">
  <h1 class="obico-settings-page__section-title">Hardware Acceleration</h1>
  <div class="obico-settings-page__section-content">
    <table class="table table-condensed">
      <tr>
        <td><strong>Platform:</strong></td>
        <td data-bind="text: hardwareInfo.platform"></td>
      </tr>
      <tr>
        <td><strong>GPU Vendor:</strong></td>
        <td data-bind="text: hardwareInfo.gpu_vendor || 'None detected'"></td>
      </tr>
      <tr>
        <td><strong>Hardware Encoder:</strong></td>
        <td data-bind="text: hardwareInfo.encoder || 'Software (MJPEG)'"></td>
      </tr>
      <tr>
        <td><strong>VA-API Support:</strong></td>
        <td>
          <span data-bind="visible: hardwareInfo.vaapi_supported">
            <i class="fa fa-check text-success"></i> Available
          </span>
          <span data-bind="visible: !hardwareInfo.vaapi_supported">
            <i class="fa fa-times text-error"></i> Not available
          </span>
        </td>
      </tr>
    </table>
    <div class="alert alert-info" data-bind="visible: hardwareInfo.platform === 'generic'">
      <strong>Tip:</strong> Install VA-API drivers to enable hardware acceleration on Intel/AMD systems.
      <a href="https://obico.io/docs/vaapi-setup" target="_blank">Learn more</a>
    </div>
  </div>
</section>
```

### 7.2 Troubleshooting Enhancements

**Add Encoder Diagnostics:**
- Show detected hardware in troubleshooting page
- Display FFmpeg encoder test results
- Provide driver installation instructions
- Link to hardware-specific documentation

### 7.3 Logging Improvements

**Enhanced Debug Logging:**
```python
_logger.info('Hardware Detection:')
_logger.info(f'  Platform: {platform}')
_logger.info(f'  GPU Vendor: {gpu_vendor}')
_logger.info(f'  VA-API Device: {vaapi_device}')
_logger.info(f'  Selected Encoder: {encoder}')
```

---

## 8. Testing Strategy

### 8.1 Test Matrix

| Platform | GPU | Driver | Expected Encoder | Test Status |
|----------|-----|--------|------------------|-------------|
| Raspberry Pi 4 | VideoCore VI | V4L2 | h264_v4l2m2m | ✅ Existing |
| Raspberry Pi 3 | VideoCore IV | OMX | h264_omx | ✅ Existing |
| Intel NUC | HD Graphics 630 | intel-media-va-driver | h264_vaapi | 🔲 New |
| AMD Ryzen | Vega iGPU | mesa-va-drivers | h264_vaapi | 🔲 New |
| Generic x86 | No GPU | N/A | MJPEG fallback | 🔲 New |
| Docker | GPU Passthrough | Host drivers | h264_vaapi | 🔲 New |

### 8.2 Test Scenarios

#### Functional Tests
- [ ] Encoder detection on each platform
- [ ] Successful H.264 encoding with VA-API
- [ ] Fallback to MJPEG when no hardware available
- [ ] Backward compatibility with Raspberry Pi
- [ ] Multiple webcam support with VA-API

#### Performance Tests
- [ ] CPU usage comparison: VA-API vs Software
- [ ] Memory usage during encoding
- [ ] Streaming latency measurements
- [ ] Quality comparison at various bitrates
- [ ] Stability over extended periods (24+ hours)

#### Error Handling Tests
- [ ] Missing VA-API drivers
- [ ] Missing /dev/dri/renderD* device
- [ ] FFmpeg without VA-API support
- [ ] GPU device busy/in use
- [ ] Permission denied on /dev/dri

#### Edge Cases
- [ ] System with multiple GPUs
- [ ] Headless server configuration
- [ ] Hybrid graphics (Intel + NVIDIA)
- [ ] Docker container with GPU passthrough
- [ ] User without video group membership

### 8.3 Manual Testing Checklist

**Pre-Implementation:**
- [ ] Document current baseline performance (CPU %, FPS, quality)
- [ ] Take screenshots of current settings UI
- [ ] Record typical use case videos

**Post-Implementation:**
- [ ] Verify encoder detection logic
- [ ] Test all supported resolutions (480p, 720p, 1080p)
- [ ] Test all FPS settings (5, 15, 25, 30)
- [ ] Verify settings UI shows correct hardware info
- [ ] Check troubleshooting page displays useful info
- [ ] Confirm logs contain helpful debug information

**Regression Testing:**
- [ ] Test on Raspberry Pi (no regression)
- [ ] Verify existing MJPEG fallback works
- [ ] Ensure OctoPrint plugin still loads correctly
- [ ] Check no performance degradation on RPi

---

## 9. Documentation Requirements

### 9.1 User Documentation

#### **A. Installation Guide** (`docs/VAAPI_SETUP.md`)
- System requirements
- Driver installation per Linux distro
- FFmpeg installation/verification
- Permissions setup (`/dev/dri` access)
- Troubleshooting common issues

#### **B. Performance Guide**
- Expected CPU usage reduction
- Quality vs performance trade-offs
- Resolution and FPS recommendations
- Bandwidth considerations

#### **C. Troubleshooting Guide**
- "Hardware encoder not detected"
- "Permission denied on /dev/dri"
- "FFmpeg test failed"
- "Streaming still uses high CPU"
- VA-API driver conflicts

### 9.2 Developer Documentation

#### **A. Architecture Documentation**
- Hardware detection flow diagram
- Encoder selection decision tree
- FFmpeg command construction
- Integration points with existing code

#### **B. API Documentation**
- `HardwareCapabilities` class methods
- `find_ffmpeg_h264_encoder()` function
- Configuration data structures
- Extension points for future encoders

#### **C. Testing Documentation**
- How to run tests locally
- How to test with different GPUs
- Docker testing setup
- Performance benchmarking tools

### 9.3 In-Code Documentation

**Required for all new/modified functions:**
- Function docstrings with examples
- Parameter descriptions and types
- Return value descriptions
- Exception documentation
- Usage examples in comments

---

## 10. Compatibility & Backward Compatibility

### 10.1 Backward Compatibility Guarantees

**Must Not Break:**
- ✅ Existing Raspberry Pi hardware encoder support
- ✅ MJPEG fallback on unsupported hardware
- ✅ Plugin configuration format
- ✅ OctoPrint plugin API compatibility
- ✅ Existing user settings

**Safe to Change:**
- ✅ Internal encoder detection logic
- ✅ FFmpeg command construction
- ✅ Logging messages
- ✅ Settings UI layout (non-breaking)

### 10.2 Migration Path

**For Existing Users:**
- No action required - automatic detection
- Plugin will continue using existing encoder if available
- VA-API will be detected automatically on next restart
- Optional: Users can check hardware status in settings

**For New Users:**
- Auto-detection works out of the box
- Optional driver installation guide
- Clear documentation in setup wizard

### 10.3 Platform Support Matrix

| Platform | Current Support | After Implementation | Notes |
|----------|----------------|---------------------|-------|
| Raspberry Pi 3/4 | ✅ Full | ✅ Full | No changes |
| Raspberry Pi Zero | ✅ Full | ✅ Full | No changes |
| Intel NUC | ❌ MJPEG only | ✅ VA-API | New feature |
| AMD Mini PC | ❌ MJPEG only | ✅ VA-API | New feature |
| Generic x86 | ❌ MJPEG only | ⚠️ MJPEG (VA-API if GPU) | Improved fallback |
| ARM SBC (non-RPi) | ⚠️ May work | ⚠️ May work | No changes |
| Docker | ⚠️ Limited | ✅ GPU passthrough | New feature |

---

## 11. Risks & Mitigation

### 11.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| FFmpeg compatibility issues | Medium | High | Extensive testing, version checks |
| Driver dependency problems | High | Medium | Clear documentation, graceful fallback |
| Performance regression on RPi | Low | High | Comprehensive regression testing |
| VA-API device detection fails | Medium | Medium | Multiple detection methods, fallback |
| Permission issues (/dev/dri) | High | Low | Clear error messages, documentation |
| Docker GPU passthrough complexity | Medium | Low | Optional feature, document limitations |

### 11.2 Mitigation Strategies

**For Driver Dependencies:**
- Don't require VA-API - make it optional
- Provide clear installation instructions per distro
- Graceful fallback to software encoding
- Detect and report driver issues clearly

**For Compatibility:**
- Test on multiple FFmpeg versions (4.x, 5.x, 6.x)
- Test on major Linux distros (Ubuntu, Debian, Fedora, Arch)
- Maintain list of known working configurations
- Version detection and warnings

**For Performance:**
- Benchmark before/after on reference hardware
- Monitor memory usage during encoding
- Add performance metrics to logging
- Allow users to disable hardware acceleration

**For User Experience:**
- Clear error messages with actionable steps
- Troubleshooting guide with common issues
- Hardware detection status in UI
- Link to community support resources

---

## 12. Implementation Timeline

### Week 1: Foundation
- **Days 1-2:** Create `hardware_detection.py` module
- **Days 3-4:** Implement detection logic and unit tests
- **Day 5:** Update `utils.py` and `bin/utils.sh`

### Week 2: Core Features
- **Days 1-2:** Modify `find_ffmpeg_h264_encoder()`
- **Day 3:** Add VA-API FFmpeg integration
- **Days 4-5:** Testing and debugging

### Week 3: Polish & Documentation
- **Days 1-2:** Update Settings UI with hardware info
- **Day 3:** Create user documentation
- **Days 4-5:** Testing on multiple platforms

### Week 4: Testing & Release
- **Days 1-2:** Integration testing
- **Day 3:** Performance benchmarking
- **Day 4:** Bug fixes and polish
- **Day 5:** Documentation review and release prep

---

## 13. Success Criteria

### 13.1 Technical Success Metrics

✅ **Must Have:**
- [ ] VA-API encoder detected on Intel/AMD systems
- [ ] Hardware encoding works with common resolutions
- [ ] No regression on Raspberry Pi devices
- [ ] Graceful fallback to MJPEG when no hardware
- [ ] All existing tests pass
- [ ] No memory leaks during 24h test

🎯 **Should Have:**
- [ ] CPU usage reduced by >50% with VA-API
- [ ] Support for 720p @ 25 FPS on Intel HD 630
- [ ] Docker GPU passthrough working
- [ ] Hardware info displayed in settings UI

⭐ **Nice to Have:**
- [ ] Support for 1080p @ 30 FPS on modern GPUs
- [ ] Automatic encoder selection optimization
- [ ] Quality comparison metrics in logs
- [ ] Performance dashboard in UI

### 13.2 User Experience Metrics

✅ **Must Have:**
- [ ] Clear error messages for common issues
- [ ] Troubleshooting guide covers 80% of issues
- [ ] Setup works with default FFmpeg installation
- [ ] No user action required for auto-detection

🎯 **Should Have:**
- [ ] <5 minutes to verify hardware acceleration
- [ ] Hardware status visible in settings
- [ ] Driver installation guide per major distro

### 13.3 Documentation Metrics

✅ **Must Have:**
- [ ] README updated with hardware requirements
- [ ] VA-API setup guide created
- [ ] All new functions have docstrings
- [ ] Troubleshooting section added

---

## 14. Future Enhancements (Out of Scope)

**Phase 2 - Future Work:**

1. **NVIDIA NVENC Support**
   - Add `h264_nvenc` encoder detection
   - Requires CUDA runtime
   - Higher implementation complexity

2. **Encoder Quality Tuning**
   - Automatic bitrate optimization
   - Quality presets (fast, balanced, quality)
   - Dynamic resolution adjustment

3. **Encoder Benchmarking**
   - Built-in performance testing
   - Quality metrics (PSNR, SSIM)
   - Automatic encoder selection based on benchmark

4. **Multi-GPU Support**
   - Select specific GPU for encoding
   - Load balancing across multiple GPUs
   - Per-webcam GPU assignment

5. **Advanced VA-API Features**
   - VPP (Video Post Processing) filters
   - Low-latency mode tuning
   - Rate control modes (CBR, VBR, CQP)

6. **Web UI Enhancements**
   - Real-time encoding statistics
   - GPU utilization monitoring
   - Encoder comparison tool

---

## 15. Development Setup

### 15.1 Local Development Environment

**Prerequisites:**
```bash
# Install VA-API drivers (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y \
    intel-media-va-driver \
    i965-va-driver \
    mesa-va-drivers \
    vainfo \
    ffmpeg

# Verify VA-API
vainfo

# Add user to video group for /dev/dri access
sudo usermod -a -G video $USER
# Log out and back in for group changes
```

**Clone and Setup:**
```bash
# Clone repository
git clone https://github.com/EvasiveXkiller/OctoPrint-Obico.git
cd OctoPrint-Obico

# Install in development mode
pip install -e .

# For Docker development
docker compose up -d
docker compose exec op pip3 install -e /app
docker compose exec op ./start.sh
```

### 15.2 Testing Commands

**Test Hardware Detection:**
```bash
# From Python
python3 -c "
from octoprint_obico.hardware_detection import HardwareCapabilities
hw = HardwareCapabilities()
print(hw.get_capabilities_info())
"
```

**Test Encoder Detection:**
```bash
# From Python (requires test video file)
python3 -c "
from octoprint_obico.webcam_stream import find_ffmpeg_h264_encoder
encoder = find_ffmpeg_h264_encoder()
print(f'Detected encoder: {encoder}')
"
```

**Manual FFmpeg Test:**
```bash
# Test VA-API encoding
ffmpeg -re -i test-video.mp4 -t 5 \
    -vaapi_device /dev/dri/renderD128 \
    -vf 'format=nv12,hwupload' \
    -c:v h264_vaapi \
    -b:v 2000k \
    output.mp4
```

### 15.3 Debug Tips

**Enable Verbose Logging:**
```python
# In octoprint_obico/__init__.py or settings
import logging
logging.getLogger('octoprint.plugins.obico').setLevel(logging.DEBUG)
```

**Check VA-API Device Permissions:**
```bash
ls -la /dev/dri/
# Should show renderD128 with group 'video' or 'render'

# Check your groups
groups
# Should include 'video' or 'render'
```

**FFmpeg Debugging:**
```bash
# Show all available encoders
ffmpeg -encoders | grep 264

# Detailed VA-API info
LIBVA_MESSAGING_LEVEL=2 vainfo
```

---

## 16. Questions & Decisions Needed

### 16.1 Technical Decisions

**Q1: Should we support Intel QSV separately from VA-API?**
- QSV uses VA-API backend on Linux, but has different FFmpeg flags
- **Recommendation:** Yes, test both and use whichever works better

**Q2: Minimum FFmpeg version requirement?**
- FFmpeg 4.0 has VA-API support, but 4.4+ is more stable
- **Recommendation:** Require 4.0, document 4.4+ as recommended

**Q3: Should we auto-install VA-API drivers?**
- Could use apt/dnf/pacman to install drivers
- **Recommendation:** No, too risky. Provide clear instructions instead

**Q4: How to handle multiple GPUs?**
- Intel + NVIDIA hybrid laptops, multi-GPU workstations
- **Recommendation:** Use first available, add GPU selection in future

### 16.2 User Experience Decisions

**Q5: Should hardware detection run on every restart?**
- Pro: Always up-to-date
- Con: Slight startup delay
- **Recommendation:** Yes, cache results but re-check on restart

**Q6: What if hardware encoder produces lower quality?**
- Some hardware encoders have quality limitations
- **Recommendation:** Allow manual fallback to software, document trade-offs

**Q7: Should we add an "encoder preference" setting?**
- Let users manually select encoder
- **Recommendation:** Add in future, start with auto-detection

---

## 17. Rollout Plan

### 17.1 Beta Testing Phase

**Week 1-2: Internal Testing**
- Test on developer machines
- Verify basic functionality
- Fix critical bugs

**Week 3-4: Limited Beta**
- Invite 10-20 testers with Intel/AMD GPUs
- Collect feedback and logs
- Monitor for common issues
- Iterate on documentation

**Week 5-6: Public Beta**
- Announce on Discord/forums
- Tag release as "beta" in GitHub
- Monitor issue reports
- Prepare for stable release

### 17.2 Stable Release

**Prerequisites for Stable:**
- [ ] Zero critical bugs
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Positive feedback from beta testers
- [ ] No performance regressions

**Release Checklist:**
- [ ] Version bump
- [ ] Changelog updated
- [ ] Release notes written
- [ ] Tag release in Git
- [ ] Update plugin repository
- [ ] Announce on all channels

---

## 18. Support Plan

### 18.1 Common Issues & Solutions

**Issue 1: "Hardware encoder not detected"**
- Check: Is FFmpeg installed with VA-API support?
- Check: Are VA-API drivers installed?
- Check: Does /dev/dri/renderD128 exist?
- Solution: Install drivers, verify with `vainfo`

**Issue 2: "Permission denied on /dev/dri"**
- Check: Is user in 'video' or 'render' group?
- Solution: `sudo usermod -a -G video $USER`, then restart

**Issue 3: "FFmpeg test timeout"**
- Check: Is GPU busy with other processes?
- Check: Are drivers loaded correctly?
- Solution: Restart system, check dmesg for GPU errors

**Issue 4: "Streaming still uses high CPU"**
- Check: Is MJPEG fallback being used?
- Check: Settings UI shows correct encoder?
- Solution: Check logs for encoder detection failure reason

### 18.2 Support Channels

**For Users:**
- GitHub Issues (bugs and feature requests)
- Discord Server (community support)
- Documentation Wiki (guides and FAQs)
- Email support (premium users)

**For Developers:**
- GitHub Discussions (architecture questions)
- Code comments and docstrings
- Development documentation
- Direct communication on Discord

---

## 19. Conclusion

This implementation plan provides a comprehensive roadmap for adding VA-API hardware acceleration support to OctoPrint-Obico. The phased approach ensures:

✅ **Backward Compatibility:** No breaking changes for existing users  
✅ **Gradual Rollout:** Beta testing before stable release  
✅ **Clear Documentation:** Users and developers have needed resources  
✅ **Risk Mitigation:** Fallback mechanisms and extensive testing  
✅ **Future-Proof:** Extensible architecture for additional encoders  

**Estimated Total Effort:** 3-4 weeks for initial implementation + 2 weeks for beta testing and polish

**Next Steps:**
1. Review and approve this plan
2. Set up development environment
3. Create feature branch: `feature/vaapi-support`
4. Begin Phase 1: Hardware Detection implementation

---

## 20. Appendix

### A. References

- **VA-API Documentation:** https://01.org/linuxgraphics/community/vaapi
- **FFmpeg VA-API Guide:** https://trac.ffmpeg.org/wiki/Hardware/VAAPI
- **Intel Media Driver:** https://github.com/intel/media-driver
- **Mesa3D:** https://docs.mesa3d.org/

### B. Example FFmpeg Commands

```bash
# Intel VA-API H.264 encoding
ffmpeg -i input.mp4 \
    -vaapi_device /dev/dri/renderD128 \
    -vf 'format=nv12,hwupload' \
    -c:v h264_vaapi \
    -b:v 2000k \
    output.mp4

# Intel QSV H.264 encoding  
ffmpeg -i input.mp4 \
    -init_hw_device qsv=hw \
    -filter_hw_device hw \
    -vf 'hwupload=extra_hw_frames=64,format=qsv' \
    -c:v h264_qsv \
    -b:v 2000k \
    output.mp4

# AMD VA-API H.264 encoding
ffmpeg -i input.mp4 \
    -vaapi_device /dev/dri/renderD128 \
    -vf 'format=nv12,hwupload' \
    -c:v h264_vaapi \
    -b:v 2000k \
    output.mp4
```

### C. Driver Installation Commands

**Ubuntu/Debian:**
```bash
# Intel (modern)
sudo apt-get install intel-media-va-driver vainfo

# Intel (legacy)
sudo apt-get install i965-va-driver vainfo

# AMD
sudo apt-get install mesa-va-drivers vainfo
```

**Fedora/RHEL:**
```bash
# Intel
sudo dnf install intel-media-driver libva-utils

# AMD
sudo dnf install mesa-va-drivers libva-utils
```

**Arch Linux:**
```bash
# Intel
sudo pacman -S intel-media-driver libva-utils

# AMD
sudo pacman -S libva-mesa-driver libva-utils
```

---

**Document Version:** 1.0  
**Last Updated:** October 31, 2025  
**Status:** Awaiting Review & Approval
