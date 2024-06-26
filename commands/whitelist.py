from telethon import events
from telethon.tl.functions.contacts import BlockRequest
import commands.database as db
from translations import translations

def register(client):
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
                await event.reply(translations['user_added_whitelist'].format(user_id=user_id))
        except Exception as e:
            await event.reply(translations['error_occurred'].format(error=str(e)))

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
                await event.reply(translations['user_removed_whitelist'].format(user_id=user_id))
            else:
                await event.edit(translations['user_not_in_whitelist'].format(user_id=user_id))
        except Exception as e:
            await event.reply(translations['error_occurred'].format(error=str(e)))

    @client.on(events.NewMessage(incoming=True))
    async def handle_message(event):
        if event.is_private:
            sender = await event.get_sender()
            user_id = sender.id
            
            if db.is_whitelisted(user_id):
                return  # Do nothing if the user is whitelisted
            
            warning_count = db.get_warning_count(user_id)
            
            if warning_count >= 2:
                await client(BlockRequest(user_id))
                db.reset_warning_count(user_id)
                await event.reply(translations['blocked_reported'])
            else:
                db.increment_warning_count(user_id)
                await event.reply(translations['warning_message'].format(current_warning=warning_count + 1))
