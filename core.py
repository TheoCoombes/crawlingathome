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
def init(url="http://crawlingathome.duckdns.org/", nickname=None, type="Hybrid"):
    t = type.lower()[0]
    if t == "h":
        return HybridClient(url, nickname)
    elif t == "c":
        return CPUClient(url, nickname)
    elif t == "g":
        return GPUClient(url, nickname)
    else:
        raise ValueError("[crawling@home] invalid worker `type`")


# The main 'hybrid' client instance.
class HybridClient:
    def __init__(self, url, nickname, _recycled=False):
        if _recycled:
            return
        
        if url[-1] != "/":
            url += "/"
        
        self.s = session()
        self.url = url

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
        
        print(f"[crawling@home] worker name: {self.display_name}")
        print(f"\n\nYou can view this worker's progress at {self.url + 'worker/' + self.display_name}\n")
    
    
    # Finds the amount of available jobs from the server, returning an integer.
    def jobCount(self):
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
    def newJob(self):
        print("[crawling@home] looking for new job...")

        r = self.s.post(self.url + "api/newJob", json={"token": self.token, "type": "HYBRID"})

        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")
        else:
            data = r.json()
            self.shard = data["url"]
            self.start_id = np.int64(data["start_id"])
            self.end_id = np.int64(data["end_id"])
            self.shard_piece = data["shard"]
            
            print("[crawling@home] recieved new job")
    
    
    # Downloads the current job's shard to the current directory (./shard.wat)
    def downloadShard(self):
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
    def completeJob(self, total_scraped : int):
        r = self.s.post(self.url + "api/markAsDone", json={"token": self.token, "count": total_scraped, "type": "HYBRID"})
        print("[crawling@home] marked job as done")
        
        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")

    
    # Wrapper for `completeJob` (for older workers)
    def _markjobasdone(self, total_scraped : int):
        print("[crawling@home] WARNING: avoid using `_markjobasdone(...)` and instead use `completeJob(...)` to mark a job as done.")
        self.completeJob(total_scraped)
        

    # Logs the string progress into the server.
    def log(self, progress : str, crashed=False, noprint=False):
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
    def dump(self):
        from .recycler import dump as _dump
        return _dump(self)
    
    
    # Returns True if the worker is still alive, otherwise returns False.
    def isAlive(self):
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
    def bye(self):
        self.s.post(self.url + "api/bye", json={"token": self.token, "type": "HYBRID"})
        print("[crawling@home] closed worker")

        
        
# The CPU client instance.
# Programatically similar to `HybridClient`, with different completion functions.
class CPUClient:
    def __init__(self, url, nickname):
        self.s = session()
        self.url = url

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
        print(f"\n\nYou can view this worker's progress at {self.url + 'worker/' + self.display_name}\n")
    
    
    # Finds the amount of available jobs from the server, returning an integer.
    def jobCount(self):
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
    def newJob(self):
        print("[crawling@home] looking for new job...")

        r = self.s.post(self.url + "api/newJob", json={"token": self.token, "type": "CPU"})

        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")
        else:
            data = r.json()
            self.shard = data["url"]
            self.start_id = np.int64(data["start_id"])
            self.end_id = np.int64(data["end_id"])
            self.shard_piece = data["shard"]
            
            print("[crawling@home] recieved new job")
    
    
    # Downloads the current job's shard to the current directory (./shard.wat)
    def downloadShard(self):
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
    def completeJob(self, image_download_url : str):
        r = self.s.post(self.url + "api/markAsDone", json={"token": self.token, "url": image_download_url, "type": "CPU"})
        print("[crawling@home] marked job as done")
        
        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")
    
    
    # Logs the string progress into the server.
    def log(self, progress : str, crashed=False, noprint=False):
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
    
    
    # Returns True if the worker is still alive, otherwise returns False.
    def isAlive(self):
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
    def bye(self):
        self.s.post(self.url + "api/bye", json={"token": self.token, "type": "CPU"})
        print("[crawling@home] closed worker")



# The GPU client instance.
class GPUClient:
    def __init__(self, url, nickname):
        if url[-1] != "/":
            url += "/"
        
        self.s = session()
        self.url = url

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
        
        print(f"[crawling@home] worker name: {self.display_name}")
        print(f"\n\nYou can view this worker's progress at {self.url + 'worker/' + self.display_name}\n")
    
    
    # Finds the amount of available jobs from the server, returning an integer.
    def jobCount(self):
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
    def newJob(self):
        print("[crawling@home] looking for new job...")

        r = self.s.post(self.url + "api/newJob", json={"token": self.token, "type": "GPU"})

        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")
        else:
            data = r.json()
            self.shard = data["url"]
            self.start_id = np.int64(data["start_id"])
            self.end_id = np.int64(data["end_id"])
            self.shard_piece = data["shard"]
            
            print("[crawling@home] recieved new job")
    
    
    # Downloads the CPU worker's processed images to a (new) ./images/ directory
    def downloadShard(self):
        print("[crawling@home] downloading uploaded data...")
        self.log("Fetching images", noprint=True)

        with self.s.get(self.shard, stream=True) as r:
            r.raise_for_status()
            with open("temp.tar", 'w+b') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
        
        try:
            os.mkdir("images")
        except:
            pass
        
        with tarfile.open('temp.tar', 'r') as tar:
            tar.extractall("./images")
        
        sleep(1) # Causes errors otherwise?
        os.remove("temp.tar")

        self.log("Downloaded images", noprint=True)
        print("[crawling@home] finished downloading data")
        
    
    # Uploads the image download URL for the GPU workers to use, marking the CPU job complete.
    def completeJob(self, total_scraped : int):
        r = self.s.post(self.url + "api/markAsDone", json={"token": self.token, "count": total_scraped, "type": "GPU"})
        print("[crawling@home] marked job as done")
        
        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise ServerError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}\n")
    
    
    # Logs the string progress into the server.
    def log(self, progress : str, crashed=False, noprint=False):
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
    
    
    # Returns True if the worker is still alive, otherwise returns False.
    def isAlive(self):
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
    def bye(self):
        self.s.post(self.url + "api/bye", json={"token": self.token, "type": "GPU"})
        print("[crawling@home] closed worker")
        
