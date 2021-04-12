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

client = cah.init(url="https://clip-sharding.theocoombes.repl.co/")

while client.jobCount() > 0:
    client.newJob()
    client.downloadShard()
    
    # Saved shard at ./shard.wat
    while processing_shard:
        # ... do stuff

        client.log("Completed 12 / 12345 images") # Updates the client's progress to the server
    
    client.uploadData("path/to/images")

client.bye()
```

## Reference

### [crawlingathome.init(url="http://localhost:8080") -> crawlingathome.core.__node](https://github.com/TheoCoombes/clipdist/blob/main/core.py#L10)
Creates and returns a new node instance.
* `url`: the clipdist server URL

### [crawlingathome.core.__node.jobCount() -> int](https://github.com/TheoCoombes/clipdist/blob/main/core.py#L34)
Finds the amount of available jobs from the server, returning an integer.

### [crawlingathome.core.__node.newJob()](https://github.com/TheoCoombes/clipdist/blob/main/core.py#L46)
Makes the node send a request to the server, asking for a new job.

### [crawlingathome.core.__node.downloadShard()](https://github.com/TheoCoombes/clipdist/blob/main/core.py#L58)
Downloads the current job's shard to the current directory (`./shard.wat`)

### [crawlingathome.core.__node.uploadData(path : str)](https://github.com/TheoCoombes/clipdist/blob/main/core.py#L77)
Uploads the files from `path` to the server, marking the job as complete.
* `path` (required): the path to the data

### [crawlingathome.core.__node.log(progress : str)](https://github.com/TheoCoombes/clipdist/blob/main/core.py#L104)
Logs the string `progress` into the server.
* `progress` (required): The string detailing the progress, e.g. `"12 / 100 (12%)"`

### [crawlingathome.core.__node.bye()](https://github.com/TheoCoombes/clipdist/blob/main/core.py#L114)
Removes the node instance from the server, ending all current jobs.
