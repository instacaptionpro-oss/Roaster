import os
import psycopg2
from psycopg2 import pool

class RoastPostgresDB:
    def __init__(self):
        # Get the database URL from Render's environment variable
        self.db_url = os.environ.get('DATABASE_URL')
        if not self.db_url:
            raise Exception("DATABASE_URL environment variable not set!")
        
        # Initialize a connection pool for better performance
        self.connection_pool = psycopg2.pool.SimpleConnectionPool(1, 10, self.db_url)
        self._init_db()

    def _get_connection(self):
        return self.connection_pool.getconn()

    def _release_connection(self, conn):
        self.connection_pool.putconn(conn)

    def _init_db(self):
        """Create the memes table if it doesn't exist."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS memes (
                        id SERIAL PRIMARY KEY,
                        image_path TEXT NOT NULL,
                        roast_text TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
        finally:
            self._release_connection(conn)

    def save_meme(self, image_path, roast_text):
        """Save meme metadata to PostgreSQL."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO memes (image_path, roast_text) VALUES (%s, %s) RETURNING id",
                    (image_path, roast_text)
                )
                meme_id = cursor.fetchone()[0]
                conn.commit()
                return meme_id
        finally:
            self._release_connection(conn)

# --- HOW TO USE IN YOUR MAIN APP ---
# from postgres_manager import RoastPostgresDB
# db = RoastPostgresDB()
# db.save_meme("path/to/image.png", "Your code is spaghetti!")
