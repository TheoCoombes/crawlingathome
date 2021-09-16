import numpy as np
from requests import session

from .core import CPUClient, GPUClient, HybridClient
from .temp import TempCPUWorker
from .errors import *


# Dump a client's attributes into a dictionary so that it can be used remotely.
def dump(c):
    try:
        return {
            "_type": c.type,
            "url": c.url,
            "token": c.token,
            "nickname": c.nickname,
            "shard": c.shard if hasattr(c, 'shard') else None,
            "start_id": str(c.start_id) if hasattr(c, 'start_id') else None,
            "end_id": str(c.end_id) if hasattr(c, 'end_id') else None,
            "shard_piece": c.shard_piece if hasattr(c, 'shard_piece') else None,
            "wat": c.wat if hasattr(c, 'wat') else None,
            "shards": c.shards if hasattr(c, 'shards') else None
        }
    except AttributeError as e:
        raise DumpError(f"[crawling@home] unable to dump client: {e}")

# Load an existing client using its attributes. It's best to load using an existing dumpClient(): `loadClient(**dump)`
def load(_type=None, url=None, token=None, nickname=None, shard=None,
              start_id=None, end_id=None, shard_piece=None, wat=None, shards=None):
    
    if _type == "HYBRID":
        c = HybridClient(*[None] * 2, _recycled=True)
    elif _type == "CPU":
        c = CPUClient(*[None] * 2, _recycled=True)
    elif _type == "GPU":
        c = GPUClient(*[None] * 2, _recycled=True)
    elif _type == "FULLWAT":
        c = TempCPUWorker(url, nickname, _recycled=True)
    else:
        raise ValueError(f"Invalid worker type: {_type}")
    
    c.s = session()
    c.type = _type
    c.url = url
    c.token = token
    c.nickname = nickname
    c.shard = shard
    c.start_id = start_id if isinstance(start_id, np.int64) else np.int64(start_id)
    c.end_id = end_id if isinstance(end_id, np.int64) else np.int64(end_id)
    c.shard_piece = shard_piece
    c.wat = wat
    c.shards = shards
    
    return c
