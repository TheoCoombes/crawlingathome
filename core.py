##############################
#    Crawling@Home Client    #
#   (c) Theo Coombes, 2021   #
# TheoCoombes/crawlingathome #
##############################

from requests import session, Response
from typing import Optional, Union
from time import sleep
import numpy as np
import logging
import tarfile
import shutil
import gzip
import os

from .errors import *

logging.basicConfig(format="[%(asctime)s captions@home] %(message)s", datefmt="%H:%M", level=logging.INFO)

_builtin_print = print

def print(message) -> None:
    logging.info(message)

def _safe_request(function, *args, **kwargs) -> Response:
    try:
        return function(*args, **kwargs)
    except Exception as e:
        print(f"retrying request after {e} error...")
        sleep(60)
        return _safe_request(function, *args, **kwargs)

def _handle_exceptions(status_code: int, text: str) -> Optional[Exception]:
    if status_code == 200:
        return None
    elif status_code == 400:
        return ValueError(f"[captions@home] {text} (status {status_code})")
    elif status_code == 403:
        return ZeroJobError(f"[captions@home] {text} (status {status_code})")
    elif status_code == 404:
        return WorkerTimedOutError(f"[captions@home] {text} (status {status_code})")
    else:
        return ServerError(f"[captions@home] {text} (status {status_code})")

# The main client instance.
class Client:
    def __init__(self, url, nickname, _recycled=False) -> None:
        if _recycled:
            return
        
        if url[-1] != "/":
            url += "/"
        
        self.s = session()
        self.url = url
        self.nickname = nickname

        print("connecting to BLIP@home server...")
        payload = {"nickname": nickname}
        r = _safe_request(self.s.get, self.url + "api/new", params=payload)

        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc

        print("connected to BLIP@home server")
        data = r.json()
        self.token = data["token"]
        self.display_name = data["display_name"]
        self.upload_address = data["upload_address"]
        
        print(f"worker name: {self.display_name}")
        _builtin_print("\n\n")
        print(f"You can view this worker's progress at {self.url + 'worker/' + self.display_name}\n")
    
    
    # Finds the amount of available jobs from the server, returning an integer.
    def updateUploadServer(self) -> None:
        r = _safe_request(self.s.get, self.url + "api/getUploadAddress")

        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc

        self.upload_address = r.text
        
        print("updated upload server address")
    
    
    # Updates the upload server.
    def jobCount(self) -> int:
        r = _safe_request(self.s.get, self.url + "api/jobCount")

        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc

        count = int(r.text)
        
        print(f"jobs remaining: {count}")

        return count

    
    # Makes the node send a request to the server, asking for a new job.
    def newJob(self) -> None:
        print("looking for new job...")

        r = _safe_request(self.s.post, self.url + "api/newJob", json={"token": self.token})

        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc
        else:
            data = r.json()
            self.tar_url = data["url"]
            self.shard = data["url"]
            
            print("recieved new job")


    # Marks a job as completed/done.
    def completeJob(self) -> None:
        r = _safe_request(self.s.post, self.url + "api/markAsDone", json={"token": self.token})
        
        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc
        
        print("marked job as done")

        
    # Logs the string progress into the server.
    def log(self, progress : str, crashed=False, noprint=False) -> None:
        data = {"token": self.token, "progress": progress}

        r = _safe_request(self.s.post, self.url + "api/updateProgress", json=data)

        exc = _handle_exceptions(r.status_code, r.text)
        if exc and not crashed:
            self.log("Crashed", crashed=True)
            raise exc
        
        if not crashed and not noprint:
            print(f"logged new progress data: {progress}")
    
    
    # Client wrapper for `recycler.dump`.
    def dump(self) -> dict:
        from .recycler import dump as _dump
        return _dump(self)
    
    
    def recreate(self) -> None:
        print("recreating client instance...")
        new = HybridClient(self.url, self.nickname)
        self.token = new.token
        self.display_name = new.display_name
        self.upload_address = new.upload_address
    
    
    # Returns True if the worker is still alive, otherwise returns False.
    def isAlive(self) -> bool:
        r = _safe_request(self.s.post, self.url + "api/validateWorker", json={"token": self.token})

        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc
        else:
            return ("True" in r.text)
    
    # Returns True if the worker has been flagged to be killed, otherwise returns False.
    def shouldDie(self) -> bool:
        r = _safe_request(self.s.post, self.url + "api/shouldKill", json={"token": self.token})

        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc
        else:
            return ("True" in r.text)
    
    
    # Removes the node instance from the server, ending all current jobs.
    def bye(self) -> None:
        _safe_request(self.s.post, self.url + "api/bye", json={"token": self.token})
        print("closed worker")


# Creates and returns a new client instance.
def init(url="http://crawlingathome.duckdns.org/", device_id="<machine>:<device>.<worker>") -> Client:     
    return Client(url, device_id)
