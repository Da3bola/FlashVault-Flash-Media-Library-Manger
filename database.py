import sqlite3
import os

class GameDatabase:
    def __init__(self, db_path="data/library.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
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
    
    def add_game(self, title, swf_path, thumbnail_path=None):
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