import sys
import os
import json
import subprocess
import platform
import shutil
import webbrowser
import urllib.request
from urllib.parse import quote, urlparse
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage

# Database class
class GameDatabase:
    def __init__(self):
        import sqlite3
        os.makedirs("data", exist_ok=True)
        self.conn = sqlite3.connect("data/games.db", check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                swf_path TEXT NOT NULL,
                thumbnail_path TEXT,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_played TIMESTAMP,
                play_count INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()
    
    def add_game(self, title, swf_path, thumbnail_path):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO games (title, swf_path, thumbnail_path)
            VALUES (?, ?, ?)
        ''', (title, swf_path, thumbnail_path))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_all_games(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM games ORDER BY title')
        return cursor.fetchall()
    
    def update_play_stats(self, game_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE games 
            SET last_played = CURRENT_TIMESTAMP, 
                play_count = play_count + 1 
            WHERE id = ?
        ''', (game_id,))
        self.conn.commit()

class CustomWebEnginePage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
    
    def javaScriptConsoleMessage(self, level, message, line, source_id):
        """Handle JavaScript console messages"""
        if "Image selected:" in message:
            # Parse image URL from console message
            url = message.replace("Image selected:", "").strip()
            if self.parent:
                self.parent.handle_image_selected(url)

class ImageBrowserDialog(QDialog):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.parent = parent
        self.selected_image_url = None
        self.selected_image_filename = None
        self.image_button = None
        self.setup_ui(title)
    
    def setup_ui(self, title):
        self.setWindowTitle(f"Search Cover: {title}")
        self.setGeometry(100, 100, 1200, 800)
        
        layout = QVBoxLayout(self)
        
        # Top panel with search and controls
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        
        # Search bar
        search_layout = QWidget()
        search_hbox = QHBoxLayout(search_layout)
        
        self.search_input = QLineEdit(f"{title} flash game cover")
        search_btn = QPushButton("🔍 Search")
        
        search_hbox.addWidget(QLabel("Search:"))
        search_hbox.addWidget(self.search_input)
        search_hbox.addWidget(search_btn)
        search_hbox.addStretch()
        
        # Action buttons panel
        self.action_panel = QWidget()
        action_layout = QHBoxLayout(self.action_panel)
        action_layout.setContentsMargins(10, 5, 10, 5)
        
        self.action_panel.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border: 1px solid #4CAF50;
                border-radius: 5px;
            }
        """)
        
        # Image selection button
        self.image_button = QPushButton("📁 Select This Image as Cover")
        self.image_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #66bb6a;
            }
            QPushButton:disabled {
                background-color: #666;
            }
        """)
        self.image_button.setEnabled(False)
        
        action_layout.addWidget(self.image_button)
        
        top_layout.addWidget(search_layout)
        top_layout.addWidget(self.action_panel)
        
        # Web view
        self.web_view = QWebEngineView()
        self.web_page = CustomWebEnginePage(self)
        self.web_view.setPage(self.web_page)
        
        # Enable JavaScript and plugins
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        
        # Instructions
        instructions = QLabel("💡 Right-click on any image → 'Choose This Image', then click 'Select This Image as Cover'")
        instructions.setStyleSheet("""
            QLabel {
                color: #4CAF50;
                padding: 8px;
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 4px;
                font-weight: bold;
            }
        """)
        instructions.setWordWrap(True)
        
        layout.addWidget(top_panel)
        layout.addWidget(instructions)
        layout.addWidget(self.web_view)
        
        # Connect signals
        search_btn.clicked.connect(self.perform_search)
        self.search_input.returnPressed.connect(self.perform_search)
        self.image_button.clicked.connect(self.confirm_image_selection)
        
        # Load initial search
        self.perform_search()
        
        # Inject JavaScript for custom right-click and image handling
        self.inject_javascript()
    
    def inject_javascript(self):
        """Inject JavaScript to handle custom right-click menu and image selection"""
        js_code = """
        // Add custom right-click menu for images
        document.addEventListener('contextmenu', function(e) {
            if (e.target.tagName === 'IMG') {
                e.preventDefault();
                
                // Remove any existing custom menu
                var existingMenu = document.getElementById('custom-image-menu');
                if (existingMenu) existingMenu.remove();
                
                // Create custom menu
                var menu = document.createElement('div');
                menu.id = 'custom-image-menu';
                menu.style.cssText = `
                    position: fixed;
                    left: ${e.pageX}px;
                    top: ${e.pageY}px;
                    background: #4CAF50;
                    color: white;
                    padding: 10px 15px;
                    border-radius: 4px;
                    cursor: pointer;
                    z-index: 10000;
                    font-weight: bold;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                `;
                menu.textContent = '📁 Choose This Image';
                
                // Add click handler
                menu.onclick = function() {
                    var img = e.target;
                    console.log('Image selected: ' + img.src);
                    
                    // Add visual feedback
                    img.style.border = '3px solid #4CAF50';
                    img.style.borderRadius = '5px';
                    
                    // Store the selected image
                    window.selectedImageUrl = img.src;
                    window.selectedImageFilename = img.src.split('/').pop().split('?')[0];
                    
                    // Show button with filename
                    if (window.showImageButton) {
                        window.showImageButton(img.src, window.selectedImageFilename);
                    }
                    
                    menu.remove();
                };
                
                document.body.appendChild(menu);
                
                // Remove menu when clicking elsewhere
                setTimeout(function() {
                    document.addEventListener('click', function removeMenu() {
                        if (menu && menu.parentNode) {
                            menu.remove();
                        }
                        document.removeEventListener('click', removeMenu);
                    });
                }, 10);
            }
        });
        
        // Add hover effect for images
        document.addEventListener('mouseover', function(e) {
            if (e.target.tagName === 'IMG') {
                e.target.style.transition = 'border 0.2s';
                e.target.style.border = '2px solid #4CAF50';
            }
        });
        
        document.addEventListener('mouseout', function(e) {
            if (e.target.tagName === 'IMG') {
                e.target.style.border = '';
            }
        });
        
        // Listen for clicks on images to show selection button
        document.addEventListener('click', function(e) {
            if (e.target.tagName === 'IMG') {
                // Store the clicked image
                window.selectedImageUrl = e.target.src;
                window.selectedImageFilename = e.target.src.split('/').pop().split('?')[0];
                
                // Show button with filename
                if (window.showImageButton) {
                    window.showImageButton(e.target.src, window.selectedImageFilename);
                }
            }
        });
        
        // Function to be called from Python to show button
        window.showImageButton = function(url, filename) {
            // This will be overridden by Python
            console.log('Image ready for selection:', url, filename);
        };
        """
        
        self.web_view.page().runJavaScript(js_code)
    
    def handle_image_selected(self, image_url):
        """Handle image selection from JavaScript"""
        self.selected_image_url = image_url
        filename = image_url.split('/')[-1].split('?')[0]
        self.selected_image_filename = filename if filename else "image.jpg"
        
        # Enable the image button
        if self.image_button:
            self.image_button.setEnabled(True)
    
    def perform_search(self):
        """Perform image search"""
        search_query = quote(self.search_input.text())
        url = f"https://www.google.com/search?q={search_query}&tbm=isch&tbs=isz:l"
        self.web_view.load(QUrl(url))
        
        # Re-inject JavaScript after page loads
        self.web_view.loadFinished.connect(self.on_page_loaded)
    
    def on_page_loaded(self):
        """Handle page load completion"""
        # Disconnect to avoid multiple connections
        try:
            self.web_view.loadFinished.disconnect(self.on_page_loaded)
        except:
            pass
        
        # Re-inject JavaScript
        self.inject_javascript()
        
        # Set up showImageButton function
        self.setup_image_button_handler()
    
    def setup_image_button_handler(self):
        """Set up JavaScript function to show image button"""
        js_code = """
        window.showImageButton = function(url, filename) {
            // Send to Python
            console.log('Image selected: ' + url);
            
            // Store for button
            window.selectedImageUrl = url;
            window.selectedImageFilename = filename;
        };
        """
        
        self.web_view.page().runJavaScript(js_code)
    
    def confirm_image_selection(self):
        """Show confirmation dialog and handle image selection"""
        if not self.selected_image_url:
            QMessageBox.warning(self, "No Image", "Please select an image first!")
            return
        
        reply = QMessageBox.question(
            self, "Use This Image?",
            f"Use this image as cover?\n\nURL: {self.selected_image_url[:100]}...",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.accept()

class GameLibraryApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FlashVault - Flash Media Library")
        self.setGeometry(100, 100, 1200, 800)
        
        # Set window icon
        self.set_window_icon()
        
        # Initialize database
        self.db = GameDatabase()
        
        # Load configuration
        self.config = self.load_config()
        
        # Create hidden games folder structure
        self.hidden_games_folder = "data/.games"
        self.hidden_covers_folder = "data/.covers"
        
        for folder in [self.hidden_games_folder, self.hidden_covers_folder]:
            os.makedirs(folder, exist_ok=True)
        
        # Set hidden attribute on Windows
        if platform.system() == "Windows":
            try:
                import ctypes
                for folder in [self.hidden_games_folder, self.hidden_covers_folder]:
                    if os.path.exists(folder):
                        ctypes.windll.kernel32.SetFileAttributesW(folder, 2)
            except:
                pass
        
        # Default cover path - in covers folder
        self.default_cover_path = os.path.join(self.hidden_covers_folder, "default_cover.png")
        
        # Check if default cover exists, if not create a placeholder
        self.ensure_default_cover()
        
        self.setup_ui()
        self.load_games()
    
    def set_window_icon(self):
        """Set the window icon using the FlashVault logo"""
        icon_paths = [
            "flashvault_icon_256.png",
            "flashvault_icon_128.png",
            "flashvault_icon_64.png",
            "flashvault_icon.png",
            "logos/flashvault_icon_256.png",
            "logos/flashvault_icon_128.png",
            "logos/flashvault_icon_64.png"
        ]
        
        for path in icon_paths:
            if os.path.exists(path):
                self.setWindowIcon(QIcon(path))
                print(f"Using icon: {path}")
                break
        else:
            # Fallback: Create a simple icon
            self.create_fallback_icon()
    
    def create_fallback_icon(self):
        """Create a fallback icon if no logo file is found"""
        icon = QPixmap(64, 64)
        icon.fill(QColor(40, 80, 160))
        
        painter = QPainter(icon)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw simple vault icon
        painter.setBrush(QBrush(QColor(220, 180, 60)))
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawEllipse(12, 12, 40, 40)
        
        # Draw F inside
        painter.setPen(QPen(QColor(40, 80, 160), 3))
        painter.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        painter.drawText(icon.rect(), Qt.AlignmentFlag.AlignCenter, "F")
        
        painter.end()
        
        self.setWindowIcon(QIcon(icon))
    
    def ensure_default_cover(self):
        """Ensure default cover exists in the covers folder"""
        if not os.path.exists(self.default_cover_path):
            # Create a simple default cover
            pixmap = QPixmap(180, 140)
            gradient = QLinearGradient(0, 0, 180, 140)
            gradient.setColorAt(0, QColor(50, 50, 80))
            gradient.setColorAt(1, QColor(20, 20, 40))
            
            painter = QPainter(pixmap)
            painter.fillRect(pixmap.rect(), gradient)
            
            # Draw a game controller icon
            painter.setPen(QColor(100, 200, 255))
            painter.setBrush(QColor(100, 200, 255, 100))
            painter.drawEllipse(60, 30, 60, 60)  # Left circle
            painter.drawEllipse(120, 30, 60, 60)  # Right circle
            painter.drawRect(80, 50, 80, 40)  # Middle rectangle
            
            # Draw text
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "FLASH GAME")
            
            painter.setFont(QFont("Arial", 8))
            painter.setPen(QColor(200, 200, 200))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, "DEFAULT COVER")
            
            painter.end()
            
            # Save to covers folder
            pixmap.save(self.default_cover_path)
            print(f"Created default cover at: {self.default_cover_path}")
    
    def load_config(self):
        """Load or create configuration file"""
        config_path = "data/config.json"
        default_config = {
            "flash_players": [
                {
                    "name": "Standalone Flash Player",
                    "path": "flash_player/flashplayer.exe",
                    "args": "{file}",
                    "enabled": True
                }
            ],
            "use_inapp_browser": True,
            "thumbnail_style": "name_background",  # Options: "name_background", "default_picture"
            "recent_searches": []
        }
        
        if not os.path.exists(config_path):
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
            
            return config
        except:
            return default_config
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create header with logo
        header = self.create_header()
        main_layout.addWidget(header)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: white;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
            }
            QTabBar::tab:hover:!selected {
                background-color: #3d3d3d;
            }
        """)
        
        self.library_tab = QWidget()
        self.setup_library_tab()
        self.tabs.addTab(self.library_tab, "📚 Game Library")
        
        self.settings_tab = QWidget()
        self.setup_settings_tab()
        self.tabs.addTab(self.settings_tab, "⚙️ Settings")
        
        main_layout.addWidget(self.tabs)
        
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: white;
            }
            QPushButton {
                background-color: #444;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:pressed {
                background-color: #333;
            }
            QLineEdit, QComboBox {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #444;
                padding: 6px;
                border-radius: 4px;
            }
            QLabel {
                color: white;
            }
        """)
    
    def create_header(self):
        """Create header with FlashVault logo and title"""
        header = QWidget()
        header.setFixedHeight(80)
        header.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-bottom: 2px solid #4CAF50;
            }
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # Try to load logo
        logo_label = QLabel()
        logo_label.setFixedSize(60, 60)
        
        logo_paths = [
            "flashvault_icon_64.png",
            "flashvault_icon.png",
            "logos/flashvault_icon_64.png",
            "logos/flashvault_icon.png"
        ]
        
        logo_loaded = False
        for path in logo_paths:
            if os.path.exists(path):
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    logo_label.setPixmap(pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    logo_loaded = True
                    break
        
        if not logo_loaded:
            # Create simple logo
            pixmap = QPixmap(60, 60)
            pixmap.fill(QColor(40, 80, 160))
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QBrush(QColor(220, 180, 60)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(10, 10, 40, 40)
            
            painter.setPen(QPen(QColor(40, 80, 160), 3))
            painter.setFont(QFont("Arial", 20, QFont.Weight.Bold))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "F")
            painter.end()
            
            logo_label.setPixmap(pixmap)
        
        # Title
        title_label = QLabel("FlashVault")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 28px;
                font-weight: bold;
                padding-left: 15px;
            }
        """)
        
        # Subtitle
        subtitle_label = QLabel("Flash Media Library Manager")
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #aaa;
                font-size: 14px;
                padding-left: 15px;
            }
        """)
        
        title_layout = QVBoxLayout()
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        title_layout.setSpacing(0)
        
        layout.addWidget(logo_label)
        layout.addLayout(title_layout)
        layout.addStretch()
        
        # Stats label
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("""
            QLabel {
                color: #4CAF50;
                font-size: 12px;
                padding: 5px 10px;
                background-color: #333;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.stats_label)
        
        return header
    
    def setup_library_tab(self):
        layout = QVBoxLayout(self.library_tab)
        
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        
        add_btn = QPushButton("➕ Add Game")
        add_btn.clicked.connect(self.add_game_dialog)
        add_btn.setStyleSheet("background-color: #4CAF50;")
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_games)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search games...")
        self.search_input.textChanged.connect(self.filter_games)
        
        toolbar_layout.addWidget(add_btn)
        toolbar_layout.addWidget(refresh_btn)
        toolbar_layout.addWidget(self.search_input)
        toolbar_layout.addStretch()
        
        self.games_scroll = QScrollArea()
        self.games_widget = QWidget()
        self.games_layout = QGridLayout(self.games_widget)
        self.games_layout.setSpacing(20)
        self.games_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.games_scroll.setWidget(self.games_widget)
        self.games_scroll.setWidgetResizable(True)
        
        layout.addWidget(toolbar)
        layout.addWidget(self.games_scroll)
    
    def setup_settings_tab(self):
        layout = QVBoxLayout(self.settings_tab)
        
        player_group = QGroupBox("⚡ Flash Player Configuration")
        player_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4CAF50;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        player_layout = QVBoxLayout(player_group)
        
        player_layout.addWidget(QLabel("Flash Player Path:"))
        
        player_path_layout = QHBoxLayout()
        self.player_path_input = QLineEdit(self.config["flash_players"][0]["path"])
        browse_player_btn = QPushButton("Browse...")
        browse_player_btn.clicked.connect(self.browse_flash_player)
        
        player_path_layout.addWidget(self.player_path_input)
        player_path_layout.addWidget(browse_player_btn)
        player_layout.addLayout(player_path_layout)
        
        test_player_btn = QPushButton("🧪 Test Flash Player")
        test_player_btn.clicked.connect(self.test_current_player)
        player_layout.addWidget(test_player_btn)
        
        browser_group = QGroupBox("🌐 In-App Browser & Cover Settings")
        browser_group.setStyleSheet(player_group.styleSheet())
        browser_layout = QVBoxLayout(browser_group)
        
        self.use_inapp_browser_cb = QCheckBox("Use enhanced in-app browser for image searches")
        self.use_inapp_browser_cb.setChecked(self.config.get("use_inapp_browser", True))
        
        browser_features = QLabel("Features: Right-click menu, Auto-download, Visual feedback")
        browser_features.setStyleSheet("color: #aaa; font-size: 11px; padding-left: 20px;")
        
        browser_layout.addWidget(self.use_inapp_browser_cb)
        browser_layout.addWidget(browser_features)
        
        # Cover style settings
        cover_style_group = QGroupBox("🖼️ Default Cover Style")
        cover_style_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2196F3;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        cover_style_layout = QVBoxLayout(cover_style_group)
        
        # Thumbnail style radio buttons
        self.name_background_rb = QRadioButton("Name Background (game name on gradient)")
        self.default_picture_rb = QRadioButton("Default Picture (uses Program Icno as background)")
        
        # Set current selection
        if self.config.get("thumbnail_style", "name_background") == "name_background":
            self.name_background_rb.setChecked(True)
        else:
            self.default_picture_rb.setChecked(True)
        
        cover_style_layout.addWidget(self.name_background_rb)
        cover_style_layout.addWidget(self.default_picture_rb)
        
        browser_layout.addWidget(cover_style_group)
        
        danger_group = QGroupBox("⚠️  Dangerous Actions")
        danger_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ff4444;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        danger_layout = QVBoxLayout(danger_group)
        
        import_btn = QPushButton("📂 Import All SWF Files from Folder")
        import_btn.clicked.connect(self.import_from_folder)
        
        clear_btn = QPushButton("🗑️ DELETE ALL GAMES")
        clear_btn.clicked.connect(self.clear_library)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #ff6666;
            }
        """)
        
        danger_layout.addWidget(import_btn)
        danger_layout.addWidget(clear_btn)
        
        save_btn = QPushButton("💾 Save Settings")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setStyleSheet("background-color: #4CAF50;")
        
        layout.addWidget(player_group)
        layout.addWidget(browser_group)
        layout.addWidget(danger_group)
        layout.addStretch()
        layout.addWidget(save_btn)
    
    def load_games(self):
        """Load and display games from database"""
        for i in reversed(range(self.games_layout.count())): 
            widget = self.games_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        games = self.db.get_all_games()
        
        # Update stats
        total_games = len(games)
        total_plays = sum(game[6] for game in games)  # play_count is at index 6
        
        self.stats_label.setText(f"📊 Games: {total_games} | 🎮 Total Plays: {total_plays}")
        
        for i, game in enumerate(games):
            game_id, title, swf_path, thumbnail_path, added_date, last_played, play_count = game
            
            card = self.create_game_card(game_id, title, swf_path, thumbnail_path, play_count)
            
            row = i // 4
            col = i % 4
            self.games_layout.addWidget(card, row, col)
        
        self.games_layout.setRowStretch(self.games_layout.rowCount(), 1)
    
    def create_game_card(self, game_id, title, swf_path, thumbnail_path, play_count):
        """Create a game card widget"""
        card = QWidget()
        card.setFixedSize(220, 280)
        card.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-radius: 8px;
                border: 1px solid #444;
            }
            QWidget:hover {
                border: 1px solid #4CAF50;
                background-color: #333;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        thumbnail_label = QLabel()
        thumbnail_label.setFixedSize(180, 140)
        thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumbnail_label.setCursor(Qt.CursorShape.PointingHandCursor)
        
        pixmap = self.create_thumbnail(thumbnail_path, title)
        thumbnail_label.setPixmap(pixmap)
        
        thumbnail_label.mousePressEvent = lambda event, gid=game_id, t=title, sp=swf_path: self.edit_game_thumbnail(gid, t, sp)
        
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_label.setWordWrap(True)
        
        info_label = QLabel(f"▶️ Plays: {play_count}")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #aaa; font-size: 12px;")
        
        play_btn = QPushButton("🎮 Play")
        play_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #66bb6a;
            }
        """)
        play_btn.clicked.connect(lambda: self.play_game(game_id, title, swf_path))
        
        menu_btn = QPushButton("⋯ Menu")
        menu_btn.setStyleSheet("""
            QPushButton {
                background-color: #666;
                font-size: 11px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #777;
            }
        """)
        menu_btn.clicked.connect(lambda: self.show_game_menu(game_id, title, swf_path))
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(play_btn)
        button_layout.addWidget(menu_btn)
        
        layout.addWidget(thumbnail_label)
        layout.addWidget(title_label)
        layout.addWidget(info_label)
        layout.addLayout(button_layout)
        
        return card
    
    def create_thumbnail(self, thumbnail_path, title):
        """Create thumbnail based on settings"""
        # If there's a custom thumbnail, use it
        if thumbnail_path and os.path.exists(thumbnail_path):
            pixmap = QPixmap(thumbnail_path)
            return pixmap.scaled(180, 140, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        # Otherwise, use default style based on settings
        style = self.config.get("thumbnail_style", "name_background")
        
        if style == "default_picture" and os.path.exists(self.default_cover_path):
            # Use default picture from covers folder
            pixmap = QPixmap(self.default_cover_path)
            return pixmap.scaled(180, 140, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        else:
            # Create name-based background
            return self.create_name_based_thumbnail(title)
    
    def create_name_based_thumbnail(self, title):
        """Create a nice default thumbnail with game name"""
        pixmap = QPixmap(180, 140)
        
        # Create gradient background
        gradient = QLinearGradient(0, 0, 180, 140)
        gradient.setColorAt(0, QColor(70, 70, 120))
        gradient.setColorAt(1, QColor(30, 30, 60))
        
        painter = QPainter(pixmap)
        painter.fillRect(pixmap.rect(), gradient)
        
        # Draw game icon
        painter.setPen(QColor(100, 200, 255, 150))
        painter.setBrush(QColor(100, 200, 255, 50))
        painter.drawEllipse(90, 50, 60, 60)
        
        # Draw game title
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        
        # Split title if too long
        if len(title) > 15:
            words = title.split()
            lines = []
            current_line = ""
            
            for word in words:
                if len(current_line) + len(word) + 1 <= 15:
                    current_line += (" " if current_line else "") + word
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            # Draw multiple lines
            font_metrics = painter.fontMetrics()
            line_height = font_metrics.height()
            total_height = len(lines) * line_height
            start_y = (140 - total_height) // 2 + font_metrics.ascent()
            
            for i, line in enumerate(lines):
                text_rect = painter.fontMetrics().boundingRect(line)
                x = (180 - text_rect.width()) // 2
                y = start_y + (i * line_height)
                painter.drawText(x, y, line)
        else:
            # Draw single line
            text_rect = painter.fontMetrics().boundingRect(title)
            x = (180 - text_rect.width()) // 2
            y = (140 - text_rect.height()) // 2 + painter.fontMetrics().ascent()
            painter.drawText(x, y, title)
        
        # Draw "Flash Game" label
        painter.setFont(QFont("Arial", 8))
        painter.setPen(QColor(200, 200, 200))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, "FLASH GAME")
        
        painter.end()
        
        return pixmap.scaled(180, 140, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    
    def add_game_dialog(self):
        """Open dialog to add a new game"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Game - FlashVault")
        dialog.setFixedSize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("Select Flash Game File (.swf):"))
        file_layout = QHBoxLayout()
        
        swf_path_input = QLineEdit()
        browse_swf_btn = QPushButton("Browse...")
        browse_swf_btn.clicked.connect(lambda: self.browse_file(swf_path_input, "Flash Files (*.swf)"))
        
        file_layout.addWidget(swf_path_input)
        file_layout.addWidget(browse_swf_btn)
        layout.addLayout(file_layout)
        
        layout.addWidget(QLabel("Game Title:"))
        title_input = QLineEdit()
        
        def auto_fill_title():
            if swf_path_input.text() and not title_input.text():
                filename = os.path.basename(swf_path_input.text())
                title = os.path.splitext(filename)[0]
                title_input.setText(title)
        
        swf_path_input.textChanged.connect(auto_fill_title)
        layout.addWidget(title_input)
        
        layout.addWidget(QLabel("\nThumbnail Options (Choose One):"))
        
        # Create exclusive thumbnail options
        thumbnail_group = QButtonGroup()
        
        default_style = self.config.get("thumbnail_style", "name_background")
        default_style_name = "Name Background" if default_style == "name_background" else "Default Picture"
        
        # Radio button for default thumbnail
        default_rb = QRadioButton(f"Default ({default_style_name})")
        default_rb.setChecked(True)
        
        # Radio button for custom thumbnail
        custom_rb = QRadioButton("Custom Image")
        
        # Radio button for web search
        web_rb = QRadioButton("Search Web")
        
        # Add to button group for exclusivity
        thumbnail_group.addButton(default_rb)
        thumbnail_group.addButton(custom_rb)
        thumbnail_group.addButton(web_rb)
        
        layout.addWidget(default_rb)
        layout.addWidget(custom_rb)
        layout.addWidget(web_rb)
        
        # Custom file selection (initially disabled)
        custom_file_layout = QHBoxLayout()
        custom_file_input = QLineEdit()
        custom_file_input.setEnabled(False)
        browse_custom_btn = QPushButton("Browse...")
        browse_custom_btn.setEnabled(False)
        browse_custom_btn.clicked.connect(lambda: self.browse_file(custom_file_input, "Images (*.png *.jpg *.jpeg)"))
        
        custom_file_layout.addWidget(custom_file_input)
        custom_file_layout.addWidget(browse_custom_btn)
        
        # Enable/disable custom file selection based on radio button
        def toggle_custom_file(enabled):
            custom_file_input.setEnabled(enabled)
            browse_custom_btn.setEnabled(enabled)
        
        custom_rb.toggled.connect(toggle_custom_file)
        
        layout.addLayout(custom_file_layout)
        
        # Note about web search
        note_label = QLabel(f"💡 Web search uses enhanced browser with right-click menu and auto-download")
        note_label.setStyleSheet("color: #4CAF50; font-size: 11px; padding: 5px; background-color: #2d2d2d;")
        note_label.setWordWrap(True)
        layout.addWidget(note_label)
        
        button_layout = QHBoxLayout()
        
        def add_game_to_library():
            swf_path = swf_path_input.text().strip()
            title = title_input.text().strip()
            
            if not swf_path or not os.path.exists(swf_path):
                QMessageBox.warning(dialog, "Invalid File", "Please select a valid SWF file!")
                return
            
            if not title:
                title = os.path.splitext(os.path.basename(swf_path))[0]
            
            # Copy to hidden folder
            new_swf_path = self.copy_to_hidden_folder(swf_path, title)
            
            thumbnail_path = None
            
            # Handle thumbnail based on selected option
            if custom_rb.isChecked():
                # Custom image
                if custom_file_input.text():
                    thumb_source = custom_file_input.text()
                    if os.path.exists(thumb_source):
                        thumbnail_path = self.save_thumbnail(thumb_source, title)
                    else:
                        QMessageBox.warning(dialog, "Invalid File", "Selected image file doesn't exist!")
                        return
                else:
                    QMessageBox.warning(dialog, "No Image", "Please select a custom image!")
                    return
                    
            elif web_rb.isChecked():
                # Web search
                thumbnail_path = self.open_inapp_browser_search(title, dialog)
                
                if not thumbnail_path:
                    # User cancelled or failed to download, use default
                    thumbnail_path = None
            
            # If default is selected or web search failed, thumbnail_path remains None (will use default)
            
            self.db.add_game(title, new_swf_path, thumbnail_path)
            self.load_games()
            
            # Determine what thumbnail was used
            if thumbnail_path:
                thumb_type = "Custom"
            else:
                thumb_type = f"Default ({default_style_name})"
            
            QMessageBox.information(dialog, "Success", 
                f"Game '{title}' added successfully!\n"
                f"Location: Hidden Games Folder\n"
                f"Thumbnail: {thumb_type}")
            
            dialog.accept()
        
        add_btn = QPushButton("➕ Add Game")
        add_btn.clicked.connect(add_game_to_library)
        add_btn.setStyleSheet("background-color: #4CAF50;")
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addWidget(add_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def copy_to_hidden_folder(self, swf_path, title):
        """Copy SWF file to hidden games folder"""
        try:
            base_name = os.path.basename(swf_path)
            name, ext = os.path.splitext(base_name)
            
            # Clean title for filename
            clean_title = title.replace(' ', '_')
            clean_title = "".join(c for c in clean_title if c.isalnum() or c in ('_', '-')).strip()
            
            new_filename = f"{clean_title}{ext}"
            new_path = os.path.join(self.hidden_games_folder, new_filename)
            
            counter = 1
            while os.path.exists(new_path):
                new_filename = f"{clean_title}_{counter}{ext}"
                new_path = os.path.join(self.hidden_games_folder, new_filename)
                counter += 1
            
            shutil.copy2(swf_path, new_path)
            return new_path
            
        except Exception as e:
            QMessageBox.warning(self, "Copy Failed", 
                f"Could not copy to hidden folder:\n{str(e)}\n\nUsing original location.")
            return swf_path
    
    def save_thumbnail(self, image_path, title):
        """Save thumbnail to hidden covers folder"""
        try:
            # Clean title for filename
            clean_title = title.replace(' ', '_')
            clean_title = "".join(c for c in clean_title if c.isalnum() or c in ('_', '-')).strip()
            
            ext = os.path.splitext(image_path)[1].lower()
            if ext not in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
                ext = '.jpg'
            
            thumb_filename = f"{clean_title}_cover{ext}"
            thumb_path = os.path.join(self.hidden_covers_folder, thumb_filename)
            
            counter = 1
            while os.path.exists(thumb_path):
                thumb_filename = f"{clean_title}_cover_{counter}{ext}"
                thumb_path = os.path.join(self.hidden_covers_folder, thumb_filename)
                counter += 1
            
            shutil.copy2(image_path, thumb_path)
            return thumb_path
            
        except Exception as e:
            print(f"Failed to save thumbnail: {e}")
            return None
    
    def open_inapp_browser_search(self, title, parent_dialog=None):
        """Open enhanced in-app browser for image search"""
        try:
            browser_dialog = ImageBrowserDialog(self, title)
            
            if browser_dialog.exec() == QDialog.DialogCode.Accepted:
                if browser_dialog.selected_image_url:
                    # Download the image
                    thumbnail_path = self.download_image_from_url(
                        browser_dialog.selected_image_url, 
                        title
                    )
                    return thumbnail_path
            
            return None
            
        except Exception as e:
            print(f"In-app browser error: {e}")
            QMessageBox.warning(self, "Browser Error", 
                f"In-app browser error:\n{str(e)}\n\nOpening external browser instead.")
            return self.open_external_browser_search(title, parent_dialog)
    
    def download_image_from_url(self, image_url, title):
        """Download image from URL and save to covers folder"""
        try:
            if image_url.startswith('file:///'):
                # Local file
                local_path = image_url.replace('file:///', '')
                if os.path.exists(local_path):
                    return self.save_thumbnail(local_path, title)
                return None
            
            # Download from web
            # Create clean filename
            clean_title = title.replace(' ', '_')
            clean_title = "".join(c for c in clean_title if c.isalnum() or c in ('_', '-')).strip()
            
            # Get extension from URL or use default
            parsed_url = urlparse(image_url)
            path = parsed_url.path
            filename = os.path.basename(path)
            
            if '.' in filename:
                ext = os.path.splitext(filename)[1].split('?')[0]
                if len(ext) > 5:  # Too long, probably not extension
                    ext = '.jpg'
            else:
                ext = '.jpg'
            
            if ext not in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp']:
                ext = '.jpg'
            
            thumb_filename = f"{clean_title}_cover{ext}"
            thumb_path = os.path.join(self.hidden_covers_folder, thumb_filename)
            
            # Download the image
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            req = urllib.request.Request(image_url, headers=headers)
            
            with urllib.request.urlopen(req) as response:
                image_data = response.read()
            
            # Save to file
            with open(thumb_path, 'wb') as f:
                f.write(image_data)
            
            print(f"Image downloaded to: {thumb_path}")
            return thumb_path
            
        except Exception as e:
            print(f"Failed to download image: {e}")
            QMessageBox.warning(self, "Download Failed", 
                f"Could not download image:\n{str(e)}")
            return None
    
    def open_external_browser_search(self, title, parent_dialog=None):
        """Open external browser for image search"""
        search_query = quote(f"{title} flash game cover")
        webbrowser.open(f"https://www.google.com/search?q={search_query}&tbm=isch")
        
        if parent_dialog:
            QMessageBox.information(parent_dialog, "Browser Opened",
                "Browser opened for image search.\n\n"
                "Find and download an image, then select it.")
            
            image_file, _ = QFileDialog.getOpenFileName(
                parent_dialog, "Select Downloaded Image", "", 
                "Images (*.png *.jpg *.jpeg)"
            )
            
            if image_file:
                return self.save_thumbnail(image_file, title)
        
        return None
    
    def edit_game_thumbnail(self, game_id, title, swf_path):
        """Edit thumbnail for a game"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit Thumbnail: {title}")
        dialog.setFixedSize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("Choose thumbnail option:"))
        
        # Get current thumbnail style
        style = self.config.get("thumbnail_style", "name_background")
        default_style_name = "Name Background" if style == "name_background" else "Default Picture"
        
        online_btn = QPushButton("🔍 Search Web")
        online_btn.clicked.connect(lambda: self.search_and_set_thumbnail(game_id, title, dialog))
        
        custom_btn = QPushButton("📁 Use Custom Image")
        custom_btn.clicked.connect(lambda: self.update_thumbnail_from_file(game_id, dialog))
        
        default_btn = QPushButton(f"🎨 Use Default ({default_style_name})")
        default_btn.clicked.connect(lambda: self.update_thumbnail_to_default(game_id, dialog))
        
        for btn in [online_btn, custom_btn, default_btn]:
            btn.setStyleSheet("text-align: left; padding: 10px;")
            layout.addWidget(btn)
        
        layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        layout.addWidget(cancel_btn)
        
        dialog.exec()
    
    def search_and_set_thumbnail(self, game_id, title, dialog):
        """Search online and set thumbnail"""
        thumbnail_path = self.open_inapp_browser_search(title, dialog)
        
        if thumbnail_path:
            cursor = self.db.conn.cursor()
            cursor.execute('UPDATE games SET thumbnail_path = ? WHERE id = ?', (thumbnail_path, game_id))
            self.db.conn.commit()
            self.load_games()
            QMessageBox.information(self, "Success", "Thumbnail updated from web search!")
            dialog.accept()
    
    def update_thumbnail_from_file(self, game_id, dialog):
        """Update thumbnail from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Thumbnail Image", "", 
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        
        if file_path:
            cursor = self.db.conn.cursor()
            cursor.execute('SELECT title FROM games WHERE id = ?', (game_id,))
            result = cursor.fetchone()
            title = result[0] if result else f"game_{game_id}"
            
            thumbnail_path = self.save_thumbnail(file_path, title)
            
            if thumbnail_path:
                cursor.execute('UPDATE games SET thumbnail_path = ? WHERE id = ?', (thumbnail_path, game_id))
                self.db.conn.commit()
                self.load_games()
                QMessageBox.information(self, "Success", "Custom thumbnail saved!")
                dialog.accept()
    
    def update_thumbnail_to_default(self, game_id, dialog):
        """Set thumbnail to default"""
        cursor = self.db.conn.cursor()
        cursor.execute('UPDATE games SET thumbnail_path = ? WHERE id = ?', (None, game_id))
        self.db.conn.commit()
        self.load_games()
        QMessageBox.information(self, "Success", "Thumbnail set to default!")
        dialog.accept()
    
    def show_game_menu(self, game_id, title, swf_path):
        """Show context menu for game"""
        menu = QMenu(self)
        
        play_action = menu.addAction("🎮 Play")
        play_action.triggered.connect(lambda: self.play_game(game_id, title, swf_path))
        
        edit_thumb_action = menu.addAction("🖼️ Edit Thumbnail")
        edit_thumb_action.triggered.connect(lambda: self.edit_game_thumbnail(game_id, title, swf_path))
        
        menu.addSeparator()
        
        remove_action = menu.addAction("🗑️ Remove Game")
        remove_action.triggered.connect(lambda: self.remove_game(game_id, title))
        
        menu.exec(QCursor.pos())
    
    def browse_flash_player(self):
        """Browse for Flash player executable"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Flash Player", "", "Executables (*.exe);;All Files (*.*)")
        if file_path:
            self.player_path_input.setText(file_path)
    
    def browse_file(self, input_widget, filter_str):
        """Browse for file"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", "", filter_str)
        if file_path:
            input_widget.setText(file_path)
    
    def test_current_player(self):
        """Test the current Flash player"""
        player_path = self.player_path_input.text()
        
        if not player_path or not os.path.exists(player_path):
            QMessageBox.warning(self, "Player Not Found", 
                "Flash player path is invalid or file doesn't exist.")
            return
        
        games = self.db.get_all_games()
        if games:
            test_file = games[0][2]
            try:
                subprocess.Popen([player_path, test_file])
                QMessageBox.information(self, "Test Successful", 
                    f"Flash player launched successfully!\n\n"
                    f"Player: {os.path.basename(player_path)}\n"
                    f"Test Game: {games[0][1]}")
            except Exception as e:
                QMessageBox.critical(self, "Test Failed", 
                    f"Failed to launch Flash player:\n\n{str(e)}")
        else:
            QMessageBox.information(self, "No Games", 
                "Add a game first to test the Flash player.")
    
    def play_game(self, game_id, title, swf_path):
        """Play the selected game"""
        self.db.update_play_stats(game_id)
        
        player_path = self.player_path_input.text() or self.config["flash_players"][0]["path"]
        
        if not os.path.exists(player_path):
            reply = QMessageBox.question(
                self, "Flash Player Not Found",
                f"Flash player not found at:\n{player_path}\n\n"
                "Browse for Flash player?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.browse_flash_player()
                player_path = self.player_path_input.text()
            else:
                return
        
        try:
            subprocess.Popen([player_path, swf_path])
            self.statusBar().showMessage(f"🎮 Playing: {title}", 3000)
            
        except Exception as e:
            QMessageBox.critical(self, "Launch Failed", 
                f"Error launching game:\n\n{str(e)}")
    
    def remove_game(self, game_id, title):
        """Remove game from library"""
        reply = QMessageBox.question(
            self, "Remove Game",
            f"Remove '{title}' from library?\n\n"
            "✓ Game file will be deleted from hidden folder\n"
            "✓ Custom thumbnail will be deleted\n"
            "✓ This cannot be undone",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            cursor = self.db.conn.cursor()
            cursor.execute('SELECT swf_path, thumbnail_path FROM games WHERE id = ?', (game_id,))
            result = cursor.fetchone()
            
            if result:
                swf_path, thumb_path = result
                
                # Only delete custom thumbnails, not the default cover
                if thumb_path and os.path.exists(thumb_path) and thumb_path != self.default_cover_path:
                    try:
                        os.remove(thumb_path)
                    except:
                        pass
                
                if self.hidden_games_folder in swf_path and os.path.exists(swf_path):
                    try:
                        os.remove(swf_path)
                    except:
                        pass
            
            cursor.execute('DELETE FROM games WHERE id = ?', (game_id,))
            self.db.conn.commit()
            self.load_games()
            QMessageBox.information(self, "Removed", f"'{title}' removed from library!")
    
    def import_from_folder(self):
        """Import all SWF files from a folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with SWF Files")
        if folder:
            count = 0
            for file in os.listdir(folder):
                if file.lower().endswith('.swf'):
                    swf_path = os.path.join(folder, file)
                    title = os.path.splitext(file)[0]
                    
                    cursor = self.db.conn.cursor()
                    cursor.execute('SELECT id FROM games WHERE swf_path = ?', (swf_path,))
                    if not cursor.fetchone():
                        new_path = self.copy_to_hidden_folder(swf_path, title)
                        # Add with default thumbnail (None means use default style)
                        self.db.add_game(title, new_path, None)
                        count += 1
            
            self.load_games()
            QMessageBox.information(self, "Import Complete", 
                f"Imported {count} new games with default thumbnails!\n\n"
                f"All games copied to: {self.hidden_games_folder}")
    
    def clear_library(self):
        """Clear all games from library"""
        reply = QMessageBox.question(
            self, "⚠️ DELETE ALL GAMES", 
            "Are you SURE you want to delete ALL games from your library?\n\n"
            "This will delete:\n"
            "• All games from the database\n"
            "• All custom thumbnails\n"
            "• All games in hidden folder\n\n"
            "THIS ACTION CANNOT BE UNDONE!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            final_reply = QMessageBox.critical(
                self, "⚠️ FINAL WARNING",
                "🚨 LAST CHANCE TO CANCEL! 🚨\n\n"
                "Clicking YES will PERMANENTLY delete:\n"
                "• All your games\n"
                "• All thumbnails\n"
                "• Everything in the hidden folder\n\n"
                "Are you ABSOLUTELY sure?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if final_reply == QMessageBox.StandardButton.Yes:
                games = self.db.get_all_games()
                game_count = len(games)
                
                thumb_count = 0
                for game in games:
                    thumb_path = game[3]
                    # Only delete custom thumbnails, not the default cover
                    if thumb_path and os.path.exists(thumb_path) and thumb_path != self.default_cover_path:
                        try:
                            os.remove(thumb_path)
                            thumb_count += 1
                        except:
                            pass
                
                game_files_count = 0
                if os.path.exists(self.hidden_games_folder):
                    for file in os.listdir(self.hidden_games_folder):
                        if file.lower().endswith('.swf'):
                            try:
                                os.remove(os.path.join(self.hidden_games_folder, file))
                                game_files_count += 1
                            except:
                                pass
                
                cursor = self.db.conn.cursor()
                cursor.execute('DELETE FROM games')
                self.db.conn.commit()
                self.load_games()
                
                QMessageBox.information(self, "Library Cleared", 
                    f"✅ All games have been deleted!\n\n"
                    f"• {game_count} games removed from database\n"
                    f"• {thumb_count} custom thumbnails deleted\n"
                    f"• {game_files_count} game files deleted from hidden folder")
    
    def filter_games(self):
        """Filter games based on search text"""
        search_text = self.search_input.text().lower() if self.search_input else ""
        
        for i in reversed(range(self.games_layout.count())): 
            widget = self.games_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        games = self.db.get_all_games()
        
        visible_games = 0
        for i, game in enumerate(games):
            game_id, title, swf_path, thumbnail_path, added_date, last_played, play_count = game
            
            if search_text and search_text not in title.lower():
                continue
            
            card = self.create_game_card(game_id, title, swf_path, thumbnail_path, play_count)
            
            row = visible_games // 4
            col = visible_games % 4
            self.games_layout.addWidget(card, row, col)
            visible_games += 1
        
        self.games_layout.setRowStretch(self.games_layout.rowCount(), 1)
    
    def save_settings(self):
        """Save settings to config file"""
        try:
            self.config["use_inapp_browser"] = self.use_inapp_browser_cb.isChecked()
            self.config["flash_players"][0]["path"] = self.player_path_input.text()
            
            # Get thumbnail style
            if self.name_background_rb.isChecked():
                self.config["thumbnail_style"] = "name_background"
            else:
                self.config["thumbnail_style"] = "default_picture"
            
            config_path = "data/config.json"
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            
            QMessageBox.information(self, "Success", "Settings saved successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n\n{str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = GameLibraryApp()
    window.show()
    
    sys.exit(app.exec())