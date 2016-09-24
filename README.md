# precache
This is a modified version of the precache.py available at https://github.com/krypted/precache

This version will cache:
* iOS
* tvOS
* watchOS
* macOS Installers from the Mac App Store
* IPSW's (defaults to storing them in /tmp/precache/ so you can move them to archive if required)

**Note** macOS Installers from the Mac App Store are _not_ scraped from an XML feed, instead they have to be updated each time a new release or dot release comes out.

**Current macOS Installers (public releases)**
* Mountain Lion 10.8.5
* Mavericks 10.9.5
* Yosemite 10.10.5
* El Capitan 10.11.6
* Sierra 10.12.0

To use:
Make sure `precache.py` is executable: `chmod +x precache.py`

To get a list of supported hardware models and macOS installers: `./precache.py -l`

```
usage: precache.py [-h] [-cs <http://cachingserver:port>] [-l]
                   [-m <model> [<model> ...]]
                   [-os <macOS installer> [<macOS installer> ...]]
                   [-i <model> [<model> ...]]

optional arguments:
  -h, --help            show this help message and exit
  -cs, --caching-server <http://cachingserver:port>
                        Provide the cache server URL and port
  -l, --list            Lists models available for caching
  -m, --model <model> [<model> ...]
                        Provide one or more models, i.e iPhone8,2
  -os, --os-installer <macOS installer> [<macOS installer> ...]
                        Provide one or more macOS installers.
  -i, --ipsw <model> [<model> ...]
                        Download IPSW files for one or more models
```

Note: Model identifiers and macOS names re currently case sensitive.
