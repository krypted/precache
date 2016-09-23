# precache
Used to cache available Apple updates into an OS X Server running the Caching Service. To use, run the script followed by the name of the model. For example, for an iPad 2,1, you would use the following syntax:

sudo python precache.py iPad2,1

To eliminate beta operating systems from your precache,use the --no-beta argument:

sudo python precache.py iPad2,1 --no-beta

Precache also now supports AppleTV, so to cache updates for an AppleTV, use the model, as follows:

sudo python precache.py AppleTV5,4

Also, if you have another port for server (differ from default http://localhost:57466) you need to run with sudo as "serveradmin fullstatus caching" only executes with elevated privileges. 

Note: Model identifiers are currently case sensitive.
