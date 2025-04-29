import os
import json
import queue
import logging

# Global log queue
log_queue = queue.Queue()

# Setup basic logging
LOG_FILENAME = "switchboard_log.txt"
logging.basicConfig(filename=LOG_FILENAME, level=logging.INFO, format="%(asctime)s - %(message)s")

def log_action(action):
    logging.info(action)
    log_queue.put(action)

# Settings persistence
SETTINGS_FILE = "settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)
