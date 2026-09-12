"""
Main Entry Point for Windows Book Cover Generator Tool.
"""

import sys
import tkinter as tk
from gui import BookCoverApp

def main():
    root = tk.Tk()
    app = BookCoverApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
