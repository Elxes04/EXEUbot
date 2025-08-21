import os
import re
from telethon import events
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.tl.types import User
from translations import translations

async def copy_info(event, client):
    try:
        # Get username from command
        username = event.pattern_match.group(1)
        
        # Clean username (remove @ if present)
        username = username.replace("@", "")
        
        # Validate username
        if not username:
            await event.reply("Please provide a valid username")
            return
        
        # Get user entity
        try:
            user = await client.get_entity(f"@{username}")
        except Exception:
            await event.reply(translations['user_not_found'])
            return
        
        # Validate that we got a valid user
        if not user or not isinstance(user, User):
            await event.reply(translations['user_not_found'])
            return
        
        # Get full user info
        try:
            user_info = await client(GetFullUserRequest(user))
        except Exception as e:
            await event.reply(f"Error getting user info: {str(e)}")
            return

        # Extract user data
        first_name = user.first_name or ""
        last_name = user.last_name or ""
        bio = user_info.full_user.about or ""
        
        # Update profile
        try:
            await client(UpdateProfileRequest(
                first_name=first_name,
                last_name=last_name,
                about=bio,
            ))
        except Exception as e:
            await event.reply(f"Error updating profile: {str(e)}")
            return

        # Download and upload profile photo
        try:
            profile_photo = await client.download_profile_photo(user, file='profile_photo.jpg')
            
            if profile_photo and os.path.exists(profile_photo):
                await client(UploadProfilePhotoRequest(
                    file=await client.upload_file(profile_photo)
                ))
                os.remove(profile_photo)
        except Exception as e:
            # Photo copy failed, but profile info was updated
            await event.reply(f"Profile info copied successfully, but photo copy failed: {str(e)}")
            return
        
        await event.reply(translations['copy_successfully'])

    except Exception as e:
        await event.reply(translations['error_occurred'].format(error=str(e)))
        print(f"Error in copy_info: {str(e)}")

def register(client):
    @client.on(events.NewMessage(pattern=r'^\.copy\s+(\S+)$', outgoing=True))
    async def handler(event):
        await copy_info(event, client)