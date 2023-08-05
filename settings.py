import os
import json


def get_settings():
    with open(f'{os.getcwd()}/settings.json', 'r') as read_settings:
        return json.load(read_settings)
