from TelosAirSAMDBoardFlashGUI.models.board import Board
from pathlib import Path
from threading import Thread
from pathlib import Path
from typing import Union, Tuple
from serial import Serial, SerialTimeoutException
from queue import Queue
from serial.tools.list_ports import comports as list_comports
import os
from time import time, sleep
from platform import system
import subprocess

prepend_err_msg = lambda msg, err: Exception(msg+err.args[0], *err.args[1:])

import logging
logger = logging.getLogger("Flash")
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

handler = logging.StreamHandler()
handler.setFormatter(formatter)

logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

OS_NAME = system()

BOSSAC_BIN_PATH_MAC_OS = f"{Path(__file__).parent}/bossac"
BOSSAC_BIN_PATH_WINDOWS = f"{Path(__file__).parent}/bossac.exe"
BIN_PATH = f"{Path(__file__).parent}/bin/flash.ino.bin"

""" 
Valid VID:PID combos for QT Py. For some reason, when the QT Py is put in bootloader mode,
the PID changes to match the second combo here.
"""
VALID_VID_PID = [(0x80CB,0x239A), (0x00CB,0x239A)]

def find_connected_board(board_serial: str) -> Union[Board, None]:
    """
    Check the computers USB connections to QT Py's and try to match the given
    `board_serial` to it.
    
    Return a new `Board` if found, `None` otherwise
    """
    for port in list_comports():
        # First match PID:VID known for QT Py
        if (port.pid, port.vid) in VALID_VID_PID:
            # Then match serial
            if board_serial == port.serial_number:
                return Board(
                    board_name=port.description,
                    pid=port.pid,
                    sn=port.serial_number,
                    vid=port.vid,
                    port_address=port.name
                )

def get_connected_boards(port_path_only: bool = False) -> Union['list[Board]', 'list[str]']:
    """
    Check the computer's USB connections for QT Py with known PID:VID and return
    new `Board` objects for each (if any).

    If `port_path_only` is set to `True` [defaults to `False`], instead return a list of 
    port path `str`.
    """
    ret = []
    for port in list_comports():
        if (port.pid, port.vid) in VALID_VID_PID:
            if port_path_only:
                ret.append(port.device) # .device is its "path"
            else:
                ret.append(Board(
                        board_name=port.description,
                        pid=port.pid,
                        sn=port.serial_number,
                        vid=port.vid,
                        port_address=port.name
                    ))
    return ret

def _do_soft_request_bootloader_mode(path: str) -> None:
    """
    Put the QT Py into bootloader mode by opening a `Serial` port with a `baudrate` of `1200`.
    This tells the SAMD21 chip to go into bootloader mode.
    
    Does not catch any exceptions.
    """
    SPECIAL_BAUDRATE = 1200
    try:
        s = Serial(path, baudrate=SPECIAL_BAUDRATE)
        sleep(1)
    finally:
        s.close()

if OS_NAME in ['Darwin', 'Linux']:
    __get_drives = lambda: os.listdir("/Volumes/")
elif OS_NAME in ['Windows']:
    import win32api
    __get_drives = lambda: [win32api.GetVolumeInformation(d)[0] for d in win32api.GetLogicalDriveStrings().split("\000")[:-1]]
    
def _verify_bootloader_mode_set(timeout: float = 5) -> bool:
    """
    Check to see if the QT Py is in bootloader by looking for an external drive called `"QTPY_BOOT"`.

    Returns success as `bool`.

    This currently doesn't check bootloader version nor verify correct SN, although it probably could.

    Exceptions not caught.

    Currently requires implementation of some funcs for OS tolerance:

    * `__get_drives`: Returns names of all external drives connected to computer.
    
    """
    QTPY_VOLUME_NAME = "QTPY_BOOT"
    timeout_at = time() + timeout
    external_drives = __get_drives()
    logger.debug(f"Mounted Drives: {external_drives}")
    if QTPY_VOLUME_NAME in external_drives:
        return True

    while time() < timeout_at:
        external_drives = __get_drives()
        logger.debug(f"\tMounted Drives: {external_drives}")
        if QTPY_VOLUME_NAME in external_drives:
            logger.debug(f"Found {QTPY_VOLUME_NAME}.")
            return True
        sleep(.5) # Let's not hog the processor just for listing drives
    
    return False


def soft_request_bootloader_mode(device_path: str) -> bool:
    """
    Perform a software request to the SAMD21 chip to enter bootloader mode.

    Will rethrow exceptions caught.

    Returns success as `bool`.
    """

    try:
        if not _verify_bootloader_mode_set(timeout=.1):
            logger.info("Attempting to put device in bootloader mode.")
            _do_soft_request_bootloader_mode(device_path)
    except Exception as e:
        raise(prepend_err_msg("<Verifying Bootloader Mode Set>: ", e))
    
    logger.info("Waiting for device mount.")
    if not _verify_bootloader_mode_set():
        logger.error("Device drive not mounted - looks like bootloader mode has not been set.")
        return False
    return True

if OS_NAME == 'Darwin':
    def flash_samd21_device(full_device_path: str, full_file_path: str) -> bool:
        CMD_TEMPLATE = "\"%s\" -i -d --port=%s -U -i --offset=0x2000 -w -v \"%s\" -R"
        return not os.system(CMD_TEMPLATE%(BOSSAC_BIN_PATH, full_device_path, full_file_path))
elif OS_NAME == 'Windows':
    import subprocess
    def flash_samd21_device(full_device_path: str, full_file_path: str) -> bool:
        CMD_TEMPLATE = "%s -i -d --port=%s -U -i --offset=0x2000 -w -v %s -R"
        CMD = (CMD_TEMPLATE%("TelosAirSAMDBoardFlashGUI\\util\\bossac.exe", full_device_path, full_file_path))
        res = subprocess.run(['cmd', '/c', CMD], shell=True, capture_output=True)
        return not res.returncode

if OS_NAME == 'Darwin':
    CMD_TEMPLATE = f"\"{BOSSAC_BIN_PATH_MAC_OS}\" -i -d --port=%s -U -i --offset=0x2000 -w -v \"%s\" -R"
elif OS_NAME == 'Windows':
    CMD_TEMPLATE = f"{BOSSAC_BIN_PATH_WINDOWS} -i -d --port=%s -U -i --offset=0x2000 -w -v %s -R"

def flash_samd21_device(device_path: str, full_file_path: str) -> bool:
    """
    Flash the board at the given `device_path` using the BOSSA tool, `bossac`. 
    The file flashed will be the one given by `full_file_path`.

    Returns success (measured by a zero `returncode`) as a `bool`.

    Depends on implementations per OS of:

    * CMD_TEMPLATE (`str`): The execute command template, intended for `cmd` (Windows) or `Terminal` (OS X),
    that takes, in order, the `device_path` `str` parameter and the `full_file_path` `str` parameter.
    """
    logger.debug(f"flash_samd21({device_path}, {full_file_path}). CMD_TEMPLATE: {CMD_TEMPLATE}")
    cmd = CMD_TEMPLATE%(device_path, full_file_path)
    logger.debug(f"Running command {cmd}.")
    res = subprocess.run([cmd], shell=True, capture_output=True)
    logger.debug(f"Flashing process results: Return Code: {res.returncode}, Std. Err.: {res.stderr}.")
    return not res.returncode

#TODO: Improve error catching and reporting
class FlashThread(Thread):
    def __init__(self, dev_path: str, dev_sn: str, updates_queue: Queue = None):
        super().__init__(daemon=True)
        self.dev = dev_path
        self.dev_sn = dev_sn
        if system() in ["Darwin", "Linux"]:
            self.dev = f"/dev/{self.dev}"

        self.result = None

        self.updates_queue = updates_queue or Queue()
        self.ser: Serial = None

    def wait_for_real_data(self):
        return
        line = b''
        while len(line) != 32:
            try:
                line = self.ser.read(32)
                if line: print(line)
            except SerialTimeoutException:
                pass

        return

    def run(self):
        
        self.updates_queue.put(('Putting board in bootloader mode...', True, False))
        try:
            res = soft_request_bootloader_mode(self.dev)
        except Exception as e:
            logger.exception(f"Exception during soft_request_bootloader_mode({self.dev}): {e}")
            self.updates_queue.put(("Failed to put the board in bootloader mode. (Exception).", False, False))
            return
        
        if not res:
            logger.debug(f"Nonzero return code from soft_request_bootloader_mode({self.dev}), cancelling.")
            self.updates_queue.put(("Something went wrong. Failed to put board in bootloader mode.", False, False))
            return
        
        # Sometimes, especially on Windows/Linux, if the board disconnects, it might change connection path.
        # So we must try to locate it.
        connected_boards_paths = get_connected_boards(True)
        logger.debug(f"After bootloader mode, connected boards at: {connected_boards_paths}")
        if self.dev not in connected_boards_paths:
            logger.info(f"Port path must have changed (Expecting {self.dev}). Searching for new.")

            new_board = find_connected_board(board_serial=self.dev_sn)
            if not new_board:
                logger.error(f"Failed to locate new board connection for serial {self.dev_sn}")
                self.updates_queue.put(('Failed to locate board after putting in bootloader mode. Please try again.', False, False))
                return
            else:
                logger.info(f"New path detected for board is {new_board.port_path}")
                self.dev = new_board.port_path
        

        self.updates_queue.put(('Flashing Board...', True, False))
        try:
            res = flash_samd21_device(self.dev, BIN_PATH)
        except Exception as e:
            logger.exception(f"Flashing failed with exception: {e}")
            self.updates_queue.put(('Flashing failed. (Exception)', False, False))
            return
        if not res:
            logger.error("Flashing failed due to failure.")
            self.updates_queue.put(('Something went wrong. Flashing failed.', False, False))
            return

        self.updates_queue.put(('Board flash successful.', True, True))
        