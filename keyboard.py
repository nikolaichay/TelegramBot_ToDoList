from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# b1 = KeyboardButton('/start')

# kb_Client = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
# kb_Client.add(b1)

def start_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Начать'))
    return kb

def get_main_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Добавить напоминание'), KeyboardButton('Редактировать текущие дела')) \
        .add(KeyboardButton('Посмотреть запланированные дела'), KeyboardButton('Посмотреть завершенные дела'))
    return kb


def get_file_kb() -> ReplyKeyboardMarkup:

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Файлы не требуются'))

    return kb


def get_what_to_change_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Описание'), KeyboardButton('Файлы')) \
        .add(KeyboardButton('Дата'), KeyboardButton('Время')) \
        .add(KeyboardButton('Отметить как выполненное'), KeyboardButton('Изменить периодичность')) \
        .add(KeyboardButton('Удалить напоминание'), KeyboardButton('Вернуться в главное меню'))

    return kb


def get_files_update_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Добавить новый'), KeyboardButton('Удалить имеющийся')) \
        .add(KeyboardButton('Вернуться в главное меню'))

    return kb


def get_done_tasks_kb() -> ReplyKeyboardMarkup:

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Вернуть дело в незавершенное'), KeyboardButton('Вернуться в главное меню'))

    return kb


def get_back_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Вернуться в главное меню'))

    return kb


def get_ikb_with_notifications(list_of_notifications: list) -> InlineKeyboardMarkup:
    ikb = InlineKeyboardMarkup(row_width=2)
    for i in range(len(list_of_notifications)):
        noty = list_of_notifications[i][1] + list_of_notifications[i][2] + list_of_notifications[i][3]
        ikb.add(InlineKeyboardButton(text=f'{noty}',
                                     callback_data=f'{list_of_notifications[i][0]}'))
    return ikb


def get_ikb_with_filenames(list_of_files: list) -> InlineKeyboardMarkup:
    ikb = InlineKeyboardMarkup(row_width=2)
    for i in range(len(list_of_files)):
        ikb.add(InlineKeyboardButton(text=f'{list_of_files[i]}',
                                     callback_data=f'{list_of_files[i]}'))
    return ikb