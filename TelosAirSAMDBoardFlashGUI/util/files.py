import sys
import os

# Determine if running as a bundled application or in a normal Python environment
if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app 
    # path into variable _MEIPASS.
    APP_PATH = sys._MEIPASS
else:
    APP_PATH = os.path.dirname(os.path.abspath(__file__))

BIN_FOLDER_PATH = os.path.join(APP_PATH, '/bossac_binaries')

DEVICE_FILE_NICKNAMES = [
        "QT Py - Plantower PMS5003 Read",
        "QT Py - AlphaSense OPC-R2 Read",
        "QT Py - Test Flashing"
]

DEVICE_FILE_PATHS = [
    None,
    None,
    BIN_FOLDER_PATH + "/test.ino.bin"
]