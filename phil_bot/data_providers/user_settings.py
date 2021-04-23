import datetime

from atools import memoize
from sqlalchemy.sql.expression import and_, or_

from phil_bot.data_providers._base0 import Session, TelegramUserSettings
from phil_bot.data_providers._utils import togudb_serializator, reconnect_decorator


@reconnect_decorator
def set_user_settings(user_id, update_params={}, username='', ):
    session = Session()

    setting_ = session.query(TelegramUserSettings)\
        .filter(TelegramUserSettings.entity_id == str(user_id))\
        .first()

    if not setting_:
        setting_ = TelegramUserSettings()
        setting_.params = {}

    params = {k: v for k, v in setting_.params.items()}
    if not params:
        params = {}

    setting_.active = True
    setting_.name = username
    setting_.entity_id = str(user_id)
    params.update(update_params)
    setting_.params = params
    session.add(setting_)
    session.flush()
    session.commit()

    return togudb_serializator(setting_, include=('id',
                                                  'name',
                                                  'entity_id',
                                                  'params',
                                                  ))


@reconnect_decorator
def delete_user_param(user_id, key):
    session = Session()

    setting_ = session.query(TelegramUserSettings)\
        .filter(TelegramUserSettings.entity_id == str(user_id))\
        .first()

    if setting_:
        params = {k: v for k, v in setting_.params.items()}
        if not params:
            params = {}

        if key in params:
            par = params.pop(key)

        if not len(params):
            params = None

        setting_.params = params
        session.add(setting_)
        session.flush()
        session.commit()

    return True


@reconnect_decorator
def delete_user_settings(user_id):
    session = Session()

    result = session.query(TelegramUserSettings)\
        .filter(TelegramUserSettings.entity_id == str(user_id))\
        .delete()  # synchronize_session=False

    session.flush()
    session.commit()

    return result


@reconnect_decorator
def get_users_settings(user_ids):
    user_ids = list(map(str, user_ids))
    session = Session()
    if not user_ids or not len(user_ids):
        return []

    settings_ = session.query(TelegramUserSettings)\
        .filter(TelegramUserSettings.entity_id.in_(user_ids))\
        .all()

    if not len(settings_):
        return []

    results = map(lambda x: togudb_serializator(x, include=('id',
                                                            'name',
                                                            'entity_id',
                                                            'params',
                                                            )), settings_)

    results = list(results)

    return results


def get_user_settings(user_id):
    r = get_users_settings([user_id])
    if len(r):
        return r[0]

    return None
