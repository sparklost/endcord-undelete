import logging
import os
import threading
import time

from endcord import formatter, peripherals

EXT_NAME = "Undelete"
EXT_VERSION = "0.1.0"
EXT_ENDCORD_VERSION = "1.5.0"
EXT_DESCRIPTION = "An extension that persistently stores deleted messages for specific channels/servers and shows them in the chat"
EXT_SOURCE = "https://github.com/sparklost/endcord-undelete"
logger = logging.getLogger(__name__)


class Extension:
    """Main extension class"""

    def __init__(self, app):
        if not app.config["keep_deleted"]:
            del type(self).on_message_event_is_irrelevant
            del type(self).on_message_event
            return

        self.app = app
        self.listen_channels = app.config.get("ext_undelete_listen_channel", [])
        self.listen_guilds = app.config.get("ext_undelete_listen_guilds", [])
        self.user_blacklist = app.config.get("ext_undelete_user_blacklist", [])
        self.history_window = max(app.config.get("ext_undelete_history_window", 50), 10)
        self.read_only = app.config.get("ext_undelete_read_only", False)
        self.keep_all = app.config.get("ext_undelete_keep_all", False)
        cleanup_interval = app.config.get("ext_undelete_cleanup_interval", 7)

        if self.read_only:
            del type(self).on_message_event_is_irrelevant
            del type(self).on_message_event

        try:
            if app.config.get("ext_undelete_db_postgresql_host", None):
                import database_postgres
                host = app.config.get("ext_undelete_db_postgresql_host")
                user = app.config.get("ext_undelete_db_postgresql_user", "user")
                password = app.config.get("ext_undelete_db_postgresql_password", "password")
                self.messages_db = database_postgres.ChannelStore(host, user, password, "deleted-store")
            else:
                import database_sqlite
                database_path = app.config.get("ext_undelete_db_dir_path")
                if not database_path:
                    database_path = f"{os.path.expanduser(peripherals.config_path)}/db/"
                database_path = os.path.expanduser(database_path)
                if not os.path.exists(database_path):
                    os.makedirs(database_path, exist_ok=True)
                database_path = os.path.join(database_path, "deleted-store.db")
                self.messages_db = database_sqlite.ChannelStore(database_path)
        except Exception as e:
            logger.error(f"Failed connecting to database: {e}")
            del type(self).on_message_event_is_irrelevant
            del type(self).on_message_event
            return

        self.shutdown_event = threading.Event()
        if not self.read_only:
            self.cleanup_thread = threading.Thread(target=self.cleanup, args=(cleanup_interval,), daemon=True)
            self.cleanup_thread.start()

        self.listen_cache = {}

        self.app.cache_deleted = self.cache_deleted
        self.app.restore_deleted = self.restore_deleted


    def on_message_event_is_irrelevant(self, message, optext):
        """Check if message is relevant or not"""
        if optext not in ("MESSAGE_CREATE", "MESSAGE_UPDATE", "MESSAGE_DELETE"):
            return False
        if message["channel_id"] not in self.listen_channels and message.get("guild_id") not in self.listen_guilds:
            return False
        return True


    def on_message_event(self, new_message):
        """Ran when message event is received"""
        data = new_message["d"]
        channel_id = data["channel_id"]
        if channel_id not in self.listen_channels and data.get("guild_id") not in self.listen_guilds:
            return
        if data.get("user_id") in self.user_blacklist:
            return

        if self.keep_all:
            if new_message["op"] == "MESSAGE_CREATE":
                try:
                    self.messages_db.add_message(channel_id, data)
                except Exception as e:
                    logger.error(f"Error adding message to database: {e}")
            else:
                return

        op = new_message["op"]
        if op == "MESSAGE_CREATE":
            if channel_id not in self.listen_cache:
                self.listen_cache[channel_id] = []
            self.listen_cache[channel_id].append(data)
            if len(self.listen_cache[channel_id]) > self.history_window:
                self.listen_cache[channel_id].pop(0)

        elif op == "MESSAGE_UPDATE":
            if channel_id not in self.listen_cache:
                return
            for message in reversed(self.listen_cache[channel_id]):
                if message["id"] == data["id"]:
                    message["content"] = data["content"]
                    message["edited"] = True
                    break

        if op == "MESSAGE_DELETE":
            if channel_id not in self.listen_cache:
                return
            for message in reversed(self.listen_cache[channel_id]):
                if message["id"] == data["id"]:
                    break
            else:
                return
            minimal_msg = {k: v for k, v in message.items() if k not in ("channel_id", "guild_id", "mentions", "mention_roles", "timestamp")}
            if "referenced_message" in minimal_msg:
                if minimal_msg["referenced_message"]:
                    minimal_msg["referenced_message"].pop("embeds", None)
                    minimal_msg["referenced_message"].pop("timestamp", None)
                else:
                    del minimal_msg["referenced_message"]
            try:
                self.messages_db.add_message(channel_id, minimal_msg)
            except Exception as e:
                logger.error(f"Error adding message to database: {e}")


    def cleanup(self, cleanup_interval):
        """Thread that that executes database cleanup every N days"""
        if not cleanup_interval:
            return
        interval_seconds = cleanup_interval * 24 * 60 * 60
        while not self.shutdown_event.is_set():
            try:
                min_message_id = (int(time.time() - interval_seconds) * 1000 - formatter.DISCORD_EPOCH_MS) << 22
                logger.info(f"Starting scheduled cleanup (interval: {cleanup_interval} days). Removing messages older than ID: {min_message_id}")
                try:
                    self.messages_db.clean_database(min_message_id)
                except Exception as e:
                    logger.error(f"Error cleaning the database: {e}")
            except Exception as e:
                logger.error(f"Error during database cleanup: {e}", exc_info=True)
            if self.shutdown_event.wait(timeout=interval_seconds):
                break


    def undelete(self, messages=None):
        """Fetch messages from db and add them to currently active chat"""
        channel_id = self.app.active_channel["channel_id"]
        guild_id = self.app.active_channel["channel_id"]
        start_id = self.app.messages[-1]["id"]
        if self.app.tui.get_chat_selected()[1] == 0 and self.app.get_chat_last_message_id() == self.app.last_message_id:
            end_id = str((int(time.time()) * 1000 - formatter.DISCORD_EPOCH_MS) << 22)
        else:
            end_id = self.app.messages[0]["id"]
        deleted_messages = self.messages_db.get_message_range(channel_id, start_id, end_id)
        if not deleted_messages or channel_id != guild_id:
            return messages

        # restore missing data in minified message
        for message in deleted_messages:
            if "channel_id" in message:
                continue
            message["channel_id"] = channel_id
            if guild_id:
                message["guild_id"] = guild_id
            message["mentions"] = []
            message["mention_roles"] = []
            message["timestamp"] = formatter.timestamp_from_snowflake(message["id"], format_string="%Y-%m-%dT%H:%M:%S.%f%z")
            if "referenced_message" in message:
                message["referenced_message"]["timestamp"] = formatter.timestamp_from_snowflake(
                    message["referenced_message"]["id"],
                    format_string="%Y-%m-%dT%H:%M:%S.%f%z",
                )
                message["referenced_message"]["embeds"] = []
            else:
                message["referenced_message"] = None
            message["deleted"] = True

        # update messages
        if messages:
            for message_c in deleted_messages:
                message_c_id = int(message_c["id"])
                if message_c_id < int(messages[-1]["id"]):
                    continue
                if message_c_id > int(messages[0]["id"]):
                    if int(messages[0]["id"]) >= int(self.app.last_message_id):
                        messages.insert(0, message_c)
                    continue
                for num, message in enumerate(messages):
                    try:
                        if int(message["id"]) > message_c_id > int(messages[num+1]["id"]):
                            messages.insert(num+1, message_c)
                            break
                    except IndexError:
                        break
            return messages

        # if no messages then this is update on self.app.messages
        for message_c in deleted_messages:
            message_c_id = int(message_c["id"])
            if message_c_id < int(self.app.messages[-1]["id"]):
                continue
            if message_c_id > int(self.app.messages[0]["id"]):
                if int(self.app.messages[0]["id"]) >= int(self.app.last_message_id):
                    self.app.messages.insert(0, message_c)
                continue
            for num, message in enumerate(self.app.messages):
                try:
                    if int(message["id"]) > message_c_id > int(self.app.messages[num+1]["id"]):
                        self.app.messages.insert(num+1, message_c)
                        break
                except IndexError:
                    break
        if self.app.emoji_as_text:
            for num, message in enumerate(self.app.messages):
                self.app.messages[num] = formatter.demojize_message(message)
        self.app.update_chat()



    def restore_deleted(self, messages):
        """Restore all cached deleted messages for this channels in the correct position"""
        channel_id = self.app.active_channel["channel_id"]

        # ADDED CODE
        if channel_id in self.listen_channels or self.app.active_channel["guild_id"] in self.listen_guilds:
            if self.read_only:
                threading.Thread(target=self.undelete, daemon=True).start()
                return messages
            return self.undelete(messages)
        # ADDED CODE END

        for channel in self.app.deleted_cache:
            if channel["channel_id"] ==channel_id:
                this_channel_cache = channel["messages"]
                break
        else:
            return messages
        for message_c in this_channel_cache:
            message_c_id = int(message_c["id"])
            # ids are discord snowflakes containing unix time so it can be used as message sent time
            if message_c_id < int(messages[-1]["id"]):
                # if message_c date is before last message date
                continue
            if message_c_id > int(messages[0]["id"]):
                # if message_c date is after first message date
                if int(messages[0]["id"]) >= int(self.app.last_message_id):
                    # if it is not scrolled up
                    messages.insert(0, message_c)
                continue
            for num, message in enumerate(messages):
                try:
                    if int(message["id"]) > message_c_id > int(messages[num+1]["id"]):
                        # if message_c date is between this and next message dates
                        messages.insert(num+1, message_c)
                        break
                except IndexError:
                    break
        return messages


    def cache_deleted(self):
        """Cache all deleted messages from current channel"""
        channel_id = self.app.active_channel["channel_id"]
        if not channel_id:
            return

        # ADDED CODE
        if channel_id in self.listen_channels or self.app.active_channel["guild_id"] in self.listen_guilds:
            return
        # ADDED CODE END

        for channel in self.app.deleted_cache:
            if channel["channel_id"] == channel_id:
                this_channel_cache = channel["messages"]
                break
        else:
            self.app.deleted_cache.append({
                "channel_id": channel_id,
                "messages": [],
            })
            this_channel_cache = self.app.deleted_cache[-1]["messages"]
        for message in self.app.messages:
            if message.get("deleted"):
                for message_c in this_channel_cache:
                    if message_c["id"] == message["id"]:
                        break
                else:
                    this_channel_cache.append(message)
                    if len(this_channel_cache) > self.app.limit_cache_deleted:
                        this_channel_cache.pop(0)
