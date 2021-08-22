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

logging.basicConfig(format="[%(asctime)s crawling@home] %(message)s", datefmt="%H:%M", level=logging.INFO)

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
        return ValueError(f"[crawling@home] {text} (status {status_code})")
    elif status_code == 403:
        return ZeroJobError(f"[crawling@home] {text} (status {status_code})")
    elif status_code == 404:
        return WorkerTimedOutError(f"[crawling@home] {text} (status {status_code})")
    else:
        return ServerError(f"[crawling@home] {text} (status {status_code})")

# The main 'hybrid' client instance.
class HybridClient:
    def __init__(self, url, nickname, _recycled=False) -> None:
        if _recycled:
            return
        
        if url[-1] != "/":
            url += "/"
        
        self.s = session()
        self.url = url
        self.type = "HYBRID"
        self.nickname = nickname

        print("connecting to crawling@home server...")
        payload = {"nickname": nickname, "type": "HYBRID"}
        r = _safe_request(self.s.get, self.url + "api/new", params=payload)

        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc

        print("connected to crawling@home server")
        data = r.json()
        self.token = data["token"]
        self.display_name = data["display_name"]
        self.upload_address = data["upload_address"]
        
        print(f"worker name: {self.display_name}")
        _builtin_print("\n\n")
        print(f"You can view this worker's progress at {self.url + 'worker/hybrid/' + self.display_name}\n")
    
    
    # Finds the amount of available jobs from the server, returning an integer.
    def updateUploadServer(self) -> None:
        r = _safe_request(self.s.get, self.url + "api/getUploadAddress", params={"type": "HYBRID"})

        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc

        self.upload_address = r.text
        
        print("updated upload server address")
    
    
    # Updates the upload server.
    def jobCount(self) -> int:
        r = _safe_request(self.s.get, self.url + "api/jobCount", params={"type": "HYBRID"})

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

        r = _safe_request(self.s.post, self.url + "api/newJob", json={"token": self.token, "type": "HYBRID"})

        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc
        else:
            data = r.json()
            self.shard = data["url"]
            self.start_id = np.int64(data["start_id"])
            self.end_id = np.int64(data["end_id"])
            self.shard_piece = data["shard"]
            
            print("recieved new job")
    
    
    # Downloads the current job's shard to the current directory (./shard.wat)
    def downloadShard(self, path="") -> None:
        print("downloading shard...")
        self.log("Downloading shard", noprint=True)

        with self.s.get(self.shard, stream=True) as r:
            r.raise_for_status()
            with open(path + "temp.gz", 'w+b') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
        
        with gzip.open(path + 'temp.gz', 'rb') as f_in:
            with open(path + 'shard.wat', 'w+b') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        sleep(1) # Causes errors otherwise?
        os.remove(path + "temp.gz")

        self.log("Downloaded shard", noprint=True)
        print("finished downloading shard")


    # Marks a job as completed/done.
    def completeJob(self, total_scraped : int) -> None:
        r = _safe_request(self.s.post, self.url + "api/markAsDone", json={"token": self.token, "count": total_scraped, "type": "HYBRID"})
        
        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc
        
        print("marked job as done")

    
    # Wrapper for `completeJob` (for older workers)
    def _markjobasdone(self, total_scraped : int) -> None:
        print("WARNING: avoid using `_markjobasdone(...)` and instead use `completeJob(...)` to mark a job as done.")
        self.completeJob(total_scraped)
        

    # Logs the string progress into the server.
    def log(self, progress : str, crashed=False, noprint=False) -> None:
        data = {"token": self.token, "progress": progress, "type": "HYBRID"}

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
        r = _safe_request(self.s.post, self.url + "api/validateWorker", json={"token": self.token, "type": "HYBRID"})

        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc
        else:
            return ("True" in r.text)
    
    
    # Removes the node instance from the server, ending all current jobs.
    def bye(self) -> None:
        _safe_request(self.s.post, self.url + "api/bye", json={"token": self.token, "type": "HYBRID"})
        print("closed worker")

        
        
# The CPU client instance.
# Programatically similar to `HybridClient`, with different completion functions.
class CPUClient:
    def __init__(self, url, nickname, _recycled=False) -> None:
        if _recycled:
            return
        
        if url[-1] != "/":
            url += "/"
        
        self.s = session()
        self.url = url
        self.type = "CPU"
        self.nickname = nickname

        print("connecting to crawling@home server...")
        payload = {"nickname": nickname, "type": "CPU"}
        r = _safe_request(self.s.get, self.url + "api/new", params=payload)

        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc

        print("connected to crawling@home server")
        data = r.json()
        self.token = data["token"]
        self.display_name = data["display_name"]
        self.upload_address = data["upload_address"]
        
        print(f"worker name: {self.display_name}")
        _builtin_print("\n\n")
        print(f"You can view this worker's progress at {self.url + 'worker/cpu/' + self.display_name}\n")
        
    
    # Finds the amount of available jobs from the server, returning an integer.
    def updateUploadServer(self) -> None:
        r = _safe_request(self.s.get, self.url + "api/getUploadAddress", params={"type": "CPU"})

        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc

        self.upload_address = r.text
        
        print("updated upload server address")
    
    
    # Finds the amount of available jobs from the server, returning an integer.
    def jobCount(self) -> int:
        r = _safe_request(self.s.get, self.url + "api/jobCount", params={"type": "CPU"})

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

        r = _safe_request(self.s.post, self.url + "api/newJob", json={"token": self.token, "type": "CPU"})

        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc
        else:
            data = r.json()
            self.shard = data["url"]
            self.start_id = np.int64(data["start_id"])
            self.end_id = np.int64(data["end_id"])
            self.shard_piece = data["shard"]
            
            print("recieved new job")
    
    
    # Downloads the current job's shard to the current directory (./shard.wat)
    def downloadShard(self, path="") -> None:
        print("downloading shard...")
        self.log("Downloading shard", noprint=True)

        with self.s.get(self.shard, stream=True) as r:
            r.raise_for_status()
            with open(path + "temp.gz", 'w+b') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
            
        with gzip.open(path + 'temp.gz', 'rb') as f_in:
            with open(path + 'shard.wat', 'w+b') as f_out:
                shutil.copyfileobj(f_in, f_out)
            
        sleep(1) # Causes errors otherwise?
        os.remove(path + "temp.gz")

        self.log("Downloaded shard", noprint=True)
        print("finished downloading shard")
        
    
    # Uploads the image download URL for the GPU workers to use, marking the CPU job complete.
    def completeJob(self, image_download_url : str) -> None:
        r = _safe_request(self.s.post, self.url + "api/markAsDone", json={
            "token": self.token,
            "url": image_download_url,
            "type": "CPU"
        })
        
        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc
        
        print("marked job as done")
    
    
    # Logs the string progress into the server.
    def log(self, progress : str, crashed=False, noprint=False) -> None:
        data = {"token": self.token, "progress": progress, "type": "CPU"}

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
    
    
    # Recreates the client with the server, giving the client a new auth token, upload server and display name.
    def recreate(self) -> None:
        print("recreating client instance...")
        new = CPUClient(self.url, self.nickname)
        self.token = new.token
        self.display_name = new.display_name
        self.upload_address = new.upload_address
    
    
    # Returns True if the worker is still alive, otherwise returns False.
    def isAlive(self) -> bool:
        r = _safe_request(self.s.post, self.url + "api/validateWorker", json={"token": self.token, "type": "CPU"})

        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc
        else:
            return ("True" in r.text)
    
    
    # Removes the node instance from the server, ending all current jobs.
    def bye(self) -> None:
        _safe_request(self.s.post, self.url + "api/bye", json={"token": self.token, "type": "CPU"})
        print("closed worker")



# The GPU client instance.
class GPUClient:
    def __init__(self, url, nickname, _recycled=False) -> None:
        if _recycled:
            return
        
        if url[-1] != "/":
            url += "/"
        
        self.s = session()
        self.url = url
        self.type = "GPU"
        self.nickname = nickname

        print("connecting to crawling@home server...")
        payload = {"nickname": nickname, "type": "GPU"}
        r = _safe_request(self.s.get, self.url + "api/new", params=payload)

        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc

        print("connected to crawling@home server")
        data = r.json()
        self.token = data["token"]
        self.display_name = data["display_name"]
        self.upload_address = data["upload_address"]
        
        print(f"worker name: {self.display_name}")
        _builtin_print("\n\n")
        print(f"You can view this worker's progress at {self.url + 'worker/gpu/' + self.display_name}\n")
    
    
    # Finds the amount of available jobs from the server, returning an integer.
    def updateUploadServer(self) -> None:
        r = _safe_request(self.s.get, self.url + "api/getUploadAddress", params={"type": "GPU"})

        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc

        self.upload_address = r.text
        
        print("updated upload server address")
    
    
    # Finds the amount of available jobs from the server, returning an integer.
    def jobCount(self) -> int:
        r = _safe_request(self.s.get, self.url + "api/jobCount", params={"type": "GPU"})

        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc

        count = int(r.text)
        
        print(f"GPU jobs remaining: {count}")

        return count
    
    
    # Makes the node send a request to the server, asking for a new job.
    def newJob(self) -> None:
        print("looking for new job...")

        r = _safe_request(self.s.post, self.url + "api/newJob", json={"token": self.token, "type": "GPU"})

        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc
        else:
            data = r.json()
            self.shard = data["url"]
            self.start_id = np.int64(data["start_id"])
            self.end_id = np.int64(data["end_id"])
            self.shard_piece = data["shard"]
            
            print("recieved new job")
            
    
    # Flags a GPU job's URL as invalid to the server.
    def invalidURL(self) -> None:
        r = _safe_request(self.s.post, self.url + "api/gpuInvalidDownload", json={"token": self.token, "type": "GPU"})
        
        if r.status_code != 200:
            print("something went wrong when flagging a URL as invalid - not raising error.")
        else:
            print("successfully flagged url as invalid")
        raise InvalidURLError('[crawling@home] Invalid URL')
    
    
    # Downloads the CPU worker's processed images to the ./images/ (`path`) directory
    def downloadShard(self, path="") -> None:
        print("downloading shard...")
        self.log("Downloading shard", noprint=True)

        if self.shard.startswith('http'):
            with self.s.get(self.shard, stream=True) as r:
                r.raise_for_status()
                with open(path + "temp.gz", 'w+b') as f:
                    for chunk in r.iter_content(chunk_size=8192): 
                        f.write(chunk)
            
            with gzip.open(path + 'temp.gz', 'rb') as f_in:
                with open(path + 'shard.wat', 'w+b') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            sleep(1) # Causes errors otherwise?
            os.remove(path + "temp.gz")
        elif self.shard.startswith('rsync'):
            uid = self.shard.split('rsync', 1)[-1].strip()
            resp = 1
            for _ in range(5):
                resp = os.system(f'rsync -av archiveteam@5.9.55.230::gpujobs/{uid}.tar.gz {uid}.tar.gz')
                if resp == 5888:
                    print('[crawling@home] rsync job not found')
                    self.invalidURL()
                if resp == 0:
                    with tarfile.open(f"{uid}.tar.gz", "r:gz") as tar:
                        tar.extractall()
                    break
        else:
            self.invalidURL()

        self.log("Downloaded shard", noprint=True)
        print("finished downloading shard")
        
    
    # Uploads the image download URL for the GPU workers to use, marking the CPU job complete.
    def completeJob(self, total_scraped : int) -> None:
        r = _safe_request(self.s.post, self.url + "api/markAsDone", json={"token": self.token, "count": total_scraped, "type": "GPU"})
        
        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc
        
        print("marked job as done")
    
    
    # Logs the string progress into the server.
    def log(self, progress : str, crashed=False, noprint=False) -> None:
        data = {"token": self.token, "progress": progress, "type": "GPU"}

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
    
    
    # Recreates the client with the server, giving the client a new auth token, upload server and display name.
    def recreate(self) -> None:
        print("recreating client instance...")
        new = GPUClient(self.url, self.nickname)
        self.token = new.token
        self.display_name = new.display_name
        self.upload_address = new.upload_address
    
    
    # Returns True if the worker is still alive, otherwise returns False.
    def isAlive(self) -> bool:
        r = _safe_request(self.s.post, self.url + "api/validateWorker", json={"token": self.token, "type": "GPU"})

        exc = _handle_exceptions(r.status_code, r.text)
        if exc:
            self.log("Crashed", crashed=True)
            raise exc
        else:
            return ("True" in r.text)
    
    
    # Removes the node instance from the server, ending all current jobs.
    def bye(self) -> None:
        _safe_request(self.s.post, self.url + "api/bye", json={"token": self.token, "type": "GPU"})
        print("closed worker")


# Creates and returns a new client instance.
def init(url="http://crawlingathome.duckdns.org/", nickname="anonymous", type="Hybrid") -> Optional[Union[HybridClient, CPUClient, GPUClient]]:
    if isinstance(type, str):
        type = type.lower()[0]
        
    if type == "h" or type == HybridClient:
        return HybridClient(url, nickname)
    elif type == "c" or type == CPUClient:
        return CPUClient(url, nickname)
    elif type == "g" or type == GPUClient:
        return GPUClient(url, nickname)
    else:
        raise ValueError(f"[crawling@home] invalid worker `{type}`")
