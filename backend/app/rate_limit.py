from slowapi import Limiter
from slowapi.util import get_remote_address

# общий мягкий лимит на всё api + строгие на чувствительных эндпоинтах
limiter = Limiter(key_func=get_remote_address, default_limits=["300/minute"])
