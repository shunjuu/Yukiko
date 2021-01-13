import anitopy
import metsuke
import os
import rabbitpy
import re
import shutil
import signal
import subprocess
import sys
import tempfile

from ayumi import Ayumi
from config import settings
from json import dumps, loads, JSONDecodeError
from retry import retry
from time import sleep
from typing import Dict, Tuple

# Signal handler


def sig_handler(sig, frame):
    Ayumi.warning("SIG command {} detected, exiting...".format(
        sig), color=Ayumi.LRED)
    sys.exit()


# Add in SIGKILL handler
signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)


def _load_amqp_message_body(message) -> Dict:
    try:
        feeditem = loads(message.body.decode('utf-8'))
        return feeditem
    except JSONDecodeError:
        Ayumi.warning(
            "Received an AMQP message that is invalid JSON, will not process...", color=Ayumi.RED)
        return None


def _strip_title(show_title) -> str:
    """
    Strips a provided show title name to a spaceless, punctuation-less title.
    """
    return re.sub(r'[^\w]', '', show_title)


def _parse_shows_map(show_title) -> Tuple[str, str]:
    if "->" in show_title:
        original_title, override_title = show_title.split(" -> ")
        Ayumi.debug(
            "Found '->' in title, mapping (unstripped) {} to {}".format(original_title, override_title))
        return (_strip_title(original_title), override_title)
    else:
        return (_strip_title(show_title), show_title)


def _load_shows_map() -> Dict[str, str]:
    shows_map = settings.get(
        'ACQUISITION_DOWNLOAD_BITTORRENT_SHOWS_MAP', [])
    Ayumi.debug("Fetched shows map from config: {}".format(shows_map))

    show_name_map = dict()
    Ayumi.debug("Creating a stripped title to override title mapping...")

    for show in shows_map:
        stripped_title, override_title = _parse_shows_map(show)
        show_name_map[stripped_title] = override_title
        Ayumi.debug("Mapped {} to key {}.".format(
            override_title, stripped_title))
    return show_name_map


def _generate_new_filename(dl_file):
    info = anitopy.parse(dl_file)
    new_dl_file = info['anime_title']
    if 'anime_season' in info:
        Ayumi.debug('Found anime_season "{}"'.format(info['anime_season']))
        new_dl_file = new_dl_file + " S" + str(info['anime_season'])
    if 'episode_number' in info:
        Ayumi.debug('Found episode_number "{}"'.format(info['episode_number']))
        new_dl_file = new_dl_file + " - " + str(info['episode_number'])
    if 'video_resolution' in info:
        Ayumi.debug('Found video_resolution "{}"'.format(
            info['video_resolution']))
        new_dl_file = new_dl_file + " [{}]".format(info['video_resolution'])
    if 'other' in info and 'uncensored' in info['other'].lower():
        Ayumi.debug(
            'Detected this episode is uncensored, adding "(Uncensored)" to the title.')
        new_dl_file += " (Uncensored)"
    _, ext = os.path.splitext(dl_file)
    new_dl_file += ext
    Ayumi.debug('returning new_dl_file: {}'.format(new_dl_file))
    return new_dl_file


def _clean_title(title: str) -> str:
    if title.endswith("/"):
        return title[:-1]
    else:
        return title


@retry(delay=60, backoff=1.5, max_delay=3600)
def bittorrent():
    try:
        with rabbitpy.Connection('amqp://{username}:{password}@{host}:{port}/{vhost}'.format(
            username=settings.get('RABBITMQ_USERNAME'),
            password=settings.get('RABBITMQ_PASSWORD'),
            host=settings.get('RABBITMQ_HOST'),
            port=settings.get('RABBITMQ_PORT'),
            vhost=settings.get('RABBITMQ_VHOST')
        )) as conn:
            with conn.channel() as channel:

                Ayumi.set_rabbitpy_channel(channel)
                channel.enable_publisher_confirms()

                queue_name = settings.get('ACQUISITION_BITTORRENT_QUEUE')
                Ayumi.debug("Connecting to queue: {}".format(queue_name))
                queue = rabbitpy.Queue(channel, queue_name)
                queue.declare(passive=True)

                Ayumi.info('Now listening for messages on queue: {}...'.format(
                    queue_name), color=Ayumi.LYELLOW)

                for message in queue.consume(prefetch=1):

                    Ayumi.info(
                        "Received new message, starting...", color=Ayumi.CYAN)

                    feeditem_preprocess = _load_amqp_message_body(message)
                    Ayumi.debug('Loaded message raw: "{}"'.format(
                        feeditem_preprocess))
                    if not feeditem_preprocess or not metsuke.validate_feeditem(feeditem_preprocess):
                        Ayumi.error('Invalid message received, rejecting. Output: "{}"'.format(
                            feeditem_preprocess), color=Ayumi.RED)
                        message.reject()
                        continue

                    # Load initial data
                    feeditem: metsuke.FeedItem = metsuke.generate_feeditem(
                        feeditem_preprocess)
                    shows_map = _load_shows_map()
                    overload_title = feeditem.show_title
                    Ayumi.info(
                        'Setting overload title: "{}"'.format(overload_title))
                    # If there is a central override, use it instead.
                    if _strip_title(anitopy.parse(feeditem.title)['anime_title']) in shows_map:
                        central_overload_title = shows_map[_strip_title(
                            feeditem.title)]
                        Ayumi.info('Overwriting overload title with central overload title: "{}"'.format(
                            central_overload_title))
                        overload_title = central_overload_title

                    with tempfile.TemporaryDirectory() as temp_dir:

                        Ayumi.debug(
                            'Created temporary directory under path: "{}"'.format(temp_dir))

                        # Download the episode
                        try:
                            res = subprocess.run(
                                [
                                    "aria2c",
                                    "--seed-time=0",
                                    "--rpc-save-upload-metadata=false",
                                    "--bt-save-metadata=false",
                                    "--dir={}".format(temp_dir),
                                    feeditem.link
                                ]
                            )
                            if res.returncode != 0:
                                Ayumi.warning(
                                    "Aria2 did not return a 0 exit code, assuming download errored and nacking.", color=Ayumi.RED)
                                message.nack()
                                continue
                        except subprocess.TimeoutExpired:
                            Ayumi.warning(
                                "Download via webtorrent timed out - nacking.", color=Ayumi.RED)
                            message.nack()
                            continue

                        if res.returncode != 0:
                            Ayumi.warning(
                                "Webtorrent did not have a return code of 0, nacking.", color=Ayumi.RED)
                            message.nack()
                            continue

                        # Rename it
                        potential_files = [f for f in os.listdir(
                            temp_dir) if f.endswith(".mkv")]
                        Ayumi.debug(
                            "Loaded potential files: {}".format(potential_files))
                        if len(potential_files) != 1:
                            Ayumi.warning(
                                "Found more than one .mkv file, rejecting this job.", color=Ayumi.RED)
                            message.reject()
                            continue
                        dl_file = potential_files[0]
                        Ayumi.info('Found file: "{}"'.format(dl_file))
                        dl_file_path = os.path.abspath(
                            '{}/{}'.format(_clean_title(temp_dir), potential_files[0]))
                        Ayumi.debug(
                            'dl_file_path: "{}"'.format(dl_file_path))

                        # Remove unneeded files
                        # TODO: THIS IS A HOTFIX, CHANGE LOGIC IN B2
                        bad_files = [f for f in os.listdir(
                            temp_dir) if not f.endswith(".mkv")]
                        Ayumi.debug("Found bad files: {}".format(bad_files))
                        for bf in bad_files:
                            try:
                                Ayumi.debug("Removing bad file: {}".format(bf))
                                os.remove(
                                    '{}/{}'.format(_clean_title(temp_dir), bf))
                            except:
                                Ayumi.debug("Removing bad tree: {}".format(bf))
                                shutil.rmtree(
                                    '{}/{}'.format(_clean_title(temp_dir), bf))

                        # Move the file to proper layout with updated name
                        dl_file_new_name = _generate_new_filename(dl_file)
                        Ayumi.info('Generated new episode name: "{}"'.format(
                            dl_file_new_name))
                        dl_file_new_dir = "{}/{}".format(
                            temp_dir, overload_title)
                        Ayumi.debug(
                            'dl_file_new_dir: "{}"'.format(dl_file_new_dir))
                        dl_file_new_path = "{}/{}".format(
                            dl_file_new_dir, dl_file_new_name)
                        Ayumi.debug(
                            'dl_file_new_path: "{}"'.format(
                                dl_file_new_path))
                        Ayumi.debug('Moving "{}" to "{}"'.format(
                            dl_file_path, dl_file_new_path))
                        os.mkdir(dl_file_new_dir)
                        shutil.move(dl_file_path, dl_file_new_path)

                        # Upload the file to rclone destination
                        with tempfile.NamedTemporaryFile(suffix=".conf", mode="w+b") as rconf:
                            rconf.write(str.encode(
                                settings.get("RCLONE_CONFIG_FILE")))
                            rconf.flush()
                            Ayumi.debug(
                                'Created temporary rclone file under path: "{}"'.format(rconf.name))
                            rclone_dest = _clean_title(settings.get(
                                "ACQUISITION_BITTORRENT_RCLONE_DEST"))
                            rclone_flags = settings.get("RCLONE_FLAGS", "")
                            command = [
                                "rclone", "--config={}".format(rconf.name), "copy", temp_dir, rclone_dest]
                            command.extend(rclone_flags.split())
                            Ayumi.debug(
                                'Rclone command to be run: "{}"'.format(command))

                            try:
                                Ayumi.info(
                                    'Now uploading new blob to: "{}"'.format(rclone_dest))
                                rclone_res = subprocess.run(
                                    command, timeout=3600)
                                if rclone_res.returncode != 0:
                                    Ayumi.warning('Rclone returned non-zero code of {}, nacking.'.format(
                                        rclone_res.returncode), color=Ayumi.LRED)
                                    message.nack()
                            except subprocess.TimeoutExpired:
                                Ayumi.warning(
                                    'Rclone upload timed out, nacking.', color=Ayumi.LRED)
                                message.nack()
                                continue

                        # Fetch information on the file to create a job
                        new_message = rabbitpy.Message(channel, dumps(
                            {
                                "show": overload_title,
                                "episode": dl_file_new_name,
                                "filesize": int(os.path.getsize(dl_file_new_path)),
                                "sub": "SOFTSUB"
                            }
                        ))
                        acquisition_bittorrent_exchange_name = settings.get(
                            'ACQUISITION_BITTORRENT_EXCHANGE')
                        Ayumi.info('Sending to exchange: "{}"'.format(
                            acquisition_bittorrent_exchange_name), color=Ayumi.CYAN)
                        while not new_message.publish(acquisition_bittorrent_exchange_name, mandatory=True):
                            Ayumi.warning(
                                "Failed to publish feed item, trying again in 60 seconds")
                            sleep(60)
                        Ayumi.info("Published feed item with title: " +
                                   overload_title, color=Ayumi.LGREEN)

                    message.ack()

    except rabbitpy.exceptions.AMQPConnectionForced:
        Ayumi.warning(
            "Operator manually closed RabbitMQ connection, shutting down.", color=Ayumi.LYELLOW)
        return


if __name__ == "__main__":
    bittorrent()
