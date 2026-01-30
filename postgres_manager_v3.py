import os
import psycopg2
from psycopg2 import pool

class RoastPostgresDB:
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        if not self.db_url:
            raise Exception("DATABASE_URL environment variable not set!")
        
        self.connection_pool = psycopg2.pool.SimpleConnectionPool(1, 10, self.db_url)
        self._init_db()

    def _get_connection(self):
        return self.connection_pool.getconn()

    def _release_connection(self, conn):
        self.connection_pool.putconn(conn)

    def _init_db(self):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(80) UNIQUE NOT NULL,
                        email VARCHAR(120) UNIQUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS memes (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        image_url TEXT NOT NULL, -- CHANGED: Now stores the URL from Cloudflare R2
                        roast_text TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
        finally:
            self._release_connection(conn)

    def get_or_create_user(self, username, email=None):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                if user:
                    return user[0]
                cursor.execute(
                    "INSERT INTO users (username, email) VALUES (%s, %s) RETURNING id",
                    (username, email)
                )
                user_id = cursor.fetchone()[0]
                conn.commit()
                return user_id
        finally:
            self._release_connection(conn)

    def save_meme(self, user_id, image_url, roast_text):
        """Save meme metadata with the Cloudflare R2 URL."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO memes (user_id, image_url, roast_text) VALUES (%s, %s, %s) RETURNING id",
                    (user_id, image_url, roast_text)
                )
                meme_id = cursor.fetchone()[0]
                conn.commit()
                return meme_id
        finally:
            self._release_connection(conn)
