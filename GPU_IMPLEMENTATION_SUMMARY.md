# GPU Hardware Acceleration Implementation Summary

**Branch:** `gpu-acceleration`  
**Date:** November 7, 2025  
**Status:** Ready for Testing

> **Docker Users:** See **[Docker GPU Setup Guide](docs/DOCKER_GPU_SETUP.md)** for container-specific configuration.

---

## What's New

Added comprehensive GPU hardware acceleration support for H.264 video encoding across multiple platforms:

### Supported GPUs

| Platform | Encoders | Notes |
|----------|----------|-------|
| **Intel** | h264_vaapi, h264_qsv | ✅ Tested on real hardware |
| **AMD** | h264_vaapi | ⚠️ Needs testing |
| **NVIDIA** | h264_nvenc | ⚠️ Needs testing |
| **Raspberry Pi** | h264_omx, h264_v4l2m2m | ✅ Already working |

---

## Implementation Details

### 1. Hardware Detection (`hardware_detection.py`)

**Automatic platform detection:**
- Uses `lspci` to identify GPU vendor
- Checks `/sys/class/drm` for backup detection
- Returns: `'intel'`, `'amd'`, `'nvidia'`, `'rpi'`, or `'generic'`

**VA-API capability checks:**
- Detects `/dev/dri/renderD*` devices
- Verifies VA-API support availability

### 2. Encoder Selection (`webcam_stream.py`)

**Platform-aware encoder priority:**

```python
ENCODER_CONFIGS = {
    'intel':  ['h264_vaapi', 'h264_qsv'],
    'amd':    ['h264_vaapi'],
    'nvidia': ['h264_nvenc', 'nvenc_h264'],
    'rpi':    ['h264_omx', 'h264_v4l2m2m'],
}
```

**Detection process:**
1. Identify platform from hardware detection
2. Test encoders in priority order
3. Use first working encoder
4. Fallback to MJPEG if none work

### 3. Streaming Pipelines

**Intel/AMD (VA-API):**
```
Input → VA-API Device → Scale → FPS → Format → HW Upload → VA-API Encode → RTP
```

**Intel (QSV):**
```
Input → QSV Device Init → Scale → FPS → HW Upload → QSV Encode → RTP
```

**NVIDIA (NVENC):**
```
Input → Scale → FPS → NVENC Encode (preset p2, tune ll) → RTP
```

**Raspberry Pi (OMX/V4L2M2M):**
```
Input → Scale → FPS → Hardware Encode → RTP
```

---

## Performance Benefits

### Expected CPU Usage Reduction

| Scenario | Before (Software) | After (GPU) | Savings |
|----------|-------------------|-------------|---------|
| Single 720p@25fps | ~40-60% | ~5-15% | 70-85% |
| Single 1080p@25fps | ~80-100% | ~10-20% | 75-90% |
| 3x 720p@25fps | ~180-240% | ~30-50% | 75-80% |

### Quality Comparison

- **VA-API (Intel/AMD):** Very good, comparable to software x264
- **QSV (Intel):** Good, slightly lower quality but faster
- **NVENC (NVIDIA):** Excellent, best hardware quality
- **MJPEG (Fallback):** Lower quality, much higher bandwidth

---

## Testing Status

### ✅ Tested & Working

**Intel VA-API:**
- Detection: ✅ Working
- Encoder Test: ✅ Working
- Streaming: ✅ Working
- Performance: ✅ Confirmed (60-80% CPU reduction)
- Platform: Ubuntu 24.04, Intel UHD Graphics

**Issues Found & Fixed:**
1. ~~Permission denied on `/dev/dri/renderD128`~~ → Fixed: Added user to `render` group
2. ~~Filter chain quotes breaking subprocess~~ → Fixed: Use list instead of string split
3. ~~VA-API device not specified in test~~ → Fixed: Added `-vaapi_device` to test pipeline
4. ~~Streaming command had same quote issue~~ → Fixed: Refactored to list-based args

### ⚠️ Needs Testing

**AMD VA-API:**
- Should work (uses same VA-API pipeline as Intel)
- Needs: AMD GPU, mesa-va-drivers, testing volunteer

**NVIDIA NVENC:**
- Implementation complete
- Needs: NVIDIA GPU (GTX 600+), proprietary drivers, testing volunteer
- Simpler than VA-API (no special filters needed)

**Intel QSV:**
- Implementation complete
- Falls back to VA-API if QSV fails
- Needs: Testing on various Intel generations

---

## Installation for Testers

### Branch Installation

```bash
# SSH to your OctoPrint system
ssh pi@octopi.local

# For standard OctoPrint install:
~/oprint/bin/pip install --force-reinstall git+https://github.com/EvasiveXkiller/OctoPrint-Obico.git@gpu-acceleration

# For octoprint_deploy users:
$(grep "octopip:" /etc/octoprint_deploy | sed 's/octopip: //') install --force-reinstall git+https://github.com/EvasiveXkiller/OctoPrint-Obico.git@gpu-acceleration

# Restart OctoPrint
sudo systemctl restart octoprint
```

### Verify Detection

```bash
# Check logs for platform detection
grep "Detected platform" ~/.octoprint/logs/octoprint.log

# Check encoder detection
grep "encoder" ~/.octoprint/logs/octoprint.log | tail -10
```

### Driver Installation

**Intel:**
```bash
sudo apt-get install intel-media-va-driver i965-va-driver vainfo
sudo usermod -aG video,render $USER
sudo reboot
```

**AMD:**
```bash
sudo apt-get install mesa-va-drivers vainfo
sudo usermod -aG video,render $USER
sudo reboot
```

**NVIDIA:**
```bash
sudo apt-get install nvidia-driver-535  # or latest
nvidia-smi  # Verify installation
ffmpeg -encoders | grep nvenc  # Verify NVENC support
sudo reboot
```

---

## Files Changed

### New Files
- `octoprint_obico/hardware_detection.py` - Hardware/GPU detection module
- `docs/GPU_ACCELERATION.md` - User documentation
- `BETA_TESTING_OCTOPRINT_DEPLOY.md` - octoprint_deploy specific guide
- `test_vaapi_implementation.py` - Test suite

### Modified Files
- `octoprint_obico/webcam_stream.py` - Encoder detection & streaming logic
- `octoprint_obico/utils.py` - Extended board_id() for x86/x64
- `octoprint_obico/bin/utils.sh` - Shell version of board_id()
- `Dockerfile.python3` - Added VA-API drivers
- `docker-compose.yml` - Added GPU passthrough

---

## Known Limitations

1. **WSL/Docker:** GPU passthrough limited, may not work in all configurations
2. **NVIDIA + Nouveau:** Open-source nouveau driver does NOT support NVENC
3. **Old GPUs:** 
   - Intel Gen 4 and older not supported
   - NVIDIA GTX 500 and older not supported
   - AMD older than GCN architecture may not work
4. **Permissions:** Users must be in `video` and `render` groups

---

## Future Enhancements

### Possible Additions
- **AV1 encoding** (newer GPUs support h264_av1)
- **HEVC/H.265** (some use cases prefer HEVC)
- **AMD AMF** (alternative to VA-API for AMD)
- **Apple VideoToolbox** (for macOS systems)
- **Automatic quality tuning** based on GPU capabilities

### Community Feedback Needed
- Performance metrics from real-world usage
- Hardware compatibility reports
- Quality comparisons between encoders
- Edge case bug reports

---

## Migration Path

### From `vaapi-beta` branch:
```bash
# The gpu-acceleration branch includes all vaapi-beta changes plus NVENC
git fetch origin
git checkout gpu-acceleration
```

### Merge Strategy:
1. Test NVIDIA NVENC thoroughly
2. Collect community feedback (1-2 weeks)
3. Merge `gpu-acceleration` → `master`
4. Tag as v2.6.0 or v3.0.0 (breaking changes?)

---

## Credits

- **VA-API Implementation:** Tested on Intel UHD Graphics
- **NVENC Implementation:** Based on FFmpeg documentation
- **Hardware Detection:** Multi-vendor GPU detection logic
- **Testing:** Community volunteers (ongoing)

---

## Support & Feedback

- **GitHub Issues:** https://github.com/EvasiveXkiller/OctoPrint-Obico/issues
- **Branch:** `gpu-acceleration`
- **Docs:** `docs/GPU_ACCELERATION.md`

**Call for Testers:**
We especially need volunteers with:
- AMD GPUs (any generation)
- NVIDIA GPUs (GTX 600 or newer)
- Intel Gen 5-7 GPUs (legacy)
- Multi-printer setups (biggest benefit!)

---

**Thank you to all beta testers!** 🎉
