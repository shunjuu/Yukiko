
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
        'NOTIFICATIONS_DISCORD_WEBHOOK_QUEUE',
        'NOTIFICATIONS_DISCORD_WEBHOOK_ENDPOINTS'
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
        Validator('NOTIFICATIONS_DISCORD_WEBHOOK_QUEUE', is_type_of=str, must_exist=True),
        Validator('NOTIFICATIONS_DISCORD_WEBHOOK_ENDPOINTS', is_type_of=list, must_exist=True),
    ]
)

# `envvar_prefix` = export envvars with `export YUKIKO_FOO=bar`.
# `settings_files` = Load this files in the order.
