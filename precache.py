import argparse
import logging
import urllib2
import plistlib
import subprocess
import re
from urlparse import urlparse


class PreCache(object):

    logger = logging.getLogger('precache')
    logger.level = logging.INFO

    default_caching_server = 'http://localhost:57466'

    exclude_beta_updates = False

    update_feeds = [
        'http://mesu.apple.com/assets/com_apple_MobileAsset_SoftwareUpdate/com_apple_MobileAsset_SoftwareUpdate.xml',
        'http://mesu.apple.com/assets/tv/com_apple_MobileAsset_SoftwareUpdate/com_apple_MobileAsset_SoftwareUpdate.xml'
    ]

    feeds_cache = {}

    def __init__(self, caching_server=None):
        self.caching_server = caching_server if caching_server else self.detect_caching_server()

    def cache(self, model):
        update_urls = self.get_update_urls(model)

        if update_urls:
            for update_url in update_urls:
                url = urlparse(update_url)
                cache_url = '{caching_server}{path}?source={sourse}'.format(caching_server=self.caching_server,
                                                                            path=url.path,
                                                                            sourse=url.netloc)

                self.logger.info('Caching update for the model {}:\n{}...'.format(model, cache_url))
                try:
                    response = urllib2.urlopen(cache_url)
                    response.read()

                    self.logger.info("Update for the model {} is cached".format(model))
                except (urllib2.URLError, urllib2.HTTPError) as ex:
                    self.logger.error("Update for the model {} is not cached: {}".format(model, ex.reason))
        else:
            self.logger.error("Updates for the model {} not found in feeds".format(model))

    def get_update_urls(self, model):
        update_urls = set()

        for feed in self.update_feeds:
            if feed in self.feeds_cache:
                feed_data = self.feeds_cache
            else:
                try:
                    response = urllib2.urlopen(feed)
                    feed_data = plistlib.readPlistFromString(response.read())

                    self.feeds_cache[feed] = feed_data
                except (urllib2.URLError, urllib2.HTTPError) as ex:
                    self.logger.error("Can't load feed {}: {}".format(feed, ex.reason))

            if feed_data:
                for asset in feed_data['Assets']:
                    if model in asset['SupportedDevices']:
                        if asset.get('ReleaseType') == 'Beta' and self.exclude_beta_updates:
                            continue

                        if 'RealUpdateAttributes' in asset:
                            update_urls.add(asset['RealUpdateAttributes']['RealUpdateURL'])
                        else:
                            update_urls.add(asset['__BaseURL'] + asset['__RelativePath'])

        return update_urls

    def detect_caching_server(self):
        self.logger.info("Detecting Cache Server...")

        try:
            caching_status = subprocess.check_output(['serveradmin', 'fullstatus', 'caching'])
        except:
            self.logger.warn('Caching Server not found\nTrying default {}'.format(self.default_caching_server))
            return self.default_caching_server
        else:
            caching_server_port = re.findall(r'caching:Port *= *(\d+)', caching_status, re.I)

            if caching_server_port:
                return 'http://localhost:{}'.format(caching_server_port[0])
            else:
                self.logger.warn('Can not detect Caching Server port\nTrying default {}'.format(self.default_caching_server))
                return self.default_caching_server

if __name__ == "__main__":
    logging.basicConfig()

    parser = argparse.ArgumentParser(description='PreCache. Populate iOS updates in the Caching Server.')

    parser.add_argument('models',
                        metavar='model',
                        nargs='+',
                        help='The iOS device model that PreCache will download updates for')
    parser.add_argument('-s', '--caching-server',
                        dest='server',
                        help='The base URL of the Caching Server')
    parser.add_argument('--no-beta',
                        action='store_true',
                        help='Exclude Beta updates from the caching')

    args = parser.parse_args()

    precache = PreCache(args.server)
    precache.exclude_beta_updates = args.no_beta

    for model in args.models:
        precache.cache(model)
