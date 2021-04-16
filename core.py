from subprocess import run, PIPE
from time import sleep
from json import loads
import numpy as np
import grequests # For CommonCrawl notebook
import shutil
import gzip
import os

def get(*args, **kwargs):
    rs = (grequests.get(*args, **kwargs),)
    return grequests.map(rs)[0]

def post(*args, **kwargs):
    rs = (grequests.post(*args, **kwargs),)
    return grequests.map(rs)[0]

def get_stream(*args, **kwargs):
    rs = (grequests.get(*args, **kwargs),)
    return grequests.map(rs, stream=True)[0]

# Creates and returns a new node instance.
def init(url="http://localhost:8080", rsync_addr="user@0.0.0.0", rsync_dir="/path/to/data"):
    return __node(url=url, rsync_addr=rsync_addr, rsync_dir=rsync_dir)

# The main node instance.
class __node:
    def __init__(self, url, rsync_addr, rsync_dir):
        if url[-1] != "/":
            url += "/"
        self.url = url
        self.rsync_addr = rsync_addr
        self.rsync_dir = rsync_dir

        print("[crawling@home] connecting to crawling@home server...")
        r = get(self.url + "api/new")

        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise RuntimeError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}")

        print("[crawling@home] connected to crawling@home server")
        self.name = r.text
        print(f"[crawling@home] node name: {self.name}")
    
    # Finds the amount of available jobs from the server, returning an integer.
    def jobCount(self):
        r = get(self.url + "api/jobCount")

        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise RuntimeError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}")

        count = int(r.text)
        print(f"[crawling@home] jobs remaining: {count}")

        return count

    # Makes the node send a request to the server, asking for a new job.
    def newJob(self):
        print("[crawling@home] looking for new job...")

        r = post(self.url + "api/newJob", json={"name": self.name})

        if r.status_code != 200:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise RuntimeError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}")
        else:
            data = loads(r.text)
            self.shard = data["url"]
            self.start_id = np.int64(data["start_id"])
            self.end_id = np.int64(data["end_id"])
            print("[crawling@home] recieved new job")
    
    # Downloads the current job's shard to the current directory (./shard.wat)
    def downloadShard(self):
        print("[crawling@home] downloading shard...")
        self.log("Downloading shard")

        with get_stream(self.shard, stream=True) as r:
            r.raise_for_status()
            with open("temp.gz", 'w+b') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
        
        with gzip.open('temp.gz', 'rb') as f_in:
            with open('shard.wat', 'w+b') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        sleep(1) # Causes errors otherwise?
        os.remove("temp.gz")

        self.log("Downloaded shard")
        print("[crawling@home] finished downloading shard")
    

    # Uploads the files from path to the server, marking the job as complete.
    def uploadPath(self, path : str):
        print("[crawling@home] uploading...")
        self.log("Uploading shard")
        
        r = run([
            "rsync", "-a", "-P", path, (self.rsync_addr + ":" + self.rsync_dir)
        ], stderr=PIPE, universal_newlines=True)

        print("[crawling@home] finished uploading")

        if r.returncode != 0:
            self.log("Crashed", crashed=True)
            raise RuntimeError(f"[crawling@home] Something went wrong when uploading, returned code {r.returncode}:\n{r.stderr}")
        
        self.__markjobasdone()
        print("[crawling@home] uploaded shard")


    # Marks a job as completed/done. (do NOT use in scripts)
    def __markjobasdone(self):
        post(self.url + "api/markAsDone", json={"name": self.name})
        print("[crawling@home] marked job as done")

    # Logs the string progress into the server.
    def log(self, progress : str, crashed=False):
        data = {"name": self.name, "progress": progress}

        r = post(self.url + "api/updateProgress", json=data)
        print("[crawling@home] logged new progress data")

        if r.status_code != 200 and not crashed:
            try:
                self.log("Crashed", crashed=True)
            except:
                pass
            raise RuntimeError(f"[crawling@home] Something went wrong, http response code {r.status_code}\n{r.text}")
    
    # Removes the node instance from the server, ending all current jobs.
    def bye(self):
        post(self.url + "api/bye", json={"name": self.name})
        print("[crawling@home] ended run")
