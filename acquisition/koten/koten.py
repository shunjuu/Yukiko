
import anitopy
import metsuke
import naomi
import os
import pathlib
import rabbitpy
import shutil
import shikyou
import tempfile
import time
import util

from ayumi import Ayumi
from config import settings
from retry import retry
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

DEFAULT_SLEEP_INTERVAL = 5
DEFAULT_WATCH_PATH = "/opt/koten/"

class IzumiHandler(FileSystemEventHandler):

    def __init__(self, channel):
        self.channel = channel

    # We only need to handle on_created events.
    def on_created(self, event):

        Ayumi.info('Detected new creation event under path "{}", running preflight checks.'.format(event.src_path), color=Ayumi.LCYAN)

        # Do not process new directory events
        if event.is_directory:
            Ayumi.info('Detected new event directory under path "{}", ignoring.'.format(event.src_path), color=Ayumi.LYELLOW)
            return

        if not os.path.exists(event.src_path):
            Ayumi.info("Event detected as false positive, will not proceed.", color=Ayumi.LYELLOW)
            return

        Ayumi.info("Preflight check good, starting pipeline.", color=Ayumi.LGREEN)
        on_new_file(event.src_path, self.channel)


@retry(delay=60, tries=3, exceptions=(shikyou.ShikyouResponseException, shikyou.ShikyouTimeoutException), backoff=1.5, max_delay=3600, logger=Ayumi.get_logger())
def on_new_file(src_path, channel):

    show_name = None
    episode_name = None

    new_file = src_path.replace(os.path.commonpath([settings.get('KOTEN_WATCH_PATH', DEFAULT_WATCH_PATH), src_path]) + "/", "")

    if m := util._show_manually_specified(new_file):
        Ayumi.info("Detected show name and episode name in event, using Mode 1.")
        show_name = m.group(1)
        episode_name = util._clean_episode_name(m.group(2))
        Ayumi.info("New show name: {}".format(show_name), color=Ayumi.LYELLOW)
        Ayumi.info("New episode name: {}".format(episode_name), color=Ayumi.LYELLOW)
    else:
        Ayumi.debug("Non-conformant episode provided, using Naomi to find show name.")
        episode_name = util._clean_episode_name(pathlib.PurePath(src_path).name)
        show_name = naomi.find_closest_title(anitopy.parse(new_file)['anime_title'])
        Ayumi.info("New show name: {}".format(show_name), color=Ayumi.LYELLOW)
        Ayumi.info("New episode name: {}".format(episode_name), color=Ayumi.LYELLOW)

        # There is an event where Anilist is down, and Naomi could return None.
        # In this case, use the assumed-parsed show as the title
        if not show_name:
            show_name = anitopy.parse(new_file)['anime_title']

    job = {
        "show": show_name,
        "episode": episode_name,
        "filesize": os.path.getsize(src_path),
        "sub": "softsub"
    }

    # Create the temporary rclone file
    with tempfile.NamedTemporaryFile(suffix=".conf", mode="w+b") as rconf:
        Ayumi.debug("Opening context managed rclone config file under path: {}.".format(rconf.name))
        rconf.write(str.encode(settings.get("RCLONE_CONFIG_FILE")))
        rconf.flush()  # YOU MUST FLUSH THE FILE SO RCLONE CAN READ IT!
        Ayumi.debug("Configurations written to temporary file. Size is {} bytes.".format(rconf.tell()))

        shikyou.upload(metsuke.generate(job), settings.get('KOTEN_RCLONE_UPLOAD'), src_path, rconf.name, settings.get('RCLONE_FLAGS', ""))

    Ayumi.debug("Closed context managed rclone config file.")

    # Send the notification to RabbitMQ
    # Because of threading reasons the publishing could fail, but we're not concerned with guaranteeing it.
    try:
        message = rabbitpy.Message(
            channel,
            job,
            properties={
                "content_type": "application/json",
                "delivery_mode": 2
            })

        if message.publish(settings.get('KOTEN_EXCHANGE')):
            Ayumi.info("Job successfully published to RabbitMQ", color=Ayumi.LGREEN)
        else:
            Ayumi.warning("Job unsuccessfully published to RabbitMQ", color=Ayumi.LRED)
            raise Exception()

    except:
        # RabbitPy could have timed out, etc. at this point
        Ayumi.warning("Some kind of error occured when attempting to publish to RabbitMQ, printing json body.", color=Ayumi.LYELLOW)
        Ayumi.warning(str(job))

    if settings.get('KOTEN_CLEANUP'):
        Ayumi.info("Cleanup mode enabled, removing original file.", color=Ayumi.LYELLOW)

        # Two cleanup modes - only the file itself, or possibly also the parent folder.
        if util._show_manually_specified(new_file):
            Ayumi.info("Mode 1 detected, removing file and parent directory if allowed.")
            p = pathlib.Path(src_path)
            p.unlink()
            try:
                p.parent.rmdir()
            except:
                Ayumi.info("Parent folder has other items, will not empty.")
                for child in p.parent.iterdir():
                    Ayumi.debug(child.name)
            Ayumi.info("Cleanup complete.", color=Ayumi.GREEN)

        else:
            Ayumi.info("Mode 2 detected, removing single file.")
            os.remove(src_path)

    return


def observe():
    try:
        with rabbitpy.Connection('amqp://{username}:{password}@{host}:{port}/{vhost}'.format(
            username=settings.get('RABBITMQ_USERNAME'),
            password=settings.get('RABBITMQ_PASSWORD'),
            host=settings.get('RABBITMQ_HOST'),
            port=settings.get('RABBITMQ_PORT'),
            vhost=settings.get('RABBITMQ_VHOST')
        )) as conn:
            with conn.channel() as channel:

                channel.enable_publisher_confirms()
                Ayumi.set_rabbitpy_channel(channel)
                Ayumi.info("Now connected AMQP provider.", color=Ayumi.GREEN)

                event_handler = IzumiHandler(channel)
                observer = Observer()
                observer.schedule(event_handler, settings.get('KOTEN_WATCH_PATH', DEFAULT_WATCH_PATH), recursive=True)
                observer.start()
                Ayumi.info("Now observing: {}".format(settings.get('KOTEN_WATCH_PATH', DEFAULT_WATCH_PATH)), color=Ayumi.BLUE)

                try:
                    while True:
                        time.sleep(settings.get('KOTEN_SLEEP_INTERVAL', DEFAULT_SLEEP_INTERVAL))
                except:
                    Ayumi.warning("Detected SIGKILL or error, returning...", color=Ayumi.YELLOW)
                    observer.stop()
                observer.join()

    except rabbitpy.exceptions.AMQPConnectionForced:

        Ayumi.rabbitpy_channel = None
        Ayumi.critical("Operator manually closed RabbitMQ connection, shutting down.", color=Ayumi.RED)
        # Use return for now because in some cases, calling exit() may invoke the retry() header.
        return


if __name__ == "__main__":
    observe()
