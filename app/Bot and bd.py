
import psycopg2
import telebot
from telebot import types
import json
from Parser_hh_ru import collect_vacancies, collect_resumes

# Инициализация телеграмм бота
bot_token = "7053754743:AAHjXIYUkGUMVRLlPy9Nz_moMsSBG0obHgk"
bot = telebot.TeleBot(bot_token)

# Настройка базы данных PostgreSQL
db_config = {
    "database": "parser",
    "user": "postgres",
    "password": "12345",
    "host": "localhost",
    "port": "5432",
}

# Соединение с базой данных
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

# Константы для фильтров
sites = ("hh.ru",)
data_types = ("вакансии", "резюме")
experience_levels = ("не имеет значения", "от 1 года до 3 лет", "нет опыта")
education_vacancies = ("не имеет значения", "не требуется или не указано", "высшее", "среднее профессиональное")
education_resumes = ("не имеет значения", "среднее", "среднее специальное", "незаконченное высшее", "бакалавр", "магистр", "высшее", "кандидат наук", "доктор наук")
schedules = ("не имеет значения", "полный день", "сменный график", "вахтовый метод", "удаленная работа", "гибкий график")

# Переменные для состояния бота
site = ""
data_type = ""
last_parsed = ""
search_id = ""
current_filter = {}
is_parsing_in_process = False

# Команды для телеграмм бота
bot.set_my_commands([
    telebot.types.BotCommand("/start", "Начать работу с ботом"),
    telebot.types.BotCommand("/parse", "Запустить парсинг данных"),
    telebot.types.BotCommand("/search", "Просмотреть результаты"),
    telebot.types.BotCommand("/filter", "Установить фильтры"),
])

@bot.message_handler(commands=['start'])
def start_handler(message):
    keyboard = types.ReplyKeyboardMarkup()
    keyboard.row("HH.ru")
    keyboard.row("Вакансии", "Резюме")
    bot.send_message(message.chat.id, 'Выберите сайт hh.ru, затем используйте команду /parse', reply_markup=keyboard)

@bot.message_handler(commands=['help'])
def help_handler(message):
    help_text = (
        "Основные команды:\n"
        "/help - помощь по командам бота\n"
        "/filter - установка фильтров\n"
        "/parse - запрос на парсинг данных\n"
        "/search - просмотр полученных данных\n\n"
        "Ключевые слова для фильтров:\n\n"
        "Тип данных: 'Вакансии', 'Резюме'\n"
        "Опыт работы: 'Не имеет значения', 'От 1 года до 3 лет', 'Нет опыта'\n"
        "Образование для вакансий: 'Не имеет значения', 'Не требуется или не указано', 'Высшее', 'Среднее профессиональное'\n"
        "Образование для резюме: 'Не имеет значения', 'Среднее', 'Среднее специальное', 'Незаконченное высшее', 'Бакалавр', 'Магистр', 'Кандидат наук', 'Доктор наук'\n"
        "График работы: 'Не имеет значения', 'Полный день', 'Сменный график', 'Вахтовый метод', 'Удаленная работа', 'Гибкий график'"
    )
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['parse'])
def parse_handler(message):
    global site, data_type, is_parsing_in_process, current_filter

    if is_parsing_in_process:
        bot.send_message(message.chat.id, 'Процесс парсинга уже запущен')
        return

    if not site or not data_type:
        bot.send_message(message.chat.id, 'Сначала выберите сайт и цель парсинга')
        return

    is_parsing_in_process = True
    query_text = message.text[7:]
    cursor.execute(f'DROP TABLE IF EXISTS data_{message.chat.id}')
    bot.send_message(message.chat.id, 'Запуск парсинга...')

    if data_type == "вакансии":
        cursor.execute(f'CREATE TABLE data_{message.chat.id} (id SERIAL PRIMARY KEY, name VARCHAR(256), link VARCHAR(1024), salary VARCHAR(256), company VARCHAR(256), city VARCHAR(128), exp VARCHAR(128))')
        conn.commit()
        result_num, vacancies = collect_vacancies(query_text, current_filter)
        insert_data(cursor, f"data_{message.chat.id}", ["name", "link", "salary", "company", "city", "exp"], vacancies)
    else:
        cursor.execute(f'CREATE TABLE data_{message.chat.id} (id SERIAL PRIMARY KEY, name VARCHAR(512), link VARCHAR(1024), age VARCHAR(128), exp VARCHAR(128), status VARCHAR(128))')
        conn.commit()
        result_num, resumes = collect_resumes(query_text, current_filter)
        insert_data(cursor, f"data_{message.chat.id}", ["name", "link", "age", "exp", "status"], resumes)

    cursor.execute(f"SELECT count(*) FROM data_{message.chat.id};")
    total_loaded = cursor.fetchone()[0]
    bot.send_message(message.chat.id, f'Парсинг завершен\nНайдено: {result_num}\nЗагружено: {total_loaded}\nИспользуйте команду /search для просмотра результатов')
    is_parsing_in_process = False

def insert_data(cursor, table_name, columns, data):
    sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES "
    sql += ", ".join(cursor.mogrify(f"({', '.join(['%s'] * len(row))})", row).decode('utf-8') for row in data)
    cursor.execute(sql)
    conn.commit()

@bot.message_handler(commands=['search'])
def search_handler(message):
    global search_id, last_parsed

    if not last_parsed:
        bot.send_message(message.chat.id, "Сначала выполните команду /parse")
        return

    cursor.execute(f"SELECT count(*) FROM data_{message.chat.id};")
    total_records = cursor.fetchone()[0]

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("<--", callback_data=f'{{"method":"pagination","page":0,"total":{total_records}}}'),
               types.InlineKeyboardButton(f'1/{total_records}', callback_data=' '),
               types.InlineKeyboardButton("-->", callback_data=f'{{"method":"pagination","page":2,"total":{total_records}}}'))

    cursor.execute(f"SELECT * FROM data_{message.chat.id} WHERE id=1;")
    if last_parsed == "вакансии":
        row = cursor.fetchone()
        message_text = format_vacancy(row)
    elif last_parsed == "резюме":
        row = cursor.fetchone()
        message_text = format_resume(row)

    msg = bot.send_message(message.chat.id, message_text, reply_markup=markup, parse_mode='Markdown')
    search_id = msg.message_id

def format_vacancy(vacancy):
    our_id, name, link, salary, company, city, exp = vacancy
    return f"{name}\n[Ссылка]({link})\nЗарплата: {salary}\nОпыт работы: {exp}\nКомпания: {company}\nГород: {city}"

def format_resume(resume):
    our_id, name, link, age, exp, status = resume
    return f"{name}\n[Ссылка]({link})\nВозраст: {age}\nОпыт работы: {exp}\n{status}"

@bot.message_handler(commands=['filter'])
def filter_handler(message):
    global data_type, current_filter
    current_filter = {}
    if not data_type:
        bot.send_message(message.chat.id, 'Сначала выберите цель парсинга')
        return

    keyboard = types.ReplyKeyboardMarkup()
    for exp in experience_levels:
        keyboard.row(exp)
    bot.send_message(message.chat.id, 'Выберите опыт работы', reply_markup=keyboard)

@bot.message_handler(commands=['now_filter'])
def now_filter_handler(message):
    global current_filter
    if current_filter:
        filter_text = "\n".join(f"{key} - {value}" for key, value in current_filter.items())
        bot.send_message(message.chat.id, f'Текущий фильтр:\n{filter_text}')
    else:
        bot.send_message(message.chat.id, 'Фильтр пуст')

@bot.callback_query_handler(func=lambda call: True)
def pagination_callback(call):
    global search_id, last_parsed

    if call.message.message_id != search_id:
        return

    data = json.loads(call.data)
    total_records = data['total']
    page = data['page']

    if page == 0:
        page = total_records
    elif page == total_records + 1:
        page = 1

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("<--", callback_data=f'{{"method":"pagination","page":{page-1},"total":{total_records}}}'),
               types.InlineKeyboardButton(f'{page}/{total_records}', callback_data=' '),
               types.InlineKeyboardButton("-->", callback_data=f'{{"method":"pagination","page":{page+1},"total":{total_records}}}'))

    cursor.execute(f"SELECT * FROM data_{call.message.chat.id} WHERE id=%s;", (page,))
    row = cursor.fetchone()

    if last_parsed == "вакансии":
        message_text = format_vacancy(row)
    elif last_parsed == "резюме":
        message_text = format_resume(row)

    bot.edit_message_text(message_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(content_types=['text'])
def text_handler(message):
    global site, data_type, current_filter

    msg_text = message.text.lower()
    if msg_text in sites:
        site = msg_text
        bot.send_message(message.chat.id, f'Выбран сайт: {site}')
    elif msg_text in data_types:
        data_type = msg_text
        current_filter = {}
        bot.send_message(message.chat.id, f'Цель парсинга: {data_type}')
    else:
        if data_type:
            handle_filter_selection(message, msg_text)

def handle_filter_selection(message, msg_text):
    global current_filter, data_type

    if msg_text in experience_levels and len(current_filter) == 0:
        current_filter["Опыт работы"] = msg_text
        keyboard = types.ReplyKeyboardMarkup()
        education_options = education_vacancies if data_type == "вакансии" else education_resumes
        for option in education_options:
            keyboard.row(option)
        bot.send_message(message.chat.id, 'Выберите уровень образования', reply_markup=keyboard)

    elif (msg_text in education_vacancies and data_type == "вакансии" or
          msg_text in education_resumes and data_type == "резюме") and len(current_filter) == 1:
        current_filter["Образование"] = msg_text
        keyboard = types.ReplyKeyboardMarkup()
        for schedule in schedules:
            keyboard.row(schedule)
        bot.send_message(message.chat.id, 'Выберите тип занятости', reply_markup=keyboard)

    elif msg_text in schedules and len(current_filter) == 2:
        current_filter["График работы"] = msg_text
        bot.send_message(message.chat.id, "Фильтры установлены")

if __name__ == "__main__":
    bot.polling(none_stop=True, interval=0)
