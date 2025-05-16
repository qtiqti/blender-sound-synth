import sqlite3
import os

DB_MANAGER = None  # Глобальный объект, который будет инициализирован в init_db()


class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        print(f"[DEBUG] Создаём DatabaseManager с базой: {db_path}")
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        # Таблица для кэширования результатов Freesound
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS freesound_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sound_id TEXT UNIQUE NOT NULL,
                name TEXT,
                preview_url TEXT,
                retrieved DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Таблица для истории поисковых запросов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_query TEXT NOT NULL,
                created DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Таблица для пользовательских пресетов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                preset_name TEXT UNIQUE NOT NULL,
                start_frame INTEGER,
                end_frame INTEGER,
                volume REAL,
                repeat_frames TEXT,
                spectral_mod REAL,
                created DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
        print("[DEBUG] Таблицы созданы.")

    def add_freesound_result(self, sound_id, name, preview_url):
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO freesound_cache (sound_id, name, preview_url)
                VALUES (?, ?, ?)
            """, (sound_id, name, preview_url))
            self.conn.commit()
            print(f"[DEBUG] Добавлена запись в freesound_cache: {sound_id}, {name}")
        except Exception as e:
            print("Ошибка записи в freesound_cache:", e)

    def add_search_history(self, search_query):
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO user_search_history (search_query)
                VALUES (?)
            """, (search_query,))
            self.conn.commit()
            print(f"[DEBUG] Добавлен поисковой запрос в историю: {search_query}")
        except Exception as e:
            print("Ошибка записи в user_search_history:", e)

    def add_user_preset(self, preset_name, start_frame, end_frame, volume, repeat_frames, spectral_mod):
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO user_presets (preset_name, start_frame, end_frame, volume, repeat_frames, spectral_mod)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (preset_name, start_frame, end_frame, volume, repeat_frames, spectral_mod))
            self.conn.commit()
            print(f"[DEBUG] Добавлен пользовательский пресет: {preset_name}")
        except Exception as e:
            print("Ошибка записи в user_presets:", e)

    def close(self):
        self.conn.close()
        print("[DEBUG] Соединение с БД закрыто.")


def init_db():
    global DB_MANAGER
    base_dir = os.path.expanduser("~")  # Домашняя директория пользователя
    db_path = os.path.join(base_dir, "sound_synth.db")
    DB_MANAGER = DatabaseManager(db_path)
    print(f"[DEBUG] init_db() вызвана; DB_MANAGER = {DB_MANAGER}")
    print(f"[DEBUG] База данных инициализирована по пути: {db_path}")


def close_db():
    if DB_MANAGER:
        DB_MANAGER.close()
