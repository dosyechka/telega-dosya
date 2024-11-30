import random
import requests
import json
import time
import asyncio
import logging
import tempfile
import os
import dropbox
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from dropbox import Dropbox
from dropbox.exceptions import ApiError

# Устанавливаем базовое логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ID чата для отправки сообщений
LOG_CHAT_ID = -1002497223445  # Здесь указываем ID чата с логами

# Конфигурация приложения Dropbox
APP_KEY = os.getenv("DROPBOX_APP_KEY")
APP_SECRET = os.getenv("DROPBOX_APP_SECRET")
REFRESH_TOKEN = os.getenv("DROPBOX_REFRESH_TOKEN")

# Путь для хранения токена
TOKEN_FILE = 'dropbox_token.json'

def refresh_access_token():
    url = "https://api.dropbox.com/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN
    }

    response = requests.post(url, headers=headers, data=data, auth=(APP_KEY, APP_SECRET))

    if response.status_code == 200:
        access_token = response.json().get("access_token")
        return access_token
    else:
        raise Exception(f"Failed to refresh token: {response.status_code}, {response.text}")

# Пример использования
access_token = refresh_access_token()

# В дальнейшем используйте обновленный `access_token` для работы с Dropbox API

def get_new_access_token():
    url = "https://api.dropbox.com/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": APP_KEY,
        "client_secret": APP_SECRET
    }

    response = requests.post(url, headers=headers, data=data)

    if response.status_code == 200:
        token_data = response.json()
        token_data['expires_at'] = time.time() + token_data['expires_in']
        # Сохранение токена в файл
        with open(TOKEN_FILE, 'w') as token_file:
            json.dump(token_data, token_file)
        return token_data['access_token']
    else:
        print("Ошибка обновления токена:", response.json())
        return None

def get_access_token():
    try:
        with open(TOKEN_FILE, 'r') as token_file:
            token_data = json.load(token_file)
            if time.time() < token_data['expires_at']:
                return token_data['access_token']
            else:
                return get_new_access_token()
    except FileNotFoundError:
        return get_new_access_token()

# Использование токена в коде
ACCESS_TOKEN = get_access_token()
dbx = Dropbox(ACCESS_TOKEN)
print("Подключение к Dropbox установлено.")
print("Текущий токен доступа:", ACCESS_TOKEN)

def get_dropbox_temporary_link(file_path):
    global dbx
    """
    Получает временную ссылку на файл в Dropbox.
    :param file_path: Путь к файлу в Dropbox
    :return: Временная ссылка или None в случае ошибки
    """
    try:
        result = dbx.files_get_temporary_link(file_path)  # Возвращает один объект
        return result.link  # Извлекаем ссылку из объекта
    except ApiError as e:
        logger.error(f"Ошибка получения ссылки Dropbox для {file_path}: {e}")
        return None


# Функция обработки команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"Пользователь {user_id} запустил /start.")

    if context.user_data.get("has_started", False):
        logger.info(f"Пользователь {user_id} уже запускал /start ранее.")
        await update.message.reply_text("Бот обновлен")
        return

    context.user_data["has_started"] = True

    dropbox_file_path = "/Виктория Курсы Бот/IMG_1729.mp4"

    try:
        # Получаем временную ссылку на файл из Dropbox
        link = dbx.files_get_temporary_link(dropbox_file_path).link
        await update.message.reply_video(
            video=link,
            width=720,
            height=1280
        )
        logger.info(f"Видео {dropbox_file_path} успешно отправлено пользователю {user_id}.")
    except Exception as e:
        logger.error(f"Ошибка отправки видео {dropbox_file_path}: {e}")
        
    text = '''Привет! Рада тебя видеть ♥️✨

И сегодня ты бесплатно получишь:
🎁 Чек-лист с 500 идеями для Reels в любую нишу
🎁 1 самую простую воронку продаж, которую запустишь сразу же!

А еще в чек-листе тебя ждет кодовое слово, которое выдаст БЕСПЛАТНЫЙ УРОК ПО МОНТАЖУ того самого трендового видео со стикерами и wow-эффектом!

Жду тебя!'''

    keyboard = [
        [
            InlineKeyboardButton("Стратегии 50 Ниш", callback_data='strategies'),
            InlineKeyboardButton("Воронка", callback_data='funnel')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, reply_markup=reply_markup)
    logger.info(f"Приветственное сообщение отправлено пользователю {user_id}.")

    await asyncio.sleep(10)
    reminder_text = '''Напоминаю, что в чек-листе спрятано СЛОВО 🎁

Напиши его в Бот и забирай еще один подарок от меня! ✨

А также ты после бесплатного урока можешь скачать 6 уроков по съемке 😍
Которые научат тебя создавать контент где угодно с навыками профессионального фотографа!'''
    await update.message.reply_text(reminder_text)
    logger.info("Напоминание отправлено.")

async def send_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"Пользователь {user_id} запросил PDF файл.")

    dropbox_pdf_path = "/Виктория Курсы Бот/funnel.pdf"

    try:
        # Получаем временную ссылку на PDF файл из Dropbox
        link = dbx.files_get_temporary_link(dropbox_pdf_path).link
        await update.message.reply_document(
            document=link,
            filename="funnel.pdf"
        )
        logger.info(f"PDF {dropbox_pdf_path} успешно отправлен пользователю {user_id}.")
    except Exception as e:
        logger.error(f"Ошибка отправки PDF {dropbox_pdf_path}: {e}")


# Функция для обработки кодового слова
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text

    if 'Основной курс' in message_text:
        keyboard = [
            ["1-2 Урок"],
            ["3-4 Урок"],
            ["5-6 Урок"],
            ["Финальный Урок"],
            ["Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Выберите урок из основного курса:", reply_markup=reply_markup)
        logger.info(f"Пользователю {update.effective_user.id} предоставлены кнопки уроков для основного курса.")

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Определяем user_id из объекта update
    user_id = update.effective_user.id
    message_text = update.message.text
    logger.info(f"Пользователь {user_id} отправил сообщение: {message_text}")

    if 'Основной курс' in message_text:
        # Пример уже существующего кода
        keyboard = [
            ["1-2 Урок"],
            ["3-4 Урок"],
            ["5-6 Урок"],
            ["Финальный Урок"],
            ["Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Выберите урок из основного курса:", reply_markup=reply_markup)
        logger.info(f"Пользователю {update.effective_user.id} предоставлены кнопки уроков для основного курса.")

    elif 'Съемка' in message_text:
        # Новый блок для текста "Съемка"
        dropbox_video_paths = [
            "/Виктория Курсы Бот/Платные/Секция 2/1.mp4",
            "/Виктория Курсы Бот/Платные/Секция 2/2.mp4",
            "/Виктория Курсы Бот/Платные/Секция 2/3.mp4",
            "/Виктория Курсы Бот/Платные/Секция 2/4.mp4",
            "/Виктория Курсы Бот/Платные/Секция 2/5.mp4"
        ]

        for dropbox_path in dropbox_video_paths:
            try:
                # Получаем временную ссылку на файл из Dropbox
                temp_link = get_dropbox_temporary_link(dropbox_path)
                if temp_link:
                    # Отправляем файл через временную ссылку
                    await update.message.reply_document(temp_link, filename=os.path.basename(dropbox_path))
                    logger.info(f"Видео {dropbox_path} отправлено пользователю {update.effective_user.id} через Dropbox.")
                else:
                    await update.message.reply_text(f"Не удалось загрузить файл: {os.path.basename(dropbox_path)}")
            except Exception as e:
                logger.error(f"Ошибка отправки видео {dropbox_path}: {e}")
                await update.message.reply_text(f"Произошла ошибка при отправке файла: {os.path.basename(dropbox_path)}")


        # Отправка текста с домашним заданием
        homework_text = '''Домашнее задание :

Создай видео из референса с использованием:

• наложение
• шрифт
• кадры
• извлечь звук
• уменьшить шум
• ключи (ромбики)
• цветокоррекция

Домашнее задание жду в [личный чат](https://t.me/domanivi), где разберем ошибки или наоборот восхитимся твоей чудесной работой 🪄🤍'''
        await update.message.reply_text(homework_text, parse_mode="Markdown")
        logger.info(f"Пользователю {update.effective_user.id} отправлено сообщение с домашним заданием.")

    elif '1-2 Урок' in message_text:
        # Текст для урока "1-2 Урок"
        text = '''[ Памятка ] 

🎞️Настройки камеры : 
4к | 60 
HD | 60 
Экспозиция -0,7 

🎬Настройки киноэффекта : 
Глубина 2,8 (можно меньше -больше по вашей картинке и задумке)
Экспозиция - 1.0

📸 Настройки фото
Портрет 
Контурный свет 
Глубина 2,8 
Свет 30 
Экспозиция -0,7 / -1,3 (как 
сами видите)

Чтобы настройки не терялись каждый раз: 

Настройки - Камера - Сохранение настроек - [Режим камеры], [Творчество], [Управление глубиной], [Корректировка экспозиции], [Live photo] - это все должно быть зеленым!'''

        # Пути к видеофайлам
        dropbox_video_paths = [
            "/Виктория Курсы Бот/Платные/обработанное/1.mp4",
            "/Виктория Курсы Бот/Платные/обработанное/2.mp4"
        ]

            # Отправляем текст
        await update.message.reply_text(text)
        logger.info(f"Текст для урока '1-2 Урок' отправлен пользователю {user_id}.")

            # Отправляем видеофайлы
        for video_path in dropbox_video_paths:
            temp_link = dbx.files_get_temporary_link(video_path).link
            await update.message.reply_document(temp_link, filename=video_path.split("/")[-1])

        logger.info(f"Пользователю {update.effective_user.id} отправлены файлы для урока '5-6 Урок'.")

    elif '3-4 Урок' in message_text:
        # Текст для урока "3-4 Урок"
        text = '''[Оборудование]

• Штатив ~ легкий, с пультом , 3-4 ножки 
• Свет прямой 

Артикулы в видео, но вы выбирайте сами , тк я привела примеры 

Учитесь выбирать комфорт себе ! 🤍

Не смотрите на других или на меня, мне удобно работать со штативом на трех ножках, кому то удобно с тяжелым огромным для камеры !
при нажатии на 3 кнопку, 2 видео и текст 
[Свет] 
Выбирайте тот, который можно держать в руках и в комплекте со штативом (у вас все таки не 10 рук) 

Ставите свет на штатив и снимаете видео! 

(Кольцевая лампа не то же самое! Она не подойдет)'''

        # Пути к видеофайлам
        dropbox_video_paths = [
            "/Виктория Курсы Бот/Платные/обработанное/3.mp4",
            "/Виктория Курсы Бот/Платные/обработанное/4.mp4"
        ]

            # Отправляем текст
        await update.message.reply_text(text)
        logger.info(f"Текст для урока '3-4 Урок' отправлен пользователю {user_id}.")

            # Отправляем видеофайлы
        for video_path in dropbox_video_paths:
            temp_link = dbx.files_get_temporary_link(video_path).link
            await update.message.reply_document(temp_link, filename=video_path.split("/")[-1])

        logger.info(f"Пользователю {update.effective_user.id} отправлены файлы для урока '3-4 Урок'.")


    elif '5-6 Урок' in message_text:
        dropbox_video_paths = [
            "/Виктория Курсы Бот/Платные/обработанное/5.mp4",
            "/Виктория Курсы Бот/Платные/обработанное/6.mp4"
        ]

        for video_path in dropbox_video_paths:
            temp_link = dbx.files_get_temporary_link(video_path).link
            await update.message.reply_document(temp_link, filename=video_path.split("/")[-1])

        logger.info(f"Пользователю {update.effective_user.id} отправлены файлы для урока '5-6 Урок'.")


    elif 'Финальный Урок' in message_text:
        dropbox_path_7 = "/Виктория Курсы Бот/Платные/обработанное/7.mp4"
        temp_link = get_dropbox_temporary_link(dropbox_path_7)
        if temp_link:
            await update.message.reply_document(temp_link, filename="7.mp4")
            logger.info(f"Пользователю {update.effective_user.id} отправлены файлы для урока 'Финальный Урок' через Dropbox.")
        else:
             await update.message.reply_text("Не удалось загрузить видео. Попробуйте позже.")

    elif 'Продвижение' in message_text:
        # Ваш код для обработки кодового слова 'Продвижение'
        congratulations_text = '''Поздравляю! Ты добралась до второго БЕСПЛАТНОГО ПОДАРКА 🎁
    
        дорогая, он сложный! Пересмотри несколько раз и пробуй! Пробуй дома, в офисе снимай что угодно, даже кривляния.
    
        Главное — научись, и тогда сможешь создавать свои стратегии и генерировать идеи 💡
    
        Смотри скорее 👇🏻'''
        dropbox_video_path = "/Виктория Курсы Бот/dos.mp4"

        await update.message.reply_text(congratulations_text)
        try:
            temp_link = dbx.files_get_temporary_link(dropbox_video_path).link
            await update.message.reply_document(temp_link, filename="dos.mp4")
            logger.info(f"Пользователю {update.effective_user.id} отправлен второй подарок.")
        except ApiError as e:
            logger.error(f"Ошибка получения ссылки для подарка: {e}")
            await update.message.reply_text("Не удалось загрузить подарок. Попробуйте позже.")
            logger.info(f"Пользователю {update.effective_user.id} отправлен второй подарок.")

        # Задержка перед следующим сообщением
        await asyncio.sleep(10)
        additional_text = '''Ты уже узнала много всего 💡

И сейчас хочу тебя спросить…а если бы ты смогла научиться снимать себя везде на камеру , ты вела бы блог?

Ты можешь научиться снимать GRWM, видео в путешествиях, дома, в студии, где угодно!

А главное сама себя ! ✨😍

Имея только телефон и пару помощников рядом 
(не ожидая мужа или подругу)

• 5-6 уроков 
• 2 самые популярные стратегии Reels , которые актуальны и залетают на 1 🍋

Все это ты можешь открыть тут 👇🏻'''
        additional_keyboard = [[InlineKeyboardButton("✨Скачать тут✨", callback_data='show_info')]]
        await update.message.reply_text(additional_text, reply_markup=InlineKeyboardMarkup(additional_keyboard))
        

    elif 'Назад' in message_text:
        keyboard = [
            [InlineKeyboardButton("Основной курс", callback_data='main_course'), InlineKeyboardButton("Съемка", callback_data='shooting')]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Вы вернулись назад. Выберите одну из доступных опций:", reply_markup=reply_markup)
        logger.info(f"Пользователь {update.effective_user.id} вернулся на предыдущий уровень меню с кнопкой 'Основной курс' и 'Съемка'.")

    # Остальные блоки elif остаются без изменений


    # Остальные блоки elif остаются без изменений

    elif 'Продвижение' in message_text:
        # Ваш код для обработки кодового слова 'Продвижение'
        congratulations_text = '''Поздравляю! Ты добралась до второго БЕСПЛАТНОГО ПОДАРКА 🎁
        
        дорогая , он сложный ! Пересмотри несколько раз и пробуй! Пробуй дома, в офисе снимай что угодно, даже кривляния
        
        Главное научись и тогда сможешь создавать свои стратегии и генерировать идеи 💡
        
        Смотри скорее 👇🏻'''
        dropbox_video_path = "/Виктория Курсы Бот/dos.mp4"

        await update.message.reply_text(congratulations_text)
        link = dbx.files_get_temporary_link(dropbox_video_path).link
        await update.message.reply_document(document=link, filename="dos.mp4")

        logger.info(f"Пользователю {update.effective_user.id} отправлен второй подарок.")

        # Задержка перед следующим сообщением
        await asyncio.sleep(10)
        additional_text = '''Ты уже узнала много всего 💡

И сейчас хочу тебя спросить…а если бы ты смогла научиться снимать себя везде на камеру , ты вела бы блог?

Ты можешь научиться снимать GRWM, видео в путешествиях, дома, в студии, где угодно!

А главное сама себя ! ✨😍

Имея только телефон и пару помощников рядом 
(не ожидая мужа или подругу)

• 5-6 уроков 
• 2 самые популярные стратегии Reels , которые актуальны и залетают на 1 🍋

Все это ты можешь открыть тут 👇🏻'''
        additional_keyboard = [[InlineKeyboardButton("✨Скачать тут✨", callback_data='show_info')]]
        await update.message.reply_text(additional_text, reply_markup=InlineKeyboardMarkup(additional_keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    logger.info(f"Пользователь {user_id} нажал кнопку {query.data}.")

    if query.data == 'strategies':
        dropbox_pdf_path = "/Виктория Курсы Бот/Strategies 50 Niches.pdf"
        try:
            # Получаем временную ссылку на PDF файл из Dropbox
            link = dbx.files_get_temporary_link(dropbox_pdf_path).link
            await query.message.reply_document(
                document=link,
                filename="Strategies_50_Niches.pdf",
                caption="Стратегии 50 Ниш"
            )
            logger.info(f"PDF {dropbox_pdf_path} успешно отправлен пользователю {user_id}.")
        except Exception as e:
            logger.error(f"Ошибка отправки PDF {dropbox_pdf_path}: {e}")
    elif query.data == 'funnel':
        dropbox_pdf_path = "/Виктория Курсы Бот/Funnel.pdf"
        try:
            # Получаем временную ссылку на PDF файл из Dropbox
            link = dbx.files_get_temporary_link(dropbox_pdf_path).link
            await query.message.reply_document(
                document=link,
                caption="Воронка",
                filename="Funnel.pdf"
            )
            logger.info(f"PDF {dropbox_pdf_path} успешно отправлен пользователю {user_id}.")
        except Exception as e:
            logger.error(f"Ошибка отправки PDF {dropbox_pdf_path}: {e}")

    elif query.data == 'main_course':
        # Создаем кнопки для выбора уроков
        keyboard = [
            [
                InlineKeyboardButton("1-2 Урок", callback_data='lesson_1_2'),
                InlineKeyboardButton("3-4 Урок", callback_data='lesson_3_4'),
                InlineKeyboardButton("5-6 Урок", callback_data='lesson_5_6'),
                InlineKeyboardButton("Финальный Урок", callback_data='lesson_final')
            ],
            [InlineKeyboardButton("Назад", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Выберите урок из основного курса:", reply_markup=reply_markup)
        logger.info(f"Пользователь {user_id} выбрал основной курс.")

    elif query.data == 'show_info':
        payment_code = random.randint(100, 999)
        text_to_show = f'''💳 Выбран способ оплаты через карту. 💳

Сумма оплаты: 15 000 тенге. 

Kaspi (Казахстан): 4400430274692844
Forte (Международные кроме РФ): 5177920011179996

Код: {payment_code}

Укажите комментарий с кодом к переводу.'''
        
        keyboard = [[InlineKeyboardButton("Оплачено", callback_data=f'payment_{payment_code}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.reply_text(text_to_show, reply_markup=reply_markup)
        logger.info(f"Информация об оплате отправлена пользователю {user_id}. Код: {payment_code}.")
    elif query.data == 'back':
        # Кнопки на предыдущую фазу с кнопкой "Основной курс" и "Съемка"
        keyboard = [
            [InlineKeyboardButton("Основной курс", callback_data='main_course'), InlineKeyboardButton("Съемка", callback_data='shooting')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Вы вернулись назад. Выберите одну из доступных опций:", reply_markup=reply_markup)
        logger.info(f"Пользователь {user_id} вернулся на предыдущий уровень меню с кнопкой 'Основной курс' и 'Съемка'.")
    elif query.data == 'shooting':
    # Пути к видеофайлам на Dropbox
        dropbox_video_paths = [
            "/Виктория Курсы Бот/Платные/Секция 2/1.mp4",
            "/Виктория Курсы Бот/Платные/Секция 2/2.mp4",
            "/Виктория Курсы Бот/Платные/Секция 2/3.mp4",
            "/Виктория Курсы Бот/Платные/Секция 2/4.mp4",
            "/Виктория Курсы Бот/Платные/Секция 2/5.mp4"
        ]

    # Отправляем видео через Dropbox
    for dropbox_path in dropbox_video_paths:
        temp_link = get_dropbox_temporary_link(dropbox_path)
        if temp_link:
            await query.message.reply_document(temp_link, filename=os.path.basename(dropbox_path))
        else:
            await query.message.reply_text(f"Не удалось загрузить файл: {os.path.basename(dropbox_path)}")
    logger.info(f"Пользователю {user_id} отправлены файлы для 'Съемка' через Dropbox.")


async def confirm_reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith('payment_'):
        payment_code = data.split('_')[1]
        log_message = f'''💳 Детали платежа:
Пользователь ID: {user_id}
Код: {payment_code}
'''
        keyboard = [
            [
                InlineKeyboardButton("Успешно", callback_data=f"confirm_{payment_code}_{user_id}"),
                InlineKeyboardButton("Отклонить", callback_data=f"reject_{payment_code}_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем сообщение в лог-чат
        await context.bot.send_message(chat_id=LOG_CHAT_ID, text=log_message, reply_markup=reply_markup)
        logger.info(f"Детали платежа отправлены в лог-чат. Пользователь {user_id}, код {payment_code}.")


async def confirm_reject_payment_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # Проверяем структуру данных перед разбиением
    if len(data.split('_')) == 3:
        action, payment_code, user_id = data.split('_')
        user_id = int(user_id)  # Преобразуем в целое число, так как ID пользователя должен быть целым числом

        if action == "confirm":
            # Подтверждаем пользователя
            context.user_data["is_confirmed"] = True

            # Клавиатура с кнопкой основного курса
            keyboard = [
                [InlineKeyboardButton("Основной курс", callback_data='main_course')]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            # Отправляем сообщение с кнопкой "Основной курс"
            text = "Благодарю тебя ! Приступай к удобному обучению прямо здесь и начинай вести блог после курса ниже"
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup)
            logger.info(f"Пользователю {user_id} подтверждена оплата. Отправлена клавиатура с кнопкой основного курса.")

        elif action == "reject":
            # Уведомление об отклонении платежа
            await context.bot.send_message(
                chat_id=user_id,
                text="Платеж неуспешен!\nСвяжитесь с @ne_dosand для урегулирования проблемы."
            )
            logger.info(f"Платеж с кодом {payment_code} отклонен. Пользователю {user_id} отправлено уведомление об отклонении.")
    else:
        logger.error(f"Некорректный формат данных callback_data: {data}")
        # Отправляем предупреждение в лог-чат
        await context.bot.send_message(
            chat_id=LOG_CHAT_ID,
            text=f"Некорректный формат данных callback_data: {data}. Возможно, кнопка была создана до обновления формата данных."
        )

async def handle_lesson_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    logger.info(f"Пользователь {user_id} нажал на кнопку {query.data}.")

    if query.data == 'lesson_1_2':
        # Текст для урока "1-2 Урок"
        text = '''[ Памятка ] 

🎞️Настройки камеры : 
4к | 60 
HD | 60 
Экспозиция -0,7 

🎬Настройки киноэффекта : 
Глубина 2,8 (можно меньше -больше по вашей картинке и задумке)
Экспозиция - 1.0

📸 Настройки фото
Портрет 
Контурный свет 
Глубина 2,8 
Свет 30 
Экспозиция -0,7 / -1,3 (как 
сами видите)

Чтобы настройки не терялись каждый раз: 

Настройки - Камера - Сохранение настроек - [Режим камеры], [Творчество], [Управление глубиной], [Корректировка экспозиции], [Live photo] - это все должно быть зеленым!'''

        # Путь к видеофайлам в Dropbox
        dropbox_video_paths = [
            "/Виктория Курсы Бот/Платные/обработанное/1.mp4",
            "/Виктория Курсы Бот/Платные/обработанное/2.mp4"
        ]

        try:
            # Отправляем текст
            if query.message:
                await query.message.reply_text(text)
                logger.info(f"Текст для урока '1-2 Урок' отправлен пользователю {user_id}.")
            else:
                logger.error(f"query.message отсутствует для пользователя {user_id}.")

            # Отправляем видеофайлы
            for dropbox_path in dropbox_video_paths:
                try:
                    # Получаем временную ссылку
                    temp_link = get_dropbox_temporary_link(dropbox_path)
                    if temp_link:
                        await query.message.reply_document(temp_link, filename=os.path.basename(dropbox_path))
                        logger.info(f"Видео {dropbox_path} отправлено пользователю {user_id}.")
                    else:
                        logger.error(f"Не удалось получить ссылку на файл: {dropbox_path}")
                        await query.message.reply_text(f"Не удалось загрузить файл: {os.path.basename(dropbox_path)}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке видео {dropbox_path}: {e}")
                    await query.message.reply_text(f"Произошла ошибка при отправке файла: {os.path.basename(dropbox_path)}")
        except Exception as e:
            logger.error(f"Ошибка при отправке урока '1-2 Урок' пользователю {user_id}: {e}")

    elif query.data == 'lesson_3_4':
        # Текст для урока "3-4 Урок"
        text = '''[Оборудование]

• Штатив ~ легкий, с пультом , 3-4 ножки 
• Свет прямой 

Артикулы в видео, но вы выбирайте сами , тк я привела примеры 

Учитесь выбирать комфорт себе ! 🤍

Не смотрите на других или на меня, мне удобно работать со штативом на трех ножках, кому то удобно с тяжелым огромным для камеры !
при нажатии на 3 кнопку, 2 видео и текст 
[Свет] 
Выбирайте тот, который можно держать в руках и в комплекте со штативом (у вас все таки не 10 рук) 

Ставите свет на штатив и снимаете видео! 

(Кольцевая лампа не то же самое! Она не подойдет)'''

        # Путь к видеофайлам
        dropbox_video_paths = [
            "/Виктория Курсы Бот/Платные/обработанное/3.mp4",
            "/Виктория Курсы Бот/Платные/обработанное/4.mp4"
        ]

        try:
            # Отправляем текст
            await query.message.reply_text(text)
            logger.info(f"Текст для урока '3-4 Урок' отправлен пользователю {user_id}.")

            # Отправляем видеофайлы
            for dropbox_path in dropbox_video_paths:
                try:
                    temp_link = get_dropbox_temporary_link(dropbox_path)
                    if temp_link:
                        await query.message.reply_document(temp_link, filename=os.path.basename(dropbox_path))
                        logger.info(f"Видео {dropbox_path} отправлено пользователю {user_id}.")
                    else:
                        logger.error(f"Не удалось получить ссылку на файл: {dropbox_path}")
                        await query.message.reply_text(f"Не удалось загрузить файл: {os.path.basename(dropbox_path)}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке видео {dropbox_path}: {e}")
                    await query.message.reply_text(f"Произошла ошибка при отправке файла: {os.path.basename(dropbox_path)}")
        except Exception as e:
            logger.error(f"Ошибка при отправке урока '3-4 Урок' пользователю {user_id}: {e}")

    # Аналогично для других уроков...


    elif query.data == 'lesson_5_6':
        dropbox_video_paths = [
            "/Виктория Курсы Бот/Платные/обработанное/5.mp4",
            "/Виктория Курсы Бот/Платные/обработанное/6.mp4"
        ]

        for video_path in dropbox_video_paths:
            temp_link = dbx.files_get_temporary_link(video_path).link
            await query.message.reply_document(temp_link, filename=video_path.split("/")[-1])

        logger.info(f"Пользователю {user_id} отправлены файлы для '5-6 Урок'.")


    elif query.data == 'lesson_final':
        dropbox_path_7 = "/Виктория Курсы Бот/Платные/обработанное/7.mp4"
        temp_link = get_dropbox_temporary_link(dropbox_path_7)
        if temp_link:
            await query.message.reply_document(temp_link, filename="7.mp4")
            logger.info(f"Пользователю {user_id} отправлены файлы для 'Финальный Урок' через Dropbox.")
        else:
            await query.message.reply_text("Не удалось загрузить видео. Попробуйте позже.")

def main():
    application = Application.builder().token("7525962074:AAGHsMd8pCqO8MORcgeIs-eBuPvPP5oUajE").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback, pattern='^(strategies|funnel|main_course|show_info|back)$'))
    application.add_handler(CallbackQueryHandler(confirm_reject_payment, pattern='^payment_\\d+$'))
    application.add_handler(CallbackQueryHandler(confirm_reject_payment_action, pattern='^(confirm|reject)_\\d+_\\d+$'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    application.add_handler(CallbackQueryHandler(handle_lesson_buttons, pattern='^(lesson_1_2|lesson_3_4|lesson_5_6|lesson_final)$'))
    application.add_handler(CommandHandler("pdf", send_pdf))


    logger.info("Бот запущен и ожидает событий.")
    application.run_polling()

if __name__ == '__main__':
    main()
