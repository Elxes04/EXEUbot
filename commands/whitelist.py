import os
import commands.database as db
import configparser
from translations import translations
from telethon import events
from telethon.tl.functions.contacts import BlockRequest
from telethon.tl.types import User


config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.ini')
config.read(config_path)


limit_warning = int(config.get('whitelist', 'message_limit', fallback=3))
whitelist_enabled = config.getboolean('whitelist', 'enabled', fallback=True)

def register(client):
    if not whitelist_enabled:
        return

    db.initialize_database()

    @client.on(events.NewMessage(pattern=r'^\.addwl(?: |$)(.*)', outgoing=True))
    async def add_whitelist(event):
        try:
            user_id = event.pattern_match.group(1)
            if user_id.isdigit():
                user_id = int(user_id)
            else:
                user = await client.get_entity(user_id)
                user_id = user.id

            if db.is_whitelisted(user_id):
                await event.edit(translations['user_whitelisted'].format(user_id=user_id))
            else:
                db.add_to_whitelist(user_id)
                await event.edit(translations['user_added_whitelist'].format(user_id=user_id))
        except Exception as e:
            await event.edit(translations['error_occurred'].format(error=str(e)))

    @client.on(events.NewMessage(pattern=r'^\.rmwl(?: |$)(.*)', outgoing=True))
    async def remove_whitelist(event):
        try:
            user_id = event.pattern_match.group(1)
            if user_id.isdigit():
                user_id = int(user_id)
            else:
                user = await client.get_entity(user_id)
                user_id = user.id

            if db.is_whitelisted(user_id):
                db.remove_from_whitelist(user_id)
                await event.edit(translations['user_removed_whitelist'].format(user_id=user_id))
            else:
                await event.edit(translations['user_not_in_whitelist'].format(user_id=user_id))
        except Exception as e:
            await event.edit(translations['error_occurred'].format(error=str(e)))

    @client.on(events.NewMessage(pattern=r'^[\./!]rmwlu$', outgoing=True)) # removes from the whitelist the message reciver 
    async def remove_whitelist_you(event):
        try:
            chat = await event.get_chat()
            
            if isinstance(chat, User):
                user_id = chat.id  

                if db.is_whitelisted(user_id):
                    db.remove_from_whitelist(user_id)
                    await event.edit(translations['user_removed_whitelist'].format(user_id=user_id))
                else:
                    await event.edit(translations['user_not_in_whitelist'].format(user_id=user_id))
            else:
                await event.edit(translations['dm_only_command'])
        except Exception as e:
            await event.edit(translations['error_occurred'].format(error=str(e)))
        
    @client.on(events.NewMessage(pattern=r'^[\./!]addwlu$', outgoing=True)) # adds to whitelist the message reciver 
    async def add_whitelist_you(event):
        try:
            chat = await event.get_chat()
            
            if isinstance(chat, User):
                user_id = chat.id  

                if db.is_whitelisted(user_id):
                    await event.edit(translations['user_whitelisted'].format(user_id=user_id))
                else:
                    db.add_to_whitelist(user_id)
                    await event.edit(translations['user_added_whitelist'].format(user_id=user_id))
            else:
                await event.edit(translations['dm_only_command'])
        except Exception as e:
            await event.edit(translations['error_occurred'].format(error=str(e)))

    @client.on(events.NewMessage(incoming=True))
    async def handle_message(event):
        if event.is_private:
            sender = await event.get_sender()
            user_id = sender.id

            if db.is_whitelisted(user_id):
                return  # Do nothing if the user is whitelisted

            warning_count = db.get_warning_count(user_id)

            if warning_count >= limit_warning - 1:
                await client(BlockRequest(user_id))
                db.reset_warning_count(user_id)
                await event.reply(translations['blocked_reported'])
            else:
                db.increment_warning_count(user_id)
                await event.reply(translations['warning_message'].format(current_warning=warning_count + 1, warning_count=limit_warning))
