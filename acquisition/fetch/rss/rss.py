import anitopy
import argparse
import feedparser
import json
import metsuke
import rabbitpy
import re
import signal
import sys

from ayumi import Ayumi
from datetime import datetime
from config import settings
from retry import retry
from time import sleep
from typing import Dict, List, Tuple

_DEFAULT_SLEEP_INTERVAL = 300

# Signal handler
def sig_handler(sig, frame):
    Ayumi.critical("SIG command {} detected, exiting...".format(
        sig), color=Ayumi.LRED)
    sys.exit()


# Add in SIGKILL handler
signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)

def _strip_title(show_title) -> str:
    """
    Strips a provided show title name to a spaceless, punctuation-less title.
    """
    return re.sub(r'[^\w]', '', show_title)


def _parse_accepted_shows(show_title) -> Tuple[str, str]:
    if "->" in show_title:
        original_title, override_title = show_title.split(" -> ")
        return (_strip_title(original_title), override_title)
    else:
        return (_strip_title(show_title), show_title)


def _load_accepted_shows() -> Dict[str, str]:
    accepted_shows = settings.get('ACQUISITION_RSS_ACCEPTED_SHOWS', list())
    show_name_map = dict()
    for show in accepted_shows:
        stripped_title, override_title = _parse_accepted_shows(show)
        show_name_map[stripped_title] = override_title
    return show_name_map


def _load_history() -> List[str]:
    try:
        with open("data.json", "r") as data:
            history = json.load(data)
        Ayumi.debug("Loaded history: {}".format(history))
    except:
        history = []
        Ayumi.debug("No history loaded - using empty list")
    return history


def _write_history(new_history) -> None:
    with open('data.json', 'w') as data:
        json.dump(new_history, data, indent=4)
    Ayumi.debug(
        "Wrote new_history to data.json. Contents: {}".format(new_history), color=Ayumi.YELLOW)


@retry(delay=60, backoff=1.5, max_delay=3600, logger=Ayumi.get_logger())
def rss(last_guid=None):

    try:
        with rabbitpy.Connection('amqp://{username}:{password}@{host}:{port}/{vhost}'.format(
            username=settings.get_fresh('RABBITMQ_USERNAME'),
            password=settings.get_fresh('RABBITMQ_PASSWORD'),
            host=settings.get_fresh('RABBITMQ_HOST'),
            port=settings.get_fresh('RABBITMQ_PORT'),
            vhost=settings.get_fresh('RABBITMQ_VHOST')
        )) as conn:
            with conn.channel() as channel:

                Ayumi.set_rabbitpy_channel(channel)
                channel.enable_publisher_confirms()

                while True:

                    Ayumi.info("Now starting feed fetch.", color=Ayumi.LCYAN)

                    feed = feedparser.parse(settings.get(
                        'ACQUISITION_RSS_FEED_URL', None))
                    accepted_shows = _load_accepted_shows()
                    Ayumi.debug(
                        "Loaded accepted shows map: {}".format(accepted_shows))
                    history = _load_history()
                    new_history = list()

                    for entry in feed.entries:

                        # Fetch data first
                        title, link, guid = entry.title, entry.link, entry.guid
                        Ayumi.debug(
                            'Encountered RSS item with title "{}", and guid "{}"'.format(title, guid))

                        # If feed item with last GUID encountered, do not process any further
                        if guid == last_guid:
                            Ayumi.debug(
                                "Encountered RSS item with last_guid {} matching argument, breaking and writing history.".format(
                                    last_guid),
                                color=Ayumi.YELLOW)
                            break

                        # Check the title data
                        # Use the parsed title to match user provided titles.
                        parsed_title = anitopy.parse(title)['anime_title']
                        if _strip_title(parsed_title) not in accepted_shows:
                            Ayumi.info('Feed item with title "{}" (show title: "{}") is not in accepted shows, skipping.'.format(
                                title, parsed_title))
                        else:
                            if guid in history:
                                # This item has been previously processed, skip it.
                                Ayumi.info('Feed item with title "{}" (show title: "{}") has already been processed, skipping.'.format(
                                    title, parsed_title), color=Ayumi.GREEN)
                            else:
                                # A new feeditem! Let us process it.
                                Ayumi.info(
                                    'Feed item with title "{}" (show title: "{}") is in accepted shows, processing.'.format(title, parsed_title), color=Ayumi.YELLOW)
                                message = rabbitpy.Message(channel, json.dumps({
                                    "title": title,
                                    "link": link,
                                    "guid": guid,
                                    "show_title": accepted_shows[_strip_title(parsed_title)]
                                }))
                                acquisition_rss_exchange_name = settings.get(
                                    'ACQUISITION_RSS_EXCHANGE')
                                while not message.publish(acquisition_rss_exchange_name, mandatory=True):
                                    Ayumi.warning(
                                        'Failed to publish feed item with title "{}" to exchange "{}", retrying in 60s...'.format(
                                            title, acquisition_rss_exchange_name), color=Ayumi.RED)
                                    sleep(60)
                                Ayumi.info('Published feed item with title "{}" to exchange "{}".'.format(
                                    title, acquisition_rss_exchange_name,), color=Ayumi.LGREEN)

                            # Keep all items processed in the new history - it will be auto deleted by the expiry of the RSS
                            Ayumi.debug('Appending item "{}" with title "{}" (show title: "{}") to new_history for write.'.format(
                                guid, title, parsed_title), color=Ayumi.YELLOW)
                            new_history.append(guid)

                    _write_history(new_history)

                    # Sleep till the next iteration
                    sleep_duration = settings.get(
                        'ACQUISITION_RSS_SLEEP_INTERVAL', _DEFAULT_SLEEP_INTERVAL)
                    Ayumi.info("Now sleeping {} seconds.".format(
                        sleep_duration), color=Ayumi.LCYAN)
                    sleep(sleep_duration)

    except rabbitpy.exceptions.AMQPConnectionForced:
        Ayumi.rabbitpy_channel = None
        Ayumi.critical(
            "Operator manually closed RabbitMQ connection, shutting down.", color=Ayumi.RED)
        # Use return for now because in some cases, calling exit() may invoke the retry() header.
        return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-g', '--guid',
                        action='store',
                        help="Manually set the last GUID encountered by the RSS feed.",
                        default=None,
                        dest="guid")
    args = parser.parse_args()
    rss(args.guid)
