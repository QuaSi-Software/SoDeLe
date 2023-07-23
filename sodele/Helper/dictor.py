def dictor(data, path, default=None):
    try:
        path = path.split(".")
        tmp = data
        for key in path:
            tmp = tmp[key]
            if isinstance(tmp, str):
                try:
                    tmp = float(tmp)
                except ValueError:
                    tmp = tmp
        return tmp
    except KeyError:
        return default
