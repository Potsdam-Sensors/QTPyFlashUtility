from pathlib import Path
BIN_FOLDER_PATH = f"{Path(__file__).parent}/bin"

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