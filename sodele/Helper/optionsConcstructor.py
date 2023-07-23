def getDefault(type, name, description, required=False, default=None):
    return {
        name: {
            "type": type,
            "default": default,
            "description": description,
            "_required": required,
        }
    }


def getBoolean(name, description, required=False, default=False):
    return getDefault("boolean", name, description, required, default)


def getInteger(name, description, required=False, default=0):
    return getDefault("integer", name, description, required, default)


def getFloat(name, description, required=False, default=0.0):
    return getDefault("float", name, description, required, default)


def getString(name, description, required=False, default=""):
    return getDefault("string", name, description, required, default)


def getList(params):
    result = []
    for param in params:
        result.append({
            param: {
                "type": "list",
                "required": True,
            }
        })
    return result
