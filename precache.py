#!/usr/bin/python
"""
This is a modified version of the precache.py processor available from
https://github.com/krypted/precache

Differences:
    This version doesn't require sudo, downloads the files to /tmp/precache,
    and doesn't download beta releases.
    A percentage indicator provides feedback for the download progress.

Usage:
    Before working with this any further, you'll need to change the
    initialisation of the class PreCache() to specifically point to your
    caching server.


    precache.py [-h] [-l] [-m <model> [<model> ...]]

    optional arguments:
          -h, --help            Show this help message and exit
          -l, --list            Lists models available for caching
          -m, --model <model> [<model> ...]
                                Provide one or model numbers, i.e
                                iPhone8,2
"""

import argparse
import collections
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
    def __init__(self, caching_server=None, caching_port=None):
        """ Initialise the object with some basic configurations
            When initialising, detect if the script is running on the cache
            server, if it isn't, then use values provided by arguments when the
            object is initialised.
            Can also override by providing those arguments."""

        self.logger = logging.getLogger('precache')
        self.logger.setLevel(logging.INFO)
        # self.logger.setLevel(logging.DEBUG)
        self.fh = logging.FileHandler('/tmp/precache.log')
        self.formatter = logging.Formatter(
            '%(asctime)s %(levelname)s - %(message)s'
        )
        self.fh.setFormatter(self.formatter)
        self.logger.addHandler(self.fh)
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

        self.cache_config_path = '/Library/Server/Caching/Config/Config.plist'

        if not caching_server:
            self.cache_server = 'http://localhost'
            self.logger.debug(
                'Fallback to default host %s' % self.cache_server
            )
        else:
            self.cache_server = caching_server

        if not caching_port:
            if os.path.exists(self.cache_config_path):
                try:
                    self.cache_srv_conf = plistlib.readPlist(
                        self.cache_config_path
                    )
                    self.cache_server_port = self.cache_srv_conf['Port']
                except:
                    pass
            else:
                self.cache_server_port = '49672'
                self.logger.debug(
                    'Fallback to default port %s' % self.cache_server_port
                )
        else:
            self.cache_server_port = caching_port

        self.cache_server = '%s:%s' % (self.cache_server,
                                       self.cache_server_port)
        self.logger.debug(
            'Cache server and port %s' % (self.cache_server)
        )

        self.exclude_beta = True
        self.assets_master = []

    def convert_asset_url(self, asset_url):
        asset_url = urlparse(asset_url)
        asset_url = '%s%s?source=%s' % (self.cache_server,
                                        asset_url.path,
                                        asset_url.netloc)
        return asset_url

    def cache_ipsw(self, device_model):
        Asset = collections.namedtuple('Asset', ['model',
                                                 'download_url',
                                                 'os_version'])

        url = 'http://api.ipsw.me/v2.1/%s/latest/url' % device_model
        try:
            request = urllib2.urlopen(url)
        except urllib2.HTTPError as e:
            print '%s - Model or IPSW may not exist (%s)' % (e, device_model)
        else:
            ipsw_url = urlparse(request.read())
            os_ver = ipsw_url.path.split('/')[1]
            ipsw_url = '%s%s?source=%s' % (self.cache_server,
                                           ipsw_url.path,
                                           ipsw_url.netloc)

            asset = Asset(
                model=device_model + ' (ipsw)',
                download_url=ipsw_url,
                os_version=os_ver
            )

            return asset

    def download_ipsw(self, device_model):
        for model in device_model:
            try:
                asset = self.cache_ipsw(model)
                self.download(asset, keep_file=True)
            except:
                pass

    def process_update_feed(self, feed_url):
        """ Gets the update feed from Apple.
            If the asset item processed can be cached, it gets added to the
            assets_master list that is empty when initialised.
        """
        try:
            Asset = collections.namedtuple('Asset', ['model',
                                                     'download_url',
                                                     'os_version'])

            response = urllib2.urlopen(feed_url)
            self.logger.debug('Opening URL %s' % feed_url)
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

                asset = Asset(
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
                                self.logger.debug(
                                    'Added %s to master assets' % url
                                )

                if 'Watch' in asset.model:
                    if asset not in self.assets_master:
                        if not item.get('ReleaseType') == 'Beta':
                            self.assets_master.append(asset)
                            self.logger.debug(
                                'Added %s to master assets' % url
                            )

        except (urllib2.URLError, urllib2.HTTPError) as e:
            self.logger.debug('Error processing assets: %s' % e)
            raise e

    def build_asset_master_list(self):
        for item in self.update_feeds:
            self.process_update_feed(self.update_feeds[item])

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

    def convert_size(self, file_size, precision=2):
        """ Converts the size of remote object to human readable format"""
        suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
        suffix_index = 0
        while file_size > 1024 and suffix_index < 4:
            suffix_index += 1
            file_size = file_size/1024.0
        return '%.*f%s' % (precision, file_size, suffixes[suffix_index])

    def download(self, asset, keep_file=False, download_dir='/tmp/precache'):
        remote_file = asset.download_url
        local_file = remote_file.split("?")[0].split("/")[-1]
        if keep_file:
            if not os.path.isdir(download_dir):
                os.mkdir(download_dir)
                local_file = os.path.join(download_dir, local_file)
                print 'IPSW saving to %s' % local_file
        if not keep_file:
            local_file = os.path.join('/dev/null', local_file)
        try:
            if ('.zip' or '.ipsw' or '.xip' in remote_file):
                req = urllib2.urlopen(remote_file)
                self.logger.debug("Looking for Content-Type header")
                if req.info().getheader('Content-Type') is not None:
                    self.logger.debug(
                        'No Content-Type header found... caching'
                    )
                    try:
                        self.logger.debug(
                            'Trying to get remote file size attempt 1'
                        )
                        ts = req.info().getheader('Content-Length').strip()
                        human_fs = self.convert_size(float(ts))
                        header = True
                    except AttributeError:
                        try:
                            self.logger.debug(
                                'Trying to get remote file size attempt 2'
                            )
                            ts = req.info().getheader('Content-Length').strip()
                            human_fs = self.convert_size(float(ts))
                            header = True
                        except AttributeError:
                            header = False
                            human_fs = 0
                    if header:
                        ts = int(ts)
                    bytes_so_far = 0
                    self.logger.debug(
                        'Beggining download of %s' % remote_file
                    )
                    while True:
                        buffer = req.read(8192)
                        if not buffer:
                            print ''
                            break

                        bytes_so_far += len(buffer)
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

                    self.logger.info(
                        'Cached %s %s - %s' % (asset.model,
                                               asset.os_version,
                                               remote_file)
                    )
                else:
                    print 'Skipping %s - already in cache' % asset.model
                    self.logger.info(
                        'Skipping %s %s - already in cache' % (asset.model,
                                                               remote_file)
                    )
            else:
                self.logger.debug(
                    'Falling back to no progress download method'
                )
                req = urllib2.urlopen(remote_file)
                print 'Caching %s (%s)' % (asset.model[0],
                                           asset.os_version)
                with open(local_file, 'wb') as f:
                    f.write(req.read())
                    f.close()
        except (urllib2.URLError, urllib2.HTTPError) as e:
            print '%s' % e
            self.logger.debug('Error downloading file - %s' % e)
            exit(1)
        sleep(0.05)

    def cache_asset(self, model=None):
        self.build_asset_master_list()

        if model:
            self.logger.info('Caching models %s' % model)
            for m in model:
                for item in self.assets_master:
                    if m in item.model:
                        self.download(item)
        else:
            print 'Caching all models'
            self.logger.info('Caching all models')
            for item in self.assets_master:
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

    parser.add_argument('-l', '--list',
                        action='store_true',
                        dest='list_models',
                        help='Lists models available for caching',
                        required=False)

    parser.add_argument('-m', '--model',
                        type=str,
                        nargs='+',
                        dest='model',
                        metavar='<model>',
                        help='Provide one or model numbers, i.e iPhone8,2',
                        required=False)

    parser.add_argument('-i', '--ipsw',
                        type=str,
                        nargs='+',
                        dest='ipsw',
                        metavar='<model>',
                        help='Download IPSW files for one or more models',
                        required=False)

    args = parser.parse_args()

    pop = PreCache(caching_server='http://thor', caching_port='49672')

    if len(argv) > 1:
        if args.list_models:
            pop.list_devices_in_feed()
        if args.model:
            pop.cache_asset(args.model)
        if args.ipsw:
            pop.download_ipsw(args.ipsw)
    else:
        parser.print_usage()
        exit(1)


if __name__ == '__main__':
    main()
