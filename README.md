# Crawling@Home Client
A distributed compute module for DALLE-pytorch dataset creation.
* Server Repo: [TheoCoombes/crawlingathome-server](https://github.com/TheoCoombes/crawlingathome-server)
* Live Dashboard: http://crawlingathome.duckdns.org/

## Prerequisites
* Python >= 3.7
* rsync

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
    rsync_addr="host@127.0.0.1",
    rsync_dir="/dataset/chunks"
)

while client.jobCount() > 0:
    client.newJob()
    client.downloadShard()
    
    # Saved shard at ./shard.wat
    
    while processing_shard:
        # ... do stuff

        client.log("Completed x / y images") # Updates the client's progress to the server
    
    client.uploadData("path/to/images") # Uploads the data in the path and marks the job as complete

client.bye()
```

## Methods

### [crawlingathome.init(url="http://localhost", nickname=None) -> crawlingathome.core.__node](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L21)
Creates and returns a new node instance.
* `url`: the Crawling@Home server URL
* `nickname`: the user's nickname (for the leaderboard)

### [crawlingathome.core.__node.jobCount() -> int](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L61)
Finds the amount of available jobs from the server, returning an integer.

### [crawlingathome.core.__node.newJob()](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L79)
Makes the node send a request to the server, asking for a new job.

### [crawlingathome.core.__node.downloadShard()](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L100)
Downloads the current job's shard to the current directory (`./shard.wat`)

### [crawlingathome.core.__node.uploadPath(path : str)](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L122)
Uploads the files from `path` to the server, marking the job as complete. **[OBSOLETE, use _markjobasdone(...)]**
* `path` (required): the path to the data

### [crawlingathome.core.__node._markjobasdone(total_scraped : int)](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L154)
Marks the current job as done to the server, along with submitting the total amount of alt-text pairs scraped.
* `total_scraped` (required): the amount of alt-text pairs scraped for the current job

### [crawlingathome.core.__node.log(progress : str)](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L167)
Logs the string `progress` into the server.
* `progress` (required): The string detailing the progress, e.g. `"12 / 100 (12%)"`

### [crawlingathome.core.__node.bye()](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L181)
Removes the node instance from the server, ending all current jobs.

## Variables

### [crawlingathome.core.__node.shard](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L92)
The URL to the current shard.

### [crawlingathome.core.__node.start_id](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L93)
The starting ID. Type: `np.int64`.

### [crawlingathome.core.__node.end_id](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L94)
The ending ID - usually 1 million more than starting ID. Type: `np.int64`.

### [crawlingathome.core.__node.shard_piece](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L95)
The 'shard' of the chunk, either 0 (first 50%) or 1 (last 50%).
