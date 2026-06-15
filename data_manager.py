# data_manager.py - SQLite Database Layer
import sqlite3
import os
from datetime import datetime

class DataManager:
    def __init__(self, db_path='data/bookrecommender.db'):
        self.db_path = db_path
        os.makedirs('data', exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                authors TEXT,
                description TEXT,
                categories TEXT,
                published_date TEXT,
                publisher TEXT,
                page_count INTEGER,
                thumbnail TEXT,
                last_accessed TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                book_title TEXT NOT NULL,
                rating INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        self.conn.commit()
    
    def save_book(self, book_data):
        cursor = self.conn.cursor()
        title = book_data.get('title', '')
        authors = '; '.join(book_data.get('authors', [])) if isinstance(book_data.get('authors'), list) else str(book_data.get('authors', ''))
        description = book_data.get('description', '')
        categories = '; '.join(book_data.get('categories', [])) if isinstance(book_data.get('categories'), list) else str(book_data.get('categories', ''))
        published_date = book_data.get('published_date', '')
        thumbnail = book_data.get('thumbnail', '')
        
        cursor.execute("SELECT id FROM books WHERE LOWER(title) = ?", (title.lower(),))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('''
                UPDATE books SET authors=?, description=?, categories=?, published_date=?, thumbnail=?, last_accessed=?
                WHERE id=?
            ''', (authors, description, categories, published_date, thumbnail, datetime.now().isoformat(), existing['id']))
        else:
            cursor.execute('''
                INSERT INTO books (title, authors, description, categories, published_date, thumbnail, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, authors, description, categories, published_date, thumbnail, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_book(self, title):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM books WHERE LOWER(title) = ?", (title.lower(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def save_rating(self, user_id, book_title, rating):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO ratings (user_id, book_title, rating, timestamp) VALUES (?, ?, ?, ?)',
                      (user_id, book_title, rating, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_user_ratings(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ratings WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_all_ratings(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ratings ORDER BY timestamp DESC")
        return [dict(row) for row in cursor.fetchall()]
    
    def get_rating_count(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM ratings")
        return cursor.fetchone()['count']
    
    def export_training_data(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT r.rating, b.description, b.title
            FROM ratings r
            LEFT JOIN books b ON LOWER(r.book_title) = LOWER(b.title)
            WHERE b.description IS NOT NULL AND b.description != ''
        ''')
        rows = cursor.fetchall()
        descriptions = []
        rating_values = []
        for row in rows:
            if row['description']:
                descriptions.append(row['description'])
                rating_values.append(row['rating'])
        return descriptions, rating_values