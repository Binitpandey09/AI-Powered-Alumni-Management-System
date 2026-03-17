from decouple import config

environment = config('ENVIRONMENT', default='dev')

if environment == 'prod':
    from .prod import *
else:
    from .dev import *
