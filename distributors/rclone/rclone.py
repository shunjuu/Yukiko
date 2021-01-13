import json
import metsuke
import shikyou
import rabbitpy
import signal
import sys
import tempfile

from ayumi import Ayumi
from config import settings
from retry import retry

# Signal handler


def sig_handler(sig, frame):
    Ayumi.warning("SIG command {} detected, exiting...".format(
        sig), color=Ayumi.LRED)
    sys.exit()


# Add in SIGKILL handler
signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)


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

                queue = rabbitpy.Queue(channel, settings.get('DISTRIBUTORS_RCLONE_QUEUE'))
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
                        Ayumi.debug("Loaded sub type: {}".format(job['sub']))

                        metsuke_job = metsuke.Job(
                            job['show'], job['episode'], job['filesize'], job['sub'])

                        with tempfile.NamedTemporaryFile(suffix=".conf", mode="w+b") as rconf, tempfile.TemporaryDirectory() as tempdir:
                            Ayumi.debug("Opening context managed rclone config file under path: {}.".format(rconf.name))
                            Ayumi.debug("Opening context managed rclone temporary directory under path: {}".format(tempdir))
                            rconf.write(str.encode(settings.get("RCLONE_CONFIG_FILE")))
                            rconf.flush()  # YOU MUST FLUSH THE FILE SO RCLONE CAN READ IT!
                            Ayumi.debug("Configurations written to temporary file. Size is {} bytes.".format(rconf.tell()))

                            dl_sources = None
                            up_dests = None
                            if job['sub'].lower() == "softsub":
                                dl_sources = settings.get("DISTRIBUTORS_RCLONE_SOFTSUB_DOWNLOAD")
                                up_dests = settings.get("DISTRIBUTORS_RCLONE_SOFTSUB_UPLOAD")
                            elif job['sub'].lower() == "hardsub":
                                dl_sources = settings.get("DISTRIBUTORS_RCLONE_HARDSUB_DOWNLOAD")
                                up_dests = settings.get("DISTRIBUTORS_RCLONE_HARDSUB_UPLOAD")

                            Ayumi.debug("Fresh fetched download sources as: {}".format(" ".join(dl_sources)))
                            Ayumi.debug("Fresh fetched upload sources as: {}".format(" ".join(up_dests)))

                            try:
                                temp_ep = shikyou.download(metsuke_job, dl_sources, tempdir, rconf.name, settings.get("RCLONE_FLAGS", ""))
                                if temp_ep:
                                    shikyou.upload(metsuke_job, up_dests, temp_ep, rconf.name, settings.get("RCLONE_FLAGS", ""))
                                else:
                                    Ayumi.warning("Unable to find requested job in any sources, nacking...", color=Ayumi.RED)
                                    message.nack()
                                    continue
                            except shikyou.ShikyouResponseException:
                                Ayumi.critical("Rclone threw an unexpected response code, rejecting.", color=Ayumi.RED)
                                message.reject()
                                continue
                            except shikyou.ShikyouTimeoutException:
                                Ayumi.warning("Rclone timed out whilhe executing, nacking.", color=Ayumi.RED)
                                message.nack()
                                continue

                        Ayumi.debug("Closed context managed rclone config file.")
                        Ayumi.debug("Closed context managed temporary directory.")

                    else:
                        Ayumi.warning("Received a job that Metsuke was not able to validate.", color=Ayumi.LRED)
                        Ayumi.warning(json.dumps(job), color=Ayumi.LRED)

                    Ayumi.info("Completed processing this message for {}".format(job['episode']), color=Ayumi.LGREEN)
                    message.ack()

    except rabbitpy.exceptions.AMQPConnectionForced:

        Ayumi.rabbitpy_channel = None
        Ayumi.critical("Operator manually closed RabbitMQ connection, shutting down.", color=Ayumi.RED)
        # Use return for now because in some cases, calling exit() may invoke the retry() header.
        return


if __name__ == "__main__":
    consume()
