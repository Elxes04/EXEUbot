import re
from telethon import events
from telethon.tl.types import User
from translations import translations

async def send_dm(event, client):
    try:
        text = event.text.split(maxsplit=2)
        if len(text) < 3:
            await event.respond(translations['provide_username_dm'])
            return

        username = text[1].replace("@", "").strip()
        dm_message = text[2].strip()
        
        # Validate inputs
        if not username:
            await event.respond("Please provide a valid username")
            return
            
        if not dm_message:
            await event.respond("Please provide a message to send")
            return

        # Get user entity
        try:
            user = await client.get_entity(f"@{username}")
        except Exception:
            await event.respond(translations['user_not_found'])
            return
        
        # Validate that we got a valid user
        if not user or not isinstance(user, User):
            await event.respond(translations['user_not_found'])
            return

        # Send message
        try:
            await client.send_message(user, dm_message)  
            await event.respond(translations['message_sent'].format(username=username))
        except Exception as e:
            await event.respond(f"Error sending message: {str(e)}")
            
    except Exception as e:
        await event.respond(translations['error_occurred'].format(error=str(e)))
        print(f"Error in send_dm: {str(e)}")

def register(client):
    @client.on(events.NewMessage(pattern=r'^\.dm\s+\S+\s+.+$', outgoing=True))
    async def handler(event):
        await send_dm(event, client)