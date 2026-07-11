import json
import logging

import psycopg

logger = logging.getLogger(__name__)


class ChannelStore:
    """Database for storing deleted messages"""

    def __init__(self, host, user, password, dbname):
        with psycopg.connect(host=host, user=user, password=password, dbname="postgres", autocommit=True) as admin_conn:
            with admin_conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
                if cur.fetchone() is None:
                    cur.execute(f"CREATE DATABASE {dbname}")
                    logger.info(f"Created database: {dbname}")
        self.conn = psycopg.connect(host=host, user=user, password=password, dbname=dbname, autocommit=True)
        self.cleanup_conn = psycopg.connect(host=host, user=user, password=password, dbname=dbname, autocommit=True)
        self.init_db()
        self.run = True


    def init_db(self):
        """Initialize database"""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    channel_id BIGINT,
                    message_id TEXT,
                    message_body JSONB,
                    PRIMARY KEY (channel_id, message_id)
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_deleted_messages_id
                ON messages (message_id)
            """)
        logger.info("Postgresql database initialized successfully")


    def add_message(self, channel_id, message):
        """Add message to specified channel"""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO messages (channel_id, message_id, message_body)
                VALUES (%s, %s, %s)
                ON CONFLICT (channel_id, message_id)
                DO UPDATE SET message_body = EXCLUDED.message_body
                """,
                (channel_id, message["id"], json.dumps(message)),
            )


    def get_message_range(self, channel_id, start_id, end_id):
        """Get value for specified user"""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT jsonb_agg(message_body)
                FROM messages
                WHERE channel_id = %s AND message_id BETWEEN %s AND %s
                """,
                (channel_id, start_id, end_id),
            )
            row = cur.fetchone()
            return row[0] if row else None


    def clean_database(self, min_message_id):
        """Delete messages with id smaller than given value"""
        with self.cleanup_conn.cursor() as cur:
            cur.execute("DELETE FROM messages WHERE message_id < %s", (min_message_id,))
