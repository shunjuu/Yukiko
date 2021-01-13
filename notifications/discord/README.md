# Discord Webhooks

##### Izumi V6 "Yukiko": Notifications Module - Discord Webhooks

This is a core unit of Izumi Version 6, known as "Yukiko". It handles fetching episode information and sending it to users by means of Discord webhooks. More endpoints may be added in the future, but it's also unlikely due to RabbitMQ support.

### Configuration

This module relies on Python's `Dynaconf` module to manage configurations. As such, it supports any endpoint that Dynaconf does, which you can configure in `config.py`.

Configuration Keys:

| Name                                    | Type      | Use                                                                                                 |
| --------------------------------------- | --------- | --------------------------------------------------------------------------------------------------- |
| RABBITMQ_HOST                           | str       | RabbitMQ host url                                                                                   |
| RABBITMQ_PORT                           | int       | RabbtMQ port                                                                                        |
| RABBITMQ_VHOST                          | str       | RabbitMQ virtual host                                                                               |
| RABBITMQ_USERNAME                       | str       | RabbitMQ username                                                                                   |
| RABBITMQ_PASSWORD                       | str       | RabbitMQ password                                                                                   |
| NOTIFICATIONS_DISCORD_WEBHOOK_QUEUE     | str       | AMQP queue                                                                                          |
| NOTIFICATIONS_DISCORD_WEBHOOK_ENDPOINTS | List[str] | Endpoints to send notifications to.                                                                 |
| AYUMI_EXCHANGE                          | str       | The logs exchange Ayumi will send all log outputs to.                                               |
| AYUMI_CONSOLE_FORMAT                    | str       | Message format (filename, functionname, etc) Ayumi will output in.                                  |
| AYUMI_DATE_FORMAT                       | str       | Format for how dates should appear in the log messages (passed to basicConfig(datefmt=DATE_FORMAT). |
| AYUMI_LOG_FORMAT                        | str       | Format for logs (passed to basicConfig(format=LOG_FORMAT)                                           |
| AYUMI_LOG_LEVEL                         | str       | Logging level. Can't be changed after startup.                                                      |

For `discord_webhook_endpoints` on Redis, endpoints should be a List of Strings formatted as string, for example: `"['url1', 'url2', 'etc...']"`.

### Building

You can build the application using the provided Dockerfile. Note that the build does not include any configuration files - you must load those as volumes, use environmental variables, or use external providers. Redis support is included in the build.

### Starting the Application

Install all dependencies under `requirements.txt`, and then run `python3 webhook.py`. There are no command-line arguments; all configurations are loaded through Dynaconf.

For Docker runs, you should mount your settings file, use environmental variables, or specify an external source.