# Crawling@Home Client
A distributed compute module for DALLE-pytorch dataset creation.
* Server Repo: [TheoCoombes/crawlingathome-server](https://github.com/TheoCoombes/crawlingathome-server)

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

### [crawlingathome.init(url="http://localhost:8080", rsync_addr="host@0.0.0.0", rsync_dir="/path/to/data") -> crawlingathome.core.__node](https://github.com/TheoCoombes/clipdist/blob/main/core.py#L12)
Creates and returns a new node instance.
* `url`: the clipdist server URL
* `rsync_addr`: the IP/SSH address of the storage server.
* `rsync_dir`: the directory to store the data on the storage server.

### [crawlingathome.core.__node.jobCount() -> int](https://github.com/TheoCoombes/clipdist/blob/main/core.py#L39)
Finds the amount of available jobs from the server, returning an integer.

### [crawlingathome.core.__node.newJob()](https://github.com/TheoCoombes/clipdist/blob/main/core.py#L55)
Makes the node send a request to the server, asking for a new job.

### [crawlingathome.core.__node.downloadShard()](https://github.com/TheoCoombes/clipdist/blob/main/core.py#L74)
Downloads the current job's shard to the current directory (`./shard.wat`)

### [crawlingathome.core.__node.uploadData(path : str)](https://github.com/TheoCoombes/clipdist/blob/main/core.py#L96)
Uploads the files from `path` to the server, marking the job as complete.
* `path` (required): the path to the data

### [crawlingathome.core.__node.log(progress : str)](https://github.com/TheoCoombes/clipdist/blob/main/core.py#L120)
Logs the string `progress` into the server.
* `progress` (required): The string detailing the progress, e.g. `"12 / 100 (12%)"`

### [crawlingathome.core.__node.bye()](https://github.com/TheoCoombes/clipdist/blob/main/core.py#L134)
Removes the node instance from the server, ending all current jobs.

## Variables

### [crawlingathome.core.__node.shard](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L68)
The URL to the current shard.

### [crawlingathome.core.__node.start_id](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L69)
The starting ID. Type: `np.int64`.

### [crawlingathome.core.__node.end_id](https://github.com/TheoCoombes/crawlingathome/blob/main/core.py#L69)
The ending ID - usually 1 million more than starting ID. Type: `np.int64`.
