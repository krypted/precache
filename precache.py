#!/usr/bin/python
"""
precache.py is a tool that can be used to cache OTA updates for iOS, tvOS, and
watchOS, as well as download and cache IPSW files released by Apple.
macOS Combo updates are also cached, and the iLife, iWork, Xcode, Server apps
from the Mac App Store can also be cached.
macOS Installers are alo cacheable.

For more information: https://github.com/krypted/precache
For usage: ./precache.py --help
Note: Model identifiers are currently case sensitive.
"""

import argparse
import collections
import errno
import logging
import os
import plistlib
import re
import subprocess
import urllib2

from distutils.version import LooseVersion
from sys import argv
from sys import exit
from sys import stdout
from time import sleep
from urlparse import urlparse


class PreCache(object):
    def __init__(self, cache_server=None, log_level='info'):
        """ Initialise the object with some basic configurations
            When initialising, detect if the script is running on the cache
            server, if it isn't, then use values provided by arguments when the
            object is initialised.
            Can also override by providing those arguments."""
        self.version = '1.0.9'
        self.git_repo = 'https://github.com/krypted/precache'

        # Logging class
        class Logger():
            def __init__(self, log_level='info', log_path='/tmp/precache.log'):
                self.log_level = log_level
                self.logger = logging.getLogger('precache')

                # Handle log levels
                if 'info' in self.log_level:
                    self.logger.setLevel(logging.INFO)

                if 'debug' in self.log_level:
                    self.logger.setLevel(logging.DEBUG)

                self.fh = logging.FileHandler(log_path)
                self.formatter = logging.Formatter(
                    '%(asctime)s %(levelname)s - %(message)s'
                )

                self.fh.setFormatter(self.formatter)

                self.logger.addHandler(self.fh)

            # Normal log, and debug log levels
            def log(self, log_message):
                self.logger.info(log_message)

            def debug(self, log_message):
                self.logger.debug(log_message)

            def critical(self, log_message):
                self.logger.critical(log_message)

        # Configuration of precache
        l = Logger(log_level='info', log_path='/tmp/precache.log')
        self.log = l.log
        self.debug = l.debug
        self.critical = l.critical

        # URL Feeds for iOS/tvOS/watchOS
        self.base_feed_url = 'http://mesu.apple.com/assets'
        self.mobile_asset_path = 'com_apple_MobileAsset_SoftwareUpdate'
        self.xml_url = 'com_apple_MobileAsset_SoftwareUpdate.xml'

        self.osx_update_feed = (
            """https://swscan.apple.com/content/catalogs/"""
            """others/index-10.12-10.11-10.10-10.9-"""
            """mountainlion-lion-snowleopard-leopard.merged-1.sucatalog"""
        )

        self.update_feeds = {
            'watch': '%s/watch/%s/%s' % (self.base_feed_url,
                                         self.mobile_asset_path,
                                         self.xml_url),
            'tv': '%s/tv/%s/%s' % (self.base_feed_url,
                                   self.mobile_asset_path,
                                   self.xml_url),
            'ios': '%s/%s/%s' % (self.base_feed_url,
                                 self.mobile_asset_path,
                                 self.xml_url),
        }

        # Assets from Mac App Store. These are likely to change
        # with each macOS release
        self.mas_assets = {
            'MountainLion': {'version': '10.8.5',
                             'url': ['http://osxapps.itunes.apple.com/',
                                     'apple-assets-us-std-000001/',
                                     'Purple69/v4/5f/05/f7/',
                                     '5f05f76f-e0f8-62ef-5510-86cd3aed985d/',
                                     'encrypted3324837209255448993.pkg']},
            'Mavericks': {'version': '10.9.5',
                          'url': ['http://osxapps.itunes.apple.com/',
                                  'apple-assets-us-std-000001/',
                                  'Purple49/v4/a5/ef/b4/',
                                  'a5efb468-7f48-1395-d8e4-2194ba4d688a/',
                                  'encrypted5063122388219779779.pkg']},
            'Yosemite': {'version': '10.10.5',
                         'url': ['http://osxapps.itunes.apple.com/',
                                 'apple-assets-us-std-000001/',
                                 'Purple69/v4/61/cb/04/',
                                 '61cb0419-ba73-70c1-02ce-b1cee2f2269c/',
                                 'encrypted8769637421434146660.pkg']},
            'ElCapitan': {'version': '10.11.6',
                          'url': ['http://osxapps.itunes.apple.com/',
                                  'apple-assets-us-std-000001/',
                                  'Purple20/v4/dc/94/05/',
                                  'dc940501-f06f-2a91-555e-3dc272653af5/',
                                  'izt4803713449411067066.pkg']},
            'Sierra': {'version': '10.12.0',
                       'url': ['http://osxapps.itunes.apple.com/',
                               'apple-assets-us-std-000001/',
                               'Purple62/v4/af/5f/9d/',
                               'af5f9d8e-cf9c-8147-c51c-c3c1fececb99/',
                               'jze1425880974225146329.pkg']},
            'GarageBand': {'version': '10.1.2',
                           'url': ['http://osxapps.itunes.apple.com/',
                                   'apple-assets-us-std-000001/',
                                   'Purple30/v4/19/78/8b/',
                                   '19788bde-3172-3b98-8300-b8c4a9458bae/',
                                   'iat2506504784673372233.pkg']},
            'iMovie': {'version': '10.1.2',
                       'url': ['http://osxapps.itunes.apple.com/',
                               'apple-assets-us-std-000001/',
                               'Purple20/v4/80/6d/9b/',
                               '806d9b4e-776c-baae-574c-ed8afbc70acb/',
                               'gyj6237528809531298180.pkg']},
            'Keynote': {'version': '7.0',
                        'url': ['http://osxapps.itunes.apple.com/',
                                'apple-assets-us-std-000001/',
                                'Purple71/v4/a6/96/42/',
                                'a696423f-181c-fc2b-b572-3d3697146d47/',
                                'hlz1727390940373748952.pkg']},
            'Numbers': {'version': '4.0',
                        'url': ['http://osxapps.itunes.apple.com/',
                                'apple-assets-us-std-000001/',
                                'Purple71/v4/69/02/32/',
                                '69023287-bd7a-ef14-0424-234d8fc589e4/',
                                'mto6541029270492763328.pkg']},
            'Pages': {'version': '6.0',
                      'url': ['http://osxapps.itunes.apple.com/',
                              'apple-assets-us-std-000001/',
                              'Purple62/v4/8a/ee/6e/',
                              '8aee6e8b-e8cb-2434-b050-31dbbcc01974/',
                              'daf974703926683564923.pkg']},
            'Xcode': {'version': '8.0',
                      'url': ['http://osxapps.itunes.apple.com/',
                              'apple-assets-us-std-000001/',
                              'Purple62/v4/ed/3d/8e/',
                              'ed3d8e87-09da-2272-fc3a-b1678d8067a0/',
                              'iyp5743666419479406275.pkg']},
            'macOSServer': {'version': '5.2',
                            'url': ['http://osxapps.itunes.apple.com/',
                                    'apple-assets-us-std-000001/',
                                    'Purple62/v4/44/71/01/',
                                    '44710118-b2c9-1e31-73f6-fa7a0a26e594/',
                                    'wjs7031774084062486733.pkg']}
        }

        # Caching Server configuration
        self.cache_config_path = '/Library/Server/Caching/Config/Config.plist'

        # Check if the machine is running Caching Server and configure port
        if not cache_server:
            self.find_cache_server()

        if cache_server:
            self.cache_server = cache_server

        self.exclude_beta = True
        if self.exclude_beta:
            self.log('Ignoring beta releases')

        if not self.exclude_beta:
            self.log('Includng beta releases')

        # Assets master list - where all found items get stored for download
        self.assets_master = []

        # Named tuple for asset creation to drop into self.assets_master
        self.Asset = collections.namedtuple('Asset', ['model',
                                                      'download_url',
                                                      'os_version'])

    def version_info(self):
        print '%s version: %s' % (argv[0], self.version)
        print 'More information available: %s' % self.git_repo

    def find_cache_server(self):
        fallback_srv = 'http://localhost:49672'
        try:
            subprocess.Popen(['/usr/bin/AssetCacheLocatorUtil'],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.log('Forced caching server detection refresh')
        except:
            self.debug('Forced caching server detection failed')
            pass

        if os.path.exists(self.cache_config_path):
            try:
                self.cache_srv_conf = plistlib.readPlist(
                    self.cache_config_path
                )
                self.cache_server_port = self.cache_srv_conf['Port']
                self.cache_server = 'http://localhost:%s' % (
                    self.cache_server_port
                )
                self.debug('Local machine appears to be a Caching Server')
            except:
                self.cache_server = fallback_srv
                self.debug('Using fallback caching server %s' %
                           self.cache_server)
        else:
            try:
                self.disk_cache, self.error = subprocess.Popen(
                    ['/usr/bin/getconf DARWIN_USER_CACHE_DIR'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    shell=True).communicate()
                self.disk_cache = self.disk_cache.strip('\n')
                self.disk_cache = os.path.join(
                    self.disk_cache,
                    'com.apple.AssetCacheLocatorService/diskCache.plist'
                )
                self.debug('Using configuration from %s' % self.disk_cache)
                plist = plistlib.readPlist(self.disk_cache)
                self.cache_server = (
                    plist['cache'][0]['servers'][0]['localAddressAndPort']
                )
                self.cache_server = 'http://%s' % self.cache_server
            except:
                self.cache_server = fallback_srv
                self.debug('Using fallback caching server %s' %
                           self.cache_server)

        self.log('Remote Caching server found at %s' % self.cache_server)

    # Process the iOS/tvOS/watchOS XML feeds
    def process_update_feed(self, feed_url):
        """ Gets the update feed from Apple.
            If the asset item processed can be cached, it gets added to the
            assets_master list that is empty when initialised.
        """
        try:
            self.debug('Started processing update feed %s' % feed_url)
            response = urllib2.urlopen(feed_url)
            feed_data = plistlib.readPlistFromString(response.read())

            for item in feed_data['Assets']:
                if item.get('SupportedDevices'):
                    hr_model = item['SupportedDevices']

                if item.get('RealUpdateAttributes'):
                    url = item['RealUpdateAttributes']['RealUpdateURL']
                else:
                    url = '%s%s' % (item['__BaseURL'],
                                    item['__RelativePath'])

                if item.get('OSVersion'):
                    os_ver = item['OSVersion']

                if 'Watch' not in hr_model[0]:
                    if (
                        item.get('__CanUseLocalCacheServer') and
                        item['__CanUseLocalCacheServer']
                    ):
                        self.add_asset(hr_model[0], os_ver, url)

                if 'Watch' in hr_model[0]:
                    if not item.get('ReleaseType') == 'Beta':
                        self.add_asset(hr_model[0], os_ver, url)

                self.debug('Completed processing update feed %s' % feed_url)

        except (urllib2.URLError, urllib2.HTTPError) as e:
            self.debug('Exception (%s) processing feed %s' % (e, feed_url))
            print '%s' % e
            exit(1)

    # Builds the asset master list
    def build_asset_master_list(self):
        # Advise which URL is used for caching server
        print 'Found Caching Server: %s' % self.cache_server

        # iOS/tvOS/watchOS
        print 'Processing iOS device feeds'
        for item in self.update_feeds:
            self.debug('Processing item %s' % item)
            self.process_update_feed(self.update_feeds[item])

        # Mac App Store
        print 'Processing Mac App Store items'
        self.build_mas_assets_list()

        # macOS X Software Updates
        print 'Processing macOS Software Update catalog\n'
        self.build_os_x_combo_list()

    # Builds MAS assets into master list
    def build_mas_assets_list(self):
        for mas_asset in self.mas_assets:
            os_ver = self.mas_assets[mas_asset]['version']
            url = (
                ''.join(self.mas_assets[mas_asset]['url'])
            )

            self.add_asset(mas_asset, os_ver, url)

    # Builds a list of macOS X Combo updates & adds to the master assets list
    def build_os_x_combo_list(self):
        response = urllib2.urlopen(self.osx_update_feed)
        updates = plistlib.readPlistFromString(response.read())

        for item in updates['Products']:
            packages = updates['Products'][item]['Packages']
            for pkg in packages:
                if re.search('(OSXUpd[\d.]+|OSXUpdCombo[\d.]+)', pkg['URL']):

                    upd_model = os.path.basename(pkg['URL'].split('.pkg')[0])
                    os_ver = LooseVersion('.'.join(re.findall(r'[\d,]+',
                                                              upd_model)))
                    if (os_ver >= LooseVersion('10.10.0') and
                            'ForSeed' not in upd_model):
                        self.add_asset(upd_model, os_ver, pkg['URL'])

    # Adds an asset into the master assets list
    def add_asset(self, asset_model, os_ver, url):
        url = self.convert_asset_url(url)
        asset = self.Asset(
            model=asset_model,
            download_url=url,
            os_version=os_ver
        )

        if asset not in self.assets_master:
            self.assets_master.append(asset)
            self.debug('Added asset %s URL %s' % (
                asset.model, asset.download_url))

    # Converts the asset URL into the right format to cache
    def convert_asset_url(self, asset_url):
        asset_url = urlparse(asset_url)
        asset_url = '%s%s?source=%s' % (self.cache_server,
                                        asset_url.path,
                                        asset_url.netloc)
        self.debug('Converted asset url to %s' % asset_url)
        return asset_url

    # Function for listing assets available to be cached
    def list_devices_in_feed(self):
        self.build_asset_master_list()

        assets_list = []
        for item in self.assets_master:
            if item.model not in assets_list:
                assets_list.append(item.model)

        ipad_assets = []
        ipod_assets = []
        iphone_assets = []
        tv_assets = []
        watch_assets = []

        assets_list.sort()
        for item in assets_list:
            if 'iPad' in item:
                ipad_assets.append(item)

        for item in assets_list:
            if 'iPod' in item:
                ipod_assets.append(item)

        for item in assets_list:
            if 'iPhone' in item:
                iphone_assets.append(item)

        for item in assets_list:
            if 'AppleTV' in item:
                tv_assets.append(item)

        for item in assets_list:
            if 'Watch' in item:
                watch_assets.append(item)

        print 'Cacheable assets:'
        for a, b, c in zip(assets_list[::3], assets_list[1::3],
                           assets_list[2::3]):
            print '{:<20}{:<20}{:<}'.format(a, b, c)

    # Makes file sizes human friendly
    def convert_size(self, file_size, precision=2):
        """ Converts the size of remote object to human readable format"""
        suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
        suffix_index = 0
        while file_size > 1024 and suffix_index < 4:
            suffix_index += 1
            file_size = file_size/1024.0
        return '%.*f%s' % (precision, file_size, suffixes[suffix_index])

    # Downloads files, what else do you expect? :P
    def download(self, asset, keep_file=False, download_dir='/tmp/precache'):
        remote_file = asset.download_url
        local_file = remote_file.split("?")[0].split("/")[-1]
        if keep_file:
            if not os.path.isdir(download_dir):
                os.mkdir(download_dir)
                local_file = os.path.join(download_dir, local_file)
                f = open(local_file, 'wb')
                self.log('Saving IPSW %s to %s' % (remote_file, local_file))
                print 'IPSW saving to %s' % local_file
        if not keep_file:
            local_file = os.path.join('/dev/null', local_file)

        try:
            if ('.zip' or '.ipsw' or '.xip' in remote_file):
                req = urllib2.urlopen(remote_file)
                if req.info().getheader('Content-Type') is not None:
                    try:
                        self.debug('Attempting to fetch %s' % remote_file)
                        ts = req.info().getheader('Content-Length').strip()
                        human_fs = self.convert_size(float(ts))
                        header = True
                    except AttributeError:
                        try:
                            self.debug('Attempting to fetch %s' % remote_file)
                            ts = req.info().getheader('Content-Length').strip()
                            human_fs = self.convert_size(float(ts))
                            header = True
                        except AttributeError:
                            header = False
                            human_fs = 0
                    if header:
                        ts = int(ts)
                    bytes_so_far = 0
                    self.log('Starting download of %s to %s' % (
                            remote_file, local_file
                        )
                    )
                    while True:
                        buffer = req.read(8192)
                        if not buffer:
                            print ''
                            break

                        bytes_so_far += len(buffer)
                        if keep_file:
                            f.write(buffer)

                        if not header:
                            ts = bytes_so_far

                        percent = float(bytes_so_far) / ts
                        percent = round(percent*100, 2)

                        stdout.write("\r%s - Version: %s [%0.2f%% of %s]" % (
                            asset.model,
                            asset.os_version,
                            percent,
                            human_fs
                            )
                        )
                        stdout.flush()

                    self.log(
                        'Cached %s %s from %s' % (asset.model,
                                                  asset.os_version,
                                                  remote_file)
                    )
                else:
                    print 'Skipping %s - already in cache' % asset.model
                    self.log(
                        'Already in cache %s %s' % (asset.model, remote_file)
                    )
            else:
                req = urllib2.urlopen(remote_file)
                print 'Caching %s (%s)' % (asset.model[0],
                                           asset.os_version)
                with open(local_file, 'wb') as f:
                    f.write(req.read())
                    f.close()
        except (urllib2.URLError, urllib2.HTTPError) as e:
            if errno.ECONNREFUSED:
                print remote_file
                print (
                    """Error: Connection refused. """
                    """You may need to specify the cache server """
                    """with the -cs or --caching-server flag. """
                )
                self.log(
                    'Connection refused. Check Caching Server URL is correct'
                )
            elif errno.ETEIMDOUT:
                print (
                    """Error: Connection timed out. Try again later."""
                )
                self.log('Connection timed out. Try again later.')
            else:
                print '%s' % e
            self.debug('Exception (%s) downloading %s' % (e, remote_file))
            exit(1)
        sleep(0.05)

    # This is the function called to cache an iOS/tvOS/watchOS asset
    def cache_asset(self, model=None):
        self.build_asset_master_list()

        if model:
            self.log('Caching model %s' % model)
            for m in model:
                for item in self.assets_master:
                    if m in item.model:
                        self.download(item)
        else:
            print 'Caching all models'
            self.log('Caching all models')
            for item in self.assets_master:
                self.download(item)

    # Functions for downloading IPSW's
    def cache_ipsw(self, device_model):
        url = 'http://api.ipsw.me/v2.1/%s/latest/url' % device_model
        req = urllib2.urlopen(url)
        ipsw_url = urlparse(req.read())
        os_ver = ipsw_url.path.split('/')[1]
        ipsw_url = '%s%s?source=%s' % (self.cache_server,
                                       ipsw_url.path,
                                       ipsw_url.netloc)

        asset = self.Asset(
            model=device_model + ' (ipsw)',
            download_url=ipsw_url,
            os_version=os_ver
        )

        return asset

    # This is called to download the IPSW, passes through to self.download()
    def download_ipsw(self, device_model):
        for model in device_model:
            try:
                asset = self.cache_ipsw(model)
                self.download(asset, keep_file=True)
            except Exception as e:
                self.debug('Not sure what error comes up here, so bam: %s' % e)
                pass


def main():
    class SaneUsageFormat(argparse.HelpFormatter):
        """
            for matt wilkie on SO
            http://stackoverflow.com/questions/9642692/argparse-help-without-duplicate-allcaps/9643162#9643162
        """
        def _format_action_invocation(self, action):
            if not action.option_strings:
                default = self._get_default_metavar_for_positional(action)
                metavar, = self._metavar_formatter(action, default)(1)
                return metavar

            else:
                parts = []

                # if the Optional doesn't take a value, format is:
                #    -s, --long
                if action.nargs == 0:
                    parts.extend(action.option_strings)

                # if the Optional takes a value, format is:
                #    -s ARGS, --long ARGS
                else:
                    default = self._get_default_metavar_for_optional(action)
                    args_string = self._format_args(action, default)
                    for option_string in action.option_strings:
                        parts.append(option_string)

                    return '%s %s' % (', '.join(parts), args_string)

                return ', '.join(parts)

        def _get_default_metavar_for_optional(self, action):
            return action.dest.upper()

    parser = argparse.ArgumentParser(formatter_class=SaneUsageFormat)

    parser.add_argument('-cs', '--caching-server',
                        type=str,
                        nargs=1,
                        dest='cache_server',
                        metavar='http://cachingserver:port',
                        help='Provide the cache server URL and port',
                        required=False)

    parser.add_argument('-l', '--list',
                        action='store_true',
                        dest='list_models',
                        help='Lists models available for caching',
                        required=False)

    parser.add_argument('-m', '--model',
                        type=str,
                        nargs='+',
                        dest='model',
                        metavar='model',
                        help='Provide model(s)/app(s), i.e iPhone8,2 Xcode',
                        required=False)

    parser.add_argument('-i', '--ipsw',
                        type=str,
                        nargs='+',
                        dest='ipsw',
                        metavar='model',
                        help='Download IPSW files for one or more models',
                        required=False)

    parser.add_argument('--version',
                        action='store_true',
                        dest='vers',
                        help='Prints version information',
                        required=False)

    args = parser.parse_args()

    if len(argv) > 1:
        try:
            try:
                srv = args.cache_server[0]
                pop = PreCache(cache_server=srv)
            except:
                pop = PreCache()
            if args.list_models:
                pop.list_devices_in_feed()
            if args.model:
                pop.cache_asset(args.model)
            if args.ipsw:
                pop.download_ipsw(args.ipsw)
            if args.vers:
                pop.version_info()
        except KeyboardInterrupt:
            print ''
            exit(1)

    else:
        parser.print_usage()
        exit(1)


if __name__ == '__main__':
    main()
