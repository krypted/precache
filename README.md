# precache
This is a modified version of the precache.py available at https://github.com/krypted/precache

This version will cache:
* iOS
* tvOS
* watchOS
* IPSW's (defaults to storing them in /tmp/precache/ so you can move them to archive if required)

To use:
Modify line 404 to reflect your caching server address and port.

Make sure `precache.py` is executable: `chmod +x precache.py`

```
usage: precache.py [-h] [-l] [-m <model> [<model> ...]]
                   [-i <model> [<model> ...]]

optional arguments:
  -h, --help            show this help message and exit
  -l, --list            Lists models available for caching
  -m, --model <model> [<model> ...]
                        Provide one or model numbers, i.e iPhone8,2
  -i, --ipsw <model> [<model> ...]
                        Download IPSW files for one or more models
```

Note: Model identifiers are currently case sensitive.
