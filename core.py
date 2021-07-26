##############################
#    Crawling@Home Client    #
#   (c) Theo Coombes, 2021   #
# TheoCoombes/crawlingathome #
##############################

from requests import session
from time import sleep
import numpy as np
import tarfile
import shutil
import gzip
import os

from .errors import *


# Creates and returns a new node instance.
def init(url="http://crawlingathome.duckdns.org/", nickname="anonymous", type="Hybrid"):
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

        print("[crawling@home] connecting to crawling@home server...")
        payload = {"nickname": nickname, "type": "HYBRID"}
        r = self.s.get(self.url + "api/new", params=payload)

        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")

        print("[crawling@home] connected to crawling@home server")
        data = r.json()
        self.token = data["token"]
        self.display_name = data["display_name"]
        self.upload_address = data["upload_address"]
        
        print(f"[crawling@home] worker name: {self.display_name}")
        print(f"\n\nYou can view this worker's progress at {self.url + 'worker/hybrid/' + self.display_name}\n")
    
    
    # Finds the amount of available jobs from the server, returning an integer.
    def updateUploadServer(self) -> None:
        r = self.s.get(self.url + "api/getUploadAddress")

        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")

        self.upload_address = r.text
        
        print(f"[crawling@home] updated upload server address")
    
    
    # Updates the upload server.
    def jobCount(self) -> int:
        r = self.s.get(self.url + "api/jobCount", params={"type": "HYBRID"})

        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")

        count = int(r.text)
        
        print(f"[crawling@home] jobs remaining: {count}")

        return count

    
    # Makes the node send a request to the server, asking for a new job.
    def newJob(self) -> None:
        print("[crawling@home] looking for new job...")

        r = self.s.post(self.url + "api/newJob", json={"token": self.token, "type": "HYBRID"})

        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            
            if r.status_code == 503:
                raise ZeroJobError(f"{r.text}\n")
            
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")
        else:
            data = r.json()
            self.shard = data["url"]
            self.start_id = np.int64(data["start_id"])
            self.end_id = np.int64(data["end_id"])
            self.shard_piece = data["shard"]
            
            print("[crawling@home] recieved new job")
    
    
    # Downloads the current job's shard to the current directory (./shard.wat)
    def downloadShard(self) -> None:
        print("[crawling@home] downloading shard...")
        self.log("Downloading shard", noprint=True)

        with self.s.get(self.shard, stream=True) as r:
            r.raise_for_status()
            with open("temp.gz", 'w+b') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
        
        with gzip.open('temp.gz', 'rb') as f_in:
            with open('shard.wat', 'w+b') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        sleep(1) # Causes errors otherwise?
        os.remove("temp.gz")

        self.log("Downloaded shard", noprint=True)
        print("[crawling@home] finished downloading shard")


    # Marks a job as completed/done.
    def completeJob(self, total_scraped : int) -> None:
        r = self.s.post(self.url + "api/markAsDone", json={"token": self.token, "count": total_scraped, "type": "HYBRID"})
        print("[crawling@home] marked job as done")
        
        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")

    
    # Wrapper for `completeJob` (for older workers)
    def _markjobasdone(self, total_scraped : int) -> None:
        print("[crawling@home] WARNING: avoid using `_markjobasdone(...)` and instead use `completeJob(...)` to mark a job as done.")
        self.completeJob(total_scraped)
        

    # Logs the string progress into the server.
    def log(self, progress : str, crashed=False, noprint=False) -> None:
        data = {"token": self.token, "progress": progress, "type": "HYBRID"}

        r = self.s.post(self.url + "api/updateProgress", json=data)
        if not crashed and not noprint:
            print(f"[crawling@home] logged new progress data: {progress}")

        if r.status_code != 200 and not crashed:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")
    
    
    # Client wrapper for `recycler.dump`.
    def dump(self) -> dict:
        from .recycler import dump as _dump
        return _dump(self)
    
    
    def recreate(self) -> None:
        print("[crawling@home] recreating client instance...")
        new = HybridClient(self.url, self.nickname)
        self.token = new.token
        self.display_name = new.display_name
        self.upload_address = new.upload_address
    
    
    # Returns True if the worker is still alive, otherwise returns False.
    def isAlive(self) -> bool:
        r = self.s.post(self.url + "api/validateWorker", json={"token": self.token, "type": "HYBRID"})

        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")
        else:
            return ("True" in r.text)
    
    
    # Removes the node instance from the server, ending all current jobs.
    def bye(self) -> None:
        self.s.post(self.url + "api/bye", json={"token": self.token, "type": "HYBRID"})
        print("[crawling@home] closed worker")

        
        
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

        print("[crawling@home] connecting to crawling@home server...")
        payload = {"nickname": nickname, "type": "CPU"}
        r = self.s.get(self.url + "api/new", params=payload)

        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")

        print("[crawling@home] connected to crawling@home server")
        data = r.json()
        self.token = data["token"]
        self.display_name = data["display_name"]
        
        print(f"[crawling@home] worker name: {self.display_name}")
        print(f"\n\nYou can view this worker's progress at {self.url + 'worker/cpu/' + self.display_name}\n")
    
    
    # Finds the amount of available jobs from the server, returning an integer.
    def jobCount(self) -> int:
        r = self.s.get(self.url + "api/jobCount", params={"type": "CPU"})

        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")

        count = int(r.text)
        
        print(f"[crawling@home] jobs remaining: {count}")

        return count
    
    
    # Makes the node send a request to the server, asking for a new job.
    def newJob(self) -> None:
        print("[crawling@home] looking for new job...")

        r = self.s.post(self.url + "api/newJob", json={"token": self.token, "type": "CPU"})

        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            
            if r.status_code == 503:
                raise ZeroJobError(f"{r.text}\n")
            
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")
        else:
            data = r.json()
            self.shard = data["url"]
            self.start_id = np.int64(data["start_id"])
            self.end_id = np.int64(data["end_id"])
            self.shard_piece = data["shard"]
            
            print("[crawling@home] recieved new job")
    
    
    # Downloads the current job's shard to the current directory (./shard.wat)
    def downloadShard(self) -> None:
        print("[crawling@home] downloading shard...")
        self.log("Downloading shard", noprint=True)

        with self.s.get(self.shard, stream=True) as r:
            r.raise_for_status()
            with open("temp.gz", 'w+b') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
            
        with gzip.open('temp.gz', 'rb') as f_in:
            with open('shard.wat', 'w+b') as f_out:
                shutil.copyfileobj(f_in, f_out)
            
        sleep(1) # Causes errors otherwise?
        os.remove("temp.gz")

        self.log("Downloaded shard", noprint=True)
        print("[crawling@home] finished downloading shard")
        
    
    # Uploads the image download URL for the GPU workers to use, marking the CPU job complete.
    def completeJob(self, image_download_url : str) -> None:
        r = self.s.post(self.url + "api/markAsDone", json={
            "token": self.token,
            "url": image_download_url,
            "type": "CPU"
        })
        print("[crawling@home] marked job as done")
        
        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")
    
    
    # Logs the string progress into the server.
    def log(self, progress : str, crashed=False, noprint=False) -> None:
        data = {"token": self.token, "progress": progress, "type": "CPU"}

        r = self.s.post(self.url + "api/updateProgress", json=data)
        if not crashed and not noprint:
            print(f"[crawling@home] logged new progress data: {progress}")

        if r.status_code != 200 and not crashed:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")
    
    
    # Client wrapper for `recycler.dump`.
    def dump(self) -> dict:
        from .recycler import dump as _dump
        return _dump(self)
    
    
    # Recreates the client with the server, giving the client a new auth token, upload server and display name.
    def recreate(self) -> None:
        print("[crawling@home] recreating client instance...")
        new = CPUClient(self.url, self.nickname)
        self.token = new.token
        self.display_name = new.display_name
        self.upload_address = new.upload_address
    
    
    # Returns True if the worker is still alive, otherwise returns False.
    def isAlive(self) -> bool:
        r = self.s.post(self.url + "api/validateWorker", json={"token": self.token, "type": "CPU"})

        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")
        else:
            return ("True" in r.text)
    
    
    # Removes the node instance from the server, ending all current jobs.
    def bye(self) -> None:
        self.s.post(self.url + "api/bye", json={"token": self.token, "type": "CPU"})
        print("[crawling@home] closed worker")



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

        print("[crawling@home] connecting to crawling@home server...")
        payload = {"nickname": nickname, "type": "GPU"}
        r = self.s.get(self.url + "api/new", params=payload)

        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")

        print("[crawling@home] connected to crawling@home server")
        data = r.json()
        self.token = data["token"]
        self.display_name = data["display_name"]
        self.upload_address = data["upload_address"]
        
        print(f"[crawling@home] worker name: {self.display_name}")
        print(f"\n\nYou can view this worker's progress at {self.url + 'worker/gpu/' + self.display_name}\n")
    
    
    # Finds the amount of available jobs from the server, returning an integer.
    def updateUploadServer(self) -> None:
        r = self.s.get(self.url + "api/getUploadAddress")

        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")

        self.upload_address = r.text
        
        print(f"[crawling@home] updated upload server address")
    
    
    # Finds the amount of available jobs from the server, returning an integer.
    def jobCount(self) -> int:
        r = self.s.get(self.url + "api/jobCount", params={"type": "GPU"})

        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")

        count = int(r.text)
        
        print(f"[crawling@home] GPU jobs remaining: {count}")

        return count
    
    
    # Makes the node send a request to the server, asking for a new job.
    def newJob(self) -> None:
        print("[crawling@home] looking for new job...")

        r = self.s.post(self.url + "api/newJob", json={"token": self.token, "type": "GPU"})

        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            
            if r.status_code == 503:
                raise ZeroJobError(f"{r.text}\n")
                
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")
        else:
            data = r.json()
            self.shard = data["url"]
            self.start_id = np.int64(data["start_id"])
            self.end_id = np.int64(data["end_id"])
            self.shard_piece = data["shard"]
            
            print("[crawling@home] recieved new job")
            
    
    # Flags a GPU job's URL as invalid to the server.
    def invalidURL(self) -> None:
        r = self.s.post(self.url + "api/gpuInvalidDownload", json={"token": self.token, "type": "GPU"})
        
        if r.status_code != 200:
            print("[crawling@home] something went wrong when flagging a URL as invalid - not raising error.")
        else:
            print("[crawling@home] successfully flagged url as invalid")
        raise InvalidURLError('[crawling@home] Invalid URL')
    
    
    # Downloads the CPU worker's processed images to the ./images/ (`path`) directory
    def downloadShard(self) -> None:
        print("[crawling@home] downloading shard...")
        self.log("Downloading shard", noprint=True)

        if self.shard.startswith('http'):
            with self.s.get(self.shard, stream=True) as r:
                r.raise_for_status()
                with open("temp.gz", 'w+b') as f:
                    for chunk in r.iter_content(chunk_size=8192): 
                        f.write(chunk)
            
            with gzip.open('temp.gz', 'rb') as f_in:
                with open('shard.wat', 'w+b') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            sleep(1) # Causes errors otherwise?
            os.remove("temp.gz")
        elif self.shard.startswith('rsync'):
            uid = self.shard.split('rsync', 1)[-1].strip()
            resp = 1
            for _ in range(5):
                resp = os.system(f'rsync -rzh archiveteam@88.198.2.17::gpujobs/{uid}/* {uid}')
                if resp == 5888:
                    print('[crawling@home] rsync job not found')
                    self.invalidURL()
                if resp == 0:
                    break
        else:
            self.invalidURL()

        self.log("Downloaded shard", noprint=True)
        print("[crawling@home] finished downloading shard")
        
    
    # Uploads the image download URL for the GPU workers to use, marking the CPU job complete.
    def completeJob(self, total_scraped : int) -> None:
        r = self.s.post(self.url + "api/markAsDone", json={"token": self.token, "count": total_scraped, "type": "GPU"})
        print("[crawling@home] marked job as done")
        
        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")
    
    
    # Logs the string progress into the server.
    def log(self, progress : str, crashed=False, noprint=False) -> None:
        data = {"token": self.token, "progress": progress, "type": "GPU"}

        r = self.s.post(self.url + "api/updateProgress", json=data)
        if not crashed and not noprint:
            print(f"[crawling@home] logged new progress data: {progress}")

        if r.status_code != 200 and not crashed:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")
    
    
    # Client wrapper for `recycler.dump`.
    def dump(self) -> dict:
        from .recycler import dump as _dump
        return _dump(self)
    
    
    # Recreates the client with the server, giving the client a new auth token, upload server and display name.
    def recreate(self) -> None:
        print("[crawling@home] recreating client instance...")
        new = GPUClient(self.url, self.nickname)
        self.token = new.token
        self.display_name = new.display_name
        self.upload_address = new.upload_address
    
    
    # Returns True if the worker is still alive, otherwise returns False.
    def isAlive(self) -> bool:
        r = self.s.post(self.url + "api/validateWorker", json={"token": self.token, "type": "GPU"})

        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")
        else:
            return ("True" in r.text)
    
    
    # Removes the node instance from the server, ending all current jobs.
    def bye(self) -> None:
        self.s.post(self.url + "api/bye", json={"token": self.token, "type": "GPU"})
        print("[crawling@home] closed worker")
