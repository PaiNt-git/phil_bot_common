import asyncio
import glob
import itertools
import json
import logging
import memcache
import os
import re
import sys
import time
import typing

from argparse import Namespace, _UNRECOGNIZED_ARGS_ATTR, ArgumentError,\
    ArgumentParser, SUPPRESS
from copy import copy
from importlib import import_module
from random import randint
from telethon import TelegramClient, events


# main logger
# logging.basicConfig(level=logging.DEBUG)
logging.getLogger('telethon').setLevel(level=logging.WARNING)

logger = logging.getLogger('phil_bot')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


# fuck python3
MAIN_PACKAGE_DIR = os.path.abspath(os.path.join(os.path.split(str(__file__))[0], '..'))
PACKAGE_NAME = os.path.basename(MAIN_PACKAGE_DIR)
sys.path.append(MAIN_PACKAGE_DIR)


# Settings
SETTINGS = {}
with open(os.path.normpath(os.path.join(os.path.split(str(__file__))[0], 'host.json')), 'r') as f:
    SETTINGS.update(json.load(f))

with open(os.path.normpath(os.path.join(os.path.split(str(__file__))[0], 'secrets', 'bot_cred.json')), 'r') as f:
    SETTINGS.update(json.load(f))

API_ID = SETTINGS.get('API_ID')
API_HASH = SETTINGS.get('API_HASH')
BOT_TOKEN = SETTINGS.get('BOT_TOKEN')
BOT_ID = int(BOT_TOKEN.split(':')[0])

HOST_NAME = SETTINGS.get('HOST_NAME')

# /Settings


COMMANDS = {}
TEXT_HANDLERS = {}
INLINE_HANDLERS = {}

_packages = itertools.chain(
    (('command_providers', os.path.basename(p)[:-3])
     for p in (
        glob.glob(os.path.join(os.path.dirname(__file__), 'command_providers', '*.py'))
    ) if os.path.isfile(p) and not os.path.basename(p).startswith('_')),

    (('texthandl_providers', os.path.basename(p)[:-3])
     for p in (
        glob.glob(os.path.join(os.path.dirname(__file__), 'texthandl_providers', '*.py'))
    ) if os.path.isfile(p) and not os.path.basename(p).startswith('_')),

    (('inlhandl_providers', os.path.basename(p)[:-3])
     for p in (
        glob.glob(os.path.join(os.path.dirname(__file__), 'inlhandl_providers', '*.py'))
    ) if os.path.isfile(p) and not os.path.basename(p).startswith('_'))

)


for type_, p in _packages:
    _import_string = f'{type_}.{p}'
    logger.info(_import_string)

    _modules = import_module(_import_string, 'phil_bot')
    _provider = getattr(_modules, p, None)
    _is_callable = hasattr(_provider, '__call__')

    if _is_callable:
        if type_ == 'command_providers':
            _args = getattr(_modules, 'COMMAND_ARGUMENTS', [])
            _input_sec_delay = getattr(_modules, 'EXPECT_INPUT_SEC', 0)
            _inline_callback = getattr(_modules, 'inline_callback', None)
            _input_sec_string = getattr(_modules, 'EXPECT_INPUT_STRING', 'Ожидаю ввода данных через сообщение...')
            _input_sec_buttons = getattr(_modules, 'EXPECT_INPUT_BUTTONS', [])
            if not len(_input_sec_buttons):
                _input_sec_buttons = None
            _input_sec_isvoice = getattr(_modules, 'EXPECT_INPUT_IS_VOICE', False)
            COMMANDS[p] = (_provider, _args, _input_sec_delay, _inline_callback, _input_sec_string, _input_sec_buttons, _input_sec_isvoice)
        elif type_ == 'texthandl_providers':
            _mess_regex_pattern = getattr(_modules, 'MESSAGE_PATTERN', None)
            _stop_propagate = getattr(_modules, 'STOP_PROPAGATE', None)
            TEXT_HANDLERS[p] = (_provider, _mess_regex_pattern, _stop_propagate)
        elif type_ == 'inlhandl_providers':
            _inline_regex_pattern = getattr(_modules, 'INLINE_PATTERN', None)
            _stop_propagate = getattr(_modules, 'STOP_PROPAGATE', None)
            INLINE_HANDLERS[p] = (_provider, _inline_regex_pattern, _stop_propagate)


mc = memcache.Client(['127.0.0.1:11211'], debug=0)

# ==============================================================
# ==============================================================
# ==============================================================
# ==============================================================


def _is_not_from_bot(e):
    """
    Фильтр не дающий боту обрабатывать сообщения от самого себя.
    Иначе бесконечный пинг понг.

    :param e: событие
    """
    message_sender_id = e._sender_id
    return message_sender_id != BOT_ID


def _is_event_handled(e, handler_key):
    """
    Чтобы поддерживать один обрабочик событие в одно время, нужно отметить что событие передано на исполнение.
    Эта функция исполняется вначале входа в каждый обработчик

    :param e: событие
    :param handler_key: суда передается ключ обработчика, обычно смысловое имя функции
    """
    time.sleep(round(randint(0, 2000) / 1000, 3))  # Эта энтропия нужна чтобы несколько запущенных инстансов этого ТОГУ-бота не синхронно обрабатывали события,
    # т.е. если бот запущен в ОС под pid=123 и pid=456 то эта энтропия не дает гарантии что всегда хватать сообщение будет только один первый процесс,
    # я дурачок и не придумал более лучшее решение проблемы конкурентности
    return bool(mc.get(f'phil_bot-handled-{e.chat_id}-{e._sender_id}-{e.id}-{handler_key}'))


def _set_event_handled(e, handler_key):
    """
    Чтобы поддерживать один обрабочик событие в одно время, нужно отметить что событие передано на исполнение.
    Эта функция исполняется вначале входа в каждый обработчик

    :param e: событие
    :param handler_key: суда передается ключ обработчика, обычно смысловое имя функции
    """
    mc.set(f'phil_bot-handled-{e.chat_id}-{e._sender_id}-{e.id}-{handler_key}', True, time=60)


def _asyn_com_constructor(locals_):
    """
    Это функция-конструктор для обрабочика команд. Команды инициализируются при создании инстанса PhilBot.
    И в момент этого учитывая mutable / ummutable  питон-особенности, создаются независимые
    инстансы функций и настроечные переменные внутри них.

    :param locals_: сюда при инициализации передаются locals() из метода внутри инстанса класса PhiBot
    """
    command = locals_['command']

    parser = ArgumentParser(prog=command)
    allow_args = COMMANDS[command][1]
    for arg in allow_args:
        name_or_flags = arg.pop('name or flags')
        if isinstance(name_or_flags, tuple):
            parser.add_argument(*name_or_flags, **arg)
        else:
            parser.add_argument(name_or_flags, **arg)

    def parser_callable(args_):
        """
        В командные обрабочики передастся эта функция, которая будет используя питоновский agparse
        парсить переданные аргументы.

        :param args_: аргументы после команды разделенные по признаку пробела,
                      agparse их соберет в соотвествии с командным синтаксисом
        """
        # make sure that args are mutable
        args_ = list(args_)

        # default Namespace built from parser defaults
        namespace = Namespace()

        # add any action defaults that aren't present
        for action in parser._actions:
            if action.dest is not SUPPRESS:
                if not hasattr(namespace, action.dest):
                    if action.default is not SUPPRESS:
                        setattr(namespace, action.dest, action.default)

        # add any parser defaults that aren't present
        for dest in parser._defaults:
            if not hasattr(namespace, dest):
                setattr(namespace, dest, parser._defaults[dest])

        # parse the arguments and exit if there are any errors
        try:
            namespace, args_ = parser._parse_known_args(args_, namespace)
            if hasattr(namespace, _UNRECOGNIZED_ARGS_ATTR):
                args_.extend(getattr(namespace, _UNRECOGNIZED_ARGS_ATTR))
                delattr(namespace, _UNRECOGNIZED_ARGS_ATTR)
            return namespace

        except ArgumentError:
            return None

    _input_sec_delay = COMMANDS[command][2]
    _inline_callback = COMMANDS[command][3]
    _input_sec_string = COMMANDS[command][4]
    _input_sec_buttons = COMMANDS[command][5]

    self_ = locals_['self']

    async def command_handler(event):
        """
        Инстанс обработчика команды (/somecommand) который
        динамически инициализируется из папки phil_bot\command_providers

        :param event: событие
        """
        if _is_event_handled(event, f'com-{command}'):
            return
        _set_event_handled(event, f'com-{command}')

        logger.debug(f"{event.chat_id} {event.chat} {event.message}")
        logger.info(f"=>command=/{command}... {event.id}")
        mc.set(f'{self_.unid}-{event.chat_id}-{event._sender_id}-{command}-init', True, time=(60 if not _input_sec_delay else _input_sec_delay))

        mes_args = event.pattern_match.group(1)
        mes_args = mes_args.split() if mes_args else []

        # Если в модуле обработчика присутсвует EXPECT_INPUT_SEC то команда будет ожидать ввода от пользователя
        # ввод может быть и голосовым сообщеним, если задано EXPECT_INPUT_IS_VOICE
        if _input_sec_delay:

            # EXPECT_INPUT_STRING - сообщение о ожидании ввода пользователю
            inp = await event.respond(_input_sec_string, buttons=_input_sec_buttons)

            # Ожидание EXPECT_INPUT_SEC должно быть кратно 5с, и тогда скрипт ввод более ранний обработает раньше,
            # т.е. EXPECT_INPUT_SEC посути максимальное время ожидания
            mc.set(f'{self_.unid}-{event.chat_id}-{event._sender_id}-{command}-expect', inp.id, time=40)
            for i in range(int(_input_sec_delay / 5)):
                await asyncio.sleep(5)
                input_expect = mc.get(f'{self_.unid}-{event.chat_id}-{event._sender_id}-{command}-expect')
                input_event_id = mc.get(f'{self_.unid}-{event.chat_id}-{event._sender_id}-{command}-input')
                if input_event_id and not input_expect:
                    break

            await self_._bot.delete_messages(inp.chat_id, [inp.id])

            # Если ввод был успешен - то мы запустим обработчик команды ч параметром mess_input
            input_event_id = mc.get(f'{self_.unid}-{event.chat_id}-{event._sender_id}-{command}-input')
            mc.set(f'{self_.unid}-{event.chat_id}-{event._sender_id}-{command}-run', True, time=60)
            await COMMANDS[command][0](event, mes_args, parser_callable, (input_event_id[1] if input_event_id else ''))
            mc.delete(f'{self_.unid}-{event.chat_id}-{event._sender_id}-{command}-run')
            mc.delete(f'{self_.unid}-{event.chat_id}-{event._sender_id}-{command}-input')

        else:
            await COMMANDS[command][0](event, mes_args, parser_callable)

        raise events.StopPropagation

    return command_handler


def _com_filter_func_constructor(locals_):
    """
    Конструктор функции фильтра для обработчика ожидающей ввода команды,
    если для команды был задан EXPECT_INPUT_SEC
    В мемкеше хранятся различные переменные "общей памяти", со сроком действия

    :param locals_: сюда при инициализации передаются locals() из метода внутри инстанса класса PhilBot
    """
    command = locals_['command']
    self_ = locals_['self']

    def filter_func(e):
        """
        Сама функция для фильтра,
        когда обрабатывать ввод (телеграм сообщение от пользователя) а когда нет

        :param e: событие
        """

        logger.debug(f"{e.chat_id} {e.chat} {e.message}")
        logger.info(f"=>command=/{command}... {e.id}")

        r = _is_not_from_bot(e)
        if r:
            has_command_request = mc.get(f'{self_.unid}-{e.chat_id}-{e._sender_id}-{command}-init')
            return bool(has_command_request)
        return False

    return filter_func


def _asyn_com_repl_constructor(locals_):
    """
    Конструктор обработчика ввода команды, если для команды был задан EXPECT_INPUT_SEC
    Обработчик может принять и голосовое сообщение если задано EXPECT_INPUT_IS_VOICE

    :param locals_: сюда при инициализации передаются locals() из метода внутри инстанса класса PhilBot
    """
    command = locals_['command']

    _input_sec_isvoice = COMMANDS[command][6]

    self_ = locals_['self']

    async def command_reply_handler(event):
        """
        Сама функция для обработки ввода (который команда ожидала)

        :param event: событие
        """
        if _is_event_handled(event, f'com-r-{command}'):
            return
        _set_event_handled(event, f'com-r-{command}')

        logger.debug(f"{event.chat_id} {event.chat} {event.message}")
        logger.info(f"=>command=/{command}... input... {event.id}")

        # Если не голос
        if not _input_sec_isvoice:
            mc.set(f'{self_.unid}-{event.chat_id}-{event._sender_id}-{command}-input', [event.id, event.message.message], time=20)

        else:  # Или голос
            if event.message.media \
                    and hasattr(event.message, 'voice') \
                    and event.message.voice:
                mess_id = event.message.id
                media_doc_id = event.message.voice.id

                mc.set(f'{self_.unid}-{event.chat_id}-{event._sender_id}-{command}-input', [event.id, (mess_id, media_doc_id)], time=40)

        inp_id = mc.get(f'{self_.unid}-{event.chat_id}-{event._sender_id}-{command}-expect')
        message_by_id = await self_._bot.get_messages(event.chat, ids=inp_id)
        mess = message_by_id.message
        await self_._bot.delete_messages(event.chat_id, [inp_id])
        await event.respond(mess)
        await event.reply(f'Принято.. Обработка..')

        mc.delete(f'{self_.unid}-{event.chat_id}-{event._sender_id}-{command}-expect')
        has_command_run = mc.get(f'{self_.unid}-{event.chat_id}-{event._sender_id}-{command}-run')
        if has_command_run:
            mc.delete(f'{self_.unid}-{event.chat_id}-{event._sender_id}-{command}-input')

    return command_reply_handler


def _asyn_com_inline_constructor(locals_):
    """
    Конструктор для обработчиков нажатия кнопочек в контексте той или иной команды.
    В выводе команды, или же в запросе для пользовтеля (EXPECT_INPUT_STRING, EXPECT_INPUT_BUTTONS)
    могут быть inline-кнопки, и их нажатия обработает эта функция.
    ожидается что ид кнопки начинается с b'<command>_' где <command> - итмя команды

    :param locals_: сюда при инициализации передаются locals() из метода внутри инстанса класса PhilBot
    """
    command = locals_['command']
    _inline_callback = locals_['_inline_callback']
    _unid = locals_['unid']

    async def inline_handler(event):
        """
        Сама функция для обработчик нажатий кнопок

        :param event: событие
        """
        if _is_event_handled(event, f'com-i-{command}'):
            return
        _set_event_handled(event, f'com-i-{command}')

        has_command_request = False
        r = _is_not_from_bot(event)
        if r:
            has_command_request = mc.get(f'{_unid}-{event.chat_id}-{event._sender_id}-{command}-init')

        if has_command_request:
            logger.debug(f"{event.chat_id} {event.chat} {event}")
            logger.info(f"=>command=/{command}... inline... {event.id}")

            await _inline_callback(event, unid=_unid)

    return inline_handler


def _asyn_text_constructor(locals_):
    """
    Конструктор обработчиков простого текста
    Они работают по регулярному выражению MESSAGE_PATTERN в модуле обработчика

    :param locals_: сюда при инициализации передаются locals() из метода внутри инстанса класса PhilBot
    """
    t_handler = locals_['t_handler']
    _stop_propagate = TEXT_HANDLERS[t_handler][2]

    async def mess_command_handler(event):
        """
        Сама функция для обработчик текста

        :param event: событие
        """
        if _is_event_handled(event, f'thandl-{t_handler}'):
            return
        _set_event_handled(event, f'thandl-{t_handler}')

        logger.debug(f"{event.chat_id} {event.chat} {event.message}")
        logger.info(f"=>text_handler={t_handler}... {event.id}")

        await TEXT_HANDLERS[t_handler][0](event)

        if _stop_propagate:
            raise events.StopPropagation

    return mess_command_handler


def _asyn_inline_constructor(locals_):
    """
    Конструктор обработчиков нажатий кнопок.
    Они работают по регулярному выражению INLINE_PATTERN в модуле обработчика

    :param locals_: сюда при инициализации передаются locals() из метода внутри инстанса класса PhilBot
    """
    i_handler = locals_['i_handler']
    _inline_stop_propagate = INLINE_HANDLERS[i_handler][2]

    async def inline_handler(event):
        """
        Сама функция для обработчик нажатий кнопок

        :param event: событие
        """
        if _is_event_handled(event, f'ihandl-{i_handler}'):
            return
        _set_event_handled(event, f'ihandl-{i_handler}')

        logger.debug(f"{event.chat_id} {event.chat} {event}")
        logger.info(f"=>inline_handler={i_handler}... {event.id}")

        await INLINE_HANDLERS[i_handler][0](event)

        if _inline_stop_propagate:
            raise events.StopPropagation

    return inline_handler


# ==============================================================
# ==============================================================
# ==============================================================
# ==============================================================


class PhilBot:
    """
    Класс Фил-бота.
    Каждый инстанс этого класса содержит бот соединенный к телеграму,
    с определенным набором доступных событий и команд.
    Можно инициализировать с ограниченным набором команд/обработчиков ввода.

    Каждый инстанс этого класса содержит свойство unid - которое уникально для хоста+процесса+инстанса на котором запущен бот.
    Т.е. с помощью этого идентификатора и memcache можно будет использовать общую память для балансировки или чего еще

        :param allow_commands: разрешенные команды
        :param disallow_commands: запрещенные команды
        :param allow_handlers: разрешенные текстовые обработчики
        :param disallow_handlers: запрещенные тектовые обработчики
        :param allow_inline_handlers: разрешенные обработчики нажатий кнопок
        :param disallow_inline_handlers: запрещенные обработчики нажатий кнопок

        остальные параметры **kwargs скармливаются telethon.TelegramClient

    """

    @property
    def label(self):
        n = getattr(self, '_label')
        return n

    @property
    def unid(self):
        """
        Свойство уникальное для процесса и инстанса класса
        """
        memid = id(self)
        pid = os.getpid()

        return f'{HOST_NAME}-{pid}-{memid}'

    def __init__(self: 'PhilBot', *args,
                 allow_commands: typing.Union[list, tuple] = COMMANDS.keys(),
                 disallow_commands: typing.Union[list, tuple] = [],
                 allow_handlers: typing.Union[list, tuple] = TEXT_HANDLERS.keys(),
                 disallow_handlers: typing.Union[list, tuple] = [],
                 allow_inline_handlers: typing.Union[list, tuple] = INLINE_HANDLERS.keys(),
                 disallow_inline_handlers: typing.Union[list, tuple] = [],
                 **kwargs):

        self._label = kwargs.pop('label') if 'label' in kwargs else 'bot-dispatcher'

        self._allow_commands = allow_commands
        self._disallow_commands = disallow_commands

        self._allow_text_handlers = allow_handlers
        self._disallow_text_handlers = disallow_handlers

        self._allow_inline_handlers = allow_inline_handlers
        self._disallow_inline_handlers = disallow_inline_handlers

        self._bot = TelegramClient(None, API_ID, API_HASH, **kwargs).start(bot_token=BOT_TOKEN)

        self.init_commands()
        self.init_text_handlers()
        self.init_inline_handlers()

        logger.info(self.unid)
        logger.info(self.label)

        print(self.unid)
        print(self.label)

    def run_until_disconnected(self):
        """
        Редирект на bot.run_until_disconnected()
        """
        self._bot.run_until_disconnected()

    def disconnect(self):
        """
        Редирект на bot.disconnect()
        """
        self._bot.disconnect()

    def init_commands(self, *args, **kwargs):
        """
        Инициализация команд из \command_providers
        """
        _allow_commands = [x for x in COMMANDS.keys() if x in self._allow_commands]
        _allow_commands = filter(lambda x: x not in self._disallow_commands, _allow_commands)
        unid = self.unid

        for command_ in _allow_commands:
            command = copy(command_)

            logger.info(f"init command handler: {command}...")

            compiled_pattern = re.compile('/' + command + '(.+)?')

            self._bot.add_event_handler(_asyn_com_constructor(copy(locals())), events.NewMessage(pattern=compiled_pattern, incoming=True, func=_is_not_from_bot))
            pass

            _input_sec_delay = COMMANDS[command][2]
            _input_sec_isvoice = COMMANDS[command][6]

            if _input_sec_delay:
                if not _input_sec_isvoice:
                    self._bot.add_event_handler(_asyn_com_repl_constructor(copy(locals())), events.NewMessage(pattern='^[^/]', incoming=True, func=_com_filter_func_constructor(copy(locals()))))
                    pass
                else:
                    self._bot.add_event_handler(_asyn_com_repl_constructor(copy(locals())), events.NewMessage(incoming=True, func=_com_filter_func_constructor(copy(locals()))))

            _inline_callback = COMMANDS[command][3]
            if _inline_callback:
                prefix = bytes(f'{command}', 'utf-8')
                compiled_inline_pattern = re.compile(prefix + b'_')

                self._bot.add_event_handler(_asyn_com_inline_constructor(copy(locals())), events.CallbackQuery(data=compiled_inline_pattern))
                pass

    def init_text_handlers(self, *args, **kwargs):
        """
        Инициализация обработчиков текста из \texthandl_providers
        """
        _allow_text_handlers = [x for x in TEXT_HANDLERS.keys() if x in self._allow_text_handlers]
        _allow_text_handlers = list(filter(lambda x: x not in self._disallow_text_handlers, _allow_text_handlers))
        _allow_text_handlers.sort(key=lambda x: x)

        for i, t_handler_ in enumerate(_allow_text_handlers):
            t_handler = copy(t_handler_)

            logger.info(f"init text handler: {t_handler}...")

            _mess_regex_pattern = TEXT_HANDLERS[t_handler][1]

            if _mess_regex_pattern:
                mess_compiled_pattern = re.compile(_mess_regex_pattern, flags=re.IGNORECASE)

                self._bot.add_event_handler(_asyn_text_constructor(copy(locals())), events.NewMessage(pattern=mess_compiled_pattern, incoming=True, func=_is_not_from_bot))
                pass

            else:

                self._bot.add_event_handler(_asyn_text_constructor(copy(locals())), events.NewMessage(incoming=True, func=_is_not_from_bot))
                pass

    def init_inline_handlers(self, *args, **kwargs):
        """
        Инициализация обработчиков нажатий кнопок из \inlhandl_providers
        """
        _allow_inline_handlers = [x for x in INLINE_HANDLERS.keys() if x in self._allow_inline_handlers]
        _allow_inline_handlers = list(filter(lambda x: x not in self._disallow_inline_handlers, _allow_inline_handlers))
        _allow_inline_handlers.sort(key=lambda x: x)

        for i, i_handler_ in enumerate(_allow_inline_handlers):
            i_handler = copy(i_handler_)

            logger.info(f"init inline handler: {i_handler}...")

            _inline_regex_pattern = INLINE_HANDLERS[i_handler][1]

            if _inline_regex_pattern:
                mcompiled_inline_pattern = re.compile(_inline_regex_pattern)

                self._bot.add_event_handler(_asyn_inline_constructor(copy(locals())), events.CallbackQuery(data=mcompiled_inline_pattern))
                pass

            else:
                self._bot.add_event_handler(_asyn_inline_constructor(copy(locals())), events.CallbackQuery())
                pass

    def __del__(self):
        self._bot.disconnect()


def main():
    bot = PhilBot()

    bot.run_until_disconnected()


if __name__ == '__main__':
    main()
