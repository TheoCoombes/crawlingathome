from requests import session
import os, shutil, gzip
from time import sleep

from .errors import WorkerTimedOutError
from .core import CPUClient
from .core import print as cahprint


class TempCPUWorker:
    def __init__(self,
            url: str = "http://crawlingathome.duckdns.org/",
            nickname: str = "anonymous", _recycled: bool = False) -> None:
        
        if _recycled:
            return
        
        if url[-1] != "/":
            url += "/"
        
        self.s = session()
        self.url = url
        self.nickname = nickname
        
        self.completed = 0
        
        self._c = CPUClient(self.url, self.nickname)
        self.upload_address = self._c.upload_address
        
        self.log("Waiting for new job")
    
    def dump(self) -> dict:
        from .recycler import dump
        return dump(self)

    def isAlive(self) -> bool:
        return self._c.isAlive()
    
    def recreate(self) -> None:
        self._c.recreate()
        
        self.upload_address = self._c.upload_address
    
    def log(self, msg: str) -> None:
        try:
            self._c.log(msg, noprint=True)
        except WorkerTimedOutError:
            self._c = CPUClient(self.url, self.nickname)
            self.log(msg)
    
    
    def jobCount(self) -> int:
        return self._c.jobCount()
    
    
    def downloadWat(self, path="") -> None:
        cahprint("downloading shard...")
        self.log("Downloading WAT")

        with self.s.get(self.wat, stream=True) as r:
            r.raise_for_status()
            with open(path + "temp.gz", 'w+b') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
            
        with gzip.open(path + 'temp.gz', 'rb') as f_in:
            with open(path + 'shard.wat', 'w+b') as f_out:
                shutil.copyfileobj(f_in, f_out)
            
        sleep(1) # Causes errors otherwise?
        os.remove(path + "temp.gz")

        self.log("Downloaded WAT")
        cahprint("finished downloading shard")
    
    
    def updateUploadServer(self) -> None:
        try:
            self._c.updateUploadServer()
            self.upload_address = self._c.upload_address
        except WorkerTimedOutError:
            self._c = CPUClient(self.url, self.nickname)
            self.updateUploadServer()
    
    
    def newJob(self) -> None:
        while True:
            wat = self.s.get(self.url + "custom/get-cpu-wat").text
            if not "http" in wat:
                cahprint("something went wrong when finding a job, breaking loop...")
                self.log("Crashed")
                break
            
            # verify
            r = self.s.post(self.url + "custom/lookup-wat", json={
                "url": wat
            }).json()
            
            if r["status"] != "success":
                continue
            else:
                shards = r["shards"]
                if len(shards) < 2:
                    continue
                else:
                    self.shards = shards
                    self.wat = wat
                    self.log("Recieved new jobs")
                    break
    
    
    def completeJob(self, urls: dict) -> None:
        r = self.s.post(self.url + "custom/markasdone-cpu", json={
            "urls": urls,
            "shards": [shard[0] for shard in self.shards],
            "nickname": self.nickname,
            "token": self._c.token
        }).json()
        
        if r["status"] == "success":
            self.completed += r["completed"]
        
        self.shards = None
        self.wat = None
        
        self.log("Marked jobs as done")
