# Rclone Distribution

###### Izumi V6 "Yukiko": Distributors Module - Rclone

Thisi s a core unit of Izumi Version 6, known as "Yukiko". It handles distributing files between rclone sources. It will attempt to download the file once from a variety of sources (trying in order), and then will upload to all configured endpoints.

### Configuration

This module relies on Python's `Dynaconf` module to manage configurations. As such, it supports any endpoint that Dynaconf does. For Docker instances, if you wish to use a local configuration, simply set your `settings.{toml/yaml/etc}` file in `/opt/izumi`. To use external configuration loaders (e.g. Redis), you should edit the `Docker-compose.yaml` file and include environmental variables.

Configuration Keys:

| Name                                 | Type | Use                                                                                                  |
| ------------------------------------ | ---- | ---------------------------------------------------------------------------------------------------- |
| RABBITMQ_HOST                        | str  | RabbitMQ host url                                                                                    |
| RABBITMQ_PORT                        | int  | RabbtMQ port                                                                                         |
| RABBITMQ_VHOST                       | str  | RabbitMQ virtual host                                                                                |
| RABBITMQ_USERNAME                    | str  | RabbitMQ username                                                                                    |
| RABBITMQ_PASSWORD                    | str  | RabbitMQ password                                                                                    |
| DISTRIBUTORS_RCLONE_QUEUE            | str  | AMQP queue this app will listen to.                                                                  |
| RCLONE_CONFIG_FILE                   | str  | The actual rclone config file to use. You should copy your rclone file and paste the data into this. |
| RCLONE_FLAGS                         | str  | Flags passed to rclone when running commands. Commands run are `lsjson` and `copyto`.                |
| DISTRIBUTORS_RCLONE_SOFTSUB_DOWNLOAD | str  | List of rclone sources (configs) to attempt to fetch softsub files from.                             |
| DISTRIBUTORS_RCLONE_SOFTSUB_UPLOAD   | str  | List of rclone destinations (configs) to upload new softsub files to.                                |
| DISTRIBUTORS_RCLONE_HARDSUB_DOWNLOAD | str  | List of rclone sources (configs) to attempt to fetch hardsub files from.                             |
| DISTRIBUTORS_RCLONE_HARDSUB_UPLOAD   | str  | List of rclone destinations (configs) to upload new hardsub files to.                                |
| AYUMI_EXCHANGE                       | str  | The logs exchange Ayumi will send all log outputs to.                                                |
| AYUMI_CONSOLE_FORMAT                 | str  | Message format (filename, functionname, etc) Ayumi will output in.                                   |
| AYUMI_DATE_FORMAT                    | str  | Format for how dates should appear in the log messages (passed to basicConfig(datefmt=DATE_FORMAT).  |
| AYUMI_LOG_FORMAT                     | str  | Format for logs (passed to basicConfig(format=LOG_FORMAT)                                            |
| AYUMI_LOG_LEVEL                      | str  | Logging level. Can't be changed after startup.                                                       |

`DISTRIBUTORS_RCLONE_*` will fetch from/upload to "config/{SHOW_NAME}/{EPISODE_NAME}". Thus, you should specify up to the "show" folder, but not beyond. You can end with or without a `/`.


### Building

You can build the application using the provided Dockerfile. Note that the build does not include any configuration files - you must load those as volumes, use environmental variables, or use external providers. Redis and Vault support is included in the build.

### Starting the Application

Install all dependencies under `requirements.txt`, and then run `python3 rclone.py`. There are no command-line arguments; all configurations are loaded through Dynaconf.

For Docker runs, you should mount your settings file, use environmental variables, or specify an external source.