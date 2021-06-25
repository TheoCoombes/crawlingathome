# Crawling@Home Client
A client library for Crawling@Home's effort to filter CommonCrawl with CLIP, building a large scale image-text dataset.
* Server Repo: [TheoCoombes/crawlingathome-server](https://github.com/TheoCoombes/crawlingathome-server)
* Live Dashboard: http://crawlingathome.duckdns.org/

## Prerequisites
* Python >= 3.7

## Installation
As this module will only be used for creating the dataset (short-term), it has not been added to `pip`. However, installing from source is fairly simple:
```
git clone https://github.com/TheoCoombes/crawlingathome
pip install -r crawlingathome/requirements.txt
```
Now, from the current directory, you can import the module:
```py
import crawlingathome as cah
```

## Example usage
```py
import crawlingathome as cah

client = cah.init(
    url="https://example.com",
    nickname="John Doe"
)

while client.jobCount() > 0:
    client.newJob()
    client.downloadShard()
    
    # Saved shard at ./shard.wat
    
    while processing_shard:
        # ... process data

        client.log("Completed x / y images") # Updates the client's progress to the server

    client.completeJob()

client.bye()
```

## Methods

### [crawlingathome.init(url="http://localhost", nickname=None) -> crawlingathome.core.Client](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L21)
Creates and returns a new node instance.
* `url`: the Crawling@Home server URL
* `nickname`: the user's nickname (for the leaderboard)

### [crawlingathome.core.Client.jobCount() -> int](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L63)
Finds the amount of available jobs from the server, returning an integer.

### [crawlingathome.core.Client.newJob()](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L81)
Makes the node send a request to the server, asking for a new job.

### [crawlingathome.core.Client.downloadShard()](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L102)
Downloads the current job's shard to the current directory (`./shard.wat`)

### [crawlingathome.core.Client.uploadPath(path : str)](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L124)
Uploads the files from `path` to the server, marking the job as complete. **[OBSOLETE, use _markjobasdone(...)]**
* `path` (required): the path to the data

### [crawlingathome.core.Client._markjobasdone(total_scraped : int)](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L156)
Marks the current job as done to the server, along with submitting the total amount of alt-text pairs scraped.
* `total_scraped` (required): the amount of alt-text pairs scraped for the current job

### [crawlingathome.core.Client.log(progress : str)](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L169)
Logs the string `progress` into the server.
* `progress` (required): The string detailing the progress, e.g. `"12 / 100 (12%)"`

### [crawlingathome.core.Client.bye()](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L183)
Removes the node instance from the server, ending all current jobs.

## Variables

### [crawlingathome.core.Client.shard](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L94)
The URL to the current shard.

### [crawlingathome.core.Client.start_id](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L95)
The starting ID. Type: `np.int64`.

### [crawlingathome.core.Client.end_id](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L96)
The ending ID - usually 1 million more than starting ID. Type: `np.int64`.

### [crawlingathome.core.Client.shard_piece](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L97)
The 'shard' of the chunk, either 0 (first 50%) or 1 (last 50%).
