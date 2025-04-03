# Configuration - Define default values for variables
$defaultFrameRate = "30"
$defaultBitRate = "4500k"
$defaultProcessName = "NEUROSYNC-Win64-Shipping"
$defaultCaptureTarget = "title=NEUROSYNC"  # Default to capturing the application window instead of desktop
$defaultAudioDevice = "Stereo Mix (Realtek High Definition Audio)"
$defaultCaptureMethod = "auto" # Change to "auto" to automatically detect best method
$defaultShowRegion = $true  # Show the capture region by default

# Log file configuration
$logFilePath = Join-Path $PSScriptRoot "stream-neurosync.log"
$maxLogSizeMB = 10 # Maximum log file size in MB before rotation

# Function to list windows - needs to be defined early
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

# Define the Find-NeuroSyncWindow function here BEFORE it's called
function Find-NeuroSyncWindow {
    Write-Log "Automatically searching for NEUROSYNC windows..." "Cyan"
    $windows = Get-WindowsList | Where-Object { -not [string]::IsNullOrEmpty($_.Title) }
    
    # First try: Find exact match for "NEUROSYNC" (ignoring trailing spaces)
    $exactMatch = $windows | Where-Object { $_.Title.Trim() -eq "NEUROSYNC" } | Select-Object -First 1
    if ($exactMatch) {
        $processName = (Get-Process -Id $exactMatch.ProcessId -ErrorAction SilentlyContinue).ProcessName
        Write-Log "Found exact match window: '$($exactMatch.Title)' (Process: $processName, PID: $($exactMatch.ProcessId))" "Green"
        return $exactMatch
    }
    
    # Second try: Find window that starts with "NEUROSYNC"
    $startsWithMatch = $windows | Where-Object { $_.Title.TrimStart() -like "NEUROSYNC*" } | Select-Object -First 1
    if ($startsWithMatch) {
        $processName = (Get-Process -Id $startsWithMatch.ProcessId -ErrorAction SilentlyContinue).ProcessName
        Write-Log "Found window starting with NEUROSYNC: '$($startsWithMatch.Title)' (Process: $processName, PID: $($startsWithMatch.ProcessId))" "Green"
        return $startsWithMatch
    }
    
    # Third try: Find window by process name
    $processPID = (Get-Process -Name "NEUROSYNC-Win64-Shipping" -ErrorAction SilentlyContinue | Select-Object -First 1).Id
    if ($processPID) {
        $processByPID = $windows | Where-Object { $_.ProcessId -eq $processPID } | Select-Object -First 1
        if ($processByPID) {
            $processName = (Get-Process -Id $processByPID.ProcessId -ErrorAction SilentlyContinue).ProcessName
            Write-Log "Found window by process ID: '$($processByPID.Title)' (Process: $processName, PID: $($processByPID.ProcessId))" "Green"
            return $processByPID
        }
    }
    
    # No matching window found
    Write-Log "No NEUROSYNC window found automatically." "Yellow"
    return $null
}

function Select-Window {
    Write-Log "Retrieving list of visible windows..." "Cyan"
    $windows = Get-WindowsList | Where-Object { -not [string]::IsNullOrEmpty($_.Title) } | Sort-Object Title
    
    Write-Log "Found $($windows.Count) windows with titles" "Green"
    Write-Log "Select a window to capture:" "Yellow"
    
    # Display windows with index numbers
    for ($i = 0; $i -lt [Math]::Min($windows.Count, 25); $i++) {
        $window = $windows[$i]
        $processName = (Get-Process -Id $window.ProcessId -ErrorAction SilentlyContinue).ProcessName
        if ([string]::IsNullOrEmpty($processName)) { $processName = "Unknown" }
        Write-Log "[$i] '$($window.Title)' (Process: $processName, PID: $($window.ProcessId))" "White"
    }
    
    if ($windows.Count -gt 25) {
        Write-Log "...and $($windows.Count - 25) more. Type 'more' to see additional windows." "Gray"
    }
    
    $validInput = $false
    $selectedWindow = $null
    
    while (-not $validInput) {
        $input = Read-Host "Enter window number to select (or 'more' to see more windows, or 'q' to cancel)"
        
        if ($input -eq 'q') {
            return $null
        }
        elseif ($input -eq 'more' -and $windows.Count -gt 25) {
            # Show more windows
            for ($i = 25; $i -lt $windows.Count; $i++) {
                $window = $windows[$i]
                $processName = (Get-Process -Id $window.ProcessId -ErrorAction SilentlyContinue).ProcessName
                if ([string]::IsNullOrEmpty($processName)) { $processName = "Unknown" }
                Write-Log "[$i] '$($window.Title)' (Process: $processName, PID: $($window.ProcessId))" "White"
            }
        }
        elseif ($input -match '^\d+$') {
            $index = [int]$input
            if ($index -ge 0 -and $index -lt $windows.Count) {
                $selectedWindow = $windows[$index]
                $validInput = $true
            }
            else {
                Write-Log "Invalid window number. Please enter a number between 0 and $($windows.Count - 1)" "Red"
            }
        }
        else {
            Write-Log "Invalid input. Please enter a window number, 'more', or 'q'" "Red"
        }
    }
    
    return $selectedWindow
}

# Logging function to write to console and log file
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
Write-Log "--- New Streaming Session Started: $(Get-Date) ---" "Cyan"

# Check for admin rights which may be needed for proper window capture
function Test-AdminRights {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

$isAdmin = Test-AdminRights
if (-not $isAdmin) {
    Write-Log "WARNING: This script is not running with administrator privileges." "Yellow"
    Write-Log "Window capture may not work correctly without admin rights." "Yellow"
    Write-Log "Consider restarting the script as administrator." "Yellow"
    $continueAnyway = Read-Host "Continue anyway? (y/n)"
    if ($continueAnyway -ne "y") {
        Write-Log "Exiting script. Please restart with admin rights." "Red"
        exit 1
    }
}

# Force PowerShell to keep the window open on errors
$ErrorActionPreference = "Stop"

# Check if FFmpeg is installed
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

# 1. Define your .env file path
$envFilePath = Join-Path $PSScriptRoot ".env"

# 2. Check if .env exists and load variables
if (Test-Path $envFilePath) {
    Write-Log "Loading environment variables from $envFilePath"
    # Read .env file line by line
    $lines = Get-Content $envFilePath
    foreach ($line in $lines) {
        # Ignore empty lines or comments starting with #
        if (-not [string]::IsNullOrWhiteSpace($line) -and -not $line.StartsWith("#")) {
            if ($line -match "^(.*?)=(.*?)$") {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim()

                # Set environment variable in the current process scope
                [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
            }
        }
    }
    Write-Log "Environment variables loaded successfully."
} else {
    Write-Log "WARNING: .env file not found at $envFilePath." "Yellow"
    Write-Log "Will use default values for streaming. Create a .env file for customization."
}

# Add global error handling
try {
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

    # Display configuration 
    Write-Log "Streaming Configuration:" "Cyan"
    Write-Log "- Twitch Key: $($twitchStreamKey.Substring(0,4))****" "Cyan"
    Write-Log "- Frame Rate: $frameRate" "Cyan"
    Write-Log "- Bit Rate: $bitRate" "Cyan"
    Write-Log "- Capture: $captureTarget" "Cyan"
    Write-Log "- Audio: $audioDevice" "Cyan"
    Write-Log "- Capture Method: $captureMethod" "Cyan"

    # Check for audio devices
    Write-Log "Checking audio devices..." "Cyan"
    try {
        # Use a safer approach to get audio devices
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

    # Find the NeuroSync process
    $gameProcesses = @(Get-Process -Name "NEUROSYNC", "NEUROSYNC-Win64-Shipping" -ErrorAction SilentlyContinue)
    $gameProcess = $null
    $processPID = $null
    $windowTitle = $null
    
    if ($gameProcesses.Count -gt 0) {
        $gameProcess = $gameProcesses[0]
        $processPID = $gameProcess.Id
        $processName = $gameProcess.Name
        Write-Log "Found NeuroSync process: $processName (PID: $processPID)" "Green"
        
        # Get the window title if available
        if (-not [string]::IsNullOrEmpty($gameProcess.MainWindowTitle)) {
            $windowTitle = $gameProcess.MainWindowTitle
            Write-Log "Window title: '$windowTitle'" "Green"
        } else {
            Write-Log "Process doesn't have a window title, will use process ID." "Yellow"
        }
    } else {
        Write-Log "WARNING: NeuroSync process not found. Is the game running?" "Yellow"
        $startGame = Read-Host "Do you want to start streaming anyway? (y/n)"
        if ($startGame -ne "y") {
            Write-Log "Exiting." "Yellow"
            exit 0
        }
        # Fall back to desktop capture if game not found
        $captureMethod = "desktop"
        Write-Log "Falling back to desktop capture since game is not running." "Yellow"
    }

    # Determine the capture method
    if ($captureMethod -eq "auto") {
        Write-Log "Using automatic window detection..." "Cyan"
        $neuroSyncWindow = Find-NeuroSyncWindow
        
        if ($neuroSyncWindow) {
            Write-Log "Automatically selected window: '$($neuroSyncWindow.Title)'" "Green"
            $captureTarget = "title=$($neuroSyncWindow.Title)"
            $captureMethod = "window"
        } elseif ($gameProcess -and $processPID) {
            Write-Log "No suitable window found, falling back to process ID capture." "Yellow"
            $captureTarget = "pid:$processPID"
            $captureMethod = "pid"
        } else {
            Write-Log "No suitable window or process found, falling back to desktop capture." "Yellow"
            $captureTarget = "desktop"
            $captureMethod = "desktop"
        }
    } elseif ($gameProcess -and ($captureMethod -eq "pid" -or $captureMethod -eq "process") -and $processPID) {
        Write-Log "Using process ID capture method." "Cyan"
        $captureTarget = "pid:$processPID"
    } elseif ($gameProcess -and $captureMethod -eq "window" -and $windowTitle) {
        Write-Log "Using window title capture method." "Cyan"
        # Properly handle window title with spaces
        $captureTarget = "title=$windowTitle"
    } elseif ($captureMethod -eq "desktop" -or (-not $gameProcess)) {
        Write-Log "Using desktop capture method." "Cyan"
        $captureTarget = "desktop"
    } else {
        Write-Log "WARNING: Could not determine capture method, falling back to desktop." "Yellow"
        $captureTarget = "desktop"
    }

    # Final capture target
    Write-Log "Final capture target: '$captureTarget'" "Cyan"
    
    # Allow the user to override the capture method
    $override = Read-Host "Override capture method? (window/pid/desktop/select/auto/n)"
    if ($override -eq "window" -and $windowTitle) {
        $captureTarget = "title=$windowTitle"
        Write-Log "Overriding to window capture: '$captureTarget'" "Cyan"
    } elseif ($override -eq "pid" -and $processPID) {
        $captureTarget = "pid:$processPID"
        Write-Log "Overriding to process ID capture: '$captureTarget'" "Cyan"
    } elseif ($override -eq "desktop") {
        $captureTarget = "desktop"
        Write-Log "Overriding to desktop capture" "Cyan"
    } elseif ($override -eq "auto") {
        $neuroSyncWindow = Find-NeuroSyncWindow
        if ($neuroSyncWindow) {
            $captureTarget = "title=$($neuroSyncWindow.Title)"
            Write-Log "Automatically selected window: '$($neuroSyncWindow.Title)'" "Green"
            Write-Log "Overriding to window capture: '$captureTarget'" "Cyan"
        } else {
            Write-Log "No suitable window found, keeping previous capture target: '$captureTarget'" "Yellow"
        }
    } elseif ($override -eq "select") {
        # Interactive window selection
        $selectedWindow = Select-Window
        if ($selectedWindow) {
            $captureTarget = "title=$($selectedWindow.Title)"
            Write-Log "Selected window: '$($selectedWindow.Title)'" "Green"
            Write-Log "Overriding to window capture: '$captureTarget'" "Cyan"
        } else {
            Write-Log "Window selection canceled, using previous capture target: '$captureTarget'" "Yellow"
        }
    }

    # Build FFmpeg arguments array
    # IMPORTANT: Build this as an array to properly handle spaces in arguments
    $ffmpegArgs = @(
        "-y",
        "-f", "gdigrab"
    )
    
    # Add input with proper quoting for window titles
    if ($captureTarget -match "^title=(.+)$") {
        # Extract the window title and properly quote it
        $windowTitle = $matches[1]
        
        # First check if window with exact title exists
        Write-Log "Looking for window with title '$windowTitle'..." "Cyan"
        
        # Load necessary Windows API functions
        Add-Type @"
        using System;
        using System.Runtime.InteropServices;
        public class WindowFinder {
            [DllImport("user32.dll")]
            public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
            
            [DllImport("user32.dll")]
            public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
            
            [DllImport("user32.dll")]
            [return: MarshalAs(UnmanagedType.Bool)]
            public static extern bool IsWindowVisible(IntPtr hWnd);
            
            public struct RECT {
                public int Left;
                public int Top;
                public int Right;
                public int Bottom;
            }
        }
"@
        
        # Try with exact match first
        $windowHandle = [WindowFinder]::FindWindow($null, $windowTitle)
        
        # If not found, try with trimmed version (to handle trailing spaces)
        if ($windowHandle -eq [IntPtr]::Zero) {
            Write-Log "Window with exact title not found, trying with whitespace trimming..." "Yellow"
            $trimmedTitle = $windowTitle.Trim()
            
            # Get all windows and look for a case-insensitive match after trimming
            $windows = Get-WindowsList
            foreach ($window in $windows) {
                if ($window.Title.Trim() -eq $trimmedTitle) {
                    Write-Log "Found window with trimmed title: '$($window.Title)'" "Green"
                    # Use the actual window title (with spaces) for capture
                    $captureTarget = "title=$($window.Title)"
                    $windowTitle = $window.Title
                    $windowHandle = $window.Handle
                    break
                }
            }
        }
        
        if ($windowHandle -eq [IntPtr]::Zero) {
            Write-Log "WARNING: Window with title '$windowTitle' not found. Will try partial match." "Yellow"
            # Fall back to searching for window with partial title match 
            # This would require more complex logic with EnumWindows API call
            Write-Log "Falling back to standard FFmpeg window capture." "Yellow"
            
            # Use desktop capture as fallback with warning
            Write-Log "WARNING: Window not found - falling back to desktop capture" "Red"
            $ffmpegArgs += @(
                "-draw_mouse", "1",
                "-framerate", $frameRate,
                "-i", "desktop"
            )
        } else {
            # Get window dimensions
            $rect = New-Object WindowFinder+RECT
            [void][WindowFinder]::GetWindowRect($windowHandle, [ref]$rect)
            $width = $rect.Right - $rect.Left
            $width = [Math]::Max($width, 2) # Ensure valid width
            $height = $rect.Bottom - $rect.Top
            $height = [Math]::Max($height, 2) # Ensure valid height
            
            Write-Log "Found window '$windowTitle' with dimensions: ${width}x${height}" "Green"
            Write-Log "Window position: Left=$($rect.Left), Top=$($rect.Top)" "Green"
            
            # For window capture, we need to include the window dimensions
            $ffmpegArgs += @(
                "-draw_mouse", "1",
                "-framerate", $frameRate,
                "-offset_x", "$($rect.Left)",  # Use actual window position
                "-offset_y", "$($rect.Top)",   # Use actual window position
                "-video_size", "${width}x${height}" # Explicit dimensions
            )
            
            # Add show_region parameter if enabled
            if ($showRegion) {
                $ffmpegArgs += @("-show_region", "1")
            }
            
            # Use properly quoted window title
            $ffmpegArgs += @("-i", "title=`"$windowTitle`"")
            
            Write-Log "Window capture mode: Capturing window '$windowTitle' at position ($($rect.Left),$($rect.Top)) with size ${width}x${height}" "Green"
        }
    } else {
        # For desktop or pid capture
        $ffmpegArgs += @(
            "-draw_mouse", "1",
            "-framerate", $frameRate,
            "-i", $captureTarget
        )
    }

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

    $debugMode = Read-Host "Run in debug mode? (see all FFmpeg output) (y/n)"

    try {
        if ($debugMode -eq "y") {
            # Run FFmpeg in the current window to see all output
            Write-Log "Running FFmpeg in debug mode. Press Ctrl+C to stop." "Yellow"
            
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
        } else {
            # Start FFmpeg process
            $ffmpegProcess = Start-Process -FilePath "ffmpeg" -ArgumentList $ffmpegArgs -PassThru -NoNewWindow
            
            Write-Log "FFmpeg started with PID $($ffmpegProcess.Id)" "Green"
            Write-Log "Streaming to Twitch... Press Ctrl+C to stop." "Green"
            
            # Display a heartbeat to show script is still running
            $counter = 0
            $startTime = Get-Date
            $running = $true
            
            Write-Log "Press 'q' to stop streaming." "Yellow"
            
            while ($running -and -not $ffmpegProcess.HasExited) {
                $counter++
                if ($counter % 10 -eq 0) {
                    $runTime = [Math]::Round(((Get-Date) - $startTime).TotalSeconds)
                    Write-Host "." -NoNewline -ForegroundColor Green
                    Add-Content -Path $logFilePath -Value "." -NoNewline
                    
                    # Every minute, display a more substantial update
                    if ($counter % 60 -eq 0) {
                        Write-Host " Streaming for $runTime seconds" -ForegroundColor Cyan
                    }
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
            }
            
            # Check exit code
            if ($ffmpegProcess.HasExited) {
                if ($ffmpegProcess.ExitCode -ne 0) {
                    Write-Log "`nFFmpeg exited with code $($ffmpegProcess.ExitCode). This indicates an error." "Red"
                    Write-Log "Try running in debug mode to see detailed error messages." "Yellow"
                } else {
                    Write-Log "`nStreaming has ended successfully." "Green"
                }
            } else {
                Write-Log "`nFFmpeg process is still running. Attempting to close." "Yellow"
                try {
                    $ffmpegProcess.Kill()
                    Write-Log "FFmpeg process terminated." "Green"
                } catch {
                    Write-Log "Error terminating FFmpeg: $_" "Red"
                }
            }
        }
    } catch {
        Write-Log "ERROR: Failed to start FFmpeg: $_" "Red"
        Write-Log "Stack trace: $($_.ScriptStackTrace)" "Red"
        Write-Log "Press any key to exit..."
        $null = $host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        exit 1
    }

    # Final log entry
    Write-Log "--- Streaming Session Ended: $(Get-Date) ---" "Cyan"

    # Keep the window open so user can see any error messages
    Write-Log "Press any key to exit..."
    $null = $host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
} catch {
    Write-Log "CRITICAL ERROR: $($_.Exception.Message)" "Red" 
    Write-Log "Error occurred at line: $($_.InvocationInfo.ScriptLineNumber)" "Red"
    Write-Log "Stack trace: $($_.ScriptStackTrace)" "Red"
    Write-Log "Press any key to exit..."
    $null = $host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}