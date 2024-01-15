from TelosAirSAMDBoardFlashGUI.context import CONTEXT
from TelosAirSAMDBoardFlashGUI.ui.widgets.action_popup import ActionPopup
from TelosAirSAMDBoardFlashGUI.util.bossa import *
import os

def flash_button_callback(*args):
    class FlashProcessThread(Thread):
        def __init__(self, board: Board):
            self.board = board
            self.updates_queue = Queue()
            super().__init__(daemon=True)

        def run(self):
            CONTEXT.root.event_generate(CONTEXT.EVENTS.BOARD_ACTION_BUTTON_DISABLE)
            th = FlashThread(dev_path=CONTEXT.board_selected.port_path, updates_queue=self.updates_queue)
            th.start()
            popup = ActionPopup(root=CONTEXT.root, starting_text="Beginning flashing process.", 
                                msg_queue=self.updates_queue, window_title="TelosAirBoardManager - Board Flashing")
            
            th.join()
            
            

            CONTEXT.root.event_generate(CONTEXT.EVENTS.BOARD_ACTION_BUTTON_ENABLE)

    th = FlashProcessThread(CONTEXT.board_selected)
    th.start()

CONTEXT.bind_root(CONTEXT.EVENTS.FLASH_BUTTON, flash_button_callback)