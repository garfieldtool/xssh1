"""
Python script to package the Book Cover Generator tool into a standalone Windows executable (.exe).
Compatible with Windows 7 / Windows 10 / Windows 11 (Supports Python 3.8.x on Windows 7).
Uses PyInstaller.
"""

import os
import subprocess
import sys


def build():
    print("Building Windows Executable using PyInstaller (Windows 7/10/11 Compatible)...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=BookCoverGenerator",
        "--clean",
        "main.py"
    ]

    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\nBuild successful!")
        print("Executable generated in: dist/BookCoverGenerator/BookCoverGenerator.exe")
    else:
        print("\nBuild failed with exit code:", result.returncode)


if __name__ == "__main__":
    build()
