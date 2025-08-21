import os
import re
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

async def get_user_id(client, user_input):
    """Helper function to get user ID from various input formats"""
    try:
        # If it's a numeric ID
        if user_input.isdigit():
            return int(user_input)
        
        # If it's a username (with or without @)
        if user_input.startswith('@'):
            user_input = user_input[1:]
        
        # Try to get entity
        user = await client.get_entity(f"@{user_input}")
        if user and isinstance(user, User):
            return user.id
        
        return None
    except Exception:
        return None

def register(client):
    if not whitelist_enabled:
        return

    db.initialize_database()

    @client.on(events.NewMessage(pattern=r'^\.addwl(?: |$)(.*)', outgoing=True))
    async def add_whitelist(event):
        try:
            user_input = event.pattern_match.group(1).strip()
            
            if not user_input:
                await event.reply("Please provide a username or user ID")
                return
            
            user_id = await get_user_id(client, user_input)
            
            if not user_id:
                await event.reply(translations['user_not_found'])
                return

            if db.is_whitelisted(user_id):
                await event.edit(translations['user_whitelisted'].format(user_id=user_id))
            else:
                db.add_to_whitelist(user_id)
                await event.reply(translations['user_added_whitelist'].format(user_id=user_id))
        except Exception as e:
            await event.reply(translations['error_occurred'].format(error=str(e)))
            print(f"Error in add_whitelist: {str(e)}")

    @client.on(events.NewMessage(pattern=r'^\.rmwl(?: |$)(.*)', outgoing=True))
    async def remove_whitelist(event):
        try:
            user_input = event.pattern_match.group(1).strip()
            
            if not user_input:
                await event.reply("Please provide a username or user ID")
                return
            
            user_id = await get_user_id(client, user_input)
            
            if not user_id:
                await event.reply(translations['user_not_found'])
                return

            if db.is_whitelisted(user_id):
                db.remove_from_whitelist(user_id)
                await event.reply(translations['user_removed_whitelist'].format(user_id=user_id))
            else:
                await event.edit(translations['user_not_in_whitelist'].format(user_id=user_id))
        except Exception as e:
            await event.reply(translations['error_occurred'].format(error=str(e)))
            print(f"Error in remove_whitelist: {str(e)}")

    @client.on(events.NewMessage(incoming=True))
    async def handle_message(event):
        if event.is_private:
            try:
                sender = await event.get_sender()
                if not sender or not isinstance(sender, User):
                    return
                
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
            except Exception as e:
                print(f"Error in handle_message: {str(e)}")
