# Acquisition RSS

##### Izumi V6 "Yukiko": Acquisition Module - RSS Fetcher

This is a core unit of Izumi Version 6, known as "Yukiko". It handles fetching items from a given RSS feed, matching it against provided filters, and then marking it for download in the greater system as a whole to initiate the pipeline.

### Configuration

This module relies on Python's `Dynaconf` module to manage configurations. As such, it supports any endpoint that Dynaconf does, which you can configure in `config.py`. 

| Name                           | Type      | Use                                                                                                       |
| ------------------------------ | --------- | --------------------------------------------------------------------------------------------------------- |
| RABBITMQ_HOST                  | str       | RabbitMQ host url                                                                                         |
| RABBITMQ_PORT                  | int       | RabbtMQ port                                                                                              |
| RABBITMQ_VHOST                 | str       | RabbitMQ virtual host                                                                                     |
| RABBITMQ_USERNAME              | str       | RabbitMQ username                                                                                         |
| RABBITMQ_PASSWORD              | str       | RabbitMQ password                                                                                         |
| ACQUISITION_RSS_ACCEPTED_SHOWS | list[str] | For providing which shows should be downloaded and not. Read more below.                                  |
| ACQUISITION_RSS_FEED_URL       | str       | URL to fetch the feed from. Multiple feeds in the same app are not supported.                             |
| ACQUISITION_RSS_SLEEP_INTERVAL | str       | How long to sleep between each check. Defaults to 5 minutes.                                              |
| ACQUISITION_RSS_EXCHANGE       | str       | Exchange for this module to send jobs to. This exchange should only lead to other compatible downloaders. |
| AYUMI_EXCHANGE                 | str       | The logs exchange Ayumi will send all log outputs to.                                                     |
| AYUMI_CONSOLE_FORMAT           | str       | Message format (filename, functionname, etc) Ayumi will output in.                                        |
| AYUMI_DATE_FORMAT              | str       | Format for how dates should appear in the log messages (passed to basicConfig(datefmt=DATE_FORMAT).       |
| AYUMI_LOG_FORMAT               | str       | Format for logs (passed to basicConfig(format=LOG_FORMAT)                                                 |
| AYUMI_LOG_LEVEL                | str       | Logging level. Can't be changed after startup.                                                            |

`ACQUISITION_RSS_ACCEPTED_SHOWS` is a list of strings. Each string is of the following format:
```
show name [-> override name]
```
`show name` is the name of a show as it would appear in the feed. Any shows in this list will be allowlisted. You can override the shows for these titles by appending a `-> {new title}`, e.g. "name1 -> name2", and name2 will override the original detected name.

### Building

You can build the application using the provided Dockerfile. Note that the build does not include any configuration files - you must load those as volumes, use environmental variables, or use external providers. Redis support is included in the build.

### Starting the Application

Install all dependencies under `requirements.txt`, and then run `python3 rss.py`. There are no command-line arguments; all configurations are loaded through Dynaconf.

For Docker runs, you should mount your settings file, use environmental variables, or specify an external source.