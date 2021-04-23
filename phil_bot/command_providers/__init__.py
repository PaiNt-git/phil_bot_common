'''
# Если задано то команда будет парсить аргументы после /command arg1 arg2 ...
# аргументы командной строки которые питон парсит с помощью argparse
COMMAND_ARGUMENTS = [

    {
        'name or flags': 'foo',
        #'action': 'store',
        'nargs': '?',
        #'const': '',
        #'default': 'foo',
        #'type': '',
        #'choices': '',
        #'required': False,
        #'help': 'foo of the %(prog)s program',
        #'metavar': '',
        #'dest': ' foo ',
    },


    {
        'name or flags': ('-b', '--bar'),
        #'action': 'store',
        'nargs': '+',
        #'const': '',
        #'default': '',
        #'type': '',
        #'choices': '',
        #'required': False,
        #'help': 'foo of the %(prog)s program',
        #'metavar': '',
        #'dest': ' foo ',
    },
]

#Если задано, то бот принимает сообщение в качестве ввода команды в течении этого времени, затем передаст его в обработчик
EXPECT_INPUT_SEC = 10

#Если EXPECT_INPUT_SEC задано, то бот принимает сообщение с таким сообщением для пользователя
EXPECT_INPUT_STRING = 'Ожидаю ввода данных...'

#Парралельно вводу можно буддет кликнуть кнопки (обрабочик их inline_callback - ниже)
EXPECT_INPUT_BUTTONS = []

# Ожидает голосовой ответ
EXPECT_INPUT_IS_VOICE = False


#Если в основном обработчике команды возвращаются кнопки то данный обработчик будет обрабавтывать их нажатие
async def inline_callback(event, unid=None):
    print('inline acepted')
    await event.edit('Thank you for clicking {}!'.format(event.data))

'''
