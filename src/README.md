# 🧠 Telegram Habit Tracker Bot: Руководство по созданию бота-трекера привычек

Telegram-бот для создания и отслеживания привычек с широким набором команд. Позволяет пользователю управлять привычками через диалоговое меню и сокращённые команды, отслеживать прогресс, статистику и историю действий.

## Видео-презентация

https://rutube.ru/video/private/69ea96b0dd7bdeb287571e67a1877f7e/?p=2Rf_6huKIP6Hbm6hpYB5MQ

## 📚 Содержание


1. Обзор и исследование предметной области
2. Требования
3. Установка и настройка окружения
4. Создание Telegram-бота
5. Разработка функциональности бота
6. Иллюстрации и схемы
7. Размещение в GitHub
8. Заключение

---

## 🧪 1. Обзор и исследование предметной области



**Цель**: создать Telegram-бота, который поможет пользователю вести виртуальный дневник привычек. Создавать новые привычки, отмечать их и проводить базовые операции над ними: удалять, переименовывать, очищать прогресс. Также бот должен быть способным отображать статистику и историю действий для удобства.

**Исследуемые компоненты**:

- **Python** — основной язык реализации.
- **pyTelegramBotAPI** — взаимодействие с пользователями.
- **SQL Lite 3"** - взаимодействие с базой данных


---

## 🛠️ 2. Требования


- Python 3.9+
- pip (пакетный менеджер Python)
- Библиотеки:

  ```shell
   pip install pyTelegramBotAPI sqlite3
   ```
  

---

## ⚙️ 3. Установка и настройка окружения



1. Установите Python и pip.
2. Установите Python-зависимости:

  ```shell
   pip install pyTelegramBotAPI sqlite3
   ```
  

---

## 🤖 4. Создание Telegram-бота


1. Перейдите в [BotFather](https://t.me/BotFather) в Telegram.
2. Введите команду `/newbot`, задайте имя и получите API-токен.
3. Вставьте токен в переменную `API_TOKEN`.

---

## 🧩 Импорт необходимых библиотек


```python
import telebot
from telebot import types
import sqlite3
from datetime import datetime, timedelta
```

---

## 👨‍💻 5. Разработка функциональности бота


### 1. Инициализация бота и базы данных

```python
bot = telebot.TeleBot(token)
conn = sqlite3.connect('habits.db', check_same_thread=False)
cursor = conn.cursor()

if __name__ == "__main__":
	print("Бот запущен...")
	bot.infinity_polling()
```

---

### 2. Создание таблиц базы данных

```python
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
   ```

---

### 2. Команда /start

```python
@bot.message_handler(commands=['start'])
def start(message):
	...
```

---

### 3. Другие команды

```python
@bot.message_handler(commands=['reset', 'done', 'rename', 'create', 'stats', 'delete', 'menu'])
def handle_commands(message):
	...
```

---

### 4. Обработчики для команд и вспомогательные функции

```python
def handle_reset(user_id, habit_identifier):
    ...
def handle_done(user_id, habit_identifier):
	...
...
def get_habit_by_identifier(user_id, identifier):
	...
```

---

### 5. Функции для работы с привычками и отображения меню

```python
def start_habit_creation(user_id):
	...
def create_habit(user_id, category, name):
	...
def show_main_menu(user_id, message_text=None):
	...
...
```

---

### 6. Обработка callback-запросов

```python
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
	user_id = call.from_user.id
	data = call.data
	try:
	if data == "main_menu":
	    bot.delete_message(call.message.chat.id, call.message.message_id)
	...
	except Exception as e:
	    print(f"Error in callback handler: {e}")
	    bot.send_message(user_id, "Произошла ошибка. Пожалуйста, попробуйте еще раз.")
	
```

---

## 🖼️ 6. Иллюстрации и схемы

### Запуск бота и создание первой привычки

![[Pasted image 20250429194428.png]]

---

### Пример вывода статистики

![[Pasted image 20250429194519.png]]

---
### Удаление привычки

![[Pasted image 20250429194618.png]]
![[Pasted image 20250429194653.png]]

---
### Список привычек

![[Pasted image 20250429194712.png]]

---
### История действий

![[Pasted image 20250429194732.png]]

---

### Создание новой привычки и отметка её как выполненной

![[Pasted image 20250429194808.png]]

---

### Очистка прогресса по привычке

![[Pasted image 20250429194828.png]]

---

### Помощь

![[Pasted image 20250429194843.png]]

---

### Схема взаимодействия

![[Pasted image 20250429200137.png]]

---

### Пользовательский маршрут

![[Pasted image 20250429200122.png]]

---

### Команды пользователя


| Команда  | Описание                                 |
| -------- | ---------------------------------------- |
| /start   | Запустить бота и создать первую привычку |
| /help    | Помощь                                   |
| /create  | Создать новую привычку                   |
| /done    | Отметить привычку выполненной            |
| /list    | Вывести список всех привычек             |
| /stats   | Посмотреть статистику по привычке(-ам)   |
| /delete  | Удалить привычку                         |
| /rename  | Переименовать привычку                   |
| /reset   | Сбросить прогресс привычки               |
| /history | Получить историю привычек                |

---

### Структура проекта


```
HabitTrackerBot/
│
├── bot.py
├── requirements.txt
├── README.md
├── media
├── hidden.py
├── report.md
└── index.html
```

---

### Структура базы данных

```
habits.db              ← база данных трекера привычек
├── habits              ← данные о привычках (id, user_id, name, category, created_at)
├── completions         ← даты выполнения привычек (id, habit_id, completion_date)
└── history             ← журнал действий пользователей (id, user_id, action, details, timestamp)
```

---

## 7. Размещение в GitHub

Для того, чтобы разместить проект на GitHub, необходимо зайти в командную строку в файле проекта и прописать:

```bash
git init
git config --global user.mail "mail"
git config --global user.name "name" (можно ещё git config --list (q для выхода))
git add .
git commit -m "first_commit"
git branch -m main (если выделенная ветка - НЕ main)
git remote add origin (ссылка, которую дают на GitHub при создании нового репозитория)
git push  -u origin main

```

## 8. Заключение

Бот для отслеживания персональных привычек создан и загружен на GitHub, тем самым доступен для доработки. 