import datetime

import typing

from atools import memoize
from sqlalchemy.sql.expression import and_, or_

from phil_bot.data_providers._base0 import Session, TelegramNotification
from phil_bot.data_providers._utils import togudb_serializator, reconnect_decorator


@reconnect_decorator
def get_active_notifs_count(user_ids=[]):
    session = Session()

    cur_now = datetime.datetime.utcnow()

    notifs = session.query(TelegramNotification)\
        .filter(~TelegramNotification.sended,

                TelegramNotification.datetime_utc <= cur_now
                )

    if len(user_ids):
        notifs = notifs.filter(TelegramNotification.user_id.in_(user_ids))

    return notifs.count()


@reconnect_decorator
def get_active_notifs(user_ids=[], limit=30, offset=0):
    session = Session()

    cur_now = datetime.datetime.utcnow()

    notifs = session.query(TelegramNotification)\
        .filter(~TelegramNotification.sended,

                TelegramNotification.datetime_utc <= cur_now
                )

    if len(user_ids):
        notifs = notifs.filter(TelegramNotification.user_id.in_(user_ids))

    results = map(lambda x: togudb_serializator(x), notifs)

    results = list(results)

    return results


@reconnect_decorator
def mark_notif_sended(user_id, notif_id):
    session = Session()

    cur_now = datetime.datetime.utcnow()

    notif = session.query(TelegramNotification)\
        .filter(TelegramNotification.user_id == str(user_id), TelegramNotification.id == int(notif_id))\
        .first()

    if notif:
        notif.sended = True

        session.add(notif)
        session.flush()
        session.commit()

        return True

    return False


@reconnect_decorator
def delete_notif_sended():
    session = Session()

    notif = session.query(TelegramNotification)\
        .filter(TelegramNotification.sended)\
        .delete()  # synchronize_session=False

    session.flush()
    session.commit()
