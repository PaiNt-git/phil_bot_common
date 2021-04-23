import datetime

from atools import memoize
from sqlalchemy.sql.expression import and_, or_
from sqlalchemy_searchable import search

from phil_bot.data_providers._base0 import Session, TelegramBotLinkBase
from phil_bot.data_providers._utils import togudb_serializator, reconnect_decorator
from phil_bot.data_providers.user_settings import get_user_settings, set_user_settings, delete_user_param


@reconnect_decorator
def add_entry(category, name, result, abstract=None, keywords=None):
    session = Session()
    has_entry = session.query(TelegramBotLinkBase).filter(
        TelegramBotLinkBase.category == category,
        TelegramBotLinkBase.name == name,
        TelegramBotLinkBase.result == result,
    )
    if abstract:
        has_entry = has_entry.filter(TelegramBotLinkBase.abstract == abstract)

    has_entry = has_entry.first()

    if not has_entry:
        has_entry = TelegramBotLinkBase(category=category,
                                        name=name,
                                        abstract=abstract,
                                        keywords=keywords,
                                        result=result
                                        )
    else:
        keywords = list(set(has_entry.keywords)) if keywords else None
        keywords.extend(keywords) if keywords and len(keywords) else None
        abstract_ = abstract if abstract else has_entry.abstract

        has_entry.keywords = keywords
        has_entry.abstract = abstract_

    if not has_entry.abstract and not abstract:
        has_entry.abstract = abstract

    session.add(has_entry)
    session.flush()
    session.commit()

    return True


@reconnect_decorator
def set_entry(entry_id, category=None, name=None, result=None, abstract=None, keywords=None):
    session = Session()
    has_entry = session.query(TelegramBotLinkBase).filter(
        TelegramBotLinkBase.id == entry_id,
    )
    has_entry = has_entry.first()
    if not has_entry:
        return False

    if category:
        has_entry.category = category

    if name:
        has_entry.name = name

    if result:
        has_entry.result = result

    if abstract:
        has_entry.abstract = abstract

    if keywords:
        has_entry.keywords = keywords

    session.add(has_entry)
    session.flush()
    session.commit()

    return True


@reconnect_decorator
def search_entries(term, category=None, sort=False):
    session = Session()

    query = session.query(TelegramBotLinkBase)
    if category:
        query = query.filter(TelegramBotLinkBase.category == category)

    query = search(query, term, sort=sort)

    results = map(lambda x: togudb_serializator(x, include=('id',
                                                            'category',
                                                            'name',
                                                            'abstract',
                                                            'keywords',
                                                            'result',
                                                            )), query)

    results = list(results)

    return results


@reconnect_decorator
def get_entry(entry_id):
    session = Session()

    tbl = session.query(TelegramBotLinkBase).filter(TelegramBotLinkBase.id == entry_id).first()

    return togudb_serializator(tbl, include=('id',
                                             'category',
                                             'name',
                                             'abstract',
                                             'keywords',
                                             'result',
                                             ))
