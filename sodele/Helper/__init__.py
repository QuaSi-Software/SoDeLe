import json
import os

import numpy as np


class NpJsonEncoder(json.JSONEncoder):
    """Serializes numpy objects as json."""

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.floating):
            if np.isnan(obj):
                return None  # Serialized as JSON null.
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super().default(obj)


def isNumber(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def strToBool(data):
    """
    Converts a string to a boolean value

    :param data: The string to convert

    :return: The boolean value
    """
    data = str(data).lower()
    if data == "true":
        return True
    elif data == "false":
        return False
    else:
        raise ValueError("The value is not a boolean")


def runsInDocker():
    """
    A function to check if the application runs in a docker container

    :return: {bool} True if the application runs in a docker container
    """
    value = os.path.exists('/.dockerenv')
    return value


def getValueForKey(key, default=None):
    """
    Returns the value for a key from the environment.
    If the key is not set in the environment, the default value is returned.

    :param key: The key to get the value for
    :param default: The default value to return if the key is not set in the environment

    :return: The value for the key
    """
    environment_value = os.getenv(key)
    if environment_value:
        return environment_value
    return default
