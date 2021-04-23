import time
import datetime
import logging

from collections import OrderedDict
from decimal import Decimal
from functools import wraps

from sqlalchemy.exc import StatementError
from sqlalchemy.orm.attributes import InstrumentedAttribute,\
    CollectionAttributeImpl, ScalarObjectAttributeImpl

from phil_bot.data_providers._base0 import engine, Session

logger = logging.getLogger('phil_bot')


# ========


def _normalize_scalars(value):
    if isinstance(value, Decimal):
        return float(value)

    elif isinstance(value, datetime.time):
        return '{:%H:%M}'.format(value)

    elif isinstance(value, datetime.date):
        return '{:%d.%m.%Y}'.format(value)

    elif isinstance(value, datetime.datetime):
        return value.isoformat()

    elif isinstance(value, (list, tuple)):
        return list(map(normalisator, value))

    elif isinstance(value, dict):
        return {k: normalisator(v_) for k, v_ in value.items()}

    elif isinstance(value, OrderedDict):
        return OrderedDict(((k, normalisator(v_)) for k, v_ in value.items()))

    return value


def normalisator(v):

    if isinstance(v, (list, tuple)):
        v = list(map(_normalize_scalars, v))

    elif isinstance(v, dict):
        v = {k: _normalize_scalars(v_) for k, v_ in v.items()}

    elif isinstance(v, OrderedDict):
        v = OrderedDict(((k, _normalize_scalars(v_)) for k, v_ in v.items()))

    else:
        v = _normalize_scalars(v)

    return v


def togudb_serializator(togudb_obj, include=None, exclude=None):
    """
    Сериализатор модельки sqlalchemy, в json запихаются все скалярные атрибуты

    :param togudb_obj: экземпляр модельки
    :param include: Список атрибутов для возврата
    :param exclude: Список атрибутов для исключения из возврата
    """

    attrs_keys = [key for key,
                  value in togudb_obj.__class__.__dict__.items()
                  if isinstance(value, InstrumentedAttribute) \
                  and not isinstance(value.impl, (ScalarObjectAttributeImpl, CollectionAttributeImpl))]

    _temp = OrderedDict()

    if include:
        attrs_keys = filter(lambda x: x in include, attrs_keys)

    if exclude:
        for exc in exclude:
            try:
                attrs_keys.remove(exc)
            except ValueError:
                pass

    for key in attrs_keys:
        try:
            v = getattr(togudb_obj, key)

            v = normalisator(v)

            _temp[key] = v
        except Exception:
            pass

    return _temp


def reconnect_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except StatementError:
            time.sleep(5)
            Session.close_all()
            engine.dispose()
            s = Session()
            return func(*args, **kwargs)

        except Exception as e:
            logger.debug(e)
            raise e

    return wrapper
