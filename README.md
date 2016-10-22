# precache.py

## What does it do?
Assets such as iOS/tvOS/watchOS/Mac App Store apps/OS X Installers/Combo Updates are cached through the detected or provided Caching Server.
If an asset is not currently in cache, it is downloaded; if the asset is in the cache, then the asset is skipped.
A progress indicator provides feedback on how much of the download is left.

**Current macOS Installers (public releases)**
* Mountain Lion 10.8.5
* Mavericks 10.9.5
* Yosemite 10.10.5
* El Capitan 10.11.6
* Sierra 10.12.0

**Note** macOS Installers from the Mac App Store are _not_ scraped from an XML feed, instead they have to be updated each time a new release or dot release comes out.

**Combo software updates for:**
* Mac OS X Yosemite
* Mac OS X El Capitan
* macOS Sierra when released

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
2. Make sure `precache.py` is executable: `chmod +x precache.py`.
3. Copy to `/usr/local/bin`
4. Set ownership: `sudo chown root:wheel /usr/local/bin/precache.py`
5.`precache.py --help` for usage.


## How it works
1. The script will first attempt to use `AssetCacheLocatorUtil` (macOS 10.12 or newer) to force the local machine to find the Caching Server for its network.
2. The script then checks to see if the machine is a Caching Server, and if it is, uses the relevant URL and port.
3. If the machine isn't a Caching Server, then it checks to see if the machine knows where the Caching Server for its network is located, and if it finds this, uses the relevant URL and port.
4. If this fails, it falls back to `http://localhost:49672`.
* Alternatively, specify which Caching Server to use by using the flag `-cs http://cachingserver:port` - where `cachingserver:port` are the appropriate values (you can find your caching servers port by running: `sudo serveradmin fullstatus caching`).
5. Files are downloaded through the Caching Server; if the asset is already in the cache, it is skipped. Only IPSW files are kept (in `/tmp/precache`).
6. Logs are written out to `/tmp/precache.log`

## `.precache.py --help`
```
usage: precache.py [-h] [-cs http://cachingserver:port] [-l]
                   [-m model [model ...]] [-i model [model ...]] [--version]

optional arguments:
  -h, --help            show this help message and exit
  -cs, --caching-server http://cachingserver:port
                        Provide the cache server URL and port
  -l, --list            Lists models available for caching
  -m, --model model [model ...]
                        Provide model(s)/app(s), i.e iPhone8,2 Xcode
  -i, --ipsw model [model ...]
                        Download IPSW files for one or more models
  --version             Prints version information

Note: Model identifiers are currently case sensitive.
```

## Suggested Use
In some environments, it may be desirable to run this as a LaunchDaemon on a Caching server in order to keep particular assets available. To do this, you could use a basic LaunchDaemon that runs once a day.
The example below has the `precache.py` tool located in `/usr/local/bin` and is set to get the OTA updates for an iPhone8,2 and iPad6,7; it runs on a Wednesday at 19:00.

A copy of this plist is included in this repo, simply place it in `/Library/LaunchDaemons` and `precache.py` in `/usr/local/bin`.

Make sure the LaunchDaemon is `chown root:wheel && chmod 0644`, and that `/usr/local/bin/precache.py` is `chown root:wheel && chmod 0755`.

If you want to change the day/s when this runs, you can simply change the integer values for `Weekday` to any combination of days, such as `246`. This will run on Tuesday, Thursday, and Saturday.

To change the time, simply change the integer values for `Hour` and `Minute` - use 24hr time.

Further `StartCalendarInterval` reading: http://stackoverflow.com/questions/3570979/whats-the-difference-between-day-and-weekday-in-launchd-startcalendarinterv

To kickstart the LaunchDaemon, simply:<br />
`sudo launchctl load -w /Library/LaunchDaemons/com.github.krypted.precache.plist`

### com.github.krypted.precache.plist
```
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.github.krypted.precache</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python</string>
        <string>/usr/local/bin/precache.py</string>
        <string>-m</string>
        <string>iPhone8,2</string>
        <string>iPad6,7</string>
        <string>Sierra</string>
        <string>Pages</string>
        <string>OSXUpdCombo10.11.6Auto</string>
        <string>-i</string>
        <string>iPhone8,2</string>
    </array>
    <key>StartCalendarInterval</key>
    <!--  Weekdays are 1 - 5; Sunday is 0 and 7   -->
    <array>
        <dict>
            <key>Weekday</key>
            <integer>3</integer>
            <key>Hour</key>
            <integer>19</integer>
            <key>Minute</key>
            <integer>00</integer>
        </dict>

    </array>
</dict>
</plist>
```

### Outset
You could alternatively use outset with a script that calls `precache.py` with relevant flags.

Outset is available from https://github.com/chilcote/outset
