from TelosAirSAMDBoardFlashGUI.ui.app import TelosAirApp
from TelosAirSAMDBoardFlashGUI.context import CONTEXT
from TelosAirSAMDBoardFlashGUI.callbacks.refresh_button import refresh_button_callback

def main():
    app = TelosAirApp()
    #TODO: Use ini file or something
    refresh_button_callback()
    CONTEXT.init(app, client_name="TestClient", db_url="http://127.0.0.1:5001")
    

    app.mainloop()


if __name__ == "__main__":
    main()