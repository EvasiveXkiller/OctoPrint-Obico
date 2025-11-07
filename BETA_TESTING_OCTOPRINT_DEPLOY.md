# VA-API Beta Testing for octoprint_deploy Users

**Branch:** `vaapi-beta`  
**Status:** Beta Testing Phase  
**Date:** October 31, 2025

## For Users Deployed with octoprint_deploy

If you're using [octoprint_deploy](https://github.com/paukstelis/octoprint_deploy) to manage your OctoPrint instances, follow these instructions.

---

## Installation

### Step 1: SSH into your system

```bash
ssh pi@octopi.local  # or your hostname/IP
```

### Step 2: Find your OctoPrint pip path

octoprint_deploy stores this in `/etc/octoprint_deploy`:

```bash
# Check your pip path
grep "octopip:" /etc/octoprint_deploy
# Output will be something like: octopip: /home/pi/OctoPrint/bin/pip
```

### Step 3: Install the beta version

Replace `/home/pi/OctoPrint/bin/pip` with your actual path from Step 2:

```bash
# Install beta branch
/home/pi/OctoPrint/bin/pip install --force-reinstall git+https://github.com/EvasiveXkiller/OctoPrint-Obico.git@vaapi-beta
```

### Step 4: Restart ALL OctoPrint instances

```bash
# If you have octoprint_deploy script:
sudo ~/octoprint_deploy/octoprint_deploy.sh restart_all

# OR manually restart each instance:
sudo systemctl restart printer1  # replace with your instance names
sudo systemctl restart printer2
sudo systemctl restart printer3
```

---

## Verification

### Check if VA-API was detected

Wait 30 seconds after restart, then:

```bash
# Check logs for ALL instances
grep -E "platform|encoder|GPU" ~/.octoprint/logs/octoprint.log | tail -20

# For specific instance (replace .printer1 with your instance):
grep -E "platform|encoder|GPU" ~/.printer1/logs/octoprint.log | tail -20
```

**Expected output (Intel/AMD GPU):**
```
INFO - Detected platform: intel
INFO - Testing h264_vaapi encoder for platform: intel
INFO - Found working h264_vaapi encoder
```

**Expected output (no GPU/fallback):**
```
INFO - Detected platform: generic
WARNING - No hardware H.264 encoder found. Falling back to MJPEG.
```

### Quick validation test

```bash
# Get your pip path first
OCTOPIP=$(grep "octopip:" /etc/octoprint_deploy | sed 's/octopip: //')

# Run quick check (replace pip with python)
${OCTOPIP/pip/python} -c "from octoprint_obico.hardware_detection import HardwareCapabilities; caps = HardwareCapabilities(); print(f'Platform: {caps.detect_platform()}, GPU: {caps.detect_gpu_vendor()}, VA-API: {caps.has_vaapi_support()}')"
```

### Check CPU usage

```bash
# Monitor CPU while streaming
htop
# Press F4, type "python" to filter
# Look for CPU % - should be 60-80% LOWER with VA-API
```

---

## VA-API Setup (Intel/AMD Systems Only)

If you have Intel or AMD GPU and VA-API is NOT detected, install drivers:

### Debian/Ubuntu/OctoPi (Raspberry Pi OS):

```bash
# Install VA-API drivers
sudo apt-get update
sudo apt-get install -y intel-media-va-driver i965-va-driver mesa-va-drivers vainfo

# Add users to video group (replace 'pi' if different)
sudo usermod -aG video,render pi

# Reboot
sudo reboot
```

### After reboot, verify VA-API:

```bash
# Check device exists
ls -la /dev/dri/renderD*

# Test VA-API
vainfo
# Should show your GPU model and supported profiles
```

---

## Multi-Instance Considerations

### All instances share the same plugin installation

When you install the beta with pip, **all instances** get the update automatically since octoprint_deploy uses a shared Python virtual environment.

### Check each instance separately

Each instance has its own logs:

```bash
# List your instances
ls -d ~/.*/

# Check specific instance logs
grep "encoder" ~/.printer1/logs/octoprint.log | tail -5
grep "encoder" ~/.printer2/logs/octoprint.log | tail -5
```

### Streaming on multiple instances

VA-API can handle multiple encoders simultaneously. If you have 3 printers streaming:

**Before (software encoding):**
- CPU usage: ~240% (80% per stream × 3)

**After (hardware encoding):**
- CPU usage: ~45% (15% per stream × 3)

This is the BIGGEST benefit for multi-printer setups!

---

## Troubleshooting

### Problem: Plugin installed but still using MJPEG

**Solution:**
1. Make sure you restarted the instance: `sudo systemctl restart printer1`
2. Wait 30 seconds for encoder detection
3. Check logs: `grep "encoder" ~/.printer1/logs/octoprint.log | tail -10`

### Problem: "No module named hardware_detection"

**Solution:**
The plugin didn't install correctly. Try again:
```bash
OCTOPIP=$(grep "octopip:" /etc/octoprint_deploy | sed 's/octopip: //')
$OCTOPIP install --force-reinstall git+https://github.com/EvasiveXkiller/OctoPrint-Obico.git@vaapi-beta
```

### Problem: VA-API device not found on Intel system

**Solution:**
```bash
# Check if drivers are installed
dpkg -l | grep -i va-driver

# If missing, install:
sudo apt-get install intel-media-va-driver i965-va-driver

# Check permissions
ls -la /dev/dri/
# You should see renderD128 or similar

# Add to groups
sudo usermod -aG video,render $USER
sudo reboot
```

### Problem: Works on one instance but not others

**Solution:**
All instances should behave the same since they share the plugin code. Check:
```bash
# Verify all instances are actually restarted
sudo systemctl status printer1 | grep "Active:"
sudo systemctl status printer2 | grep "Active:"

# Check when they were last started (should be recent)
```

---

## Performance Testing

### Before/After CPU comparison

```bash
# Start streaming on ALL printers
# Open Obico dashboards for each printer

# Monitor CPU for 2 minutes
top -b -n 120 -d 1 | grep python > cpu_test.log

# Check average
awk '{sum+=$9; count++} END {print "Average CPU:", sum/count "%"}' cpu_test.log
```

---

## Reporting Results

### System Information

```bash
# Get system info
uname -a
lscpu | grep "Model name"
cat /etc/octoprint_deploy
cat /etc/octoprint_instances

# Get GPU info (if available)
lspci | grep -i vga
vainfo | head -10
```

### Report Template

Post in GitHub issue or Discord:

```markdown
**Deployment Method:** octoprint_deploy v1.0.11
**Number of Instances:** 3 (or however many you have)

**System:**
- Hardware: [paste lscpu output]
- OS: [paste from /etc/os-release]
- GPU: [paste lspci output]

**Detection Results:**
[paste grep output from logs]

**Performance:**
- CPU before beta: ___%
- CPU after beta: ___%
- Improvement: ___%
- Number of simultaneous streams: ___

**Issues:** (if any)
```

---

## Reverting to Stable

If you need to roll back:

```bash
# Find your pip
OCTOPIP=$(grep "octopip:" /etc/octoprint_deploy | sed 's/octopip: //')

# Reinstall from master branch
$OCTOPIP install --force-reinstall git+https://github.com/EvasiveXkiller/OctoPrint-Obico.git@master

# Restart all instances
sudo ~/octoprint_deploy/octoprint_deploy.sh restart_all
```

---

## Support

- **GitHub Issues:** https://github.com/EvasiveXkiller/OctoPrint-Obico/issues
- **OctoPrint Discord:** https://discord.com/invite/yA7stPp
- **octoprint_deploy channel:** #support-octoprint-deploy

---

## Thank You! 🎉

Multi-printer users will see the **biggest benefit** from VA-API support. Your testing is crucial!
