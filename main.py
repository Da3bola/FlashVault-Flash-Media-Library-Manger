import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import GameLibraryApp
from PyQt6.QtWidgets import QApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application style for better look
    app.setStyle('Fusion')
    
    # Create and show main window
    window = GameLibraryApp()
    window.show()
    
    sys.exit(app.exec())