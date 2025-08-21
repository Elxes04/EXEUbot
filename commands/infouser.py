import os
import re
from telethon import TelegramClient, events
from telethon.tl.types import User, Channel, Chat
from telethon.tl.functions.users import GetFullUserRequest
from translations import translations

async def userinfo(event):
    if event.is_private:  
        await event.reply(translations["command_in_groups_only"])
        return

    try:
        user = None
        
        # Check if it's a reply to a message
        if event.reply_to_msg_id:
            reply_message = await event.get_reply_message()
            if reply_message and reply_message.sender_id:
                user = await event.client.get_entity(reply_message.sender_id)
        
        # If not a reply, check for username mention or user ID in the message
        if not user:
            # Check for username mention
            username_match = re.search(r'@(\w+)', event.text)
            if username_match:
                username = username_match.group(1)
                try:
                    user = await event.client.get_entity(f"@{username}")
                except Exception:
                    await event.reply(translations["user_not_found"])
                    return
            else:
                # Check for user ID in the message
                user_id_match = re.search(r'(\d+)', event.text)
                if user_id_match:
                    try:
                        user_id = int(user_id_match.group(1))
                        user = await event.client.get_entity(user_id)
                    except (ValueError, Exception):
                        await event.reply(translations["user_not_found"])
                        return
                else:
                    await event.reply(translations["mention_or_reply_user"])
                    return

        # Validate that we got a valid user
        if not user or not isinstance(user, User):
            await event.reply(translations["user_not_found"])
            return

        # Download profile photo if available
        photo = None
        if user.photo:
            try:
                photo = await event.client.download_profile_photo(user, file='user_profile.jpg')
            except Exception:
                photo = None

        # Get datacenter info
        user_dc = user.dc_id if hasattr(user, 'dc_id') and user.dc_id else "N/D"
        
        # Try to get additional user info if possible
        try:
            full_user = await event.client(GetFullUserRequest(user))
            about = full_user.full_user.about or "N/A"
            common_chats_count = full_user.full_user.common_chats_count or 0
        except Exception:
            about = "N/A"
            common_chats_count = 0
        
        # Get account creation date if available
        try:
            if hasattr(user, 'date') and user.date:
                from datetime import datetime
                creation_date = user.date.strftime("%d/%m/%Y %H:%M")
            else:
                creation_date = "N/A"
        except Exception:
            creation_date = "N/A"

        # Build response message with better formatting
        first_name = user.first_name or "Unknown"
        last_name = user.last_name or ""
        username = user.username or "N/A"
        
        # Create compact response using translations
        response = translations["user_info_title"] + "\n\n"
        
        # Basic info
        response += translations["user_basic_info"].format(
            first_name=first_name,
            last_name=last_name,
            user_id=user.id,
            username=username,
            datacenter=user_dc
        ) + "\n\n"
        
        # Status info (compact)
        status_parts = []
        
        # User type
        if hasattr(user, 'bot') and user.bot:
            status_parts.append(translations["user_status_bot"])
        else:
            status_parts.append(translations["user_status_user"])
        
        # Verification
        if hasattr(user, 'verified') and user.verified:
            status_parts.append(translations["user_verified_yes"])
        else:
            status_parts.append(translations["user_verified_no"])
        
        # Premium
        if hasattr(user, 'premium') and user.premium:
            status_parts.append(translations["user_premium_yes"])
        else:
            status_parts.append(translations["user_premium_no"])
        
        # Scam/Fake
        if hasattr(user, 'scam') and user.scam:
            status_parts.append(translations["user_scam_yes"])
        elif hasattr(user, 'fake') and user.fake:
            status_parts.append(translations["user_fake_yes"])
        
        # Account status
        if hasattr(user, 'deleted') and user.deleted:
            status_parts.append(translations["user_deleted_yes"])
        else:
            status_parts.append(translations["user_deleted_no"])
        
        # Contact status
        if hasattr(user, 'contact') and user.contact:
            status_parts.append(translations["user_contact_yes"])
        if hasattr(user, 'mutual_contact') and user.mutual_contact:
            status_parts.append(translations["user_mutual_yes"])
        
        response += " | ".join(status_parts) + "\n\n"
        
        # Additional info (only if available)
        additional_info = []
        
        # Language
        if hasattr(user, 'lang_code') and user.lang_code:
            additional_info.append(translations["user_language"].format(lang=user.lang_code.upper()))
        
        # Phone
        if hasattr(user, 'phone') and user.phone:
            additional_info.append(translations["user_phone"].format(phone=user.phone))
        
        # Status
        if hasattr(user, 'status') and user.status:
            additional_info.append(translations["user_status_online"])
        else:
            additional_info.append(translations["user_status_offline"])
        
        # Bio
        if about != "N/A":
            bio_short = about[:50] + "..." if len(about) > 50 else about
            additional_info.append(translations["user_bio"].format(bio=bio_short))
        
        # Common chats
        if common_chats_count > 0:
            additional_info.append(translations["user_common_chats"].format(count=common_chats_count))
        
        # Creation date
        if creation_date != "N/A":
            additional_info.append(translations["user_created"].format(date=creation_date))
        
        if additional_info:
            response += " | ".join(additional_info) + "\n\n"
        
        response += translations["user_info_footer"]

        # Send response with or without photo
        if photo and os.path.exists(photo):
            await event.reply(response, file=photo)
            os.remove(photo)
        else:
            await event.reply(response)

    except Exception as e:
        await event.reply(f"An error occurred: {str(e)}")
        print(f"Error in userinfo: {str(e)}")

def register(client):
    @client.on(events.NewMessage(pattern=r'^\.infouser', outgoing=True))
    async def handler(event):
        await userinfo(event)
