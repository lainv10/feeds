from gui.controller import Controller

import logging
logging.basicConfig()
logging.root.setLevel(logging.INFO)

# run the gui
logging.info("Starting application...")
controller = Controller()
controller.run()
