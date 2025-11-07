# GPU Passthrough for Docker Users

This guide explains how to enable GPU acceleration when using the OctoPrint Docker image (https://github.com/OctoPrint/octoprint-docker).

## Prerequisites

You need:
1. A system with Intel, AMD, or NVIDIA GPU
2. Docker and Docker Compose installed
3. GPU drivers installed on the **host system** (not inside container)

---

## NVIDIA GPU Setup (NVENC)

### 1. Install NVIDIA Container Toolkit on Host

The NVIDIA Container Toolkit allows Docker containers to access NVIDIA GPUs.

#### Ubuntu/Debian:
```bash
# Add NVIDIA package repositories
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install the toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker to use the NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

#### Fedora/RHEL:
```bash
# Add NVIDIA package repositories
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.repo | \
  sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo

# Install the toolkit
sudo dnf install -y nvidia-container-toolkit

# Configure Docker to use the NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 2. Verify NVIDIA Runtime Works

Test that Docker can access your GPU:
```bash
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
```

You should see your GPU listed with driver version, temperature, etc.

### 3. Configure docker-compose.yml

Add the `deploy` section to enable GPU passthrough in your OctoPrint container:

```yaml
services:
  octoprint:
    image: octoprint/octoprint:latest
    # ... other configuration ...
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1  # Or 'all' to use all GPUs
              capabilities: [gpu, video]
```

**Full Example:**
```yaml
version: '3.7'

services:
  octoprint:
    image: octoprint/octoprint:latest
    restart: unless-stopped
    ports:
      - "80:80"
    devices:
      - /dev/ttyACM0:/dev/ttyACM0  # Your 3D printer
    volumes:
      - octoprint:/octoprint
    environment:
      ENABLE_MJPG_STREAMER: "true"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu, video]

volumes:
  octoprint:
```

### 4. Install Obico Plugin & Configure

1. Start your container: `docker-compose up -d`
2. Access OctoPrint web interface
3. Install the Obico plugin from the Plugin Manager
4. The plugin will **automatically detect** NVIDIA GPU and use NVENC hardware acceleration

### 5. Verify It's Working

Check the Obico plugin logs (Settings > Obico > Logging, set to DEBUG):

You should see:
```
Detected platform: nvidia
Testing encoder: h264_nvenc... SUCCESS
Using hardware encoder: h264_nvenc
```

---

## Intel GPU Setup (VA-API / QSV)

### 1. Verify GPU Access on Host

```bash
# Install VA-API tools
sudo apt-get install vainfo

# Check GPU access
ls -la /dev/dri/
vainfo
```

You should see `/dev/dri/renderD128` (or similar) and vainfo should list your Intel GPU.

### 2. Ensure User Has Permissions

```bash
# Add your user to the render group
sudo usermod -aG render $USER
sudo usermod -aG video $USER

# Reboot or re-login for changes to take effect
sudo reboot
```

### 3. Configure docker-compose.yml

Add the `/dev/dri` device mapping:

```yaml
services:
  octoprint:
    image: octoprint/octoprint:latest
    # ... other configuration ...
    devices:
      - /dev/dri:/dev/dri
    environment:
      # Optional: Set VA-API driver explicitly
      # iHD = modern Intel (Gen 8+), i965 = legacy Intel (Gen 5-7)
      LIBVA_DRIVER_NAME: iHD
```

**Full Example:**
```yaml
version: '3.7'

services:
  octoprint:
    image: octoprint/octoprint:latest
    restart: unless-stopped
    ports:
      - "80:80"
    devices:
      - /dev/ttyACM0:/dev/ttyACM0  # Your 3D printer
      - /dev/dri:/dev/dri           # GPU for VA-API
    volumes:
      - octoprint:/octoprint
    environment:
      ENABLE_MJPG_STREAMER: "true"
      LIBVA_DRIVER_NAME: iHD  # or i965 for older GPUs

volumes:
  octoprint:
```

### 4. Install Obico Plugin & Configure

Same process as NVIDIA - plugin will auto-detect Intel GPU.

Expected log output:
```
Detected platform: intel
Testing encoder: h264_vaapi... SUCCESS
Using hardware encoder: h264_vaapi
```

---

## AMD GPU Setup (VA-API)

### 1. Verify GPU Access on Host

```bash
# Install VA-API tools
sudo apt-get install vainfo mesa-va-drivers

# Check GPU access
ls -la /dev/dri/
vainfo
```

### 2. Ensure User Has Permissions

```bash
sudo usermod -aG render $USER
sudo usermod -aG video $USER
sudo reboot
```

### 3. Configure docker-compose.yml

Same as Intel - map `/dev/dri` device:

```yaml
services:
  octoprint:
    image: octoprint/octoprint:latest
    # ... other configuration ...
    devices:
      - /dev/dri:/dev/dri
    environment:
      LIBVA_DRIVER_NAME: radeonsi  # AMD driver
```

**Full Example:**
```yaml
version: '3.7'

services:
  octoprint:
    image: octoprint/octoprint:latest
    restart: unless-stopped
    ports:
      - "80:80"
    devices:
      - /dev/ttyACM0:/dev/ttyACM0
      - /dev/dri:/dev/dri
    volumes:
      - octoprint:/octoprint
    environment:
      ENABLE_MJPG_STREAMER: "true"
      LIBVA_DRIVER_NAME: radeonsi

volumes:
  octoprint:
```

### 4. Install Obico Plugin & Configure

Plugin will auto-detect AMD GPU.

Expected log output:
```
Detected platform: amd
Testing encoder: h264_vaapi... SUCCESS
Using hardware encoder: h264_vaapi
```

---

## Troubleshooting

### NVIDIA: "could not select device driver"

**Problem:** Docker can't find NVIDIA runtime.

**Solution:**
```bash
# Reconfigure Docker daemon
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify /etc/docker/daemon.json contains:
{
  "runtimes": {
    "nvidia": {
      "path": "nvidia-container-runtime",
      "runtimeArgs": []
    }
  }
}
```

### Intel/AMD: "Permission denied" on /dev/dri/renderD128

**Problem:** Container user doesn't have access to GPU device.

**Solution 1 - Add user to render group (preferred):**
```bash
sudo usermod -aG render $USER
sudo reboot
```

**Solution 2 - Change device permissions (less secure):**
```bash
sudo chmod 666 /dev/dri/renderD128
```

### "No encoders detected" in Obico logs

**Problem:** FFmpeg inside container doesn't have hardware encoder support.

**Solution:** This means the base OctoPrint Docker image doesn't include FFmpeg with hardware encoding. You may need to:

1. Build a custom Docker image with FFmpeg installed
2. Use the Obico plugin's bundled FFmpeg (should work automatically)
3. Check Obico logs - it should still fall back to software encoding

### Verify GPU is Accessible Inside Container

**For NVIDIA:**
```bash
docker exec -it <container_name> nvidia-smi
```

**For Intel/AMD:**
```bash
docker exec -it <container_name> ls -la /dev/dri/
docker exec -it <container_name> vainfo
```

If these commands fail, the GPU isn't properly passed through to the container.

---

## Performance Expectations

### CPU Usage Reduction

With hardware acceleration enabled:

| Scenario | Software Encoding | Hardware Encoding | Reduction |
|----------|------------------|-------------------|-----------|
| Single camera 720p | ~60-80% CPU | ~10-20% CPU | **60-75% less** |
| Single camera 1080p | ~90-100% CPU | ~15-25% CPU | **70-80% less** |
| Multiple cameras | Often unusable | ~20-40% CPU | **Massive improvement** |

### Quality

- **NVIDIA NVENC:** Excellent quality, comparable to software encoding
- **Intel QSV/VA-API:** Very good quality, slight difference from software
- **AMD VA-API:** Good quality, similar to Intel

### Latency

Hardware encoding typically reduces latency by 100-300ms due to lower system load.

---

## Docker Compose Version Requirements

**NVIDIA GPU passthrough requires Docker Compose v1.28.0+ with `deploy` syntax.**

If you're using an older version, you need the legacy syntax:
```yaml
services:
  octoprint:
    runtime: nvidia
    environment:
      NVIDIA_VISIBLE_DEVICES: all
```

Check your version:
```bash
docker-compose --version
```

Upgrade if needed:
```bash
# Install latest docker-compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

---

## Multiple GPU Systems

If you have multiple GPUs (e.g., Intel iGPU + NVIDIA dGPU):

### Prefer NVIDIA:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu, video]
```

### Prefer Intel/AMD:
```yaml
devices:
  - /dev/dri:/dev/dri
```

The Obico plugin will automatically prefer NVIDIA if both are available.

---

## Additional Resources

- **NVIDIA Container Toolkit Docs:** https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
- **Docker Compose GPU Support:** https://docs.docker.com/compose/gpu-support/
- **OctoPrint Docker Docs:** https://github.com/OctoPrint/octoprint-docker
- **Obico GPU Acceleration Guide:** See `GPU_ACCELERATION.md` in this repo

---

## Summary

1. **Install GPU drivers on host** (not in container)
2. **For NVIDIA:** Install NVIDIA Container Toolkit and use `deploy` syntax
3. **For Intel/AMD:** Map `/dev/dri` device and add user to `render` group
4. **Install Obico plugin** - it will auto-detect GPU
5. **Verify in logs** - should see "Using hardware encoder: h264_nvenc/h264_vaapi"

The plugin handles everything else automatically - no manual configuration needed!
