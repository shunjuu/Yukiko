import datetime
import hisha
import json
import metsuke
import rabbitpy
import requests
import sys
import signal
import time

from ayumi import Ayumi  # Logging
from config import settings
from hurry.filesize import size
from retry import retry
from typing import List, Dict

_EMPTY_INFO = "〇〇"
_MAL_ANI_BASE = "https://myanimelist.net/anime/"
_ANI_ANI_BASE = "https://anilist.co/anime/"
_KIT_ANI_BASE = "https://kitsu.io/anime/"
_KIT_DOWN = "https://kitsu.io/"

# Signal handler
def sig_handler(sig, frame):
    Ayumi.warning("SIG command {} detected, exiting...".format(sig), color=Ayumi.LRED)
    sys.exit()


# Add in SIGKILL handler
signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)


def _generate_embed(job: metsuke.Job, hisha) -> Dict[str, List]:

    webhook = dict()
    webhook['embeds'] = list()

    embed = dict()
    embed['title'] = job.episode

    duration = hisha.duration if hisha.duration != -1 else _EMPTY_INFO
    filesize = size(job.filesize) if job.filesize > 0 else _EMPTY_INFO
    embed['description'] = "{} mins, {} [{}]".format(duration, filesize, job.sub.capitalize())

    embed['color'] = 65535 if job.sub.lower().startswith('s') else 65280
    embed['timestamp'] = _get_timestamp()
    embed['footer'] = {'text': hisha.title_user_preferred}
    embed['thumbnail'] = {'url': hisha.cover_image}
    embed['author'] = {'name': hisha.studio, 'url': hisha.studio_url}

    embed['fields'] = list()

    average_score = hisha.average_score if hisha.average_score != -1 else _EMPTY_INFO
    popularity = hisha.popularity if hisha.popularity != -1 else _EMPTY_INFO
    episodes = hisha.episodes if hisha.episodes != -1 else _EMPTY_INFO
    embed['fields'].append(
        {'name': 'Stats', 'value': 'Score: {}/100, Pop: {}, Total: {} Eps.'.format(average_score, popularity, episodes)})

    embed['fields'].append({'name': 'Links', 'value': "[MyAnimeList]({}) | [Anilist]({}) | [Kitsu]({})".format(
        str.strip(_MAL_ANI_BASE + str(hisha.id_mal)),
        str.strip(_ANI_ANI_BASE + str(hisha.id)),
        str.strip(_KIT_ANI_BASE + str(hisha.id_kitsu))
    )})

    webhook['embeds'].append(embed)

    return webhook


# Retry on all instances except
@retry(delay=60, backoff=1.5, max_delay=3600, logger=Ayumi.get_logger())
def consume():
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

                queue = rabbitpy.Queue(channel, settings.get('NOTIFICATIONS_DISCORD_WEBHOOK_QUEUE', 'nonexistent'))
                queue.declare(passive=True)

                Ayumi.info("Now listening for messages from AMQP provider.", color=Ayumi.YELLOW)

                for message in queue.consume(prefetch=1):

                    try:
                        job = json.loads(message.body.decode('utf-8'))
                    except json.JSONDecodeError:
                        Ayumi.warning("Received a job that is invalid json, not processing.", color=Ayumi.LRED)
                        message.reject()
                        continue

                    Ayumi.info("Received a new job: {}".format(json.dumps(job)), color=Ayumi.CYAN)
                    if metsuke.validate(job):
                        Ayumi.debug("Loaded show: {}".format(job['show']))
                        Ayumi.debug("Loaded episode: {}".format(job['episode']))
                        Ayumi.debug("Loaded filesize: {}".format(job['filesize']))
                        Ayumi.debug( "Loaded sub type: {}".format(job['sub']))

                        embed = _generate_embed(metsuke.generate(job), hisha.search(job['show']))
                        Ayumi.info( "Beginning sending embeds to webhook endpoints.", color=Ayumi.CYAN)
                        for endpoint in settings.get('NOTIFICATIONS_DISCORD_WEBHOOK_ENDPOINTS').to_list():
                            try:
                                requests.post(endpoint, json=embed, timeout=5)
                                Ayumi.debug("Sent embed to {}".format(endpoint))
                            except:
                                Ayumi.warning("Failed to send embed to {}".format(endpoint), color=Ayumi.RED)

                    else:
                        Ayumi.warning("Received a job that Metsuke was not able to validate.", color=Ayumi.LRED)
                        Ayumi.warning(json.dumps(job), color=Ayumi.LRED)

                    Ayumi.info("Completed processing this message for {}".format(job['episode']), color=Ayumi.LGREEN)
                    message.ack()

    except rabbitpy.exceptions.AMQPConnectionForced:
        Ayumi.rabbitpy_channel = None
        Ayumi.critical( "Operator manually closed RabbitMQ connection, shutting down.", color=Ayumi.RED)

        # Use return for now because in some cases, calling exit() may invoke the retry() header.
        return


def _get_timestamp():
    utc_offset_sec = time.altzone if time.localtime().tm_isdst else time.timezone
    utc_offset = datetime.timedelta(seconds=-utc_offset_sec)
    return datetime.datetime.now().replace(tzinfo=datetime.timezone(offset=utc_offset)).isoformat()


if __name__ == "__main__":
    consume()
