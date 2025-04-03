# Configuration - Define default values for variables
$defaultFrameRate = "30"
$defaultBitRate = "4500k"
$defaultProcessName = "NEUROSYNC-Win64-Shipping"
$defaultCaptureTarget = "desktop" 
$defaultAudioDevice = "Stereo Mix (Realtek High Definition Audio)"
$defaultCaptureMethod = "desktop"
$defaultShowRegion = $true
$projectDir = "$PSScriptRoot\NeuroSync"

# Log file configuration
$logFilePath = Join-Path $PSScriptRoot "stream-neurosync.log"
$maxLogSizeMB = 10

# Logging function
function Write-Log {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Message,
        
        [Parameter(Mandatory=$false)]
        [string]$ForegroundColor = "White"
    )
    
    # Get timestamp
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    
    # Write to console with color
    Write-Host $Message -ForegroundColor $ForegroundColor
    
    # Write to log file
    Add-Content -Path $logFilePath -Value $logMessage
    
    # Check log file size and rotate if needed
    if ((Get-Item $logFilePath).Length/1MB -gt $maxLogSizeMB) {
        $backupPath = "$logFilePath.old"
        if (Test-Path $backupPath) { Remove-Item $backupPath -Force }
        Rename-Item -Path $logFilePath -NewName "$logFilePath.old" -Force
        Write-Host "Log file rotated due to size limit." -ForegroundColor Yellow
    }
}

# Initialize log file with header
if (-not (Test-Path $logFilePath)) {
    New-Item -Path $logFilePath -ItemType File -Force | Out-Null
}
Write-Log "--- New NeuroSync Run & Stream Session Started: $(Get-Date) ---" "Cyan"

# Function to list windows 
function Get-WindowsList {
    Add-Type @"
    using System;
    using System.Runtime.InteropServices;
    using System.Collections.Generic;
    using System.Text;
    
    public class WindowUtils {
        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
        
        [DllImport("user32.dll")]
        public static extern bool IsWindowVisible(IntPtr hWnd);
        
        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
        
        [DllImport("user32.dll", SetLastError=true, CharSet=CharSet.Auto)]
        public static extern int GetWindowTextLength(IntPtr hWnd);
        
        [DllImport("user32.dll")]
        public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
        
        public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
        
        public static List<WindowInfo> GetWindows() {
            List<WindowInfo> windows = new List<WindowInfo>();
            EnumWindows(delegate(IntPtr hWnd, IntPtr lParam) {
                if (IsWindowVisible(hWnd)) {
                    int length = GetWindowTextLength(hWnd);
                    if (length > 0) {
                        StringBuilder sb = new StringBuilder(length + 1);
                        GetWindowText(hWnd, sb, sb.Capacity);
                        uint processId;
                        GetWindowThreadProcessId(hWnd, out processId);
                        windows.Add(new WindowInfo { 
                            Handle = hWnd, 
                            Title = sb.ToString(),
                            ProcessId = processId
                        });
                    }
                }
                return true;
            }, IntPtr.Zero);
            return windows;
        }
        
        public class WindowInfo {
            public IntPtr Handle { get; set; }
            public string Title { get; set; }
            public uint ProcessId { get; set; }
        }
    }
"@

    $windows = [WindowUtils]::GetWindows()
    return $windows
}

# Check for admin rights
function Test-AdminRights {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Check for FFmpeg installation
Write-Log "Checking for FFmpeg..." "Cyan"
$ffmpegInstalled = $null -ne (Get-Command ffmpeg -ErrorAction SilentlyContinue)
if (-not $ffmpegInstalled) {
    Write-Log "ERROR: FFmpeg not found in PATH. Please install FFmpeg first." "Red"
    Write-Log "You can download it from: https://ffmpeg.org/download.html" "Red"
    Write-Log "Press any key to exit..."
    $null = $host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}
else {
    Write-Log "FFmpeg found." "Green"
    $ffmpegVersion = (ffmpeg -version | Select-Object -First 1)
    Write-Log "Version: $ffmpegVersion" "Gray"
}

# Load environment variables from .env
$envFilePath = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFilePath) {
    Write-Log "Loading environment variables from $envFilePath"
    $lines = Get-Content $envFilePath
    foreach ($line in $lines) {
        if (-not [string]::IsNullOrWhiteSpace($line) -and -not $line.StartsWith("#")) {
            if ($line -match "^(.*?)=(.*?)$") {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim()
                [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
            }
        }
    }
    Write-Log "Environment variables loaded successfully."
} else {
    Write-Log "WARNING: .env file not found at $envFilePath." "Yellow"
    Write-Log "Will use default values for streaming. Create a .env file for customization."
}

# Get values from environment variables or use defaults
Write-Log "Checking for Twitch stream key..."
$twitchStreamKey = if ($env:TWITCH_STREAM_KEY) { $env:TWITCH_STREAM_KEY } else { 
    Write-Log "ERROR: No Twitch stream key found in .env file!" "Red"
    Write-Log "Please create a .env file with TWITCH_STREAM_KEY=your_key" "Red"
    Write-Log "Press any key to exit..."
    $null = $host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

Write-Log "Twitch stream key found, reading other parameters..."
$frameRate = if ($env:FRAMERATE) { $env:FRAMERATE } else { $defaultFrameRate }
$bitRate = if ($env:BITRATE) { $env:BITRATE } else { $defaultBitRate }
$captureTarget = if ($env:CAPTURE_TARGET) { $env:CAPTURE_TARGET } else { $defaultCaptureTarget }
$audioDevice = if ($env:AUDIO_DEVICE) { $env:AUDIO_DEVICE } else { $defaultAudioDevice }
$captureMethod = if ($env:CAPTURE_METHOD) { $env:CAPTURE_METHOD } else { $defaultCaptureMethod }
$showRegion = if ($null -ne $env:SHOW_REGION) { [bool]::Parse($env:SHOW_REGION) } else { $defaultShowRegion }
$gameExePath = "$projectDir\Game\NEUROSYNC_Demo_Build\Windows\NEUROSYNC.exe"

# Display streaming configuration 
Write-Log "Streaming Configuration:" "Cyan"
Write-Log "- Twitch Key: $($twitchStreamKey.Substring(0,4))****" "Cyan"
Write-Log "- Frame Rate: $frameRate" "Cyan"
Write-Log "- Bit Rate: $bitRate" "Cyan"
Write-Log "- Capture: $captureTarget" "Cyan"
Write-Log "- Audio: $audioDevice" "Cyan"
Write-Log "- Capture Method: $captureMethod" "Cyan"
Write-Log "- Game Path: $gameExePath" "Cyan"

# Check if game exists
if (-not (Test-Path $gameExePath)) {
    Write-Log "ERROR: NeuroSync executable not found at $gameExePath" "Red"
    Write-Log "Please run setup.ps1 first to install the game." "Red"
    Write-Log "Press any key to exit..."
    $null = $host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# Launch the game
Write-Log "Launching NeuroSync..." "Green"
try {
    $gameProcess = Start-Process -FilePath $gameExePath -PassThru
    $gamePID = $gameProcess.Id
    Write-Log "Game process started with PID: $gamePID" "Green"
    
    # Wait a few seconds for the game window to initialize
    Write-Log "Waiting for game window to initialize..." "Gray"
    Start-Sleep -Seconds 10
} catch {
    Write-Log "ERROR: Failed to launch NeuroSync: $_" "Red"
    Write-Log "Press any key to exit..."
    $null = $host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# Check for audio devices
Write-Log "Checking audio devices..." "Cyan"
try {
    $tempFile = Join-Path $env:TEMP "ffmpeg-devices.txt"
    Start-Process -FilePath "ffmpeg" -ArgumentList "-list_devices", "true", "-f", "dshow", "-i", "dummy" -NoNewWindow -RedirectStandardError $tempFile -Wait
    
    if (Test-Path $tempFile) {
        $audioDevicesOutput = Get-Content -Path $tempFile -Raw
        Write-Log "Available audio devices:" "Gray"
        
        # Parse the output to get available audio devices
        $audioDevices = @()
        $audioLines = $audioDevicesOutput -split "`r?`n" | Where-Object { $_ -match "\(audio\)" }
        foreach ($line in $audioLines) {
            Write-Log "  $line" "Gray"
            if ($line -match '"([^"]+)"\s+\(audio\)') {
                $audioDevices += $matches[1]
            }
        }
        
        # Check if the configured audio device exists
        $audioDeviceExists = $audioDevicesOutput -match [regex]::Escape($audioDevice)
        
        # If the configured device doesn't exist but we found other devices, use the first one
        if (-not $audioDeviceExists -and $audioDevices.Count -gt 0) {
            Write-Log "Default audio device '$audioDevice' not found." "Yellow"
            $audioDevice = $audioDevices[0]
            Write-Log "Automatically selected audio device: '$audioDevice'" "Green"
            $audioDeviceExists = $true
        }
    } else {
        Write-Log "WARNING: Could not retrieve audio device list" "Yellow"
        $audioDeviceExists = $false
    }
} catch {
    Write-Log "ERROR: Failed to enumerate audio devices: $($_.Exception.Message)" "Red"
    Write-Log "Will continue without audio" "Yellow"
    $audioDeviceExists = $false
}

if (-not $audioDeviceExists) {
    Write-Log "WARNING: No audio devices found. Streaming will continue without audio." "Yellow"
    $audioDevice = $null
}

# Using desktop capture by default
Write-Log "Using desktop capture as default: '$captureTarget'" "Cyan"

# Build FFmpeg arguments array
$ffmpegArgs = @(
    "-y",
    "-f", "gdigrab"
)

# Add basic grab parameters
$ffmpegArgs += @(
    "-draw_mouse", "1",
    "-framerate", $frameRate,
    "-i", $captureTarget
)

# Add audio capture if device is specified
if (-not [string]::IsNullOrEmpty($audioDevice)) {
    $ffmpegArgs += @(
        "-f", "dshow",
        "-i", "audio=`"$audioDevice`""
    )
}

# Calculate a safe buffer size (2x bitrate, but with a maximum value)
$bitRateValue = [int]($bitRate -replace 'k','')
$bufferSize = [Math]::Min($bitRateValue * 2, 8000) # Cap at 8000k to be safe
$bufferSizeStr = $bufferSize.ToString() + "k"

# Add encoding parameters
$ffmpegArgs += @(
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-b:v", $bitRate,
    "-maxrate", $bitRate,
    "-bufsize", $bufferSizeStr,
    "-g", ([int]$frameRate * 2).ToString(), # Set keyframe interval to 2 seconds (framerate * 2)
    "-pix_fmt", "yuv420p",
    "-vf", "format=yuv420p" # Ensure correct pixel format
)

# Add audio encoding parameters if we're capturing audio
if (-not [string]::IsNullOrEmpty($audioDevice)) {
    $ffmpegArgs += @(
        "-c:a", "aac",
        "-b:a", "160k",
        "-ar", "44100"
    )
}

# Add output
$ffmpegArgs += @(
    "-f", "flv",
    "rtmp://live.twitch.tv/app/$twitchStreamKey"
)

# Start the stream
Write-Log "Starting FFmpeg with the following arguments:" "Green"
# Safely display arguments with masked window titles for privacy
$maskedArgs = $ffmpegArgs -replace '(title=")([^"]+)(")', '$1[Window Title]$3'
Write-Log ($maskedArgs -join " ") "DarkGray"

# Always run in debug mode
Write-Log "Running FFmpeg in debug mode. Press Ctrl+C to stop." "Yellow"

try {
    # Capture FFmpeg output to log file
    $ffmpegProcess = Start-Process -FilePath "ffmpeg" -ArgumentList $ffmpegArgs -NoNewWindow -PassThru -RedirectStandardOutput "$PSScriptRoot\ffmpeg-output.txt" -RedirectStandardError "$PSScriptRoot\ffmpeg-error.txt"
    
    Write-Log "FFmpeg debug output is being written to ffmpeg-output.txt and ffmpeg-error.txt"
    
    # Create a timer for periodic checking
    $checkInterval = 5 # seconds
    $startTime = Get-Date
    $lastCheckTime = $startTime
    $running = $true
    
    Write-Log "Monitoring FFmpeg process. Will check every $checkInterval seconds for issues." "Cyan"
    
    # Periodically check FFmpeg process and capture any output
    while ($running -and -not $ffmpegProcess.HasExited) {
        $currentTime = Get-Date
        
        # Check every X seconds
        if (($currentTime - $lastCheckTime).TotalSeconds -ge $checkInterval) {
            $lastCheckTime = $currentTime
            
            # Check if there's any error output we can display
            if (Test-Path "$PSScriptRoot\ffmpeg-error.txt") {
                $errorContent = Get-Content "$PSScriptRoot\ffmpeg-error.txt" -Tail 5
                if ($errorContent) {
                    Write-Log "Recent FFmpeg output:" "Yellow"
                    foreach ($line in $errorContent) {
                        # Only display informative lines, not just progress indicators
                        if ($line -match "error|failed|could not|invalid|no such") {
                            Write-Log "  $line" "Red"
                        }
                    }
                }
            }
            
            # Check if FFmpeg is still capturing frames after initial setup
            $runTime = ($currentTime - $startTime).TotalSeconds
            if ($runTime -gt 10) {
                $outputContent = Get-Content "$PSScriptRoot\ffmpeg-output.txt" -Tail 5 -ErrorAction SilentlyContinue
                # Look for signs of video capture activity
                if ($outputContent -notmatch "frame=\s*\d+") {
                    Write-Log "WARNING: FFmpeg may not be capturing frames." "Yellow"
                }
            }
            
            # Display a heartbeat
            Write-Host "." -NoNewline -ForegroundColor Green
        }
        
        Start-Sleep -Milliseconds 500
        
        # Allow user to stop with 'q' key if they press it
        if ([Console]::KeyAvailable) {
            $key = [Console]::ReadKey($true)
            if ($key.Key -eq 'Q') {
                Write-Log "`nUser requested stop." "Yellow"
                $running = $false
                try {
                    # Try to gracefully stop FFmpeg
                    $ffmpegProcess.CloseMainWindow() | Out-Null
                    if (-not $ffmpegProcess.WaitForExit(5000)) {
                        $ffmpegProcess.Kill()
                    }
                } catch {
                    Write-Log "Error stopping FFmpeg: $_" "Red"
                }
            }
        }
        
        # Check if the game process is still running
        if (-not (Get-Process -Id $gamePID -ErrorAction SilentlyContinue)) {
            Write-Log "`nGame process has exited. Stopping streaming." "Yellow"
            $running = $false
            try {
                $ffmpegProcess.CloseMainWindow() | Out-Null
                if (-not $ffmpegProcess.WaitForExit(5000)) {
                    $ffmpegProcess.Kill()
                }
            } catch {
                Write-Log "Error stopping FFmpeg: $_" "Red"
            }
        }
    }
    
    # Wait for process to complete if it's still running
    if (-not $ffmpegProcess.HasExited) {
        Write-Log "Waiting for FFmpeg to exit..." "Yellow"
        $ffmpegProcess.WaitForExit()
    }
    
    # Log results
    if ($ffmpegProcess.ExitCode -ne 0) {
        Write-Log "FFmpeg exited with code $($ffmpegProcess.ExitCode). See error log for details." "Red"
    } else {
        Write-Log "FFmpeg has exited successfully." "Green"
    }
    
    # Append FFmpeg error output to main log
    Write-Log "--- FFmpeg Error Output ---" "Yellow"
    Get-Content "$PSScriptRoot\ffmpeg-error.txt" | ForEach-Object { Write-Log $_ }
} catch {
    Write-Log "ERROR: Failed to start FFmpeg: $_" "Red"
    Write-Log "Stack trace: $($_.ScriptStackTrace)" "Red"
    
    # If streaming failed, make sure to kill the game process
    try {
        if (Get-Process -Id $gamePID -ErrorAction SilentlyContinue) {
            Write-Log "Cleaning up: Stopping the game process..." "Yellow"
            Stop-Process -Id $gamePID -Force
        }
    } catch {
        Write-Log "Error stopping game process: $_" "Red"
    }
    
    Write-Log "Press any key to exit..."
    $null = $host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# Final log entry
Write-Log "--- Streaming Session Ended: $(Get-Date) ---" "Cyan"

# Keep the window open so user can see any error messages
Write-Log "Press any key to exit..."
$null = $host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
