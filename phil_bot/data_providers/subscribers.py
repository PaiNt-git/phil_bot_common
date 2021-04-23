import datetime

from atools import memoize
from sqlalchemy.sql.expression import and_, or_

from phil_bot.data_providers._base0 import Session, TelegramSubscriber, TelegramMailing, TelegramMailingRel
from phil_bot.data_providers._utils import togudb_serializator, reconnect_decorator


@reconnect_decorator
def get_active_subscribers_count():
    session = Session()

    cur_date = datetime.date.today()

    subscribers = session.query(TelegramSubscriber)\
        .filter(TelegramSubscriber.active,
                TelegramSubscriber.actual_start_date <= cur_date, TelegramSubscriber.actual_end_date >= cur_date,
                )\
        .count()

    return subscribers


@memoize(duration=30)
@reconnect_decorator
def get_active_subscribers(limit=30, offset=0, mailing_id=None):
    session = Session()

    cur_date = datetime.date.today()

    subscribers = session.query(TelegramSubscriber)\
        .filter(TelegramSubscriber.active,
                TelegramSubscriber.actual_start_date <= cur_date, TelegramSubscriber.actual_end_date >= cur_date,
                )\
        .order_by(TelegramSubscriber.id.asc())

    if mailing_id:
        mailed_ids = session.query(TelegramMailingRel.subscriber_id)\
            .select_from(TelegramMailingRel).filter(TelegramMailingRel.mailing_id == mailing_id)\
            .subquery()

        subscribers = subscribers.filter(TelegramSubscriber.id.notin_(mailed_ids))

    subscribers = subscribers.limit(limit).offset(offset)

    results = map(lambda x: togudb_serializator(x, include=('id',
                                                            'name',
                                                            'entity_id',
                                                            'actual_start_date',
                                                            'actual_end_date',

                                                            )), subscribers)

    results = list(results)

    return results


@reconnect_decorator
def add_active_subscriber(chat_id, name=''):
    session = Session()

    cur_date = datetime.date.today()
    end_date = datetime.date.today() + datetime.timedelta(days=30)

    subscriber = session.query(TelegramSubscriber)\
        .filter(TelegramSubscriber.entity_id == str(chat_id))\
        .first()

    if not subscriber:
        subscriber = TelegramSubscriber()

    subscriber.active = True
    subscriber.actual_start_date = cur_date
    subscriber.actual_end_date = end_date
    subscriber.name = name
    subscriber.entity_id = str(chat_id)

    session.add(subscriber)
    session.flush()
    session.commit()

    return togudb_serializator(subscriber, include=('id',
                                                    'name',
                                                    'entity_id',
                                                    'actual_start_date',
                                                    'actual_end_date',
                                                    ))


@reconnect_decorator
def set_subscriber_notactive(chat_id):
    session = Session()

    result = session.query(TelegramSubscriber)\
        .filter(TelegramSubscriber.entity_id == str(chat_id))\
        .update({'active': False})  # synchronize_session=False

    session.flush()
    session.commit()

    return result


@reconnect_decorator
def delete_subscriber(chat_id):
    session = Session()

    result = session.query(TelegramSubscriber)\
        .filter(TelegramSubscriber.entity_id == str(chat_id))\
        .delete()  # synchronize_session=False

    session.flush()
    session.commit()

    return result


@memoize(duration=60)
def get_active_mailings_count():
    session = Session()

    cur_date = datetime.date.today()

    mailings = session.query(TelegramMailing)\
        .filter(TelegramMailing.active,
                TelegramMailing.actual_start_date <= cur_date, TelegramMailing.actual_end_date >= cur_date,
                )\
        .count()

    return mailings


@memoize(duration=60)
@reconnect_decorator
def get_active_mailings(limit=30, offset=0):
    session = Session()

    cur_date = datetime.date.today()

    mailings = session.query(TelegramMailing)\
        .filter(TelegramMailing.active,
                TelegramMailing.actual_start_date <= cur_date, TelegramMailing.actual_end_date >= cur_date,
                )\
        .order_by(TelegramMailing.id.asc()).limit(limit).offset(offset)

    results = map(lambda x: togudb_serializator(x, include=('id',
                                                            'name',
                                                            'text',
                                                            'actual_start_date',
                                                            'actual_end_date',

                                                            'is_pool',

                                                            'images_links',
                                                            'only_for_chats',

                                                            )), mailings)

    results = list(results)

    return results


@reconnect_decorator
def has_mailing_subscriber_id(mailing_id, subscriber_id):
    session = Session()

    mailing_rel = session.query(TelegramMailingRel)\
        .filter(TelegramMailingRel.mailing_id == mailing_id, TelegramMailingRel.subscriber_id == subscriber_id).first()

    return bool(mailing_rel)


@reconnect_decorator
def add_mailing_subscriber(mailing_id, chat_id, name=''):
    session = Session()

    has_mailing = False

    subscriber = add_active_subscriber(chat_id, name=name)

    mailing = session.query(TelegramMailing)\
        .filter(TelegramMailing.id == mailing_id)\
        .first()

    if mailing and subscriber:
        mailing_rel = session.query(TelegramMailingRel)\
            .filter(TelegramMailingRel.mailing_id == mailing_id, TelegramMailingRel.subscriber_id == subscriber['id']).first()

        if not mailing_rel:
            mailing_rel = TelegramMailingRel()
            mailing_rel.mailing_id = mailing_id
            mailing_rel.subscriber_id = subscriber['id']
            session.add(mailing_rel)
            session.flush()
            session.commit()

        has_mailing = True

    return has_mailing
