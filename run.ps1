# NeuroSync Setup Script
# This script will set up all prerequisites and launch NeuroSync

# Define log file location
$logFile = "$PSScriptRoot\neurosync_setup_log.txt"

# Function to log messages
function Log-Message {
    param($message)
    Write-Host $message
    Add-Content -Path $logFile -Value "$(Get-Date) - $message"
}

Log-Message "Starting NeuroSync setup..."

# Create temp directory for downloads
$tempDir = "$PSScriptRoot\NeuroSync_Setup_Temp"
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
Log-Message "Created temporary directory at $tempDir"

# Create project directory
$projectDir = "$PSScriptRoot\NeuroSync"
if (-not (Test-Path $projectDir)) {
    New-Item -ItemType Directory -Force -Path $projectDir | Out-Null
    Log-Message "Created project directory at $projectDir"
} else {
    Log-Message "Project directory already exists at $projectDir"
}

# Check if Git is installed
$gitInstalled = $null -ne (Get-Command git -ErrorAction SilentlyContinue)
if (-not $gitInstalled) {
    Log-Message "Git not found. Downloading and installing Git..."
    $gitUrl = "https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe"
    $gitInstaller = "$tempDir\GitInstaller.exe"
    
    # Try curl first, fall back to Invoke-WebRequest if curl fails
    try {
        curl.exe -L $gitUrl -o $gitInstaller
    }
    catch {
        Log-Message "curl failed, falling back to Invoke-WebRequest..."
        Invoke-WebRequest -Uri $gitUrl -OutFile $gitInstaller
    }
    
    Start-Process -FilePath $gitInstaller -ArgumentList "/VERYSILENT", "/NORESTART" -Wait
    Log-Message "Git installed successfully."
    # Refresh environment to use Git in the current session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
} else {
    Log-Message "Git is already installed."
}

# Clone GitHub repositories only if they don't exist
Set-Location -Path $projectDir

# Check and clone NeuroSync Player repository
$playerRepoPath = "$projectDir\NeuroSync_Player_Vt"
if (-not (Test-Path $playerRepoPath)) {
    Log-Message "Cloning NeuroSync Player repository..."
    Start-Process -FilePath "git" -ArgumentList "clone https://github.com/UD1sto/NeuroSync_Player_Vt" -Wait -NoNewWindow
    Log-Message "NeuroSync Player repository cloned successfully."
} else {
    Log-Message "NeuroSync Player repository already exists. Updating..."
    Set-Location -Path $playerRepoPath
    Start-Process -FilePath "git" -ArgumentList "pull" -Wait -NoNewWindow
    Log-Message "NeuroSync Player repository updated."
}

# Check and clone NeuroSync Local API repository
$apiRepoPath = "$projectDir\NeuroSync_Local_API"
if (-not (Test-Path $apiRepoPath)) {
    Log-Message "Cloning NeuroSync Local API repository..."
    Set-Location -Path $projectDir
    Start-Process -FilePath "git" -ArgumentList "clone https://github.com/AnimaVR/NeuroSync_Local_API" -Wait -NoNewWindow
    Log-Message "NeuroSync Local API repository cloned successfully."
} else {
    Log-Message "NeuroSync Local API repository already exists. Updating..."
    Set-Location -Path $apiRepoPath
    Start-Process -FilePath "git" -ArgumentList "pull" -Wait -NoNewWindow
    Log-Message "NeuroSync Local API repository updated."
}

# Check if Python is installed with proper version
$pythonInstalled = $null -ne (Get-Command py -ErrorAction SilentlyContinue)
$pythonVersion = ""
if ($pythonInstalled) {
    try {
        $pythonVersion = (py -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')") | Out-String
        $pythonVersion = $pythonVersion.Trim()
        Log-Message "Python version $pythonVersion is installed."
    } catch {
        $pythonInstalled = $false
        Log-Message "Error checking Python version: $_"
    }
}

# Install Python 3.13.1 if not already installed or version doesn't match
if (-not $pythonInstalled -or $pythonVersion -ne "3.13.1") {
    Log-Message "Python 3.13.1 not found. Downloading and installing..."
    $pythonUrl = "https://www.python.org/ftp/python/3.13.1/python-3.13.1-amd64.exe"
    $pythonInstaller = "$tempDir\python-3.13.1-amd64.exe"
    
    # Download Python installer using curl
    Start-Process -FilePath "curl" -ArgumentList "-o", $pythonInstaller, $pythonUrl -Wait -NoNewWindow
    
    Log-Message "Installing Python 3.13.1..."
    Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0" -Wait
    Log-Message "Python 3.13.1 installed successfully."
} else {
    Log-Message "Python 3.13.1 is already installed."
}

# Check if pip and gdown are installed
$pipInstalled = $null -ne (Get-Command pip -ErrorAction SilentlyContinue)
if ($pipInstalled) {
    # Check if gdown is installed
    $gdownInstalled = $false
    try {
        $gdownCheck = py -c "import gdown; print('installed')" 2>$null
        $gdownInstalled = $gdownCheck -eq "installed"
    } catch {
        $gdownInstalled = $false
    }
    
    if (-not $gdownInstalled) {
        Log-Message "Installing gdown Python package for Google Drive downloads..."
        py -m pip install gdown
    } else {
        Log-Message "gdown is already installed."
    }
} else {
    Log-Message "Installing pip and gdown..."
    py -m ensurepip
    py -m pip install gdown
}

# Function to download from Google Drive using PowerShell native methods
function Download-GoogleDriveFile {
    param(
        [string]$fileId,
        [string]$destination
    )
    
    Log-Message "Attempting to download Google Drive file using PowerShell method..."
    
    try {
        # Create a web session
        $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
        
        # Get the initial page to find the confirmation token
        $initialResponse = Invoke-WebRequest -Uri "https://drive.google.com/uc?id=$fileId&export=download" -SessionVariable session
        
        # Look for the download form
        if ($initialResponse.Content -match 'confirm=([0-9A-Za-z]+)') {
            $confirmCode = $matches[1]
            Log-Message "Found confirmation code: $confirmCode"
            
            # Build the final download URL with the confirmation code
            $downloadUrl = "https://drive.google.com/uc?export=download&confirm=$confirmCode&id=$fileId"
            
            # Download the file
            Log-Message "Downloading file..."
            Invoke-WebRequest -Uri $downloadUrl -OutFile $destination -WebSession $session
            
            # Verify the download
            if (Test-Path $destination) {
                $fileSize = (Get-Item $destination).Length
                Log-Message "File downloaded. Size: $fileSize bytes."
                return $true
            } else {
                Log-Message "File download failed - file not found after download."
                return $false
            }
        } else {
            Log-Message "Could not find confirmation code in Google Drive response."
            return $false
        }
    } catch {
        Log-Message "Error downloading from Google Drive: $_"
        return $false
    }
}

# Check if game files are already downloaded and extracted
$gameExePath = "$projectDir\Game\NEUROSYNC_Demo_Build\Windows\NEUROSYNC.exe"
if (-not (Test-Path $gameExePath)) {
    Log-Message "Game files not found. Downloading from CDN..."
    $outputPath = "$tempDir\NeuroSync_Game.zip"
    
    # Use the CDN URL for direct download
    $cdnUrl = "https://unreal-demo.b-cdn.net/NEUROSYNC_Demo_Build.zip"
    $downloadSuccess = $false
    
    # Check if curl is installed
    $curlInstalled = $null -ne (Get-Command curl.exe -ErrorAction SilentlyContinue)
    if (-not $curlInstalled) {
        # Try to find curl in Windows\System32
        if (Test-Path "$env:SystemRoot\System32\curl.exe") {
            $env:Path += ";$env:SystemRoot\System32"
            $curlInstalled = $true
            Log-Message "Found curl in System32."
        } else {
            Log-Message "curl not found. Installing curl..."
            try {
                # Download curl executable
                $curlDownloadUrl = "https://curl.se/windows/dl-8.6.0_2/curl-8.6.0_2-win64-mingw.zip"
                $curlZip = "$tempDir\curl.zip"
                $curlExtractPath = "$tempDir\curl"
                
                # Use Invoke-WebRequest for this small download
                Invoke-WebRequest -Uri $curlDownloadUrl -OutFile $curlZip -UseBasicParsing
                
                # Extract curl
                Expand-Archive -Path $curlZip -DestinationPath $curlExtractPath -Force
                
                # Find the curl executable in the extracted directory
                $curlExe = (Get-ChildItem -Path $curlExtractPath -Filter "curl.exe" -Recurse).FullName
                
                # Copy to a location in PATH
                Copy-Item -Path $curlExe -Destination "$PSScriptRoot\curl.exe" -Force
                Log-Message "curl installed to $PSScriptRoot\curl.exe"
                
                # Set curl path for this session
                $env:Path += ";$PSScriptRoot"
                $curlInstalled = $true
            } catch {
                Log-Message "Failed to install curl: $_"
            }
        }
    }
    
    # Try using curl for download (fastest method)
    if ($curlInstalled) {
        try {
            Log-Message "Downloading with curl (fastest method)..."
            
            # Use curl with progress bar and resume capability
            $curlArgs = "-L", "-o", $outputPath, "--progress-bar", "--retry", "3", "--retry-delay", "2", "--retry-max-time", "60", $cdnUrl
            $curlProcess = Start-Process -FilePath "curl" -ArgumentList $curlArgs -NoNewWindow -Wait -PassThru
            
            if ($curlProcess.ExitCode -eq 0) {
                $fileSize = (Get-Item $outputPath).Length
                if ($fileSize -gt 1000000) {
                    $downloadSuccess = $true
                    Log-Message "Successfully downloaded with curl. File size: $fileSize bytes."
                } else {
                    Log-Message "File downloaded with curl but seems too small ($fileSize bytes)."
                }
            } else {
                Log-Message "curl download failed with exit code $($curlProcess.ExitCode)"
            }
        } catch {
            Log-Message "curl download attempt failed: $_"
        }
    }
    
    # If curl failed, try using BITS transfer
    if (-not $downloadSuccess) {
        try {
            Log-Message "Trying BITS transfer as fallback..."
            
            # Check if BITS module is available
            if (Get-Module -ListAvailable -Name BitsTransfer) {
                Import-Module BitsTransfer
                Start-BitsTransfer -Source $cdnUrl -Destination $outputPath -DisplayName "NeuroSync Download" -Description "Downloading game files" -Priority High
                
                if (Test-Path $outputPath) {
                    $fileSize = (Get-Item $outputPath).Length
                    if ($fileSize -gt 1000000) {
                        $downloadSuccess = $true
                        Log-Message "Successfully downloaded using BITS. File size: $fileSize bytes."
                    }
                }
            } else {
                Log-Message "BITS Transfer module not available, trying .NET WebClient."
            }
        } catch {
            Log-Message "BITS download failed: $_"
        }
    }
    
    # If still not successful, try .NET WebClient
    if (-not $downloadSuccess) {
        try {
            Log-Message "Downloading using .NET WebClient..."
            $webClient = New-Object System.Net.WebClient
            $webClient.DownloadFile($cdnUrl, $outputPath)
            
            if (Test-Path $outputPath) {
                $fileSize = (Get-Item $outputPath).Length
                if ($fileSize -gt 1000000) {
                    $downloadSuccess = $true
                    Log-Message "Successfully downloaded using WebClient. File size: $fileSize bytes."
                } else {
                    Log-Message "Downloaded file seems too small ($fileSize bytes)."
                }
            }
        } catch {
            Log-Message "WebClient download failed: $_"
        }
    }
    
    # Final fallback to Invoke-WebRequest (slowest)
    if (-not $downloadSuccess) {
        try {
            Log-Message "Falling back to Invoke-WebRequest (slowest method)..."
            Invoke-WebRequest -Uri $cdnUrl -OutFile $outputPath -UseBasicParsing
            
            if (Test-Path $outputPath) {
                $fileSize = (Get-Item $outputPath).Length
                if ($fileSize -gt 1000000) {
                    $downloadSuccess = $true
                    Log-Message "Successfully downloaded. File size: $fileSize bytes."
                } else {
                    Log-Message "WARNING: Downloaded file seems too small ($fileSize bytes)."
                }
            }
        } catch {
            Log-Message "ERROR: Failed to download file: $_"
        }
    }
    
    # If download failed, offer manual download option
    if (-not $downloadSuccess) {
        Log-Message "WARNING: Automated download failed."
        Log-Message "Please download the file manually from this link:"
        Log-Message "https://unreal-demo.b-cdn.net/NEUROSYNC_Demo_Build.zip"
        Log-Message "After downloading, please save it to: $outputPath"
        
        $userResponse = Read-Host "Press Enter after you've saved the file to the correct location (or type 'skip' to proceed without it)"
        
        if ($userResponse -ne "skip") {
            if (Test-Path $outputPath) {
                $fileSize = (Get-Item $outputPath).Length
                if ($fileSize -gt 1000000) {
                    $downloadSuccess = $true
                    Log-Message "Manual download confirmed. File size: $fileSize bytes."
                } else {
                    Log-Message "WARNING: Manually downloaded file seems too small ($fileSize bytes)."
                }
            } else {
                Log-Message "ERROR: File not found at $outputPath after manual download."
                exit 1
            }
        } else {
            Log-Message "Skipping game files as requested. NeuroSync may not function properly."
        }
    }
    
    # Extract the downloaded file if download was successful
    if ($downloadSuccess) {
        Log-Message "Download verified. Extracting game files..."
        
        # Create Game directory if it doesn't exist
        if (-not (Test-Path "$projectDir\Game")) {
            New-Item -ItemType Directory -Force -Path "$projectDir\Game" | Out-Null
        }
        
        # Extract the downloaded file
        try {
            Expand-Archive -Path $outputPath -DestinationPath "$projectDir\Game" -Force
            Log-Message "Game files extracted successfully."
        } catch {
            Log-Message "ERROR: Failed to extract game files: $_"
            Log-Message "The downloaded zip file might be corrupted."
            exit 1
        }
    } else {
        Log-Message "ERROR: All download methods failed. NeuroSync may not function properly."
    }
} else {
    Log-Message "Game files already exist at $gameExePath"
}

# Download and verify model.pth file
$modelPath = "$projectDir\NeuroSync_Local_API\utils\model\model.pth"
$modelDir = Split-Path -Parent $modelPath

# Create model directory if it doesn't exist
if (-not (Test-Path $modelDir)) {
    New-Item -ItemType Directory -Force -Path $modelDir | Out-Null
    Log-Message "Created model directory at $modelDir"
}

# Check if model.pth exists and has valid size
if (-not (Test-Path $modelPath) -or (Get-Item $modelPath).Length -lt 1000000) {
    Log-Message "Downloading model.pth from CDN..."
    $modelUrl = "https://unreal-demo.b-cdn.net/model.pth"
    $modelDownloadSuccess = $false
    
    # Try downloading with curl first
    if ($curlInstalled) {
        try {
            Log-Message "Downloading model.pth with curl..."
            $curlArgs = "-L", "-o", $modelPath, "--progress-bar", "--retry", "3", "--retry-delay", "2", "--retry-max-time", "60", $modelUrl
            $curlProcess = Start-Process -FilePath "curl" -ArgumentList $curlArgs -NoNewWindow -Wait -PassThru
            
            if ($curlProcess.ExitCode -eq 0) {
                $modelSize = (Get-Item $modelPath).Length
                if ($modelSize -gt 1000000) {
                    $modelDownloadSuccess = $true
                    Log-Message "Successfully downloaded model.pth. File size: $modelSize bytes."
                } else {
                    Log-Message "Model file downloaded but seems too small ($modelSize bytes)."
                }
            } else {
                Log-Message "curl download failed with exit code $($curlProcess.ExitCode)"
            }
        } catch {
            Log-Message "curl download attempt failed: $_"
        }
    }
    
    # If curl failed, try BITS transfer
    if (-not $modelDownloadSuccess) {
        try {
            Log-Message "Trying BITS transfer for model.pth..."
            if (Get-Module -ListAvailable -Name BitsTransfer) {
                Import-Module BitsTransfer
                Start-BitsTransfer -Source $modelUrl -Destination $modelPath -DisplayName "Model Download" -Description "Downloading model file" -Priority High
                
                if (Test-Path $modelPath) {
                    $modelSize = (Get-Item $modelPath).Length
                    if ($modelSize -gt 1000000) {
                        $modelDownloadSuccess = $true
                        Log-Message "Successfully downloaded model.pth using BITS. File size: $modelSize bytes."
                    }
                }
            }
        } catch {
            Log-Message "BITS download failed: $_"
        }
    }
    
    # If still not successful, try WebClient
    if (-not $modelDownloadSuccess) {
        try {
            Log-Message "Downloading model.pth using WebClient..."
            $webClient = New-Object System.Net.WebClient
            $webClient.DownloadFile($modelUrl, $modelPath)
            
            if (Test-Path $modelPath) {
                $modelSize = (Get-Item $modelPath).Length
                if ($modelSize -gt 1000000) {
                    $modelDownloadSuccess = $true
                    Log-Message "Successfully downloaded model.pth using WebClient. File size: $modelSize bytes."
                }
            }
        } catch {
            Log-Message "WebClient download failed: $_"
        }
    }
    
    # If all automated methods failed, offer manual download
    if (-not $modelDownloadSuccess) {
        Log-Message "WARNING: Automated model download failed."
        Log-Message "Please download the model file manually from this link:"
        Log-Message "https://unreal-demo.b-cdn.net/model.pth"
        Log-Message "After downloading, please save it to: $modelPath"
        
        $userResponse = Read-Host "Press Enter after you've saved the model file to the correct location (or type 'skip' to proceed without it)"
        
        if ($userResponse -ne "skip") {
            if (Test-Path $modelPath) {
                $modelSize = (Get-Item $modelPath).Length
                if ($modelSize -gt 1000000) {
                    Log-Message "Manual model download confirmed. File size: $modelSize bytes."
                } else {
                    Log-Message "WARNING: Manually downloaded model file seems too small ($modelSize bytes)."
                }
            } else {
                Log-Message "ERROR: Model file not found at $modelPath after manual download."
                exit 1
            }
        } else {
            Log-Message "Skipping model download as requested. NeuroSync may not function properly."
        }
    }
} else {
    Log-Message "Model file already exists at $modelPath"
}

# Check if GPU is available
$hasNvidiaGPU = $false
try {
    $gpuInfo = Get-WmiObject -Class Win32_VideoController
    foreach ($gpu in $gpuInfo) {
        if ($gpu.Name -like "*NVIDIA*") {
            $hasNvidiaGPU = $true
            Log-Message "NVIDIA GPU detected: $($gpu.Name)"
            break
        }
    }
    if (-not $hasNvidiaGPU) {
        Log-Message "WARNING: No NVIDIA GPU detected. CUDA acceleration will not be available."
    }
} catch {
    Log-Message "Failed to detect GPU: $_"
}
# Install CUDA and cuDNN only if NVIDIA GPU is detected and not already installed

if ($hasNvidiaGPU) {
    # Check if CUDA is installed by looking for nvcc in Program Files
    $cudaInstalled = $false
    $nvccPath = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin\nvcc.exe"
    
    if (Test-Path $nvccPath) {
        $cudaInstalled = $true
        Log-Message "CUDA 12.4 is already installed."
    } else {
        Log-Message "CUDA 12.4 not found at expected path."
    }
    
    if (-not $cudaInstalled) {
        Log-Message "Installing CUDA Toolkit 12.4..."
        
        # First, try to remove any existing CUDA installations
        Log-Message "Checking for existing CUDA installations..."
        $cudaPath = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA"
        if (Test-Path $cudaPath) {
            Get-ChildItem $cudaPath -Directory | ForEach-Object {
                $version = $_.Name
                Log-Message "Found CUDA $version - attempting to uninstall..."
                
                # Use Windows uninstaller to remove CUDA
                $uninstallString = Get-WmiObject -Class Win32_Product | 
                    Where-Object { $_.Name -like "*CUDA*$version*" } |
                    Select-Object -ExpandProperty UninstallString
                
                if ($uninstallString) {
                    Start-Process "msiexec.exe" -ArgumentList "/x $uninstallString /quiet /norestart" -Wait
                    Log-Message "Uninstalled CUDA $version"
                }
            }
        }

        $cudaUrl = "https://developer.download.nvidia.com/compute/cuda/12.4.1/local_installers/cuda_12.4.1_551.78_windows.exe"
        $cudaInstaller = "$tempDir\cuda_12.4.1_551.78_windows.exe"
        
        # Download CUDA installer using curl
        Log-Message "Downloading CUDA installer with curl..."
        $curlArgs = "-L", "-o", $cudaInstaller, "--progress-bar", "--retry", "3", "--retry-delay", "2", "--retry-max-time", "60", $cudaUrl
        $curlProcess = Start-Process -FilePath "curl" -ArgumentList $curlArgs -NoNewWindow -Wait -PassThru
        
        if ($curlProcess.ExitCode -ne 0) {
            Log-Message "curl download failed with exit code $($curlProcess.ExitCode). Falling back to Invoke-WebRequest..."
            Invoke-WebRequest -Uri $cudaUrl -OutFile $cudaInstaller
        }
        
        # Silent install for CUDA with specific version only
        Log-Message "Installing CUDA 12.4 (this may take a while)..."
        Start-Process -FilePath $cudaInstaller -ArgumentList "-s", "CUDA_VERSION=12.4" -Wait
        Log-Message "CUDA Toolkit installation completed."
        
        # Verify installation by checking path again
        if (Test-Path $nvccPath) {
            Log-Message "CUDA 12.4 installation verified successfully."
        } else {
            Log-Message "Warning: CUDA installation completed but nvcc.exe not found at expected path."
        }
    }
    
    # Check if cuDNN is installed (more difficult to check directly)
    # For simplicity, we'll check for a common cuDNN file
    $cudnnInstalled = Test-Path "$env:CUDA_PATH\bin\cudnn*"
    if (-not $cudnnInstalled) {
        # Install cuDNN
        Log-Message "Downloading cuDNN with curl..."
        $cuDnnUrl = "https://developer.download.nvidia.com/compute/cudnn/9.8.0/local_installers/cudnn_9.8.0_windows.exe"
        $cuDnnInstaller = "$tempDir\cudnn_9.8.0_windows.exe"
        
        # Download cuDNN installer using curl
        $curlArgs = "-L", "-o", $cuDnnInstaller, "--progress-bar", "--retry", "3", "--retry-delay", "2", "--retry-max-time", "60", $cuDnnUrl
        $curlProcess = Start-Process -FilePath "curl" -ArgumentList $curlArgs -NoNewWindow -Wait -PassThru
        
        if ($curlProcess.ExitCode -ne 0) {
            Log-Message "curl download failed with exit code $($curlProcess.ExitCode). Falling back to Invoke-WebRequest..."
            Invoke-WebRequest -Uri $cuDnnUrl -OutFile $cuDnnInstaller
        }
        
        Log-Message "Installing cuDNN silently..."
        # Use silent installation flags to avoid the interactive interface
        # /s for silent mode, /norestart to prevent automatic restart
        Start-Process -FilePath $cuDnnInstaller -ArgumentList "/s /norestart /qn" -Wait
        Log-Message "cuDNN installed successfully."
    } else {
        Log-Message "cuDNN is already installed."
    }
}

# Check if FFmpeg is installed
$ffmpegInstalled = $null -ne (Get-Command ffmpeg -ErrorAction SilentlyContinue)
if (-not $ffmpegInstalled) {
    Log-Message "FFmpeg not found. Downloading and installing..."
    
    $ffmpegUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    $ffmpegZip = "$tempDir\ffmpeg.zip"
    $ffmpegExtractPath = "$tempDir\ffmpeg"
    
    # Download FFmpeg using curl
    Log-Message "Downloading FFmpeg with curl..."
    $curlArgs = "-L", "-o", $ffmpegZip, "--progress-bar", "--retry", "3", "--retry-delay", "2", "--retry-max-time", "60", $ffmpegUrl
    $curlProcess = Start-Process -FilePath "curl" -ArgumentList $curlArgs -NoNewWindow -Wait -PassThru
    
    if ($curlProcess.ExitCode -ne 0) {
        Log-Message "curl download failed with exit code $($curlProcess.ExitCode). Falling back to Invoke-WebRequest..."
        Invoke-WebRequest -Uri $ffmpegUrl -OutFile $ffmpegZip
    }
    
    Expand-Archive -Path $ffmpegZip -DestinationPath $ffmpegExtractPath -Force
    
    # Move FFmpeg to script directory and add to PATH
    $ffmpegBinPath = (Get-ChildItem -Path $ffmpegExtractPath -Filter "bin" -Recurse -Directory).FullName
    $ffmpegDestination = "$PSScriptRoot\FFmpeg"
    New-Item -ItemType Directory -Force -Path $ffmpegDestination | Out-Null
    Copy-Item -Path "$ffmpegBinPath\*" -Destination $ffmpegDestination -Recurse -Force
    
    # Add FFmpeg to PATH if not already there
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    if (-not $currentPath.Contains($ffmpegDestination)) {
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$ffmpegDestination", "Machine")
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
        Log-Message "Added FFmpeg to system PATH."
    }
    
    Log-Message "FFmpeg installed successfully."
} else {
    Log-Message "FFmpeg is already installed."
}

# Check and install Python packages
function Is-PackageInstalled {
    param($packageName)
    
    try {
        $output = py -c "try: import $packageName; print('installed') except ImportError: print('not installed')" 2>$null
        return $output -eq "installed"
    } catch {
        return $false
    }
}

# Install Python packages for the API
Log-Message "Checking and installing Python packages for the API..."
$packages = @(
    "flask",
    "numpy"
)

foreach ($package in $packages) {
    if (Is-PackageInstalled $package) {
        Log-Message "$package is already installed."
    } else {
        py -m pip install $package
        Log-Message "Installed $package"
    }
}

# Install PyTorch with CUDA if GPU available, otherwise CPU version
$pytorchInstalled = $false
try {
    $pytorchCheck = py -c "import torch; print('installed')" 2>$null
    $pytorchInstalled = $pytorchCheck -eq "installed"
} catch {
    $pytorchInstalled = $false
}

if (-not $pytorchInstalled) {
    if ($hasNvidiaGPU) {
        Log-Message "Installing PyTorch with CUDA support..."
        py -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
    } else {
        Log-Message "Installing PyTorch (CPU version)..."
        py -m pip install torch torchvision torchaudio
    }
} else {
    Log-Message "PyTorch is already installed."
}

# Install remaining packages
$morePackages = @(
    "librosa",
    "pygame",
    "pandas",
    "timecode",
    "pydub",
    "audioop-lts"
)

foreach ($package in $morePackages) {
    if (Is-PackageInstalled $package) {
        Log-Message "$package is already installed."
    } else {
        py -m pip install $package
        Log-Message "Installed $package"
    }
}

# Install requirements from the cloned repositories
Log-Message "Checking requirements from NeuroSync Player..."
if (Test-Path "$projectDir\NeuroSync_Player_Vt\requirements.txt") {
    py -m pip install -r "$projectDir\NeuroSync_Player_Vt\requirements.txt"
    Log-Message "NeuroSync Player requirements installed."
}

Log-Message "Checking requirements from NeuroSync Local API..."
if (Test-Path "$projectDir\NeuroSync_Local_API\requirements.txt") {
    py -m pip install -r "$projectDir\NeuroSync_Local_API\requirements.txt"
    Log-Message "NeuroSync Local API requirements installed."
}

# Initialize the local API
Log-Message "Starting NeuroSync Local API..."
$apiProcess = Start-Process -FilePath "py" -ArgumentList "$projectDir\NeuroSync_Local_API\neurosync_local_api.py" -PassThru -WindowStyle Hidden

# Initialize the face to LLM setup
Log-Message "Initializing LLM to face integration..."
$llmProcess = Start-Process -FilePath "py" -ArgumentList "$projectDir\NeuroSync_Player_Vt\llm_to_face.py" -PassThru -WindowStyle Hidden

# Wait for services to initialize
Log-Message "Waiting for services to initialize (10 seconds)..."
Start-Sleep -Seconds 10
# Download and install Visual C++ Runtime
Log-Message "Checking for Visual C++ Runtime..."

# Better check for Visual C++ Runtime using multiple files
$vcRuntimeFiles = @(
    "C:\Windows\System32\vcruntime140.dll",
    "C:\Windows\System32\msvcp140.dll",
    "C:\Windows\System32\vcruntime140_1.dll"
)

$vcRuntimeInstalled = ($vcRuntimeFiles | ForEach-Object { Test-Path $_ }) -notcontains $false

if (-not $vcRuntimeInstalled) {
    Log-Message "Visual C++ Runtime not fully installed. Downloading and installing..."
    
    # Use a more reliable Visual C++ 2015-2022 Redistributable link
    $vcRedistUrl = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
    $vcRedistPath = "$tempDir\vc_redist.x64.exe"
    
    # Download the installer
    try {
        if ($null -ne (Get-Command curl.exe -ErrorAction SilentlyContinue)) {
            Log-Message "Downloading Visual C++ Runtime with curl..."
            Start-Process -FilePath "curl.exe" -ArgumentList "-L", "-o", $vcRedistPath, "--retry", "3", $vcRedistUrl -Wait -NoNewWindow
        } else {
            Log-Message "Downloading Visual C++ Runtime with Invoke-WebRequest..."
            Invoke-WebRequest -Uri $vcRedistUrl -OutFile $vcRedistPath -UseBasicParsing
        }
        
        if (-not (Test-Path $vcRedistPath)) {
            throw "Download failed - installer not found"
        }
        
        # Use stronger silent installation flags
        Log-Message "Installing Visual C++ Runtime silently..."
        $process = Start-Process -FilePath $vcRedistPath -ArgumentList "/install", "/quiet", "/norestart", "/log", "$tempDir\vc_redist_install.log" -Wait -PassThru -NoNewWindow
        
        if ($process.ExitCode -ne 0 -and $process.ExitCode -ne 3010) {
            Log-Message "WARNING: Visual C++ Runtime installer returned exit code $($process.ExitCode). Installation might have failed."
            Log-Message "Checking if installation was successful despite error..."
            
            # Re-check if the files exist now
            $vcRuntimeInstalled = ($vcRuntimeFiles | ForEach-Object { Test-Path $_ }) -notcontains $false
            
            if ($vcRuntimeInstalled) {
                Log-Message "Visual C++ Runtime files found. Installation appears to be successful."
            } else {
                Log-Message "WARNING: Visual C++ Runtime files not found. You may need to install manually."
                Log-Message "For manual installation, visit: https://aka.ms/vs/17/release/vc_redist.x64.exe"
                
                # Optionally show a message to the user for manual installation
                $userResponse = Read-Host "Would you like to attempt manual installation now? (y/n)"
                if ($userResponse -eq 'y') {
                    Start-Process -FilePath $vcRedistPath
                    Read-Host "Press Enter after completing the manual installation"
                }
            }
        } else {
            Log-Message "Visual C++ Runtime installed successfully."
        }
    } catch {
        Log-Message "ERROR: Failed to install Visual C++ Runtime: $_"
        Log-Message "You may need to install Visual C++ Runtime manually."
        Log-Message "For manual installation, visit: https://aka.ms/vs/17/release/vc_redist.x64.exe"
    }
} else {
    Log-Message "Visual C++ Runtime is already installed."
}

# Launch the game
Log-Message "Launching NeuroSync..."
$gameExePath = "$projectDir\Game\NEUROSYNC_Demo_Build\Windows\NEUROSYNC.exe"
if (Test-Path $gameExePath) {
    $gameProcess = Start-Process -FilePath $gameExePath -PassThru
    Log-Message "NeuroSync launched successfully."
    
    # Wait for the game to exit
    $gameProcess.WaitForExit()
    Log-Message "Game closed. Shutting down services..."
    Stop-Process -Id $apiProcess.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $llmProcess.Id -Force -ErrorAction SilentlyContinue
} else {
    Log-Message "ERROR: Game executable not found at $gameExePath"
    Log-Message "Please ensure you downloaded and extracted the game to the correct location."
}

Log-Message "NeuroSync shutdown complete."
