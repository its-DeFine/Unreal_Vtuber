#!/usr/bin/env python3
"""
Test runner script for GraphFlow External Stimuli System.

Supports running different test categories (unit, integration, e2e),
generates coverage reports, and provides clear test summaries.
"""

import sys
import os
import argparse
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
import json


class TestRunner:
    """Main test runner class."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_dir = project_root / "tests"
        self.src_dir = project_root / "src"
        self.coverage_dir = project_root / "htmlcov"
        
    def run_tests(self, 
                  test_type: Optional[str] = None,
                  specific_test: Optional[str] = None,
                  coverage: bool = True,
                  verbose: bool = False,
                  markers: Optional[List[str]] = None,
                  fail_fast: bool = False,
                  parallel: bool = False) -> int:
        """
        Run tests with specified options.
        
        Args:
            test_type: Type of tests to run (unit, integration, e2e, all)
            specific_test: Specific test file or test to run
            coverage: Whether to generate coverage report
            verbose: Verbose output
            markers: Additional pytest markers
            fail_fast: Stop on first failure
            parallel: Run tests in parallel
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        cmd = ["python", "-m", "pytest"]
        
        # Add test path based on type
        if specific_test:
            cmd.append(specific_test)
        elif test_type == "unit":
            cmd.append(str(self.test_dir / "unit"))
        elif test_type == "integration":
            cmd.append(str(self.test_dir / "integration"))
        elif test_type == "e2e":
            cmd.append(str(self.test_dir / "e2e"))
        else:
            cmd.append(str(self.test_dir))
        
        # Add markers
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])
        elif test_type and test_type != "all":
            cmd.extend(["-m", test_type])
        
        # Add coverage options
        if coverage:
            cmd.extend([
                f"--cov={self.src_dir}",
                "--cov-report=term-missing",
                f"--cov-report=html:{self.coverage_dir}",
                "--cov-report=xml",
            ])
        else:
            # Override pytest.ini coverage settings
            cmd.append("--no-cov")
        
        # Add other options
        if verbose:
            cmd.append("-vv")
        else:
            cmd.append("-v")
            
        if fail_fast:
            cmd.append("-x")
            
        if parallel:
            cmd.extend(["-n", "auto"])
        
        # Run tests
        print(f"Running command: {' '.join(cmd)}")
        print("-" * 80)
        
        start_time = time.time()
        result = subprocess.run(cmd, cwd=self.project_root)
        duration = time.time() - start_time
        
        print("-" * 80)
        print(f"Tests completed in {duration:.2f} seconds")
        
        # Generate coverage report summary if enabled
        if coverage and result.returncode == 0:
            self._print_coverage_summary()
        
        return result.returncode
    
    def run_specific_node_tests(self, node_name: str, coverage: bool = True) -> int:
        """Run tests for a specific node."""
        test_file = self.test_dir / "unit" / f"test_{node_name}_node.py"
        
        if not test_file.exists():
            print(f"Error: Test file {test_file} not found")
            return 1
        
        print(f"\nRunning tests for {node_name} node...")
        return self.run_tests(specific_test=str(test_file), coverage=coverage)
    
    def run_coverage_only(self) -> int:
        """Generate coverage report for existing test results."""
        cmd = [
            "python", "-m", "coverage", "html",
            f"--directory={self.coverage_dir}"
        ]
        
        result = subprocess.run(cmd, cwd=self.project_root)
        
        if result.returncode == 0:
            print(f"\nCoverage report generated at: {self.coverage_dir}/index.html")
            self._print_coverage_summary()
        
        return result.returncode
    
    def run_linting(self) -> int:
        """Run linting on source and test code."""
        print("\nRunning code linting...")
        
        # Run flake8
        flake8_cmd = [
            "python", "-m", "flake8",
            str(self.src_dir),
            str(self.test_dir),
            "--max-line-length=100",
            "--ignore=E203,W503"
        ]
        
        result = subprocess.run(flake8_cmd, cwd=self.project_root)
        
        if result.returncode != 0:
            print("Linting failed!")
            return result.returncode
        
        print("Linting passed!")
        return 0
    
    def run_type_checking(self) -> int:
        """Run type checking with mypy."""
        print("\nRunning type checking...")
        
        mypy_cmd = [
            "python", "-m", "mypy",
            str(self.src_dir),
            "--ignore-missing-imports",
            "--no-strict-optional"
        ]
        
        result = subprocess.run(mypy_cmd, cwd=self.project_root)
        
        if result.returncode != 0:
            print("Type checking failed!")
            return result.returncode
        
        print("Type checking passed!")
        return 0
    
    def run_security_scan(self) -> int:
        """Run security scanning with bandit."""
        print("\nRunning security scan...")
        
        bandit_cmd = [
            "python", "-m", "bandit",
            "-r", str(self.src_dir),
            "-f", "json",
            "-o", "bandit-report.json"
        ]
        
        result = subprocess.run(bandit_cmd, cwd=self.project_root)
        
        # Parse results
        report_file = self.project_root / "bandit-report.json"
        if report_file.exists():
            with open(report_file) as f:
                report = json.load(f)
            
            if report.get("results"):
                print(f"Security issues found: {len(report['results'])}")
                for issue in report["results"][:5]:  # Show first 5
                    print(f"  - {issue['issue_text']} ({issue['severity']})")
                return 1
            else:
                print("No security issues found!")
        
        return 0
    
    def run_all_checks(self) -> int:
        """Run all checks: tests, linting, type checking, security."""
        print("Running all checks...\n")
        
        checks = [
            ("Unit Tests", lambda: self.run_tests("unit", coverage=False)),
            ("Integration Tests", lambda: self.run_tests("integration", coverage=False)),
            ("Full Coverage", lambda: self.run_tests(coverage=True)),
            ("Linting", self.run_linting),
            ("Type Checking", self.run_type_checking),
            ("Security Scan", self.run_security_scan)
        ]
        
        results = {}
        for check_name, check_func in checks:
            print(f"\n{'=' * 80}")
            print(f"Running: {check_name}")
            print('=' * 80)
            
            result = check_func()
            results[check_name] = "PASSED" if result == 0 else "FAILED"
            
            if result != 0:
                print(f"\n{check_name} failed!")
        
        # Print summary
        print(f"\n{'=' * 80}")
        print("SUMMARY")
        print('=' * 80)
        
        for check_name, status in results.items():
            symbol = "✓" if status == "PASSED" else "✗"
            print(f"{symbol} {check_name}: {status}")
        
        # Return non-zero if any check failed
        return 0 if all(s == "PASSED" for s in results.values()) else 1
    
    def _print_coverage_summary(self):
        """Print coverage summary from XML report."""
        xml_report = self.project_root / "coverage.xml"
        if not xml_report.exists():
            return
        
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(xml_report)
            root = tree.getroot()
            
            # Get coverage percentage
            coverage_percent = float(root.attrib.get('line-rate', 0)) * 100
            
            print(f"\nOverall coverage: {coverage_percent:.2f}%")
            
            # Get per-package coverage
            packages = root.findall('.//package')
            if packages:
                print("\nCoverage by package:")
                for package in packages:
                    name = package.attrib.get('name', 'unknown')
                    line_rate = float(package.attrib.get('line-rate', 0)) * 100
                    print(f"  {name}: {line_rate:.2f}%")
        except Exception as e:
            print(f"Could not parse coverage report: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test runner for GraphFlow External Stimuli System"
    )
    
    parser.add_argument(
        "command",
        choices=["test", "coverage", "lint", "typecheck", "security", "all", "node"],
        help="Command to run"
    )
    
    parser.add_argument(
        "--type",
        choices=["unit", "integration", "e2e", "all"],
        default="all",
        help="Type of tests to run"
    )
    
    parser.add_argument(
        "--node",
        help="Specific node to test (for 'node' command)"
    )
    
    parser.add_argument(
        "--test",
        help="Specific test file or test to run"
    )
    
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable coverage reporting"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "-x", "--fail-fast",
        action="store_true",
        help="Stop on first test failure"
    )
    
    parser.add_argument(
        "-p", "--parallel",
        action="store_true",
        help="Run tests in parallel (requires pytest-xdist)"
    )
    
    parser.add_argument(
        "-m", "--markers",
        nargs="+",
        help="Additional pytest markers"
    )
    
    args = parser.parse_args()
    
    # Get project root
    project_root = Path(__file__).parent.absolute()
    runner = TestRunner(project_root)
    
    # Execute command
    if args.command == "test":
        return runner.run_tests(
            test_type=args.type,
            specific_test=args.test,
            coverage=not args.no_coverage,
            verbose=args.verbose,
            markers=args.markers,
            fail_fast=args.fail_fast,
            parallel=args.parallel
        )
    elif args.command == "coverage":
        return runner.run_coverage_only()
    elif args.command == "lint":
        return runner.run_linting()
    elif args.command == "typecheck":
        return runner.run_type_checking()
    elif args.command == "security":
        return runner.run_security_scan()
    elif args.command == "all":
        return runner.run_all_checks()
    elif args.command == "node":
        if not args.node:
            print("Error: --node argument required for 'node' command")
            return 1
        return runner.run_specific_node_tests(args.node, coverage=not args.no_coverage)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())