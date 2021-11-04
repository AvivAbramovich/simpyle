def json_extract(json_str: str, path: str, default=None):
    import json
    d = json.loads(json_str)
    keys = path.split('.')
    val = d.get(keys[0])
    for key in keys[1:]:
        if val:
            val = val[key]
        elif default is not None:
            return default
        else:
            raise KeyError()
    return val


def regex_contains(pattern: str, text: str):
    import re
    return bool(re.match(pattern, text or ''))



min = min
max = max
any = any
all = all
print = print