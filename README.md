# precache.py

## What does it do?
Assets such as iOS/tvOS/watchOS/Mac App Store apps/OS X Installers/Combo Updates are cached through the detected or provided Caching Server.
If an asset is not currently in cache, it is downloaded; if the asset is in the cache, then the asset is skipped.
A progress indicator provides feedback on how much of the download is left.

**Current macOS Installers (public releases)**
* El Capitan 10.11.6
* Sierra 10.12.1

**Note** macOS Installers from the Mac App Store are _not_ scraped from an XML feed, instead they have to be updated each time a new release or dot release comes out.

**Combo software updates for:**
* Mac OS X El Capitan
* macOS Sierra (when/as released)

**Current Mac App Store apps (public releases)**
* Keynote
* Numbers
* Pages
* GarageBand
* iMovie
* macOS Server
* Xcode

## Usage
1. `git clone https://github.com/krypted/precache`
2. Make sure `precache.py` is executable: `chmod +x precache.py`
3. Copy `precache.py` to `/usr/local/bin`
4. Set ownership: `sudo chown root:wheel /usr/local/bin/precache.py`
5. See `precache.py --help` for usage

### Help
```
usage: precache.py [-h] [--cache-group <product name> [<product name> ...]]
                   [--cache-ipsw-group <product name> [<product name> ...]]
                   [-cs http://cacheserver:port] [--debug] [-n]
                   [--filter-group <product name> [<product name> ...]]
                   [-i model [model ...]] [-l] [-m model [model ...]]
                   [-o file path]

optional arguments:
  -h, --help            show this help message and exit
  --cache-group <product name> [<product name> ...]
                        Cache assets based on group
  --cache-ipsw-group <product name> [<product name> ...]
                        Cache IPSW based on group
  -cs, --cache-server http://cacheserver:port
                        Specify the cache server to use.
  --debug               Debug mode - increased log verbosity.
  -n, --dry-run         Shows what would be cached.
  --filter-group <product name> [<product name> ...]
                        Filter based on group
  -i, --ipsw model [model ...]
                        Cache IPSW for provided model/s.
  -l, --list            Lists all assets available for caching.
  -m, --model model [model ...]
                        Provide model(s)/app(s), i.e iPhone8,2 Xcode.
  -o, --output file path
                        Path to save IPSW files to.
```

### Sample output
```
[user@valkyrie]: # precache.py --cache-group installer --cache-ipsw-group iPod -i iPhone8,2 -o ~/Desktop/ipsw/
Caching Server: http://192.168.1.16:49672
Processing feeds. This may take a few moments.
Skipped: ElCapitan (10.11.6) - in cache
Skipped: Sierra (10.12.1) - in cache
Caching: iPod5,1 (9.3.5) [100.00% of 1.50GB]
Caching: iPod7,1 (10.1) [100.00% of 2.03GB]
Skipped: iPhone8,2 (10.1) - in cache
```

## How it works
1. The script will first attempt to use `AssetCacheLocatorUtil` (macOS 10.12 or newer) to force the local machine to find the Caching Server for its network
2. The script then checks to see if the machine is a Caching Server, and if it is, uses the relevant URL and port
3. If the machine isn't a Caching Server, then it checks to see if the machine knows where the Caching Server for its network is located, and if it finds this, uses the relevant URL and port
4. If this fails, it falls back to `http://localhost:49672`
5. When initalised, a test confirms that the caching server can be accessed. If not, the script exits.
  * Alternatively, specify which Caching Server to use by using the flag `-cs http://cachingserver:port` - where `cachingserver:port` are the appropriate values
  * You can find your caching servers port by running: `sudo serveradmin fullstatus caching`
6. Files are downloaded through the Caching Server; if the asset is already in the cache, it is skipped. Only IPSW files are kept
  * IPSW files are saved in `/tmp/precache` by default. Use the `-o` or `--output` flag with a file path to save to a specific location
7. Logs are written out to `/tmp/precache.log`

## Suggested Use
In some environments, it may be desirable to run this as a LaunchDaemon on a Caching server in order to keep particular assets available. To do this, you could use a basic LaunchDaemon that runs once a day.
The example below has the `precache.py` tool located in `/usr/local/bin` and is set to get the OTA updates for an iPhone8,2 and iPad6,7; it runs on a Wednesday at 19:00.

A copy of this plist is included in this repo, simply place it in `/Library/LaunchDaemons` and `precache.py` in `/usr/local/bin`.

### Using the LaunchDaemon
1. Copy the LaunchDaemon to `/Library/LaunchDaemons`
2. Change the ownership: `chown root:wheel /Library/LaunchDaemons/com.github.krypted.precache.plist`
3. Change the permissions: `chmod 644 /Library/LaunchDaemons/com.github.krypted.precache.plist`
4. Modify the LaunchDaemon file to suit your needs
  * If you're not putting the `precache.py` script in `/usr/local/bin` make sure you adjust the path in the line `<string>/usr/local/bin/precache.py</string>`
5. Make sure the `precache.py` script is in the correct location and with the correct permissions
6. Load the LaunchDaemon: `sudo launchctl load -w /Library/LaunchDaemons/com.github.krypted.precache.plist`

If you want to change the day/s when this runs, you can simply change the integer values for `Weekday` to any combination of days, such as `246`. This will run on Tuesday, Thursday, and Saturday.

To change the time, simply change the integer values for `Hour` and `Minute` - use 24hr time.

Further `StartCalendarInterval` reading: http://stackoverflow.com/questions/3570979/whats-the-difference-between-day-and-weekday-in-launchd-startcalendarinterv

### Outset
You could alternatively use outset with a script that calls `precache.py` with relevant flags.

Outset is available from https://github.com/chilcote/outset
