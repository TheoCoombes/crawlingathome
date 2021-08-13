from requests import session
from .core import CPUClient

class TempCPUWorker:
    def __init__(self,
            url: str = "http://crawlingathome.duckdns.org/",
            nickname: str = "anonymous",
            password: str = "<admin password goes here>"):
        
        if url[-1] != "/":
            url += "/"
        
        self.s = session()
        self.url = url
        self.nickname = nickname
        self.password = password
        
        self.completed = 0
        
        self._c = CPUClient(self.url, self.nickname)
        self.log("Waiting for new job...")
        
    
    def log(self, msg: str):
        self._c.log(f"{msg} | Completed: {self.completed:,}", noprint=True)
    
    
    def newJob(self):
        while True:
            wat = self.s.get(self.url + "custom/getCPUWAT").text
            if not "http" in wat:
                print("[crawling@home] something went wrong when finding a job, breaking loop...")
                self.log("Crashed.")
                break
            
            # verify
            r = self.s.post(self.url + "custom/lookup-wat", json={
                "password": self.password,
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
                    self.log("Recieved new jobs.")
    
    
    def completeJob(self, urls: list):
        r = self.s.post(self.url + "custom/markasdone-cpu", json={
            "password": self.password,
            "urls": urls,
            "shards": [shard[0] for shard in self.shards],
            "nickname": self.nickname
        }).json()
        
        if r["status"] == "success":
            self.completed += 2
        
        self.log("Marked jobs as done.")
