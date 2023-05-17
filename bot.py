import aiogram
from aiogram import Bot, types, Dispatcher
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher.filters import Text

from aiogram_calendar import simple_cal_callback, SimpleCalendar
from aiogram.types import Message, CallbackQuery

import datetime
from datetime import timedelta

import os 

import asyncio
import aioschedule

from keyboard import *
from sql_lite import *
from loader_file import create_folder_in_folder, is_exists, upload_file, get_list_of_files, \
    delete_files_from_google_disk


class CreateNotification(StatesGroup):
    """ Cостояния при создании"""
    description = State()
    calendar = State()
    time = State()
    file = State()

class EditNotification(StatesGroup):
    """ Состояния при редактировании """
    actual_tasks = State()
    done_tasks = State()
    what_to_change = State()
    description = State()
    calendar = State()
    time = State()
    file = State()
    periodic = State()


async def scheduler():
    aioschedule.every(1).minutes.do(notification_function)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


def add_days(date, add_type):
    date0 = datetime.datetime.strptime(str(date), "%d/%m/%Y").date()
    if add_type == 1:
        date = date0 + timedelta(days=1)
    if add_type == 2:
        date = date0 + timedelta(days=7)
    if add_type == 3:
        date = date0 + timedelta(days=30)


def check_time(date, project_time):
    if date:
        if '-' in date:
            date = date.replace('-', '/')
            date = date.split('/')
            date.reverse()
            date = '/'.join(date)
            date = str(date)

        d1 = datetime.datetime.strptime(date, "%d/%m/%Y").date()
        d2 = datetime.datetime.now().date()

        t1 = datetime.datetime.strptime(project_time, '%H:%M').time()

        current_date_time = datetime.datetime.now()
        t2 = current_date_time.time()

        if d2 > d1:
            return True
        elif d2 == d1 and t2 >= t1:
            return True
        else:
            return False


async def on_startup(_):
    await db_start()
    asyncio.create_task(scheduler())


TOKEN = '6186518701:AAFyuR22pM6P4gLV8Ym0jyOCd4Tqs-E2zao'

storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(bot,storage=storage)


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.answer("Нажми на кнопку", reply_markup=start_kb())


@dp.message_handler(Text(equals='Начать'))
async def cmd_start(message: types.Message):
    await message.answer("Это бот-помощник To-do List.",reply_markup=get_main_kb())
    await create_user_notifications_table(user_id=message.from_user.id)
    print ("Ok")


@dp.message_handler(Text(equals="Вернуться в главное меню"), state='*')
async def back_to_main_menu(message: types.Message, state: FSMContext):
    await message.answer("Вы вернулись в главное меню",
                        reply_markup=get_main_kb())
    await state.finish()


# Add notify


@dp.message_handler(Text(equals="Добавить напоминание"))
async def cmd_add_notify(message: types.Message) -> None:
    await message.answer("Введите текст напоминания",
                        reply_markup=get_back_kb())
    await CreateNotification.description.set()  


@dp.message_handler(content_types=['text'], state=CreateNotification.description)
async def load_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['description'] = message.text

    await message.answer("Теперь выберите дату: ",
                         reply_markup=await SimpleCalendar().start_calendar())  # клавиатура с календарем
    await CreateNotification.calendar.set()


@dp.callback_query_handler(simple_cal_callback.filter(), state=CreateNotification.calendar)
async def load_calendar(callback_query: CallbackQuery, callback_data: dict, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback_query, callback_data)
    async with state.proxy() as data_dict:
        data_dict['calendar'] = date.strftime("%d/%m/%Y")
    if selected:
        await callback_query.message.answer(
            f'Выбранная дата: {date.strftime("%d/%m/%Y")} \nТеперь введите время в формате HH:MM',
            reply_markup=get_back_kb()
        )
    await CreateNotification.time.set()
    await callback_query.message.delete()


@dp.message_handler(content_types=['text'], state=CreateNotification.time)
async def load_time(message: types.Message, state: FSMContext) -> None:
    async with state.proxy() as data:
        data['time'] = message.text

    if not check_time(data['calendar'], data['time']):
    #  добавляем запись в таблицу. Тогда устанавливается и номер в бд
        await add_notification_in_table(state, user_id=message.from_user.id)
        await message.answer(f'Время зафиксировано: {message.text} \n Теперь добавьте файлы', reply_markup=get_file_kb())
        await CreateNotification.file.set()
        await message.delete()
    else:
        await message.answer('Пожалуйста выберете будущие дату и время', reply_markup=await SimpleCalendar().start_calendar())
        await CreateNotification.calendar.set()
        await message.delete()


@dp.message_handler(Text(equals="Файлы не требуются"), state=CreateNotification.file)
async def load_no_file(message: types.Message, state: FSMContext) -> None:
    await message.answer('Напоминание создано!', reply_markup=get_main_kb())
    await state.finish()
    await message.delete()


# Load file


@dp.message_handler(content_types=types.ContentTypes.DOCUMENT, state=CreateNotification.file)
async def load_file(message: types.Message, state: FSMContext) -> None:
    if document := message.document:
        await document.download(
            destination_file=f"api_bot/{message.from_user.id}/{document.file_name}",
        )

    await bot.send_message(chat_id=message.from_user.id,
                           text='Загружаю файл')

    #  если еще ни разу не добавлялиь файлы, то создаем папку с id пользователя
    if not is_exists('api_bot', f'{message.from_user.id}'):
        create_folder_in_folder('api_bot', f'{message.from_user.id}')

    #  создаем папку с id НАПОМИНАНМЯ!
    this_notify = get_last_notification(message.from_user.id)
    create_folder_in_folder(f'{message.from_user.id}', f'{this_notify[0]}')

    if not is_exists(f'{this_notify[0]}', f'{document.file_name}'):
        upload_file(f'{message.from_user.id}', f'{this_notify[0]}', f'api_bot/{message.from_user.id}/{document.file_name}', f'{document.file_name}')

        #  удаляем файлы из локальной директории
        os.remove(f'api_bot/{message.from_user.id}/{document.file_name}')

        await bot.send_message(chat_id=message.from_user.id,
                               text='Файл загружен. Напоминание создано',
                               reply_markup=get_main_kb())
    else:
        await bot.send_message(chat_id=message.from_user.id,
                               text='Данный файл уже прикреплен к напоминанию. Напоминание создано',
                               reply_markup=get_main_kb())
    await state.finish()


# Looker


@dp.message_handler(Text(equals="Посмотреть запланированные дела"))
async def check_actual_tasks(message: types.Message) -> None:
    undone_tasks = ""
    tasks = get_undone_tasks(message.from_user.id)
    num = 1
    for task in tasks:
        undone_tasks += f"<b>{num}. {task[2]}</b> - <b>{task[3]}</b>\n {task[4]}\n"
        num = num + 1
    if num == 1:
        await bot.send_message(message.chat.id, 'Список дел пуст')
    else:
        await bot.send_message(message.chat.id, '<b>Ваши дела:</b>\n\n' + undone_tasks,
                               parse_mode=types.ParseMode.HTML)


@dp.message_handler(Text(equals="Посмотреть завершенные дела"))
async def check_actual_tasks(message: types.Message) -> None:
    done_tasks = ""
    tasks = get_done_tasks(message.from_user.id)
    num = 1
    for task in tasks:
        done_tasks += f"<b>{num}. {task[2]}</b> - <b>{task[3]}</b>\n {task[4]}\n"
        num = num + 1
    if num == 1:
        await bot.send_message(message.chat.id, 'Список выполненных дел пуст')
    else:
        await bot.send_message(message.chat.id, '<b> Завершенные дела:</b>\n\n' + done_tasks,
                               parse_mode=types.ParseMode.HTML, reply_markup=get_done_tasks_kb())


# Editor


@dp.message_handler(Text(equals="Редактировать текущие дела"))
async def check_actual_tasks(message: types.Message):
    undone_tasks = []
    tasks = get_undone_tasks(message.from_user.id)
    num = 1
    for task in tasks:
        undone_tasks.append([f"{task[0]}", f"{task[3]}, ", f"{task[4]}, ", f"{task[2]}"])
        num = num + 1
    if num == 1:
        await bot.send_message(message.chat.id, 'Список дел пуст')
    else:
        await EditNotification.actual_tasks.set()
        await bot.send_message(message.chat.id, '<b>Какое из дел вы хотите отредактировать?</b>',
                               parse_mode=types.ParseMode.HTML,
                               reply_markup=get_ikb_with_notifications(undone_tasks))


@dp.callback_query_handler(state=EditNotification.actual_tasks)
async def callback_check_actual_tasks(callback: types.CallbackQuery, state: FSMContext):
    notification_number = callback.data  # Это номер нужной нам строки в таблице
    notify = get_task_by_number(callback.from_user.id, notification_number)
    #  записываем номер выбранного пользователем сообщение (номер = id в бд)
    async with state.proxy() as data:
        data['notification_number'] = notification_number

    await callback.message.answer(f'Вы изменяете напоминание:\n{notify[3]}, {notify[4]}, {notify[2]}\nЧто именно вы ходите изменить?',
                                  reply_markup=get_what_to_change_kb())
    await EditNotification.what_to_change.set()
    await callback.answer(f'{notification_number}')
    await callback.message.delete()


#  обновляем описание
@dp.message_handler(Text(equals="Описание"), state=EditNotification.what_to_change)
async def update_description(message: types.Message) -> None:
    await message.reply("Введите новое описание для напоминания",
                        reply_markup=get_back_kb())
    await EditNotification.description.set()  # установили состояние описания


@dp.message_handler(content_types=['text'], state=EditNotification.description)
async def save_update_description(message: types.Message, state: FSMContext) -> None:
    await update_notification_field(state, user_id=message.from_user.id, field_data=message.text,
                                    field_name='description')
    #  после обновления напоминания его надо будет отправить еще раз
    await update_notification_field(state, user_id=message.from_user.id, field_data=0, field_name='is_Sent')
    await message.reply("Новое описание успешно сохранено",
                        reply_markup=get_main_kb())
    await state.finish()


#  обновляем периодичность
@dp.message_handler(Text(equals="Изменить периодичность"), state=EditNotification.what_to_change)
async def update_periodic(message: types.Message) -> None:
    await message.reply("Введите тип периодичности:\n"
                        "0 - дело не периодично\n"
                        "1 - повтор каждый день\n"
                        "2 - повтор каждую неделю\n"
                        "3 - повтор каждый месяц",
                        reply_markup=get_back_kb())
    await EditNotification.periodic.set()  # установили состояние описания


@dp.message_handler(content_types=['text'], state=EditNotification.periodic)
async def save_update_periodic(message: types.Message, state: FSMContext) -> None:
    await update_notification_field(state, user_id=message.from_user.id, field_data=int(message.text),
                                    field_name='period_type')
    #  после обновления напоминания его надо будет отправить еще раз
    await update_notification_field(state, user_id=message.from_user.id, field_data=0, field_name='is_Sent')
    await message.reply("Периодичность обновлена",
                        reply_markup=get_main_kb())
    await state.finish()


#  обновляем календарную дату
@dp.message_handler(Text(equals="Дата"), state=EditNotification.what_to_change)
async def update_description(message: types.Message) -> None:
    await message.reply("Введите новую дату для напоминания",
                        reply_markup=await SimpleCalendar().start_calendar())
    await EditNotification.calendar.set()  # установили состояние описания


#  callback календаря!
@dp.callback_query_handler(simple_cal_callback.filter(), state=EditNotification.calendar)
async def save_update_calendar(callback_query: CallbackQuery, callback_data: dict, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback_query, callback_data)
    new_date = date.strftime("%d/%m/%Y")
    if selected:
        if not check_time(new_date, '23:59'):
            await update_notification_field(state, user_id=callback_query.from_user.id, field_data=new_date,
                                            field_name='calendar')
            #  после обновления напоминания его надо будет отправить еще раз
            await update_notification_field(state, user_id=callback_query.from_user.id, field_data=0, field_name='is_Sent')
            await callback_query.message.answer(
                f'Вы изменили дату: {date.strftime("%d/%m/%Y")}',
                reply_markup=get_main_kb()
            )
        else:
            await callback_query.message.answer(
                'Нельзя выставить прошедшую дату',
                reply_markup=get_main_kb()
            )
    await state.finish()


#  обновляем время
@dp.message_handler(Text(equals="Время"), state=EditNotification.what_to_change)
async def update_time(message: types.Message) -> None:
    await message.reply("Введите новое время для напоминания",
                        reply_markup=get_back_kb())
    await EditNotification.time.set()


#  отмечаем как выполненное
@dp.message_handler(Text(equals="Отметить как выполненное"), state=EditNotification.what_to_change)
async def update_is_Done(message: types.Message, state: FSMContext) -> None:
    await update_notification_field(state, user_id=message.from_user.id, field_data=1, field_name='is_Done')
    #  сделанные дела, даже если их время и не пришло, отправлять уже не нужно
    await update_notification_field(state, user_id=message.from_user.id, field_data=1, field_name='is_Sent')
    await message.reply("Задача выполнена",
                        reply_markup=get_main_kb())
    await state.finish()


#  удаляем напоминание
@dp.message_handler(Text(equals="Удалить напоминание"), state=EditNotification.what_to_change)
async def back_to_main_menu(message: types.Message, state: FSMContext) -> None:
    await delete_notification_field(state, user_id=message.from_user.id)
    await message.reply("Вы удалили напоминание",
                        reply_markup=get_main_kb())
    await state.finish()


#  редактор файлов
@dp.message_handler(Text(equals="Файлы"), state=EditNotification.what_to_change)
async def update_files(message: types.Message) -> None:
    await message.reply("Что вы хотеите сделать с файлами?",
                        reply_markup=get_files_update_kb())
    await EditNotification.file.set()


@dp.message_handler(Text(equals="Добавить новый"), state=EditNotification.file)
async def update_files_new(message: types.Message) -> None:
    await message.reply("Добавьте файл",
                        reply_markup=get_main_kb())
    await EditNotification.file.set()


@dp.message_handler(content_types=types.ContentTypes.DOCUMENT, state=EditNotification.file)
async def update_files_new(message: types.Message, state: FSMContext) -> None:
    if document := message.document:
        await document.download(
            destination_file=f"api_bot/{message.from_user.id}/{document.file_name}",
        )

    await bot.send_message(chat_id=message.from_user.id,
                           text='Загружаю файл...')

    #  если еще ни разу не добавлялиь файлы, то создаем папку с id пользователя
    if not is_exists('api_bot', f'{message.from_user.id}'):
        create_folder_in_folder('api_bot', f'{message.from_user.id}')

    async with state.proxy() as data:
        notification_number = data['notification_number']

    if not is_exists(f'{message.from_user.id}', f'{notification_number}'):
        create_folder_in_folder(f'{message.from_user.id}', f'{notification_number}')

    if not is_exists(f'{notification_number}', f'{document.file_name}'):
        upload_file(f'{message.from_user.id}', f'{notification_number}',
                    f'api_bot/{message.from_user.id}/{document.file_name}', f'{document.file_name}')

        #  удаляем файлы из локальной директории
        os.remove(f'api_bot/{message.from_user.id}/{document.file_name}')

        await bot.send_message(chat_id=message.from_user.id,
                               text='Успешно! Файл загружен',
                               reply_markup=get_main_kb())

    else:
        await bot.send_message(chat_id=message.from_user.id,
                               text='Данный файл уже прикреплен к напоминанию',
                               reply_markup=get_main_kb())
    await state.finish()


@dp.message_handler(Text(equals="Удалить имеющийся"), state=EditNotification.file)
async def update_files_delete(message: types.Message, state: FSMContext) -> None:
    async with state.proxy() as data:
        notification_number = data['notification_number']
    await bot.send_message(message.from_user.id, 'Подгружаем файлы')
    list_of_files = get_list_of_files(message.from_user.id, notification_number)
    if len(list_of_files) != 0:
        await message.reply("Выберите, какой файл вы хотите удалить",
                            reply_markup=get_ikb_with_filenames(list_of_files))
        await EditNotification.file.set()
    else:
        await message.reply("К задаче не прикреплено ни одного файла",
                            reply_markup=get_main_kb())
        await state.finish()


@dp.callback_query_handler(state=EditNotification.file)
async def delete_files_from_disk(callback: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        notification_number = data['notification_number']
    await bot.send_message(chat_id=callback.from_user.id, text='Удаляем файл')

    delete_files_from_google_disk(f'{callback.from_user.id}', f'{notification_number}', f'{callback.data}')
    await bot.send_message(chat_id=callback.from_user.id, text='Файл успено удалён!', reply_markup=get_main_kb())
    await state.finish()


# Editor completed task


@dp.message_handler(Text(equals="Вернуть дело в незавершенное"))
async def check_done_tasks(message: types.Message) -> None:
    done_tasks = []
    tasks = get_done_tasks(message.from_user.id)
    num = 1
    for task in tasks:
        done_tasks.append([f"{task[0]}", f"{task[3]}, ", f"{task[4]}, ", f"{task[2]}"])
        num = num + 1
    if num == 1:
        await bot.send_message(message.chat.id, 'Список выполненных дел пуст')
    else:
        await bot.send_message(message.chat.id, '<b>Какое из выполненных дел вы хотите вернуть?</b>',
                               parse_mode=types.ParseMode.HTML,
                               reply_markup=get_ikb_with_notifications(done_tasks))
    await EditNotification.done_tasks.set()


@dp.callback_query_handler(state=EditNotification.done_tasks)
async def callback_check_done_tasks(callback: types.CallbackQuery, state: FSMContext):
    notification_number = callback.data  # Это номер нужной нам строки в таблице
    notify = get_task_by_number(callback.from_user.id, notification_number)
    #  записываем номер выбранного пользователем сообщение (номер = id в бд)
    async with state.proxy() as data:
        data['notification_number'] = notification_number
    await update_notification_field(state, user_id=callback.from_user.id, field_data=0, field_name='is_Done')
    #  вернули дело в невыполненные => его еще предстоит отправить
    await update_notification_field(state, user_id=callback.from_user.id, field_data=0, field_name='is_Sent')
    await callback.message.answer(f'Вы изменяете напоминание:\n{notify}\nКакую дату необходимо поставить??',
                                  reply_markup=await SimpleCalendar().start_calendar())
    await EditNotification.calendar.set()
    await callback.answer(f'{notification_number}')


@dp.message_handler(content_types=['text'], state=EditNotification.time)
async def save_update_time(message: types.Message, state: FSMContext) -> None:
    await update_notification_field(state, user_id=message.from_user.id, field_data=message.text, field_name='time')
    #  после обновления напоминания его надо будет отправить еще раз
    await update_notification_field(state, user_id=message.from_user.id, field_data=0, field_name='is_Sent')
    await message.reply("Новое время успешно сохранено",
                        reply_markup=get_main_kb())
    await state.finish()


# Sending notifications

@dp.message_handler()
async def notification_function():
    # выгружаем все задания, которые находятся в статусе "текущие"
    users = get_used_ids()
    for user_id in users:
        user_id = list(user_id)[0]
        tasks = get_unsent_tasks(user_id)
        for task in tasks:
            # проверяем не наступила ли дата и время уведомления.
            if check_time(task[3], task[4]):
                # если наступило - отправляем уведомление
                #  выгружаем файлы
                await bot.send_message(chat_id=user_id, text=f"Напоминание\n {task[2]}")
                # titles = get_list_of_files(f'{user_id}', f'{task[0]}')

                

                # for i in range(len(titles)):
                #     await bot.send_document(user_id, (f'{titles[i]}', f'api_bot/{user_id}/{titles[i]}'))
                #     os.remove(f'api_bot/{user_id}/{titles[i]}')  # удаляем из локальной директории

                # флажок, проверка на "периодичность дела"
                if task[6] == 0:
                    # если дело не переодическое то заменяем стус "в ожидании" на "отправлено"
                    await update_notification_field_by_number(number=task[0], user_id=user_id, field_data=1,
                                                              field_name='is_Sent')
                else:
                    # вычисляем новую дату для уведомления у периодических дел
                    new_date = add_days(task[3], task[6])
                    await update_notification_field_by_number(number=task[0], user_id=user_id, field_data=new_date,
                                                              field_name='calendar')



if __name__ == '__main__':
    executor.start_polling(dp,
                           skip_updates=True,
                           on_startup=on_startup)
