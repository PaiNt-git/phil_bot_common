import os
import json

import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, column_property
from sqlalchemy.pool import NullPool
from sqlalchemy_utils.types.ts_vector import TSVectorType
from sqlalchemy_searchable import vectorizer
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import Integer, String, Unicode, UnicodeText
from sqlalchemy.dialects.postgresql.array import ARRAY
from sqlalchemy.dialects.postgresql.json import JSONB


SETTINGS = {}
with open(os.path.normpath(os.path.join(os.path.split(str(__file__))[0], '..', 'secrets', 'database.json')), 'r') as f:
    SETTINGS.update(json.load(f))


engine = create_engine(SETTINGS['DATABASE_URL_0'], poolclass=NullPool, pool_recycle=40, connect_args={'connect_timeout': 10})
Base = declarative_base()
Base.metadata.reflect(engine)
Session = scoped_session(sessionmaker(bind=engine, autocommit=False))


# ========


class TelegramSubscriber(Base):
    __table__ = Base.metadata.tables['telegram_subscriber']


class TelegramMailingRel(Base):
    __table__ = Base.metadata.tables['telegram_mailing_rel']


class TelegramMailing(Base):
    __table__ = Base.metadata.tables['telegram_mailing']


class TelegramNotification(Base):
    __table__ = Base.metadata.tables['telegram_notification']


class TelegramUserSettings(Base):
    __table__ = Base.metadata.tables['telegram_user_settings']


class TelegramBotLinkBase(Base):
    __tablename__ = 'telegram_bot_link_base'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)

    category = column_property(Column(String, nullable=True, index=True),
                               info={'verbose_name': 'Категория'})

    name = column_property(Column(Unicode, nullable=False),
                           info={'verbose_name': 'Наименование ссылки'})

    abstract = column_property(Column(UnicodeText, nullable=True),
                               info={'verbose_name': 'Контент-абстракт'})

    keywords = column_property(Column(ARRAY(String), nullable=True),
                               info={'verbose_name': 'Ключевые слова',
                                     })

    result = column_property(Column(JSONB, nullable=True),
                             info={'verbose_name': 'Результат, ссылка и т.д. (JSON)',
                                   })

    search_vector = sa.Column(
        TSVectorType('name', 'abstract', 'keywords',
                     weights={'abstract': 'A', 'keywords': 'B', 'name': 'C'},
                     regconfig='pg_catalog.russian',
                     )
    )


@vectorizer(TelegramBotLinkBase.keywords)
def keywords_vectorizer(column):
    return sa.cast(sa.func.array_to_string(column, ' '), sa.Text)
