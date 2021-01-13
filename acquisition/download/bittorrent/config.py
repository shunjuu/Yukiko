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
        'ACQUISITION_BITTORRENT_EXCHANGE',
        'ACQUISITION_BITTORRENT_RCLONE_DEST',
        'ACQUISITION_BITTORRENT_QUEUE',
        'ACQUISITION_DOWNLOAD_BITTORRENT_SHOWS_MAP',
        'RCLONE_CONFIG_FILE',
        'RCLONE_FLAGS',
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
        Validator('ACQUISITION_BITTORRENT_EXCHANGE', is_type_of=str, must_exist=True),
        Validator('ACQUISITION_BITTORRENT_RCLONE_DEST', is_type_of=str, must_exist=True),
        Validator('ACQUISITION_BITTORRENT_QUEUE', is_type_of=str, must_exist=True),
        Validator('ACQUISITION_DOWNLOAD_BITTORRENT_SHOWS_MAP', is_type_of=list),
        Validator('RCLONE_CONFIG_FILE', is_type_of=str, must_exist=True),
        Validator('RCLONE_FLAGS', is_type_of=str),
    ]
)
