
from dynaconf import Dynaconf, Validator

settings = Dynaconf(
    environments=False,
    envvar_prefix="YUKIKO",
    env_switcher="YUKIKO_ENV",
    fresh_vars=[
        'RABBITMQ_USERNAME',
        'RABBITMQ_PASSWORD',
        'RABBITMQ_HOST',
        'RABBITMQ_PORT',
        'RABBITMQ_VHOST',
        'RCLONE_CONFIG_FILE',
        'RCLONE_FLAGS',
        'KOTEN_RCLONE_UPLOAD',
        'KOTEN_SLEEP_INTERVAL',
        'KOTEN_CLEANUP',
        'KOTEN_EXCHANGE'
    ],
    load_dotenv=False,
    redis_enabled=False,
    settings_files=['settings.toml', '.secrets.toml'],
    vault_enabled=False,
    validators=[
        Validator('RABBITMQ_HOST', is_type_of=str, must_exist=True),
        Validator('RABBITMQ_PORT', is_type_of=int, must_exist=True),
        Validator('RABBITMQ_VHOST', is_type_of=str, must_exist=True),
        Validator('RABBITMQ_USERNAME', is_type_of=str, must_exist=True),
        Validator('RABBITMQ_PASSWORD', is_type_of=str, must_exist=True),        
        Validator('RCLONE_CONFIG_FILE', is_type_of=str, must_exist=True),
        Validator('RCLONE_FLAGS', is_type_of=str),
        Validator('KOTEN_WATCH_PATH', is_type_of=str),
        Validator('KOTEN_RCLONE_UPLOAD', is_type_of=list, must_exist=True),
        Validator('KOTEN_SLEEP_INTERVAL', is_type_of=int),
        Validator('KOTEN_CLEANUP', is_type_of=bool, must_exist=True),
        Validator('KOTEN_EXCHANGE', is_type_of=str, must_exist=True)
    ]
)

# `envvar_prefix` = export envvars with `export YUKIKO_FOO=bar`.
# `settings_files` = Load this files in the order.
