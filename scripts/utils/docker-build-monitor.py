#!/usr/bin/env python3
"""
Docker Compose Build Monitor
Manages Docker Compose builds with real-time log monitoring and completion detection
"""

import subprocess
import threading
import time
import sys
import os
import argparse
from datetime import datetime
import signal

class DockerBuildMonitor:
    def __init__(self, compose_file, log_file="docker-build.log"):
        self.compose_file = compose_file
        self.log_file = log_file
        self.build_process = None
        self.is_building = False
        self.build_complete = False
        self.build_failed = False
        self.stop_monitoring = False
        
    def start_build(self):
        """Start Docker Compose build in background"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Docker Compose build...")
        print(f"Compose file: {self.compose_file}")
        print(f"Logs will be written to: {self.log_file}")
        print("-" * 60)
        
        self.is_building = True
        
        # Open log file for writing
        with open(self.log_file, 'w') as log:
            log.write(f"Build started at {datetime.now()}\n")
            log.write(f"Compose file: {self.compose_file}\n")
            log.write("-" * 60 + "\n")
            
        # Start build process
        cmd = ["docker", "compose", "-f", self.compose_file, "up", "-d", "--build"]
        
        try:
            self.build_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Start thread to monitor output
            monitor_thread = threading.Thread(target=self._monitor_output)
            monitor_thread.daemon = True
            monitor_thread.start()
            
        except Exception as e:
            print(f"Error starting build: {e}")
            self.build_failed = True
            self.is_building = False
            
    def _monitor_output(self):
        """Monitor build output and write to log file"""
        with open(self.log_file, 'a') as log:
            for line in self.build_process.stdout:
                if self.stop_monitoring:
                    break
                    
                # Write to log file
                log.write(line)
                log.flush()
                
                # Also print to console for real-time feedback
                print(f"[BUILD] {line.strip()}")
                
                # Check for completion indicators
                if "Running" in line and "done" in line:
                    # Build appears to be completing
                    pass
                elif "Error" in line or "ERROR" in line:
                    self.build_failed = True
                    
            # Wait for process to complete
            return_code = self.build_process.wait()
            
            if return_code == 0:
                self.build_complete = True
                log.write(f"\nBuild completed successfully at {datetime.now()}\n")
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Build completed successfully!")
            else:
                self.build_failed = True
                log.write(f"\nBuild failed at {datetime.now()} with return code {return_code}\n")
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Build failed with return code {return_code}")
                
        self.is_building = False
        
    def check_logs(self):
        """Read and display recent log entries"""
        if not os.path.exists(self.log_file):
            print("No log file found yet.")
            return
            
        print(f"\n--- Recent log entries ---")
        try:
            with open(self.log_file, 'r') as log:
                lines = log.readlines()
                # Show last 20 lines
                recent_lines = lines[-20:] if len(lines) > 20 else lines
                for line in recent_lines:
                    print(line.strip())
        except Exception as e:
            print(f"Error reading log file: {e}")
            
    def check_status(self):
        """Check current build status"""
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Build Status:")
        print(f"  Building: {self.is_building}")
        print(f"  Complete: {self.build_complete}")
        print(f"  Failed: {self.build_failed}")
        
        if self.is_building:
            print("  Build is currently in progress...")
        elif self.build_complete:
            print("  Build completed successfully!")
            # Check container status
            self._check_containers()
        elif self.build_failed:
            print("  Build failed! Check logs for details.")
            
    def _check_containers(self):
        """Check status of containers defined in compose file"""
        print("\n  Container Status:")
        try:
            result = subprocess.run(
                ["docker", "compose", "-f", self.compose_file, "ps"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(result.stdout)
            else:
                print("  Error checking container status")
        except Exception as e:
            print(f"  Error: {e}")
            
    def stop_build(self):
        """Stop the build process"""
        if self.build_process and self.is_building:
            print("\nStopping build process...")
            self.stop_monitoring = True
            self.build_process.terminate()
            time.sleep(2)
            if self.build_process.poll() is None:
                self.build_process.kill()
            print("Build process stopped.")
            
    def interactive_mode(self):
        """Run in interactive mode with commands"""
        print("\nDocker Build Monitor - Interactive Mode")
        print("Commands:")
        print("  status - Check build status")
        print("  logs   - Show recent log entries")
        print("  stop   - Stop the build")
        print("  exit   - Exit monitor")
        print("-" * 60)
        
        # Start the build
        self.start_build()
        
        # Interactive command loop
        while True:
            try:
                if self.build_complete or self.build_failed:
                    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Build finished!")
                    self.check_status()
                    break
                    
                # Non-blocking input check
                cmd = input("\n> ").strip().lower()
                
                if cmd == "status":
                    self.check_status()
                elif cmd == "logs":
                    self.check_logs()
                elif cmd == "stop":
                    self.stop_build()
                    break
                elif cmd == "exit":
                    if self.is_building:
                        print("Build is still running. Use 'stop' to stop it first.")
                    else:
                        break
                else:
                    print("Unknown command. Use status, logs, stop, or exit.")
                    
            except KeyboardInterrupt:
                print("\nReceived interrupt signal.")
                self.stop_build()
                break
                
def main():
    parser = argparse.ArgumentParser(description="Docker Compose Build Monitor")
    parser.add_argument(
        "--compose-file", "-f",
        default="docker-compose.autogen-ollama.yml",
        help="Docker Compose file to use"
    )
    parser.add_argument(
        "--log-file", "-l",
        default="docker-build.log",
        help="Log file path"
    )
    parser.add_argument(
        "--auto", "-a",
        action="store_true",
        help="Run in automatic mode (non-interactive)"
    )
    
    args = parser.parse_args()
    
    # Check if compose file exists
    if not os.path.exists(args.compose_file):
        print(f"Error: Compose file '{args.compose_file}' not found!")
        sys.exit(1)
        
    monitor = DockerBuildMonitor(args.compose_file, args.log_file)
    
    if args.auto:
        # Automatic mode - just monitor until complete
        monitor.start_build()
        
        print("\nMonitoring build progress...")
        while monitor.is_building:
            time.sleep(5)
            print(".", end="", flush=True)
            
        print()
        monitor.check_status()
    else:
        # Interactive mode
        monitor.interactive_mode()
        
    print("\nBuild monitor completed.")
    
if __name__ == "__main__":
    main()