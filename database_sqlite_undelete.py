import json
import logging

import apsw

logger = logging.getLogger(__name__)


class ChannelStore:
    """Database for storing deleted messages"""

    def __init__(self, db_path="pairs.db"):
        self.db_path = db_path
        self.conn = apsw.Connection(self.db_path)
        self.cleanup_conn = apsw.Connection(self.db_path)
        self.init_db()
        self.run = True


    def init_db(self):
        """Initialize database"""
        cur = self.conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS deleted_messages (
                channel_id INTEGER,
                message_id TEXT,
                message_body TEXT,
                PRIMARY KEY (channel_id, message_id)
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_deleted_messages_id
            ON deleted_messages (message_id)
        """)
        logger.info("Connected to SQLite database successfully")


    def add_message(self, channel_id, message):
        """Add message to specified channel"""
        with self.conn:
            cur = self.conn.cursor()
            cur.execute(
                """
                INSERT INTO deleted_messages (channel_id, message_id, message_body)
                VALUES (?, ?, ?)
                ON CONFLICT(channel_id, message_id)
                DO UPDATE SET message_body = excluded.message_body
                """,
                (channel_id, message["id"], json.dumps(message)),
            )


    def get_message_range(self, channel_id, start_id, end_id):
        """Get messages within range for specified channel"""
        with self.conn:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT json_group_array(json(message_body))
                FROM deleted_messages
                WHERE channel_id = ? AND message_id BETWEEN ? AND ?
                """,
                (channel_id, start_id, end_id),
            )
            row = cur.fetchone()
            if row and row[0] and row[0] != "[]":
                return json.loads(row[0])
            return None


    def clean_database(self, min_message_id):
        """Delete messages with id smaller than given value"""
        with self.cleanup_conn:
            cur = self.cleanup_conn.cursor()
            cur.execute("DELETE FROM deleted_messages WHERE message_id < ?", (min_message_id,))
