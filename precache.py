#!/usr/bin/python
"""
This is a modified version of the precache.py processor available from
https://github.com/krypted/precache

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
                            Provide one or more models, i.e iPhone8,2
      -os, --os-installer macOS release [macOS release ...]
                            Provide one or more macOS releases, i.e Sierra
      -i, --ipsw model [model ...]
                            Download IPSW files for one or more models

    Note: Model identifiers and macOS names re currently case sensitive.
"""

import argparse
import collections
import errno
import logging
import os
import plistlib
import urllib2

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

        # macOS Installer URLs from Mac App Store. These are likely to change
        # with each macOS release
        self.osx_installer_urls = {
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
                               'jze1425880974225146329.pkg']}
        }

        # Caching Server configuration
        self.cache_config_path = '/Library/Server/Caching/Config/Config.plist'

        # Check if the machine is running Caching Server and configure port
        if not cache_server:
            fallback_srv = 'http://localhost:49672'
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
                self.cache_server = fallback_srv
                self.debug('Using fallback caching server %s' %
                           self.cache_server)

        if cache_server:
            self.cache_server = cache_server

        self.log('Using caching server %s' % self.cache_server)

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

                url = self.convert_asset_url(url)

                asset = self.Asset(
                    model=hr_model[0],
                    download_url=url,
                    os_version=os_ver
                )

                if 'Watch' not in asset.model:
                    if (
                        item.get('__CanUseLocalCacheServer') and
                        item['__CanUseLocalCacheServer']
                    ):
                        if asset not in self.assets_master:
                            if not item.get('ReleaseType') == 'Beta':
                                self.assets_master.append(asset)
                                self.debug(
                                    'Added asset URL %s' % url
                                )

                if 'Watch' in asset.model:
                    if asset not in self.assets_master:
                        if not item.get('ReleaseType') == 'Beta':
                            self.assets_master.append(asset)
                            self.debug(
                                'Added asset %s URL %s' % (asset.model, url)
                            )
                self.debug('Completed processing update feed %s' % feed_url)

        except (urllib2.URLError, urllib2.HTTPError) as e:
            self.debug('Exception (%s) processing feed %s' % (e, feed_url))
            print '%s' % e
            exit(1)

    # Builds the asset master list
    def build_asset_master_list(self):
        # iOS/tvOS/watchOS
        for item in self.update_feeds:
            self.debug('Processing item %s' % item)
            self.process_update_feed(self.update_feeds[item])

        # macOS Installers
        for installer in self.osx_installer_urls:
            os_ver = self.osx_installer_urls[installer]['version']
            url = ''.join(self.osx_installer_urls[installer]['url'])
            url = self.convert_asset_url(url)
            asset = self.Asset(
                model=installer,
                download_url=url,
                os_version=os_ver
            )
            if asset not in self.assets_master:
                self.assets_master.append(asset)
                self.debug('Added asset %s URL %s' % (asset.model,
                                                      asset.download_url))

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
        assets_list = []

        self.build_asset_master_list()

        for item in self.assets_master:
            if item.model not in assets_list:
                assets_list.append(item.model)

        assets_list.sort()
        print 'iOS and tvOS models:'
        for i in assets_list:
            print i

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

                        stdout.write("\r%s - OS Ver: %s [%0.2f%% of %s]" % (
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

    # Function for downloading macOS installer from Mac App Store
    def cache_osx(self, osx_installer):
        self.build_asset_master_list()
        for m in osx_installer:
            for item in self.assets_master:
                if m in item.model:
                    self.log(
                        'Caching %s %s' % (item.model, item.os_version)
                    )
                    self.download(item)


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
                        help='Provide one or more models, i.e iPhone8,2',
                        required=False)

    parser.add_argument('-os', '--os-installer',
                        type=str,
                        nargs='+',
                        dest='os',
                        metavar='macOS release',
                        help='Provide one or more macOS releases, i.e Sierra',
                        required=False)

    parser.add_argument('-i', '--ipsw',
                        type=str,
                        nargs='+',
                        dest='ipsw',
                        metavar='model',
                        help='Download IPSW files for one or more models',
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
            if args.os:
                pop.cache_osx(args.os)
        except KeyboardInterrupt:
            print ''
            exit(1)

    else:
        parser.print_usage()
        exit(1)


if __name__ == '__main__':
    main()
