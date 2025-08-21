#!/usr/bin/env python3
"""
Test runner script for Sprout application
Provides easy commands to run different types of tests
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    print(f"{'='*60}\n")
    
    try:
        result = subprocess.run(command, check=True, capture_output=False)
        print(f"\n✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with exit code {e.returncode}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Run tests for Sprout application')
    parser.add_argument('--type', choices=['all', 'unit', 'integration', 'auth', 'expenses', 'categories', 'preferences', 'summary'], 
                       default='all', help='Type of tests to run')
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--fast', action='store_true', help='Skip slow tests')
    
    args = parser.parse_args()
    
    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    # Base pytest command
    pytest_cmd = ['python', '-m', 'pytest']
    
    if args.verbose:
        pytest_cmd.append('-v')
    
    if args.fast:
        pytest_cmd.extend(['-m', 'not slow'])
    
    if args.coverage:
        pytest_cmd.extend(['--cov=app', '--cov-report=term-missing', '--cov-report=html:htmlcov'])
    
    # Determine which tests to run
    if args.type == 'all':
        test_path = 'tests/'
    else:
        test_path = f'tests/test_{args.type}.py'
    
    pytest_cmd.append(test_path)
    
    # Run the tests
    success = run_command(pytest_cmd, f"{args.type.title()} tests")
    
    if success:
        print("\n🎉 All tests passed!")
        if args.coverage:
            print("\n📊 Coverage report generated in htmlcov/ directory")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
