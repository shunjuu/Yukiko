# Acquisition Bittorrent

##### Izumi V6 "Yukiko": Acquisition Module - Bittorrent Downloader

This is a core unit of Izumi Version 6, known as "Yukiko". It handles downloading provided FeedItems by means of the bittorrent protocol, and then forwards it to the rest of the system for further processing.

### Configuration

This module relies on Python's `Dynaconf` module to manage configurations. As such, it supports any endpoint that Dynaconf does, which you can configure in `config.py`. 

| Name                                      | Type      | Use                                                                                 |
| ----------------------------------------- | --------- | ----------------------------------------------------------------------------------- |
| RABBITMQ_HOST                             | str       | RabbitMQ host url                                                                   |
| RABBITMQ_PORT                             | int       | RabbtMQ port                                                                        |
| RABBITMQ_VHOST                            | str       | RabbitMQ virtual host                                                               |
| RABBITMQ_USERNAME                         | str       | RabbitMQ username                                                                   |
| RABBITMQ_PASSWORD                         | str       | RabbitMQ password                                                                   |
| ACQUISITION_DOWNLOAD_BITTORRENT_SHOWS_MAP | list[str] | A centralized show name overrider (overrides any other providers.) Read more below. |
| ACQUISITION_BITTORRENT_QUEUE              | str       | Queue (name) to listen to requests from.                                            |
| ACQUISITION_BITTORRENT_RCLONE_DEST        | str       | Rclone destination (should be a path to a folder) to upload new downloads to.       |
| ACQUISITION_BITTORRENT_EXCHANGE           | str       | Exchange to publish new job to (download complete, move to next step).              |

`ACQUISITION_DOWNLOAD_BITTORRENT_SHOWS_MAP` is a list of strings. Each string is of the following format:
```
show name [-> override name]
```
`show name` is the name of a show as it would appear in the feed. Any shows in this list will be allowlisted. You can override the shows for these titles by appending a `-> {new title}`, e.g. "name1 -> name2", and name2 will override the original detected name.

### Building

You can build the application using the provided Dockerfile. Note that the build does not include any configuration files - you must load those as volumes, use environmental variables, or use external providers. Redis support is included in the build.

### Starting the Application

Install all dependencies under `requirements.txt`, and then run `python3 bittorrent.py`. There are no command-line arguments; all configurations are loaded through Dynaconf.

For Docker runs, you should mount your settings file, use environmental variables, or specify an external source.