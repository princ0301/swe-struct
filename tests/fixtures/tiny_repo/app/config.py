def parse_config(text):
    result = {}
    for line in text.splitlines():
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result

def load_config(path):
    with open(path) as handle:
        return parse_config(handle.read())