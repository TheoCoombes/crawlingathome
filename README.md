# Crawling@Home Client
[![Discord Chat](https://img.shields.io/discord/823813159592001537?color=5865F2&logo=discord&logoColor=white)](https://discord.gg/dall-e)

A client library for Crawling@Home's effort to filter CommonCrawl with CLIP, building a large scale image-text dataset.
* Server Repo: [TheoCoombes/crawlingathome-server](https://github.com/TheoCoombes/crawlingathome-server)
* Worker Repo: [ARKSeal/crawlingathome-worker](https://github.com/ARKSeal/crawlingathome-worker)
* Live Dashboard: http://crawlingathome.duckdns.org/

# Prerequisites
* Python >= 3.7

# Installation
As this module will only be used for creating the dataset (short-term), it has not been added to `pip`. However, installing from source is fairly simple:
```
git clone https://github.com/TheoCoombes/crawlingathome
pip install -r crawlingathome/requirements.txt
```
Now, from the current directory, you can import the module:
```py
import crawlingathome as cah
```

# Methods

## crawlingathome.init(url="http://crawlingathome.duckdns.org/", nickname=None, type="HYBRID") -> Client
Creates and returns a new client instance.
* `url`: the Crawling@Home server URL
* `nickname`: the user's nickname (for the leaderboard)
* `type`: the type of worker from "HYBRID", "CPU" & "GPU"
    - You can also use the classes instead of a string, e.g. `crawlingathome.core.CPUClient` instead of `"CPU"`

## crawlingathome.dump(client) -> dict
Dumps a client into a dictionary, so that it can be loaded externally. (see below)

## crawlingathome.load(**kwargs) -> Client
Loads an existing client using dumped data passed as kwargs, returning a client instance. (see above)

# HybridClient Reference
```py
import crawlingathome as cah

client = cah.init(
    url="https://example.com",
    nickname="TheoCoombes",
    type="HYBRID"
)

while client.jobCount() > 0 and client.isAlive():
    client.newJob()
    client.downloadShard()
    
    # Saved shard at ./shard.wat
    
    while processing_shard:
        # ... process data

        client.log("Completed x / y images") # Updates the client's progress to the server

    client.completeJob(num_pairs_found)

client.bye()
```


## HybridClient.jobCount() -> int
Finds the amount of available Hybrid/CPU jobs from the server, returning an integer.

## HybridClient.newJob()
Send a request to the server, requesting for a new job.

## HybridClient.downloadShard()
Downloads the current job's shard to the current directory (`./shard.wat`)

## HybridClient.completeJob(total_scraped: int)
Marks the current job as done to the server, along with submitting the total amount of alt-text pairs scraped. (`_markjobasdone()` will be removed in future clients, use this instead)
* `total_scraped` (required): the amount of alt-text pairs scraped for the current job

## HybridClient.log(progress: str)
Logs the string `progress` into the server.
* `progress` (required): The string detailing the progress, e.g. `"12 / 100 (12%)"`

## HybridClient.isAlive() -> bool
Returns `True` if this client is still connected to the server, otherwise returns `False`.

## HybridClient.dump()
Client-side wrapper for `crawlingathome.dump(client)`.

## HybridClient.bye()
Removes the node instance from the server, ending all current jobs.

## Client Variables

### HybridClient.shard
The URL to the current shard.

### HybridClient.start_id
The starting ID. Type: `np.int64`.

### HybridClient.end_id
The ending ID, 1 million more than starting ID. Type: `np.int64`.

### HybridClient.shard_piece
The 'shard' of the chunk, either 0 (first 50%) or 1 (last 50%).

# CPUClient Reference
The CPU client is programatically similar to `HybridClient`, with only a differing upload function:

## CPUClient.completeJob(download_url: str)
Marks the current job as done to the server and sends the download URL for GPU workers to pull the generated .tar file from.
* `download_url` (required): the URL to download the shards
    - As this is a string, this could theoretically be anything. For example an IP to directly pull from the worker or a Google Drive link etc.

# GPUClient Reference
Similarly to the CPU Client, the GPU client is programatically similar to `HybridClient`, instead with a differing `downloadShard()` function, `shard` variable and new `invalidURL` method:

## GPUClient.downloadShard(path="./images")
Extracts the .tar file recieved from CPU workers into the path `path`, creating the directory if neccesary.

## GPUClient.invalidURL()
Flags a GPU job's URL as invalid to the server, moving the job back into open jobs.

## GPUClient.shard
Instead of being a CommonCrawl URL before, this is the string the CPU client uploaded in `CPUClient.completeJob(...)`.

## GPUClient Note:
GPUClient jobs are dynamically created, meaning it needs CPU clients to generate jobs for it. Because of this, there may be periods of time when your worker(s) don't have any jobs to fufil. You can prepare for this by making use of the `GPUClient.jobCount()` function as well as using a try/except on the `newJob()` call.
* `GPUClient.newJob()` raises a `crawlingathome.errors.ZeroJobError` when there are no jobs to fufil.
