import pyduinocli
from TelosAirSAMDBoardFlashGUI.models.board import Board
from pathlib import Path
from threading import Thread, Event
from os.path import exists
from os import listdir, remove
import psutil
from pathlib import Path
from typing import Union, Tuple
from Crypto.Cipher import AES
from serial import Serial, SerialTimeoutException
from queue import Queue
from serial.tools.list_ports import comports as list_comports
import os
from time import time, sleep
from platform import system

BOSSAC_BIN_PATH = f"{Path(__file__).parent}/bossac"
BIN_PATH = f"{Path(__file__).parent}/bin/flash.ino.bin"

def get_connected_boards():
    ret = []
    VALID_VID_PID = [(0x80CB,0x239A)]
    for port in list_comports():
        if (port.pid, port.vid) in VALID_VID_PID:
            ret.append(
                Board(
                    board_name=port.description,
                    pid=port.pid,
                    sn=port.serial_number,
                    vid=port.vid,
                    port_address=port.name
                )
            )
    return ret

def _do_soft_request_bootloader_mode(path: str) -> Union[str, None]:
    SPECIAL_BAUDRATE = 1200
    try:
        s = Serial(path, baudrate=SPECIAL_BAUDRATE)
        sleep(1)
        s.close()
    except Exception as e:
        err = (f"Error putting device in bootloader mode: {e}")
        return err
    return None

def _verify_bootloader_mode_set(timeout = 10) -> bool:
    timeout_at = time() + timeout
    while time() < timeout_at:
        if "QTPY_BOOT" in os.listdir("/Volumes/"):
            return True
        sleep(.2)
    return False

def soft_request_bootloader_mode(path: str) -> Union[str, None]:
    if not _verify_bootloader_mode_set(timeout=.1):
        print("Attempting to put device in bootloader mode.")
        res = _do_soft_request_bootloader_mode(path)
        if res:
            return f"Failed to request a soft reboot due to: {res}"
    print("Waiting for device mount...")
    if not _verify_bootloader_mode_set():
        err = ("Device drive not mounted - looks like bootloader mode has not been set.")
        print(err)
        return err
    return None

def flash_samd21_device(full_device_path: str, full_file_path: str) -> bool:
    CMD_TEMPLATE = "\"%s\" -i -d --port=%s -U -i --offset=0x2000 -w -v \"%s\" -R"
    return not os.system(CMD_TEMPLATE%(BOSSAC_BIN_PATH, full_device_path, full_file_path))

#TODO: Improve error catching and reporting
class FlashThread(Thread):
    def __init__(self, dev_path: str, updates_queue: Queue = None):
        super().__init__(daemon=True)
        self.dev = dev_path
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
        except Exception:
            self.updates_queue.put(("Failed to put the board in bootloader mode. (Exception).", False, False))
            return
        if res:
            self.updates_queue.put((res, False, False))
            return

        self.updates_queue.put(('Flashing Board...', True, False))
        try:
            res = flash_samd21_device(self.dev, BIN_PATH)
        except Exception:
            self.updates_queue.put(('Flashing failed. (Exception)', False, False))
            return
        if not res:
            self.updates_queue.put(('Flashing failed.', False, False))
            return

        self.updates_queue.put(('Board flash successful.', True, True))
        