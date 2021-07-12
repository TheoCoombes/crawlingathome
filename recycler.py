import numpy as np

from .core import HybridClient
from .errors import *

# Dump a client's attributes into a dictionary so that it can be used remotely.
def dump(c):
    try:
        return {
            "type": c.type,
            "url": c.url,
            "token": c.token,
            "shard": c.shard if hasattr(c, 'shard') else None,
            "start_id": str(c.start_id) if hasattr(c, 'start_id') else None,
            "end_id": str(c.end_id) if hasattr(c, 'end_id') else None,
            "shard_piece": c.shard_piece if hasattr(c, 'shard_piece') else None
        }
    except AttributeError as e:
        raise DumpError(f"[crawling@home] unable to dump client: {e}")

# Load an existing client using its attributes. It's best to load using an existing dumpClient(): `loadClient(**dump)`
def load(url=None, token=None, shard=None,
              start_id=None, end_id=None, 
              _type=None, shard_piece=None):
    
    if _type == "HYBRID":
        c = HybridClient(*[None] * 5, _recycled=True)
    elif _type == "CPU":
        c = CPUClient(*[None] * 5, _recycled=True)
    elif _type == "GPU":
        c = GPUClient(*[None] * 5, _recycled=True)
    else:
        raise ValueError(f"Invalid worker type: {_type}")
    c.type = _type
    c.url = url
    c.token = token
    c.shard = shard
    c.start_id = start_id if isinstance(start_id, np.int64) else np.int64(start_id)
    c.end_id = end_id if isinstance(end_id, np.int64) else np.int64(end_id)
    c.shard_piece = shard_piece
    return c
