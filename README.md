# endcord-undelete
An extension for [endcord](https://github.com/sparklost/endcord) discord TUI client, that persistently stores deleted messages for specific channels/servers and shows them in the chat.  
It can be used to create postgres database on the server using bot which will be logging deleted (or all) messages, then users can connect to that database over network, using this same extension and pull messages to show them in their endcord chat.

## Installing
See [official extensions documentation](https://github.com/sparklost/endcord/blob/main/docs/extensions.md#installing-extensions) for installing instructions.
Available options:
- Git clone into `Extensions` directory located in endcord config directory.
- Run `endcord -i https://github.com/sparklost/endcord-undelete`
- Or use endcord client-side command `install_extension sparklost/endcord-undelete`

## Configuration
All extension options are under `[main]` section in endcord config. This extension options are always prefixed with `ext_undelete_`.  
Note that many options can significantly impact RAM and CPU usage.

### Settings options
- `keep_deleted = True`  
    This is endcord builtin option. Disabling it will also disable this extension.
- `ext_undelete_listen_channel = []`  
    List of channel IDs where to monitor messages. IDs must be strings (`"12345"`).
- `ext_undelete_listen_guilds = []`  
    List of server IDs where to monitor messages. IDs must be strings (`"12345"`). Overrides `ext_undelete_listen_channel` if channels are from same server.
- `ext_undelete_user_blacklist = []`  
    List of user IDs to ignore messages from.
- `ext_undelete_history_window = 50`  
    Number of messages kept in cache for each channel, if message that is not in this cache is deleted it wont be stored in database.
- `ext_undelete_read_only = False`  
    Don't store deleted messages to database but only read from it. Useful when bot is logging messages on server, and user is remotely accessing the database.
- `ext_undelete_cleanup_interval = 7`  
    Delete messages from database older than this days. Set to 0 to keep forever.
- `ext_undelete_keep_all = False`  
    If True, will store all received messages, not only deleted.
- `ext_endcord_undelete_db_postgresql_host = None`  
    If this is set, then postgres database is used. Then `ext_endcord_undelete_db_dir_path` and `ext_undelete_history_window` have no effects.  
    This will increase database size but will fix the issue with `ext_undelete_history_window` option.
- `ext_endcord_undelete_db_postgresql_user = "user"`  
- `ext_endcord_undelete_db_postgresql_password = "password"`  
- `ext_endcord_undelete_db_dir_path = None`  
    Path where to store sqlite database. Leave None to store it in endcord config dir.


## Disclaimer
> [!WARNING]
> Using third-party client is against Discord's Terms of Service and may cause your account to be banned!  
> **Use endcord and/or this extension at your own risk!**  
> If this extension is modified, it may be used for harmful or unintended purposes.  
> **The developer is not responsible for any misuse or for actions taken by users.**  
