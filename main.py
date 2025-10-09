import configparser
import importlib
import os
import traceback
import asyncio
import signal
import logging
from translations import translations
from telethon import TelegramClient, events

def load_commands(client):
    commands_folder = os.path.join(os.path.dirname(__file__), 'commands')
    for filename in os.listdir(commands_folder):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = f'commands.{filename[:-3]}'
            module = importlib.import_module(module_name)
            if hasattr(module, 'register'):
                module.register(client)

def get_log_level(level_str: str):
    levels = {
        'info': logging.INFO,
        'warn': logging.WARN,
        'warning': logging.WARN,
        'debug': logging.DEBUG,
        'error': logging.ERROR,
    }
    return levels.get(level_str.lower(), logging.INFO)

async def main():
    # Read data from config.ini file
    config = configparser.ConfigParser()
    config.read('config.ini')
    api_id = config['telegram']['api_id']
    api_hash = config['telegram']['api_hash']
    backup_folder = config['var']['backup_dir']
    log_channel = config['var']['log_level']

    # Configure logging here (after reading config)
    logging.basicConfig(
        level=get_log_level(log_channel),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename="userbot.log",
        filemode="a"
    )

    client = TelegramClient('session_name', api_id, api_hash)

    try:
        await client.start()
        load_commands(client)
        logging.info(translations['userbot_started'])
        await client.run_until_disconnected()
    except asyncio.CancelledError:
        logging.warning(translations['userbot_disconnected_cancelled_error'])
    except Exception as e:
        logging.error("Unhandled exception", exc_info=True)
        logging.error(translations['error_occurred'].format(error=str(e)))

def handle_signal(signum, frame):
    logging.info(translations['abort_signal_received'])
    asyncio.get_event_loop().stop()

if __name__ == '__main__':
    signal.signal(signal.SIGINT, handle_signal)
    asyncio.run(main())
