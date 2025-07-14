# WSL Audio Support Status (2025)
*Created: 2025-07-14*

## Current State of WSL Audio

### ✅ What Works Out of the Box

**Audio Output (Playback)**
- WSLg (Windows Subsystem for Linux GUI) includes integrated PulseAudio
- Audio playback works automatically for GUI applications
- PulseAudio socket available at `/mnt/wslg/PulseServer`
- No configuration needed for basic audio output

### ❌ What Doesn't Work Natively

**Microphone Input**
- No native microphone passthrough support in WSL2
- `/dev/snd` devices not available
- ALSA hardware layer not accessible
- Built-in laptop microphones cannot be accessed

## Working Solutions for Microphone Access

### 1. USB Microphone with usbipd-win (Most Reliable)

This is the closest to "native" support you can get:

```bash
# On Windows (PowerShell as Admin)
winget install usbipd

# List USB devices
usbipd list

# Share USB microphone (replace 2-4 with your device ID)
usbipd bind --busid 2-4
usbipd attach --wsl --busid 2-4

# In WSL
lsusb  # Should show your USB microphone
```

**Pros:**
- Works with most USB microphones
- Low latency
- Reliable once configured

**Cons:**
- Requires USB microphone (not built-in)
- Windows 11 or recent Windows 10
- May need custom kernel for some devices

### 2. PulseAudio Network Streaming

Set up PulseAudio server on Windows and connect from WSL:

```bash
# Windows: Install PulseAudio for Windows
# WSL: Configure PulseAudio client
export PULSE_SERVER=tcp:$(ip route show | grep -i default | awk '{ print $3}'):4713
```

**Pros:**
- Works with any microphone
- No hardware requirements

**Cons:**
- Complex setup
- Higher latency
- Connection stability issues

### 3. Custom Kernel with Audio Support

Build WSL2 kernel with audio drivers:

```bash
# Clone WSL2 kernel
git clone https://github.com/microsoft/WSL2-Linux-Kernel.git
cd WSL2-Linux-Kernel

# Enable audio configs in .config
# CONFIG_SOUND=y
# CONFIG_SND=y
# CONFIG_SND_USB_AUDIO=y

# Build and install custom kernel
```

**Pros:**
- Most complete solution
- Direct hardware access

**Cons:**
- Very complex
- Maintenance burden
- May break with WSL updates

## Why Native Support is Missing

1. **Architecture**: WSL2 runs in a lightweight VM with limited device passthrough
2. **Security**: Direct hardware access would require significant security considerations
3. **Complexity**: Audio subsystem integration is non-trivial across VM boundaries
4. **Priority**: Microsoft has focused on GUI and networking features first

## Recommendations

For voice control applications in WSL:

1. **Production Use**: Run voice recognition on Windows, communicate with WSL via network
2. **Development**: Use text input mode or Windows-side helper scripts
3. **Testing**: USB microphone with usbipd-win for best results
4. **Future**: Monitor WSL releases for native audio input support

## Current Best Practice

Given these limitations, the architecture we've implemented (Windows voice capture → HTTP API → WSL orchestrator) is actually the recommended approach for production use. It's more reliable than trying to force audio through WSL2's current limitations.

---

*Note: This reflects the state as of January 2025. Check Microsoft's WSL documentation for updates.*