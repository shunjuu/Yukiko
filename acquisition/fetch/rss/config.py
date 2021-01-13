
from dynaconf import Dynaconf, Validator

settings = Dynaconf(
    environments=True,
    envvar_prefix="YUKIKO",
    env_switcher="YUKIKO_ENV",
    fresh_vars=[
        'RABBITMQ_USERNAME',
        'RABBITMQ_PASSWORD',
        'RABBITMQ_HOST',
        'RABBITMQ_PORT',
        'RABBITMQ_VHOST',
        'ACQUISITION_RSS_ACCEPTED_SHOWS',
        'ACQUISITION_RSS_EXCHANGE',
        'ACQUISITION_RSS_SLEEP_INTERVAL',
        'ACQUISITION_RSS_FEED_URL',
    ],
    load_dotenv=True,
    redis_enabled=True,
    settings_files=['settings.toml', '.secrets.toml'],
    vault_enabled=True,
    validators=[
        Validator('RABBITMQ_HOST', is_type_of=str, must_exist=True),
        Validator('RABBITMQ_PORT', is_type_of=int, must_exist=True),
        Validator('RABBITMQ_VHOST', is_type_of=str, must_exist=True),
        Validator('RABBITMQ_USERNAME', is_type_of=str, must_exist=True),
        Validator('RABBITMQ_PASSWORD', is_type_of=str, must_exist=True),        
        Validator('ACQUISITION_RSS_ACCEPTED_SHOWS', is_type_of=list, must_exist=True),
        Validator('ACQUISITION_RSS_FEED_URL', is_type_of=str, must_exist=True),
        Validator('ACQUISITION_RSS_EXCHANGE', is_type_of=str, must_exist=True),
        Validator('ACQUISITION_RSS_SLEEP_INTERVAL', is_type_of=int),
    ]
)

# `envvar_prefix` = export envvars with `export YUKIKO_FOO=bar`.
# `settings_files` = Load this files in the order.
