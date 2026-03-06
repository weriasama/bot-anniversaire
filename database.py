import aiosqlite
import os
from datetime import datetime

class BirthdayDatabase:
    def __init__(self, db_path="birthdays.db"):
        self.db_path = db_path
    
    async def init_db(self):
        """Initialise la base de données"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS birthdays (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    day INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    year INTEGER,
                    added_by INTEGER NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
    
    async def add_birthday(self, user_id: int, username: str, day: int, month: int, year: int, added_by: int):
        """Ajoute un anniversaire"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO birthdays (user_id, username, day, month, year, added_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, username, day, month, year, added_by))
            await db.commit()
    
    async def remove_birthday(self, user_id: int):
        """Supprime un anniversaire"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM birthdays WHERE user_id = ?", (user_id,))
            await db.commit()
            return cursor.rowcount > 0
    
    async def get_birthday(self, user_id: int):
        """Récupère l'anniversaire d'un utilisateur"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT user_id, username, day, month, year 
                FROM birthdays WHERE user_id = ?
            """, (user_id,)) as cursor:
                return await cursor.fetchone()
    
    async def get_all_birthdays(self):
        """Récupère tous les anniversaires"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT user_id, username, day, month, year 
                FROM birthdays 
                ORDER BY month, day
            """) as cursor:
                return await cursor.fetchall()
    
    async def get_today_birthdays(self, day: int, month: int):
        """Récupère les anniversaires du jour"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT user_id, username, day, month, year 
                FROM birthdays 
                WHERE day = ? AND month = ?
            """, (day, month)) as cursor:
                return await cursor.fetchall()
