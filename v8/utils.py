import sys
import _v8

__all__ = ['is_py3k', 'convert']

is_py3k = sys.version_info[0] > 2

def convert(obj):

    if type(obj) == _v8.JSArray:
        return [convert(v) for v in obj]

    if type(obj) == _v8.JSObject:
        return dict([[str(k), convert(obj.__getattr__(str(k)))] for k in (obj.__dir__() if is_py3k else obj.__members__)])

    return obj
