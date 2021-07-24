import time
from typing import Any


def get_time() -> float:
    return time.time()


def get_value(src: dict, key: str, default_value: Any = None) -> Any:
    if key in src:
        return src[key]
    elif default_value is not None:
        return default_value
    else:
        raise Exception('key \'' + key + '\' is mandatory')
