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
$playerRepoPath = "$projectDir\NeuroSync_Player"
if (-not (Test-Path $playerRepoPath)) {
    Log-Message "Cloning NeuroSync Player repository..."
    Start-Process -FilePath "git" -ArgumentList "clone https://github.com/AnimaVR/NeuroSync_Player" -Wait -NoNewWindow
    Log-Message "NeuroSync Player repository cloned successfully."
} else {
    Log-Message "NeuroSync Player repository already exists. Updating..."
    Set-Location -Path $playerRepoPath
    Start-Process -FilePath "git" -ArgumentList "pull" -Wait -NoNewWindow
    Log-Message "NeuroSync Player repository updated."
}

# Check and clone NeuroSync Local API repository
$apiRepoPath = "$projectDir\NeuroSync_Real-Time_API"
if (-not (Test-Path $apiRepoPath)) {
    Log-Message "Cloning NeuroSync Real-Time API repository..."
    Set-Location -Path $projectDir
    Start-Process -FilePath "git" -ArgumentList "clone https://github.com/AnimaVR/NeuroSync_Real-Time_API" -Wait -NoNewWindow
    Log-Message "NeuroSync Real-Time API repository cloned successfully."
} else {
    Log-Message "NeuroSync Real-Time API repository already exists. Updating..."
    Set-Location -Path $apiRepoPath
    Start-Process -FilePath "git" -ArgumentList "pull" -Wait -NoNewWindow
    Log-Message "NeuroSync Real-Time API repository updated."
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
$modelPath = "$projectDir\NeuroSync_Real-Time_API\utils\model\model.pth"
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
        
        # Check if CUDA installer already exists
        if (Test-Path $cudaInstaller) {
            Log-Message "CUDA installer already downloaded, skipping download..."
        } else {
            Log-Message "Downloading CUDA installer with curl..."
            $maxRetries = 3
            $retryCount = 0
            $downloadSuccess = $false

            while (-not $downloadSuccess -and $retryCount -lt $maxRetries) {
                $curlArgs = "-L", "-o", $cudaInstaller, "--progress-bar", "--retry", "3", "--retry-delay", "2", "--retry-max-time", "60", $cudaUrl
                $curlProcess = Start-Process -FilePath "curl" -ArgumentList $curlArgs -NoNewWindow -Wait -PassThru
                
                if ($curlProcess.ExitCode -eq 0) {
                    $downloadSuccess = $true
                    Log-Message "CUDA installer downloaded successfully."
                } else {
                    $retryCount++
                    Log-Message "curl download failed with exit code $($curlProcess.ExitCode). Attempt $retryCount of $maxRetries..."
                    Start-Sleep -Seconds 2
                }
            }

            if (-not $downloadSuccess) {
                Log-Message "Failed to download CUDA installer after $maxRetries attempts."
                throw "Failed to download CUDA installer"
            }
        }
        
        # Use correct format for CUDA 12.4 components installation
        Log-Message "Installing CUDA 12.4 (this may take a while)..."
        Start-Process -FilePath $cudaInstaller -ArgumentList "-s nvcc_12.4 cudart_12.4 visual_studio_integration_12.4" -Wait
        Log-Message "CUDA Toolkit installation completed."
        
        # Verify installation by checking path again
        if (Test-Path $nvccPath) {
            try {
                $cudaVersionInfo = & $nvccPath --version | Out-String
                Log-Message "CUDA installation verified successfully. Version info: $cudaVersionInfo"
            } catch {
                Log-Message "CUDA 12.4 installation verified, but unable to check version details."
            }
        } else {
            Log-Message "Warning: CUDA installation completed but nvcc.exe not found at expected path."
        }
    }
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

# *** MOVED: cuDNN check and installation after PyTorch is installed ***
if ($hasNvidiaGPU) {
    # Improved cuDNN installation check and verification
    Log-Message "Checking for cuDNN installation..."
    $cudnnInstalled = $false
    
    # First check by looking for cuDNN files in CUDA path
    if ($env:CUDA_PATH) {
        if (Test-Path "$env:CUDA_PATH\bin\cudnn*.dll") {
            $cudnnInstalled = $true
            Log-Message "cuDNN found in CUDA path: $env:CUDA_PATH\bin"
        }
    }
    
    # Secondary check for common installation locations
    if (-not $cudnnInstalled) {
        $commonPaths = @(
            "C:\Program Files\NVIDIA\CUDNN\*\bin\cudnn*.dll",
            "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.*\bin\cudnn*.dll"
        )
        
        foreach ($path in $commonPaths) {
            if (Test-Path $path) {
                $cudnnInstalled = $true
                $foundFile = Get-Item $path -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($foundFile) {
                    Log-Message "cuDNN found at $(Split-Path $foundFile.Directory.FullName -Parent)"
                }
                break
            }
        }
    }

    # Python-based cuDNN check now that PyTorch is installed
    try {
        $cudnnAvailable = py -c "import torch; print(torch.backends.cudnn.is_available())" 2>$null
        if ($cudnnAvailable -eq 'True') {
            $cudnnInstalled = $true
            Log-Message "Python-based check: cuDNN is available to PyTorch."
        } else {
            Log-Message "Python check indicates cuDNN is not available to PyTorch."
            $cudnnInstalled = $false
        }
    } catch {
        Log-Message "WARNING: Could not run Python-based cuDNN check. Continuing with installation."
    }

    # Install cuDNN if not found
    if (-not $cudnnInstalled) {
        Log-Message "cuDNN not found or not available. Downloading with curl..."
        $cuDnnUrl = "https://developer.download.nvidia.com/compute/cudnn/9.8.0/local_installers/cudnn_9.8.0_windows.exe"
        $cuDnnInstaller = "$tempDir\cudnn_9.8.0_windows.exe"
        $downloadSuccess = $false
        
        # Download cuDNN installer using curl with retry logic
        $maxRetries = 3
        $retryCount = 0
        
        while (-not $downloadSuccess -and $retryCount -lt $maxRetries) {
            $curlArgs = "-L", "-o", $cuDnnInstaller, "--progress-bar", "--retry", "3", "--retry-delay", "2", "--retry-max-time", "60", $cuDnnUrl
            $curlProcess = Start-Process -FilePath "curl" -ArgumentList $curlArgs -NoNewWindow -Wait -PassThru
            
            if ($curlProcess.ExitCode -eq 0 -and (Test-Path $cuDnnInstaller) -and (Get-Item $cuDnnInstaller).Length -gt 10000000) {
                $downloadSuccess = $true
                Log-Message "cuDNN installer downloaded successfully."
            } else {
                $retryCount++
                Log-Message "curl download failed or resulted in invalid file. Attempt $retryCount of $maxRetries..."
                if (Test-Path $cuDnnInstaller) {
                    $fileSize = (Get-Item $cuDnnInstaller).Length
                    Log-Message "Downloaded file size: $fileSize bytes (expected >10MB)"
                }
                Start-Sleep -Seconds 2
            }
        }
        
        # If curl failed after retries, try Invoke-WebRequest
        if (-not $downloadSuccess) {
            Log-Message "curl download failed after $maxRetries attempts. Falling back to Invoke-WebRequest..."
            try {
                Invoke-WebRequest -Uri $cuDnnUrl -OutFile $cuDnnInstaller -TimeoutSec 300
                if ((Test-Path $cuDnnInstaller) -and (Get-Item $cuDnnInstaller).Length -gt 10000000) {
                    $downloadSuccess = $true
                    Log-Message "cuDNN installer downloaded successfully with Invoke-WebRequest."
                } else {
                    Log-Message "WARNING: Downloaded file seems too small or is missing."
                }
            } catch {
                Log-Message "ERROR: Invoke-WebRequest failed: $_"
            }
        }
        
        # If download was successful, install cuDNN
        if ($downloadSuccess) {
            Log-Message "Installing cuDNN silently..."
            # Use silent installation flags to avoid the interactive interface
            Start-Process -FilePath $cuDnnInstaller -ArgumentList "/s /norestart /qn" -Wait
            
            # Verify installation
            Start-Sleep -Seconds 10
            $cudnnVerified = $false
            
            # Repeat the file-based checks
            if ($env:CUDA_PATH -and (Test-Path "$env:CUDA_PATH\bin\cudnn*.dll")) {
                $cudnnVerified = $true
                Log-Message "cuDNN installation verified successfully in CUDA path."
            } else {
                # Check common installation paths again
                foreach ($path in $commonPaths) {
                    if (Test-Path $path) {
                        $cudnnVerified = $true
                        $foundFile = Get-Item $path -ErrorAction SilentlyContinue | Select-Object -First 1
                        if ($foundFile) {
                            Log-Message "cuDNN installation verified at $(Split-Path $foundFile.Directory.FullName -Parent)"
                        }
                        break
                    }
                }
            }
            
            # Final verification with PyTorch
            try {
                $cudnnAvailable = py -c "import torch; print(torch.backends.cudnn.is_available())" 2>$null
                if ($cudnnAvailable -eq 'True') {
                    $cudnnVerified = $true
                    Log-Message "PyTorch confirms cuDNN is available after installation."
                } else {
                    Log-Message "WARNING: PyTorch reports cuDNN is still not available after installation."
                }
            } catch {
                Log-Message "WARNING: Could not verify cuDNN with PyTorch after installation."
            }
            
            if ($cudnnVerified) {
                Log-Message "cuDNN installed and verified successfully."
            } else {
                Log-Message "WARNING: cuDNN installation completed but verification failed."
                
                # Offer manual installation option
                Log-Message "You may need to manually install cuDNN. Please visit the NVIDIA cuDNN download page:"
                Log-Message "https://developer.nvidia.com/cudnn-downloads"
                
                $userResponse = Read-Host "Would you like to open the NVIDIA cuDNN download page in a browser? (y/n)"
                if ($userResponse -eq "y") {
                    Start-Process "https://developer.nvidia.com/cudnn-downloads"
                }
            }
        } else {
            Log-Message "ERROR: Failed to download cuDNN installer after multiple attempts."
            
            # Offer manual download option
            Log-Message "Please download cuDNN manually from the NVIDIA website:"
            Log-Message "https://developer.nvidia.com/cudnn-downloads"
            
            $userResponse = Read-Host "Would you like to open the NVIDIA cuDNN download page in a browser? (y/n)"
            if ($userResponse -eq "y") {
                Start-Process "https://developer.nvidia.com/cudnn-downloads"
            }
        }
    } else {
        Log-Message "cuDNN is already installed and available to PyTorch."
    }
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
if (Test-Path "$projectDir\NeuroSync_Player\requirements.txt") {
    py -m pip install -r "$projectDir\NeuroSync_Player\requirements.txt"
    Log-Message "NeuroSync Player requirements installed."
}

Log-Message "Checking requirements from NeuroSync Real-Time API..."
if (Test-Path "$projectDir\NeuroSync_Real-Time_API\requirements.txt") {
    py -m pip install -r "$projectDir\NeuroSync_Real-Time_API\requirements.txt"
    Log-Message "NeuroSync Real-Time API requirements installed."
}

# Initialize the Real-Time API
Log-Message "Starting NeuroSync Real-Time API..."
$apiProcess = Start-Process -FilePath "py" -ArgumentList "$projectDir\NeuroSync_Real-Time_API\main.py" -PassThru -WindowStyle Hidden

# Initialize the face to LLM setup
Log-Message "Initializing LLM to face integration..."
$llmProcess = Start-Process -FilePath "py" -ArgumentList "$projectDir\NeuroSync_Player\llm_to_face.py" -PassThru -WindowStyle Hidden

# Wait for services to initialize
Log-Message "Waiting for services to initialize (10 seconds)..."
Start-Sleep -Seconds 10
# Download and install all necessary Visual C++ Runtimes
Log-Message "Checking for Visual C++ Runtime packages..."

# ADDED: Helper function to check if a Visual C++ package is already installed.
function Is-VCRedistInstalled {
    param(
        [string]$partialName
    )
    try {
        # Using Win32_Product can be slow, so some environments prefer registry checks,
        # but Win32_Product is simpler in a quick script scenario.
        $products = Get-WmiObject -Class Win32_Product -ErrorAction SilentlyContinue |
                    Where-Object { $_.Name -like "*$partialName*" }
        return ($products -ne $null)
    } catch {
        return $false
    }
}

# Define all Visual C++ Runtime versions to install
$vcRedistPackages = @(
    @{
        Name = "Visual C++ 2015-2022 Redistributable (x64)";
        Url = "https://aka.ms/vs/17/release/vc_redist.x64.exe";
        Filename = "vc_redist.2022.x64.exe";
        Args = "/install /quiet /norestart /log:$tempDir\vc_redist_2022_x64_install.log";
        CheckName = "Microsoft Visual C++ 2015-2022 Redistributable (x64)"
    },
    @{
        Name = "Visual C++ 2015-2022 Redistributable (x86)";
        Url = "https://aka.ms/vs/17/release/vc_redist.x86.exe";
        Filename = "vc_redist.2022.x86.exe";
        Args = "/install /quiet /norestart /log:$tempDir\vc_redist_2022_x86_install.log";
        CheckName = "Microsoft Visual C++ 2015-2022 Redistributable (x86)"
    },
    @{
        Name = "Visual C++ 2013 Redistributable (x64)";
        Url = "https://aka.ms/highdpimfc2013x64enu";
        Filename = "vcredist_2013_x64.exe";
        Args = "/install /quiet /norestart /log:$tempDir\vc_redist_2013_x64_install.log";
        CheckName = "Microsoft Visual C++ 2013 Redistributable (x64)"
    },
    @{
        Name = "Visual C++ 2013 Redistributable (x86)";
        Url = "https://aka.ms/highdpimfc2013x86enu";
        Filename = "vcredist_2013_x86.exe";
        Args = "/install /quiet /norestart /log:$tempDir\vc_redist_2013_x86_install.log";
        CheckName = "Microsoft Visual C++ 2013 Redistributable (x86)"
    },
    @{
        Name = "Visual C++ 2012 Redistributable (x64)";
        Url = "https://download.microsoft.com/download/1/6/B/16B06F60-3B20-4FF2-B699-5E9B7962F9AE/VSU_4/vcredist_x64.exe";
        Filename = "vcredist_2012_x64.exe";
        Args = "/install /quiet /norestart /log:$tempDir\vc_redist_2012_x64_install.log";
        CheckName = "Microsoft Visual C++ 2012 Redistributable (x64)"
    },
    @{
        Name = "Visual C++ 2012 Redistributable (x86)";
        Url = "https://download.microsoft.com/download/1/6/B/16B06F60-3B20-4FF2-B699-5E9B7962F9AE/VSU_4/vcredist_x86.exe";
        Filename = "vcredist_2012_x86.exe";
        Args = "/install /quiet /norestart /log:$tempDir\vc_redist_2012_x86_install.log";
        CheckName = "Microsoft Visual C++ 2012 Redistributable (x86)"
    },
    @{
        Name = "Visual C++ 2010 Redistributable (x64)";
        Url = "https://download.microsoft.com/download/1/6/5/165255E7-1014-4D0A-B094-B6A430A6BFFC/vcredist_x64.exe";
        Filename = "vcredist_2010_x64.exe";
        Args = "/q /norestart";
        CheckName = "Microsoft Visual C++ 2010  x64 Redistributable"
    },
    @{
        Name = "Visual C++ 2010 Redistributable (x86)";
        Url = "https://download.microsoft.com/download/1/6/5/165255E7-1014-4D0A-B094-B6A430A6BFFC/vcredist_x86.exe";
        Filename = "vcredist_2010_x86.exe";
        Args = "/q /norestart";
        CheckName = "Microsoft Visual C++ 2010  x86 Redistributable"
    }
)

Log-Message "Installing all required Visual C++ Runtime packages..."

foreach ($package in $vcRedistPackages) {
    Log-Message "Processing $($package.Name)..."
    
    # Check if already installed
    if (Is-VCRedistInstalled $package.CheckName) {
        Log-Message "$($package.Name) appears to be already installed. Skipping."
        continue
    }
    
    $installerPath = "$tempDir\$($package.Filename)"
    
    # FIXED: Properly structure the conditional to check file existence first, then check size
    if ((Test-Path $installerPath) -and ((Get-Item $installerPath).Length -gt 1000000)) {
        Log-Message "$($package.Name) installer found locally. Skipping download."
    } else {
        # Download the installer
        try {
            if ($null -ne (Get-Command curl.exe -ErrorAction SilentlyContinue)) {
                Log-Message "Downloading $($package.Name) with curl..."
                Start-Process -FilePath "curl.exe" -ArgumentList "-L", "-o", $installerPath, "--retry", "3", $($package.Url) -Wait -NoNewWindow
            } else {
                Log-Message "Downloading $($package.Name) with Invoke-WebRequest..."
                Invoke-WebRequest -Uri $package.Url -OutFile $installerPath -UseBasicParsing
            }
            
            if (-not (Test-Path $installerPath)) {
                throw "Download failed - installer not found"
            }
        } catch {
            Log-Message "WARNING: Failed to download $($package.Name): $_"
            continue
        }
    }
    
    # Install the package
    Log-Message "Installing $($package.Name)..."
    try {
        $process = Start-Process -FilePath $installerPath -ArgumentList $package.Args -Wait -PassThru -NoNewWindow -ErrorAction SilentlyContinue
        Log-Message "$($package.Name) installation completed with exit code: $($process.ExitCode)"
    } catch {
        Log-Message "WARNING: Failed to install $($package.Name): $_"
    }
}

# Special case for DirectX which is often needed
Log-Message "Checking for DirectX Runtime..."

# Check if DirectX is already installed by looking for common DirectX components
function Is-DirectXInstalled {
    try {
        # Check for presence of key DirectX files
        $dxdiagPath = "$env:SystemRoot\System32\dxdiag.exe"
        $d3d9Path = "$env:SystemRoot\System32\d3d9.dll"
        $dxgiPath = "$env:SystemRoot\System32\dxgi.dll"
        
        # If critical DirectX files exist, assume it's installed
        if ((Test-Path $dxdiagPath) -and (Test-Path $d3d9Path) -and (Test-Path $dxgiPath)) {
            # Get file version of key component as additional check
            $dxgiInfo = Get-Item $dxgiPath -ErrorAction SilentlyContinue
            if ($dxgiInfo) {
                Log-Message "DirectX appears to be installed (dxgi.dll version: $($dxgiInfo.VersionInfo.FileVersion))"
                return $true
            }
        }
        return $false
    } catch {
        return $false
    }
}

if (Is-DirectXInstalled) {
    Log-Message "DirectX Runtime appears to be already installed. Skipping."
} else {
    Log-Message "Installing DirectX Runtime..."
    $dxUrl = "https://download.microsoft.com/download/1/7/1/1718CCC4-6315-4D8E-9543-8E28A4E18C4C/dxwebsetup.exe"
    $dxPath = "$tempDir\dxwebsetup.exe"

    # Check if installer is already downloaded
    if ((Test-Path $dxPath) -and ((Get-Item $dxPath).Length -gt 1000000)) {
        Log-Message "DirectX installer found locally. Skipping download."
    } else {
        try {
            if ($null -ne (Get-Command curl.exe -ErrorAction SilentlyContinue)) {
                Log-Message "Downloading DirectX with curl..."
                Start-Process -FilePath "curl.exe" -ArgumentList "-L", "-o", $dxPath, "--retry", "3", $dxUrl -Wait -NoNewWindow
            } else {
                Log-Message "Downloading DirectX with Invoke-WebRequest..."
                Invoke-WebRequest -Uri $dxUrl -OutFile $dxPath -UseBasicParsing
            }
        } catch {
            Log-Message "WARNING: Failed to download DirectX installer: $_"
        }
    }
    
    # Verify download and install
    if ((Test-Path $dxPath) -and ((Get-Item $dxPath).Length -gt 1000000)) {
        try {
            Log-Message "Running DirectX installer..."
            Start-Process -FilePath $dxPath -ArgumentList "/Q" -Wait -NoNewWindow
            Log-Message "DirectX Runtime installation completed."
        } catch {
            Log-Message "WARNING: Failed to install DirectX Runtime: $_"
        }
    } else {
        Log-Message "WARNING: DirectX installer not found or invalid. Skipping installation."
    }
}

# Repair VCRuntime dependencies
Log-Message "Running system file checker to repair any corrupted system files..."
try {
    # This requires admin privileges, but we'll try anyway
    Start-Process -FilePath "sfc.exe" -ArgumentList "/scannow" -Wait -NoNewWindow -ErrorAction SilentlyContinue
    Log-Message "System file check completed."
} catch {
    Log-Message "WARNING: System file checker could not be run: $_"
}

Log-Message "All Visual C++ Runtime packages installation completed."
# Launch the game
Log-Message "Launching NeuroSync..."
$gameExePath = "$projectDir\Game\NEUROSYNC_Demo_Build\Windows\NEUROSYNC.exe"
if (Test-Path $gameExePath) {
    Log-Message "Attempting to launch the game..."
    $gameProcess = Start-Process -FilePath $gameExePath -PassThru
    
    # Wait a bit to see if the game starts properly
    Start-Sleep -Seconds 5
    
    if ($gameProcess.HasExited -and $gameProcess.ExitCode -ne 0) {
        Log-Message "WARNING: Game seems to have crashed or failed to start properly."
        Log-Message "Exit code: $($gameProcess.ExitCode)"
        
        $userResponse = Read-Host "Would you like to try installing additional Visual C++ Runtime libraries manually? (y/n)"
        if ($userResponse -eq 'y') {
            Log-Message "Opening Microsoft's Visual C++ Runtime download page..."
            Start-Process "https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist"
            
            $userConfirm = Read-Host "After manually installing required libraries, would you like to try launching the game again? (y/n)"
            if ($userConfirm -eq 'y') {
                $gameProcess = Start-Process -FilePath $gameExePath -PassThru
            }
        }
    } else {
        Log-Message "NeuroSync launched successfully."
    }
    
    # Wait for the game to exit (if it didn't already)
    if (-not $gameProcess.HasExited) {
        $gameProcess.WaitForExit()
    }
    
    Log-Message "Game closed. Shutting down services..."
    Stop-Process -Id $apiProcess.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $llmProcess.Id -Force -ErrorAction SilentlyContinue
} else {
    Log-Message "ERROR: Game executable not found at $gameExePath"
    Log-Message "Please ensure you downloaded and extracted the game to the correct location."
}

Log-Message "NeuroSync shutdown complete."
