# precache.py

## What does it do?
This can be used to cache over the air updates for iOS, tvOS, and watchOS. It can also be used to download and cache the IPSW's released by Apple (stored in `/tmp/precache` for later retrieval). This can also cache the macOS Installers found in the Mac App Store.

If an asset is not currently in cache, it is downloaded; if the asset is in the cache, then the asset is skipped.
A progress indicator provides feedback on how much of the download is left.

Logs to `/tmp/precache.log`

**Current macOS Installers (public releases)**
* Mountain Lion 10.8.5
* Mavericks 10.9.5
* Yosemite 10.10.5
* El Capitan 10.11.6
* Sierra 10.12.0

**Note** macOS Installers from the Mac App Store are _not_ scraped from an XML feed, instead they have to be updated each time a new release or dot release comes out.

**Current Mac App Store apps (public releases)**
* Keynote
* Numbers
* Pages
* GarageBand
* iMovie
* macOS Server
* Xcode

## Usage
Before using, make sure `precache.py` is executable: `chmod +x precache.py`.

If this is used on the Caching server directly, you don't need to use `-cs http://cachingserver:port`.

If this is run on a Mac that is _not_ a Caching server, you will need to supply `-cs http://cachingserver:port` - where `cachingserver:port` are the appropriate values.
You can find your caching servers port by running: `sudo serveradmin fullstatus caching`


To get a list of supported hardware models and macOS installers: `./precache.py -l`

```
usage: precache.py [-h] [-cs http://cachingserver:port] [-l]
                   [-m model [model ...]]
                   [-os macOS release [macOS release ...]]
                   [-i model [model ...]]

optional arguments:
  -h, --help            show this help message and exit
  -cs, --caching-server http://cachingserver:port
                        Provide the cache server URL and port
  -l, --list            Lists models available for caching
  -m, --model model [model ...]
                        Provide model(s)/app(s), i.e iPhone8,2 Xcode
  -os, --os-installer macOS release [macOS release ...]
                        Provide one or more macOS releases, i.e Sierra
  -i, --ipsw model [model ...]
                        Download IPSW files for one or more models

Note: Model identifiers and macOS names are currently case sensitive.
```

## Suggested Use
In some environments, it may be desirable to run this as a LaunchDaemon on a Caching server in order to keep particular assets available. To do this, you could use a basic LaunchDaemon that runs once a day.
The example below has the `precache.py` tool located in `/usr/local/bin` and is set to get the OTA updates for an iPhone8,2 and iPad6,7; it runs on a Wednesday at 19:00.

I've included a copy of this plist in the repo, simply place it in `/Library/LaunchDaemons` and `precache.py` in `/usr/local/bin`.

Make sure the LaunchDaemon is `chown root:wheel && chmod 0644`, and that `/usr/local/bin/precache.py` is `chown root:wheel && chmod 0755`.

If you want to change the day/s when this runs, you can simply change the integer values for `Weekday` to any combination of days, such as `246`. This will run on Tuesday, Thursday, and Saturday.

To change the time, simply change the integer values for `Hour` and `Minute` - use 24hr time.

Further StartCalendarInterval reading: http://stackoverflow.com/questions/3570979/whats-the-difference-between-day-and-weekday-in-launchd-startcalendarinterv

To kickstart the LaunchDaemon, simply `sudo launchctl load -w /Library/LaunchDaemons/com.github.krypted.precache.plist`

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
You could alternatively use outset - https://github.com/chilcote/outset
