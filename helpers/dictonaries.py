from copy import deepcopy

def extend(source, *args):
    result = deepcopy(source)
    for d in args:
        for k, v in d.items():
            if k in result:
                if isinstance(result[k], dict) and isinstance(v, dict):
                    result[k] = extend(result[k], v)
                elif isinstance(result[k], list) \
                    and isinstance(v, (list, tuple)):
                    result[k].extend(v)
                else:
                    result[k] = v
            else:
                result[k] = v
    return result
