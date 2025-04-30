import telebot
from telebot import types
import sqlite3
from datetime import datetime, timedelta
import time
from hidden import token

# Инициализация бота
bot = telebot.TeleBot(token)

# Подключение к базе данных SQLite
conn = sqlite3.connect('src/habits.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц, если они не существуют
def init_db():
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        category TEXT,
        created_at TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS completions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        habit_id INTEGER,
        completion_date TEXT,
        FOREIGN KEY (habit_id) REFERENCES habits (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        details TEXT,
        timestamp TEXT
    )
    ''')
    
    conn.commit()

init_db()

# Основные команды
@bot.message_handler(commands=['reset', 'done', 'rename', 'create', 'stats', 'delete', 'menu'])
def handle_commands(message):
    user_id = message.from_user.id
    text_parts = message.text.split()
    command = text_parts[0][1:].lower()  # Приводим команду к нижнему регистру
    args = text_parts[1:] if len(text_parts) > 1 else []
    
    if command == 'reset':
        if not args:
            bot.send_message(user_id, "Использование: /reset <ID/название>")
            return
        
        habit_identifier = ' '.join(args)
        habit = get_habit_by_identifier(user_id, habit_identifier)
        if not habit:
            bot.send_message(user_id, f"Ошибка: привычка '{habit_identifier}' не найдена!")
            return
            
        clear_habit_history(user_id, habit[0])
    
    elif command == 'done':
        if not args:
            bot.send_message(user_id, "Использование: /done <ID/название>")
            return
            
        habit_identifier = ' '.join(args)
        habit = get_habit_by_identifier(user_id, habit_identifier)
        if not habit:
            bot.send_message(user_id, f"Ошибка: привычка '{habit_identifier}' не найдена!")
            return
            
        complete_habit(user_id, habit[0])
    
    elif command == 'rename':
        if len(args) < 2:
            bot.send_message(user_id, "Использование: /rename <ID/название> <новое_название> [категория]\nПример: /rename 1 Чтение Книги")
            return
            
        habit_identifier = args[0]
        new_name = ' '.join(args[1:-1]) if len(args) > 2 else args[1]
        new_category = args[-1] if len(args) > 2 else None
        
        habit = get_habit_by_identifier(user_id, habit_identifier)
        if not habit:
            bot.send_message(user_id, f"Ошибка: привычка '{habit_identifier}' не найдена!")
            return
            
        rename_habit_full(user_id, habit[0], new_name, new_category)
    
    elif command == 'create':
        if len(args) < 2:
            bot.send_message(user_id, "Использование: /create <название> <категория>")
            return
            
        category = args[-1]
        name = ' '.join(args[:-1])
        create_habit(user_id, category, name)
    
    elif command == 'stats':
        handle_stats(message)
    
    elif command == 'delete':
        if not args:
            show_delete_habit_menu(user_id)
            return
            
        habit_identifier = ' '.join(args)
        habit = get_habit_by_identifier(user_id, habit_identifier)
        if not habit:
            bot.send_message(user_id, f"Ошибка: привычка '{habit_identifier}' не найдена!")
            return
            
        confirm_delete_habit(user_id, habit[0])
    
    elif command == 'menu':
        show_main_menu(user_id)

# Обработчики для команд
def handle_reset(user_id, habit_identifier):
    habit = get_habit_by_identifier(user_id, habit_identifier)
    if not habit:
        bot.send_message(user_id, "Привычка не найдена!")
        return
    clear_habit_history(user_id, habit[0])

def handle_done(user_id, habit_identifier):
    habit = get_habit_by_identifier(user_id, habit_identifier)
    if not habit:
        bot.send_message(user_id, "Привычка не найдена!")
        return
    complete_habit(user_id, habit[0])

def rename_habit_full(user_id, habit_id, new_name, new_category=None):
    cursor.execute("SELECT name, category FROM habits WHERE id = ?", (habit_id,))
    old_name, old_category = cursor.fetchone()
    
    if new_category:
        cursor.execute("UPDATE habits SET name = ?, category = ? WHERE id = ?", 
                      (new_name, new_category, habit_id))
        conn.commit()
        log_action(user_id, "habit_renamed", 
                  f"ID: {habit_id}, Old Name: {old_name}, New Name: {new_name}, Old Category: {old_category}, New Category: {new_category}")
        bot.send_message(user_id, f"Привычка переименована!\nНовое название: {new_name}\nНовая категория: {new_category}")
    else:
        cursor.execute("UPDATE habits SET name = ? WHERE id = ?", 
                      (new_name, habit_id))
        conn.commit()
        log_action(user_id, "habit_renamed", 
                  f"ID: {habit_id}, Old Name: {old_name}, New Name: {new_name}, Category: {old_category} (unchanged)")
        bot.send_message(user_id, f"Привычка переименована!\nНовое название: {new_name}\nКатегория осталась прежней: {old_category}")

def handle_stats(message):
    user_id = message.from_user.id
    args = message.text.split()[1:]
    
    if not args:
        show_stats_menu(user_id)
        return
    
    # Обрабатываем случай "/stats all"
    if len(args) == 1 and args[0].lower() == 'all':
        show_all_stats(user_id)
        return
    
    habit_identifier = ' '.join(args)
    habit = get_habit_by_identifier(user_id, habit_identifier, case_sensitive=False)
    
    if not habit:
        bot.send_message(user_id, "Ошибка: привычка не найдена!\nИспользование:\n/stats <ID или название>\n/stats all")
        return
    
    show_habit_stats(user_id, habit[0])

def handle_delete(user_id, habit_identifier):
    habit = get_habit_by_identifier(user_id, habit_identifier)
    if not habit:
        bot.send_message(user_id, "Привычка не найдена!")
        return
    confirm_delete_habit(user_id, habit[0])

# Вспомогательная функция для поиска привычки (полностью регистронезависимая)
def get_habit_by_identifier(user_id, identifier):
    # Очищаем идентификатор от лишних пробелов
    clean_identifier = ' '.join(identifier.strip().split())
    
    try:
        # Пробуем найти по ID (если передан числовой ID)
        habit_id = int(clean_identifier)
        cursor.execute("SELECT id, name FROM habits WHERE user_id = ? AND id = ?", 
                      (user_id, habit_id))
        return cursor.fetchone()
    except ValueError:
        # Если не число, ищем по названию (регистронезависимо)
        try:
            # Вариант 1: Точное совпадение (без учета регистра)
            cursor.execute("""
            SELECT id, name 
            FROM habits 
            WHERE user_id = ? AND LOWER(name) = LOWER(?)
            """, (user_id, clean_identifier))
            result = cursor.fetchone()
            if result:
                return result
            
            # Вариант 2: Поиск по подстроке (если точного совпадения нет)
            cursor.execute("""
            SELECT id, name 
            FROM habits 
            WHERE user_id = ? AND name LIKE ? 
            ORDER BY LENGTH(name) ASC
            LIMIT 1
            """, (user_id, f"%{clean_identifier}%"))
            return cursor.fetchone()
            
        except sqlite3.OperationalError as e:
            print(f"Database error: {e}")
            return None
    
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "Привет! Давай создадим твою первую привычку!", reply_markup=create_habit_markup())

@bot.message_handler(commands=['help'])
def help_command(message):
    show_help(message.from_user.id)

#@bot.message_handler(commands=['create'])
#def create_habit_command(message):
#    start_habit_creation(message.from_user.id)

#@bot.message_handler(commands=['delete'])
#def delete_habit_command(message):
#   show_delete_habit_menu(message.from_user.id)

#@bot.message_handler(commands=['rename'])
#def rename_habit_command(message):
#    show_rename_habit_menu(message.from_user.id)

@bot.message_handler(commands=['list'])
def list_habits_command(message):
    show_habits_list(message.from_user.id)

#@bot.message_handler(commands=['complete'])
#def complete_habit_command(message):
#    show_complete_habit_menu(message.from_user.id)

#@bot.message_handler(commands=['stats'])
#def stats_command(message):
#    show_stats_menu(message.from_user.id)

@bot.message_handler(commands=['history'])
def history_command(message):
   show_history_menu(message.from_user.id)

@bot.message_handler(commands=['clear'])
def clear_history_command(message):
    show_clear_history_menu(message.from_user.id)

# Обработка текстовых сообщений
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    text = message.text
    
    if text == "ℹ️ Помощь":
        show_help(user_id)
    elif text == "➕ Создать":
        start_habit_creation(user_id)
    elif text == "🗑️ Удалить":
        show_delete_habit_menu(user_id)
    elif text == "🔤 Переименовать":
        show_rename_habit_menu(user_id)
    elif text == "📜 Список":
        show_habits_list(user_id)
    elif text == "✅ Выполнено":
        show_complete_habit_menu(user_id)
    elif text == "📈 Статистика":
        show_stats_menu(user_id)
    elif text == "📅 История":
        show_history_menu(user_id)
    elif text == "🧹 Очистить":
        show_clear_history_menu(user_id)
    else:
        bot.send_message(user_id, "Я не понимаю эту команду. Попробуйте /help для списка команд.")

# Функции для работы с привычками
def start_habit_creation(user_id):
    categories = ["Здоровье", "Спорт", "Образование", "Работа", "Другое"]
    markup = types.InlineKeyboardMarkup()
    
    for category in categories:
        markup.add(types.InlineKeyboardButton(category, callback_data=f"create_category_{category}"))
    
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="main_menu"))  # Добавили кнопку отмены
    
    bot.send_message(user_id, "Выбери категорию твоей привычки:", reply_markup=markup)

def create_habit(user_id, category, name):
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO habits (user_id, name, category, created_at) VALUES (?, ?, ?, ?)", 
                 (user_id, name, category, created_at))
    conn.commit()
    
    habit_id = cursor.lastrowid
    log_action(user_id, "habit_created", f"ID: {habit_id}, Name: {name}, Category: {category}")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Отметить выполненной", callback_data=f"complete_{habit_id}"))
    markup.add(types.InlineKeyboardButton("Главное меню", callback_data="main_menu"))  # Явно добавляем кнопку меню
    
    bot.send_message(user_id, f"Привычка '{name}' создана!", reply_markup=markup)

def complete_habit(user_id, habit_id):
    completion_date = datetime.now().strftime("%Y-%m-%d")
    
    # Проверяем, не была ли уже сегодня выполнена привычка
    cursor.execute("SELECT id FROM completions WHERE habit_id = ? AND completion_date = ?", 
                  (habit_id, completion_date))
    if cursor.fetchone():
        bot.send_message(user_id, "Эта привычка уже была отмечена сегодня!")
        return
    
    cursor.execute("INSERT INTO completions (habit_id, completion_date) VALUES (?, ?)", 
                  (habit_id, completion_date))
    conn.commit()
    
    cursor.execute("SELECT name FROM habits WHERE id = ?", (habit_id,))
    habit_name = cursor.fetchone()[0]
    
    log_action(user_id, "habit_completed", f"ID: {habit_id}, Name: {habit_name}")
    
    bot.send_message(user_id, f"Поздравляем! Сегодня привычка '{habit_name}' выполнена! ✅")
    show_habits_list(user_id)  # Показываем обновленный список

def delete_habit(user_id, habit_id):
    cursor.execute("SELECT name FROM habits WHERE id = ?", (habit_id,))
    habit_name = cursor.fetchone()[0]
    
    cursor.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    cursor.execute("DELETE FROM completions WHERE habit_id = ?", (habit_id,))
    conn.commit()
    
    log_action(user_id, "habit_deleted", f"ID: {habit_id}, Name: {habit_name}")
    
    bot.send_message(user_id, f"Привычка '{habit_name}' (ID={habit_id}) была успешно удалена!")

def rename_habit(user_id, habit_id, new_name, new_category=None):
    cursor.execute("SELECT name, category FROM habits WHERE id = ?", (habit_id,))
    old_name, old_category = cursor.fetchone()
    
    if new_category:
        cursor.execute("UPDATE habits SET name = ?, category = ? WHERE id = ?", 
                      (new_name, new_category, habit_id))
    else:
        cursor.execute("UPDATE habits SET name = ? WHERE id = ?", 
                      (new_name, habit_id))
    conn.commit()
    
    log_action(user_id, "habit_renamed", f"ID: {habit_id}, Old Name: {old_name}, New Name: {new_name}, Old Category: {old_category}, New Category: {new_category if new_category else old_category}")
    
    bot.send_message(user_id, f"Привычка с ID {habit_id} переименована в '{new_name}'!")

def clear_habit_history(user_id, habit_id):
    cursor.execute("SELECT name FROM habits WHERE id = ?", (habit_id,))
    habit_name = cursor.fetchone()[0]
    
    cursor.execute("DELETE FROM completions WHERE habit_id = ?", (habit_id,))
    conn.commit()
    
    log_action(user_id, "habit_history_cleared", f"ID: {habit_id}, Name: {habit_name}")
    
    bot.send_message(user_id, f"Прогресс привычки '{habit_name}' (ID={habit_id}) был успешно очищен!")

# Функции для отображения меню
def show_main_menu(user_id, message_text=None):
    cursor.execute("SELECT COUNT(*) FROM habits WHERE user_id = ?", (user_id,))
    total_habits = cursor.fetchone()[0]
    
    cursor.execute('''
    SELECT COUNT(*) FROM habits h
    WHERE h.user_id = ? AND NOT EXISTS (
        SELECT 1 FROM completions c 
        WHERE c.habit_id = h.id AND c.completion_date = date('now')
    )
    ''', (user_id,))
    uncompleted = cursor.fetchone()[0]
    
    status = f"{uncompleted} привычек осталось выполнить сегодня!" if uncompleted > 0 else "Все привычки на сегодня выполнены!"
    
    # Создаем полноценную клавиатуру меню
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
    "ℹ️ Помощь", "➕ Создать",
    "🗑️ Удалить", "🔤 Переименовать",
    "📜 Список", "✅ Выполнено",
    "📈 Статистика", "📅 История",
    "🧹 Очистить"
    ]
    markup.add(*[types.KeyboardButton(text) for text in buttons])
    
    # Если передано текстовое сообщение, редактируем существующее
    if message_text:
        bot.send_message(user_id, f"{status}\n\n{message_text}", reply_markup=markup)
    else:
        bot.send_message(user_id, status, reply_markup=markup)

def show_help(user_id):
    help_text = """
📚 *Помощь по командам бота*

*Основные команды:*
/create <название> <категория> - Создать новую привычку
/delete <ID/название> - Удалить привычку
/rename <ID/название> [категория] - Переименовать привычку
/list - Показать список привычек
/done <ID/название> - Отметить выполненной
/stats <ID/название> - Показать статистику
/stats all - Общая статистика
/history - Показать историю действий
/reset <ID/название> - Очистить историю привычки
/menu - Вернуться в главное меню

*Примеры:*
/create Чтение Книги
/done 1
/rename 2 Спорт
/stats Чтение
/reset 3
"""
    bot.send_message(user_id, help_text, parse_mode="Markdown")

def show_delete_habit_menu(user_id):
    cursor.execute("SELECT id, name FROM habits WHERE user_id = ?", (user_id,))
    habits = cursor.fetchall()
    
    if not habits:
        bot.send_message(user_id, "У вас нет привычек для удаления.")
        return
    
    markup = types.InlineKeyboardMarkup()
    for habit_id, name in habits:
        markup.add(types.InlineKeyboardButton(f"{name} (ID={habit_id})", callback_data=f"delete_select_{habit_id}"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data="main_menu"))
    
    bot.send_message(user_id, "Выберите привычку, которую хотите удалить:", reply_markup=markup)

def show_rename_habit_menu(user_id):
    cursor.execute("SELECT id, name FROM habits WHERE user_id = ?", (user_id,))
    habits = cursor.fetchall()
    
    if not habits:
        bot.send_message(user_id, "У вас нет привычек для переименования.")
        return
    
    markup = types.InlineKeyboardMarkup()
    for habit_id, name in habits:
        markup.add(types.InlineKeyboardButton(f"{name} (ID={habit_id})", callback_data=f"rename_select_{habit_id}"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data="main_menu"))
    
    bot.send_message(user_id, "Выберите привычку, которую хотите переименовать:", reply_markup=markup)

def show_habits_list(user_id):
    # Получаем список привычек с информацией о выполнении сегодня
    cursor.execute('''
    SELECT h.id, h.name, h.category, 
           CASE WHEN c.completion_date IS NOT NULL THEN '✅' ELSE '❌' END as today_status
    FROM habits h
    LEFT JOIN completions c ON h.id = c.habit_id AND c.completion_date = date('now')
    WHERE h.user_id = ?
    ORDER BY h.id
    ''', (user_id,))
    habits = cursor.fetchall()
    
    if not habits:
        bot.send_message(user_id, "У вас пока нет привычек.")
        return
    
    # Определяем максимальные длины для выравнивания
    max_name_len = max(len(habit[1]) for habit in habits) if habits else 0
    max_category_len = max(len(habit[2]) for habit in habits) if habits else 0
    
    # Ограничиваем максимальную длину (чтобы не было слишком широко)
    max_name_len = min(max_name_len, 20)
    max_category_len = min(max_category_len, 15)
    
    # Формируем таблицу
    habits_list = "📋 <b>Список ваших привычек:</b>\n\n"
    habits_list += "<pre>"
    habits_list += f"{'ID':<3} {'Название':<{max_name_len}} {'Категория':<{max_category_len}} Сегодня\n"
    habits_list += "-" * (3 + max_name_len + max_category_len + 10) + "\n"
    
    for habit_id, name, category, today_status in habits:
        habits_list += f"{habit_id:<3} {name[:max_name_len]:<{max_name_len}} {category[:max_category_len]:<{max_category_len}} {today_status}\n"
    
    habits_list += "</pre>"
    habits_list += "\n✅ - выполнено сегодня\n❌ - не выполнено сегодня"
    
    bot.send_message(user_id, habits_list, parse_mode="HTML")

def show_complete_habit_menu(user_id):
    cursor.execute('''
    SELECT h.id, h.name 
    FROM habits h
    WHERE h.user_id = ? AND NOT EXISTS (
        SELECT 1 FROM completions c 
        WHERE c.habit_id = h.id AND c.completion_date = date('now')
    )
    ''', (user_id,))
    habits = cursor.fetchall()
    
    if not habits:
        bot.send_message(user_id, "Все привычки на сегодня уже выполнены!")
        return
    
    markup = types.InlineKeyboardMarkup()
    for habit_id, name in habits:
        markup.add(types.InlineKeyboardButton(name, callback_data=f"complete_{habit_id}"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data="main_menu"))
    
    bot.send_message(user_id, "Выберите привычку, которую вы выполнили сегодня:", reply_markup=markup)

def show_stats_menu(user_id):
    cursor.execute("SELECT id, name FROM habits WHERE user_id = ?", (user_id,))
    habits = cursor.fetchall()
    
    if not habits:
        bot.send_message(user_id, "У вас пока нет привычек для просмотра статистики.")
        return
    
    markup = types.InlineKeyboardMarkup()
    for habit_id, name in habits:
        markup.add(types.InlineKeyboardButton(name, callback_data=f"stats_{habit_id}"))
    markup.add(types.InlineKeyboardButton("Общая статистика", callback_data="stats_all"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data="main_menu"))
    
    bot.send_message(user_id, "Выберите привычку, статистику которой хотите посмотреть:", reply_markup=markup)

def show_habit_stats(user_id, habit_id):
    cursor.execute("SELECT name, created_at FROM habits WHERE id = ?", (habit_id,))
    habit_name, created_at = cursor.fetchone()
    created_date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").date()
    
    # Количество дней с момента создания привычки
    days_since_creation = (datetime.now().date() - created_date).days + 1
    
    # Статистика за неделю
    cursor.execute('''
    SELECT COUNT(*) FROM completions 
    WHERE habit_id = ? AND completion_date >= date('now', '-7 days')
    ''', (habit_id,))
    week_count = cursor.fetchone()[0]
    
    # Статистика за месяц
    cursor.execute('''
    SELECT COUNT(*) FROM completions 
    WHERE habit_id = ? AND completion_date >= date('now', '-1 month')
    ''', (habit_id,))
    month_count = cursor.fetchone()[0]
    
    # Общая статистика
    cursor.execute('''
    SELECT COUNT(*) FROM completions 
    WHERE habit_id = ?
    ''', (habit_id,))
    total_count = cursor.fetchone()[0]
    
    # Лучший стрик
    cursor.execute('''
    WITH dates AS (
        SELECT date(?) as day
        UNION ALL
        SELECT date(day, '+1 day')
        FROM dates
        WHERE day < date('now')
    ),
    completions_marked AS (
        SELECT 
            d.day,
            CASE WHEN c.completion_date IS NOT NULL THEN 1 ELSE 0 END as completed
        FROM dates d
        LEFT JOIN completions c ON d.day = c.completion_date AND c.habit_id = ?
    ),
    streaks AS (
        SELECT 
            day,
            completed,
            SUM(CASE WHEN completed = 0 THEN 1 ELSE 0 END) OVER (ORDER BY day) as group_id
        FROM completions_marked
    )
    SELECT MAX(streak_length)
    FROM (
        SELECT COUNT(*) as streak_length
        FROM streaks
        WHERE completed = 1
        GROUP BY group_id
    )
    ''', (created_at, habit_id))
    best_streak = cursor.fetchone()[0] or 0
    
    # Текущий стрик
    cursor.execute('''
    WITH recent_completions AS (
        SELECT completion_date 
        FROM completions 
        WHERE habit_id = ? 
        ORDER BY completion_date DESC
    ),
    dates AS (
        SELECT date('now', '-' || (n-1) || ' day') as day
        FROM (
            SELECT row_number() OVER () as n FROM recent_completions LIMIT 7
        )
    ),
    marked_dates AS (
        SELECT 
            d.day,
            CASE WHEN rc.completion_date IS NOT NULL THEN 1 ELSE 0 END as completed
        FROM dates d
        LEFT JOIN recent_completions rc ON d.day = rc.completion_date
        ORDER BY d.day DESC
    ),
    streaks AS (
        SELECT 
            day,
            completed,
            SUM(CASE WHEN completed = 0 THEN 1 ELSE 0 END) OVER (ORDER BY day DESC) as group_id
        FROM marked_dates
    )
    SELECT COUNT(*) as current_streak
    FROM streaks
    WHERE completed = 1 AND group_id = 0
    ''', (habit_id,))
    current_streak = cursor.fetchone()[0] or 0
    
    # Процент выполнения (с момента создания)
    completion_percent = round((total_count / days_since_creation) * 100, 1) if days_since_creation > 0 else 0.0
    
    stats_text = f"""
📊 *Статистика по привычке "{habit_name}" (ID={habit_id})*

▪️ На этой неделе: {week_count} раз
▪️ В этом месяце: {month_count} раз
▪️ За всё время: {total_count} раз
▪️ Лучший стрик: {best_streak} дней
▪️ Текущий стрик: {current_streak} дней
▪️ Процент выполнения: {completion_percent}%
▪️ Дней с момента создания: {days_since_creation}
    """
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Статистика по месяцу", callback_data=f"month_stats_{habit_id}"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data="stats_menu"))
    
    bot.send_message(user_id, stats_text, parse_mode="Markdown", reply_markup=markup)
    
    # Последние 8 дней
    cursor.execute('''
    SELECT date('now', '-' || (n-1) || ' day') as day
    FROM (
        SELECT row_number() OVER () as n FROM habits LIMIT 8
    )
    ORDER BY day DESC
    ''')
    days = [row[0] for row in cursor.fetchall()]
    
    cursor.execute('''
    SELECT completion_date 
    FROM completions 
    WHERE habit_id = ? AND completion_date IN ({})
    '''.format(','.join(['?']*len(days))), (habit_id, *days))
    completed_days = [row[0] for row in cursor.fetchall()]
    
    days_text = "Последние 8 дней:\n"
    for day in days:
        if day in completed_days:
            days_text += f"{day} ✅\n"
        else:
            if datetime.strptime(day, "%Y-%m-%d").date() > datetime.now().date():
                days_text += f"{day} ➖\n"
            else:
                days_text += f"{day} ❌\n"
    
    bot.send_message(user_id, days_text)

def show_all_stats(user_id):
    # Общая статистика
    cursor.execute("SELECT COUNT(*) FROM habits WHERE user_id = ?", (user_id,))
    total_habits = cursor.fetchone()[0]
    
    cursor.execute('''
    SELECT COUNT(*) FROM completions c
    JOIN habits h ON c.habit_id = h.id
    WHERE h.user_id = ? AND c.completion_date >= date('now', '-7 days')
    ''', (user_id,))
    week_count = cursor.fetchone()[0]
    
    cursor.execute('''
    SELECT COUNT(*) FROM completions c
    JOIN habits h ON c.habit_id = h.id
    WHERE h.user_id = ? AND c.completion_date >= date('now', '-1 month')
    ''', (user_id,))
    month_count = cursor.fetchone()[0]
    
    cursor.execute('''
    SELECT COUNT(*) FROM completions c
    JOIN habits h ON c.habit_id = h.id
    WHERE h.user_id = ?
    ''', (user_id,))
    total_count = cursor.fetchone()[0]
    
    # Лучшая и худшая привычка
    cursor.execute('''
    SELECT h.id, h.name, COUNT(c.id) as completions, h.created_at
    FROM habits h
    LEFT JOIN completions c ON h.id = c.habit_id
    WHERE h.user_id = ?
    GROUP BY h.id
    ORDER BY completions DESC
    LIMIT 1
    ''', (user_id,))
    best_habit = cursor.fetchone()
    
    cursor.execute('''
    SELECT h.id, h.name, COUNT(c.id) as completions, h.created_at
    FROM habits h
    LEFT JOIN completions c ON h.id = c.habit_id
    WHERE h.user_id = ?
    GROUP BY h.id
    ORDER BY completions ASC
    LIMIT 1
    ''', (user_id,))
    worst_habit = cursor.fetchone()
    
    stats_text = f"""
📊 *Общая статистика*

▪️ Всего привычек: {total_habits}
▪️ На этой неделе: {week_count} выполнений
▪️ В этом месяце: {month_count} выполнений
▪️ За всё время: {total_count} выполнений
    """
    
    if best_habit:
        best_id, best_name, best_completions, best_created_at = best_habit
        best_created_date = datetime.strptime(best_created_at, "%Y-%m-%d %H:%M:%S").date()
        best_days = (datetime.now().date() - best_created_date).days + 1
        best_percent = round((best_completions / best_days) * 100, 1) if best_days > 0 else 0.0
        
        stats_text += f"\n⭐ *Лучшая привычка*: {best_name} (ID={best_id})"
        stats_text += f"\n   ▪️ Всего выполнений: {best_completions}"
        stats_text += f"\n   ▪️ Процент выполнения: {best_percent}%"
        
        # Лучший стрик для лучшей привычки
        cursor.execute('''
        WITH dates AS (
            SELECT date(?) as day
            UNION ALL
            SELECT date(day, '+1 day')
            FROM dates
            WHERE day < date('now')
        ),
        completions_marked AS (
            SELECT 
                d.day,
                CASE WHEN c.completion_date IS NOT NULL THEN 1 ELSE 0 END as completed
            FROM dates d
            LEFT JOIN completions c ON d.day = c.completion_date AND c.habit_id = ?
        ),
        streaks AS (
            SELECT 
                day,
                completed,
                SUM(CASE WHEN completed = 0 THEN 1 ELSE 0 END) OVER (ORDER BY day) as group_id
            FROM completions_marked
        )
        SELECT MAX(streak_length)
        FROM (
            SELECT COUNT(*) as streak_length
            FROM streaks
            WHERE completed = 1
            GROUP BY group_id
        )
        ''', (best_created_at, best_id))
        best_habit_streak = cursor.fetchone()[0] or 0
        stats_text += f"\n   ▪️ Лучший стрик: {best_habit_streak} дней"
    
    if worst_habit:
        worst_id, worst_name, worst_completions, worst_created_at = worst_habit
        worst_created_date = datetime.strptime(worst_created_at, "%Y-%m-%d %H:%M:%S").date()
        worst_days = (datetime.now().date() - worst_created_date).days + 1
        worst_percent = round((worst_completions / worst_days) * 100, 1) if worst_days > 0 else 0.0
        
        stats_text += f"\n\n⚠️ *Худшая привычка*: {worst_name} (ID={worst_id})"
        stats_text += f"\n   ▪️ Всего выполнений: {worst_completions}"
        stats_text += f"\n   ▪️ Процент выполнения: {worst_percent}%"
        
        # Лучший стрик для худшей привычки
        cursor.execute('''
        WITH dates AS (
            SELECT date(?) as day
            UNION ALL
            SELECT date(day, '+1 day')
            FROM dates
            WHERE day < date('now')
        ),
        completions_marked AS (
            SELECT 
                d.day,
                CASE WHEN c.completion_date IS NOT NULL THEN 1 ELSE 0 END as completed
            FROM dates d
            LEFT JOIN completions c ON d.day = c.completion_date AND c.habit_id = ?
        ),
        streaks AS (
            SELECT 
                day,
                completed,
                SUM(CASE WHEN completed = 0 THEN 1 ELSE 0 END) OVER (ORDER BY day) as group_id
            FROM completions_marked
        )
        SELECT MAX(streak_length)
        FROM (
            SELECT COUNT(*) as streak_length
            FROM streaks
            WHERE completed = 1
            GROUP BY group_id
        )
        ''', (worst_created_at, worst_id))
        worst_habit_streak = cursor.fetchone()[0] or 0
        stats_text += f"\n   ▪️ Лучший стрик: {worst_habit_streak} дней"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Назад", callback_data="stats_menu"))
    
    bot.send_message(user_id, stats_text, parse_mode="Markdown", reply_markup=markup)

def show_history_menu(user_id, page=1):
    offset = (page - 1) * 20
    cursor.execute('''
    SELECT id, action, details, timestamp 
    FROM history 
    WHERE user_id = ?
    ORDER BY timestamp DESC
    LIMIT 20 OFFSET ?
    ''', (user_id, offset))
    history_items = cursor.fetchall()
    
    if not history_items and page > 1:
        show_history_menu(user_id, 1)
        return
    
    history_text = "📜 История действий\n\n"
    for item_id, action, details, timestamp in history_items:
        history_text += f"{item_id}. {action}: {details} ({timestamp})\n"
    
    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    
    if page > 1:
        buttons.append(types.InlineKeyboardButton("◀️ Назад", callback_data=f"history_page_{page-1}"))
    
    cursor.execute("SELECT COUNT(*) FROM history WHERE user_id = ?", (user_id,))
    total_items = cursor.fetchone()[0]
    
    if offset + 20 < total_items:
        buttons.append(types.InlineKeyboardButton("Вперед ▶️", callback_data=f"history_page_{page+1}"))
    
    buttons.append(types.InlineKeyboardButton("Меню", callback_data="main_menu"))
    markup.add(*buttons)
    
    bot.send_message(user_id, history_text, reply_markup=markup)

def show_clear_history_menu(user_id):
    cursor.execute("SELECT id, name FROM habits WHERE user_id = ?", (user_id,))
    habits = cursor.fetchall()
    
    if not habits:
        bot.send_message(user_id, "У вас нет привычек для очистки истории.")
        return
    
    markup = types.InlineKeyboardMarkup()
    for habit_id, name in habits:
        markup.add(types.InlineKeyboardButton(name, callback_data=f"clear_history_{habit_id}"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data="main_menu"))
    
    bot.send_message(user_id, "Выберите привычку, историю которой хотите очистить:", reply_markup=markup)

# Вспомогательные функции
def create_habit_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Создать", callback_data="create_habit"))
    return markup

def log_action(user_id, action, details):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO history (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)", 
                  (user_id, action, details, timestamp))
    conn.commit()

# Обработка callback-запросов
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    data = call.data
    
    try:
        if data == "main_menu":
            bot.delete_message(call.message.chat.id, call.message.message_id)
            show_main_menu(call.from_user.id)
        elif data == "stats_menu":
            bot.delete_message(user_id, call.message.message_id)
            show_stats_menu(user_id)
        elif data == "create_habit":
            bot.delete_message(user_id, call.message.message_id)
            start_habit_creation(user_id)
        elif data.startswith("create_category_"):
            category = data[len("create_category_"):]
            bot.delete_message(user_id, call.message.message_id)
            msg = bot.send_message(user_id, f"Выбрана категория: {category}. Введите название вашей привычки:")
            bot.register_next_step_handler(msg, lambda m: create_habit(user_id, category, m.text))
        elif data.startswith("complete_"):
            habit_id = int(data[len("complete_"):])
            bot.delete_message(user_id, call.message.message_id)
            complete_habit(user_id, habit_id)
        elif data.startswith("delete_select_"):
            habit_id = int(data[len("delete_select_"):])
            bot.delete_message(user_id, call.message.message_id)
            confirm_delete_habit(user_id, habit_id)
        elif data.startswith("confirm_delete_"):
            parts = data.split("_")
            if parts[2] == "yes":
                habit_id = int(parts[3])
                bot.delete_message(user_id, call.message.message_id)
                delete_habit(user_id, habit_id)
            else:
                bot.delete_message(user_id, call.message.message_id)
                bot.send_message(user_id, "Удаление отменено.")
        elif data.startswith("rename_select_"):
            habit_id = int(data[len("rename_select_"):])
            bot.delete_message(user_id, call.message.message_id)
            ask_new_habit_name(user_id, habit_id)
        elif data.startswith("stats_"):
            habit_id = data[len("stats_"):]
            bot.delete_message(user_id, call.message.message_id)
            if habit_id == "all":
                show_all_stats(user_id)
            else:
                show_habit_stats(user_id, int(habit_id))
        elif data.startswith("month_stats_"):
            habit_id = int(data[len("month_stats_"):])
            bot.delete_message(user_id, call.message.message_id)
            show_month_stats(user_id, habit_id)
        elif data.startswith("history_page_"):
            page = int(data[len("history_page_"):])
            bot.delete_message(user_id, call.message.message_id)
            show_history_menu(user_id, page)
        elif data.startswith("clear_history_"):
            habit_id = int(data[len("clear_history_"):])
            bot.delete_message(user_id, call.message.message_id)
            clear_habit_history(user_id, habit_id)
        elif data.startswith("rename_category_"):
            data = call.data.split('_')
            habit_id = int(data[2])
            action = data[3]
            
            if action == "none":
                bot.send_message(user_id, "Категория привычки осталась без изменений.")
                show_main_menu(user_id)
            elif action == "custom":
                msg = bot.send_message(user_id, "Введите новую категорию:")
                bot.register_next_step_handler(msg, lambda m: finish_rename(user_id, habit_id, m.text))
            else:
                # Для стандартных категорий
                category = '_'.join(data[3:])  # На случай если категория содержит _
                finish_rename(user_id, habit_id, category)

    except Exception as e:
        print(f"Error in callback handler: {e}")
        bot.send_message(user_id, "Произошла ошибка. Пожалуйста, попробуйте еще раз.")

    
def finish_rename(user_id, habit_id, new_category):
    cursor.execute("UPDATE habits SET category = ? WHERE id = ?", (new_category, habit_id))
    conn.commit()
    cursor.execute("SELECT name FROM habits WHERE id = ?", (habit_id,))
    name = cursor.fetchone()[0]
    bot.send_message(user_id, f"Привычка успешно обновлена!\nНазвание: {name}\nКатегория: {new_category}")
    show_main_menu(user_id)

def ask_new_habit_name(user_id, habit_id):
    msg = bot.send_message(user_id, "Введите новое название привычки:")
    bot.register_next_step_handler(msg, lambda m: process_new_habit_name(user_id, habit_id, m.text))

def process_new_habit_name(user_id, habit_id, new_name):
    # Сохраняем новое название в временных данных или сразу переименовываем
    cursor.execute("UPDATE habits SET name = ? WHERE id = ?", (new_name, habit_id))
    conn.commit()
    
    # Теперь спрашиваем про категорию
    ask_change_category(user_id, habit_id, new_name)

def ask_change_category(user_id, habit_id, new_name):
    categories = ["Здоровье", "Спорт", "Образование", "Работа", "Другое"]
    markup = types.InlineKeyboardMarkup()
    
    for category in categories:
        markup.add(types.InlineKeyboardButton(category, callback_data=f"rename_category_{habit_id}_{category}"))
    
    markup.add(types.InlineKeyboardButton("Оставить текущую категорию", callback_data=f"rename_category_{habit_id}_none"))
    
    bot.send_message(user_id, 
                    f"Название привычки изменено на: {new_name}\nХотите изменить категорию?", 
                    reply_markup=markup)

def confirm_delete_habit(user_id, habit_id):
    cursor.execute("SELECT name FROM habits WHERE id = ?", (habit_id,))
    habit_name = cursor.fetchone()[0]
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Да", callback_data=f"confirm_delete_yes_{habit_id}"),
               types.InlineKeyboardButton("Нет", callback_data="confirm_delete_no"))
    
    bot.send_message(user_id, f"Вы уверены, что хотите удалить привычку '{habit_name}' (ID={habit_id})?", reply_markup=markup)

def show_month_stats(user_id, habit_id):
    cursor.execute("SELECT name FROM habits WHERE id = ?", (habit_id,))
    habit_name = cursor.fetchone()[0]
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=29)  # 30 дней включая сегодня
    
    cursor.execute('''
    SELECT completion_date 
    FROM completions 
    WHERE habit_id = ? AND completion_date BETWEEN ? AND ?
    ''', (habit_id, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))
    completed_days = {row[0] for row in cursor.fetchall()}
    
    # Создаем календарь с правильным форматированием
    cal_text = f"📅 *Статистика привычки '{habit_name}' за 30 дней*\n"
    cal_text += f"({start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')})\n\n"
    
    # Заголовок дней недели с фиксированной шириной
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    cal_text += "  ".join(f"{day:^3}" for day in weekdays) + "\n"
    
    current_date = start_date
    week_line = ""
    
    # Добавляем отступ для первого дня, если неделя начинается не с понедельника
    for _ in range(current_date.weekday()):
        week_line += "    "  # 4 пробела для выравнивания
    
    while current_date <= end_date:
        day_str = current_date.strftime("%Y-%m-%d")
        day_num = current_date.day
        
        # Определяем символ для дня
        if day_str in completed_days:
            symbol = "✅"
        elif current_date > datetime.now().date():
            symbol = "  "
        else:
            symbol = "❌"
        
        # Форматируем день с фиксированной шириной
        week_line += f"{day_num:2d}{symbol} "
        
        # Переход на новую строку в воскресенье
        if current_date.weekday() == 6:
            cal_text += week_line + "\n"
            week_line = ""
        
        current_date += timedelta(days=1)
    
    # Добавляем последнюю неделю, если она не завершена
    if week_line:
        cal_text += week_line + "\n"
    
    # Легенда
    cal_text += "\n✅ - выполнено   ❌ - не выполнено   пусто - будущий день"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Назад к статистике", callback_data=f"stats_{habit_id}"))
    
    # Используем HTML для сохранения форматирования
    bot.send_message(user_id, f"<pre>{cal_text}</pre>", 
                   parse_mode="HTML", reply_markup=markup)

# Запуск бота
if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()