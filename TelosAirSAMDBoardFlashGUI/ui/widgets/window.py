from tkinter import *
from TelosAirSAMDBoardFlashGUI.context import CONTEXT
from TelosAirSAMDBoardFlashGUI.ui.widgets.inspect import BoardInspectWidget
from pathlib import Path
from PIL import Image, ImageTk
import tkinter.messagebox
UI_FOLDER_PATH = f"{Path(__file__).parent.parent}"
STATIC_FOLDER_PATH = f"{UI_FOLDER_PATH}/static"

event_generate_func_generator = lambda event_str: lambda *args: CONTEXT.root.event_generate(event_str)

class RefreshButton(Button):
    def __init__(self, master):
        super().__init__(master=master, text='Refresh')


class RefreshButtonWidget(Frame):
    def __init__(self, master):
        super().__init__(master=master)

        self.button = RefreshButton(self)
        self.button.config(command=self.on_press)
        self.button.pack()

        #TODO: Loading wheel when button is pressed (and disabled)
        CONTEXT.bind_root(CONTEXT.EVENTS.UNLOCK_REFRESH_BUTTON, self.enable)
        self.disable()

    def on_press(self, *args):
        self.disable()
        event_generate_func_generator(CONTEXT.EVENTS.REFRESH)()

    def disable(self, *args):
        self.button.config(state='disabled')

    def enable(self, *args):
        self.button.config(state='normal')

class DeviceList(Listbox):
    def __init__(self, master):
        super().__init__(master=master, width=30)
        self.board_list = []
        self.redraws = 0
        CONTEXT.bind_root(CONTEXT.EVENTS.REDRAW_LISTBOX, self.redraw)
        self.bind('<<ListboxSelect>>', self.cursor_select_cb)

    def cursor_select_cb(self, *args):
        if len(self.curselection()) == 0:
            return
        idx = self.curselection()[0]
        if idx >= len(self.board_list):
            return
        
        board = self.board_list[idx]
        CONTEXT.board_selected = board
        CONTEXT.root.event_generate(CONTEXT.EVENTS.BOARD_SELECTED_DRAW_INSPEC)
        CONTEXT.root.event_generate(CONTEXT.EVENTS.BOARD_ACTION_BUTTON_ENABLE)

    
    def redraw(self, *args):
        self.redraws += 1
        if self.board_list:
            self.delete(0, len(self.board_list)-1)
        self.board_list = CONTEXT.board_list.copy()

        for i, port in enumerate(self.board_list):
            self.insert(i, f"{port.board_name} [@ {port.port_path}]")

        if len(self.board_list) == 0 and self.redraws > 1:
            tkinter.messagebox.showwarning(title="Device List Refresh", message="No valid devices were found connected to your computer. Please connect the device and try again.")
        
        self.focus()


class DeviceListWidget(Frame):
    def __init__(self, master):
        super().__init__(master=master)

        top_frame = Frame(master=self)
        title_label = Label(master=top_frame, text='Devices')
        refresh_button = RefreshButtonWidget(top_frame)
        help_icon = ImageTk.PhotoImage(Image.open(f"{STATIC_FOLDER_PATH}/info.png").resize((15,15)))
        help = Button(master=top_frame, borderwidth=0, border=0, highlightthickness=0)
        help.config(image=help_icon)
        help.img = help_icon

        title_label.grid(row=0, column=0)
        refresh_button.grid(row=0, column=1)
        help.grid(row=0, column=2, sticky='ns')

        list_box = DeviceList(self)
        top_frame.pack()
        
        list_box.pack()
        list_box.focus()

class MainWindow(Frame):
    def __init__(self, root: Tk):
        super().__init__(master=root)

        device_list_widget = DeviceListWidget(self)
        device_list_widget.grid(row=0, column=0, sticky='ew', padx=10, pady=10)

        board_inspect_widget = BoardInspectWidget(self)
        board_inspect_widget.grid(row=0, column=1, sticky='ew', padx=10, pady=10)

        