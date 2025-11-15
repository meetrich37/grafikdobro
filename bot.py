import os
import logging
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime

# Настройки
TOKEN = "8128748378:AAF7AJSxU6kj0xE_Ndf0Q6YoP7-ngyRaszc"

# ⬇️⬇️⬇️ ДОБАВЬ СЮДА ID МЕНЕДЖЕРОВ ⬇️⬇️⬇️
MANAGERS = [
    494645329   # Замени на свой ID
    # 987654321    # Замени на ID второго менеджера
]
# ⬆️⬆️⬆️ ДОБАВЬ СЮДА ID МЕНЕДЖЕРОВ ⬆️⬆️⬆️

# Включим логирование
logging.basicConfig(level=logging.INFO)

# Функции для работы с JSON
def load_shifts():
    try:
        with open('shifts.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_shifts():
    with open('shifts.json', 'w', encoding='utf-8') as f:
        json.dump(shifts, f, ensure_ascii=False, indent=2)

# Функция для уведомлений менеджерам
async def notify_managers(message: str, bot):
    for manager_id in MANAGERS:
        try:
            await bot.send_message(chat_id=manager_id, text=message)
        except Exception as e:
            print(f"Ошибка уведомления для {manager_id}: {e}")

# Загружаем данные
shifts = load_shifts()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "☕ Бот для записи на смены бариста!\n\n"
        "Команды:\n"
        "/record - 📝 Записаться на смену\n"
        "/graph - 👀 Посмотреть график\n"
        "/cancel - ❌ Отменить запись\n"
        "/myshift - 📋 Моя запись\n"
        "/help - ❓ Помощь"
    )

# Команда /record
async def record_shift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Напишите дату и время в формате:\n"
        "Пример: '01.12 14.30-22.00' или '1.12 8.30-22.00'"
    )

# Команда /graph
async def show_graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not shifts:
        await update.message.reply_text("📊 График пустой. Записей пока нет.")
        return

    # Собираем все даты из записей
    dates = []
    for shift_text in shifts.keys():
        if ' ' in shift_text:
            date_part = shift_text.split(' ')[0]
            dates.append(date_part)

    if not dates:
        await update.message.reply_text("📊 В графике нет записей с датами.")
        return

    # Функция для преобразования даты
    def parse_date(date_str):
        try:
            day, month = date_str.split('.')
            current_year = datetime.now().year
            return datetime(current_year, int(month), int(day))
        except:
            return datetime.now()

    # Сортируем даты
    sorted_dates = sorted(dates, key=parse_date)
    start_date = sorted_dates[0]
    end_date = sorted_dates[-1]

    # Создаем график
    text = f"‼График работы с {start_date} по {end_date}‼\n\n"
    weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    # Группируем записи по датам
    shifts_by_date = {}
    for shift_text, user_name in shifts.items():
        if ' ' in shift_text:
            date_part = shift_text.split(' ')[0]
            time_part = shift_text.split(' ')[1] if len(shift_text.split(' ')) > 1 else ""
            if date_part not in shifts_by_date:
                shifts_by_date[date_part] = []
            time_part = time_part.replace('.', ':')
            shifts_by_date[date_part].append((time_part, user_name))

    # Функция для сортировки времени
    def time_to_minutes(time_str):
        try:
            start_time = time_str.split('-')[0].strip()
            if ':' in start_time:
                hours, minutes = start_time.split(':')
                return int(hours) * 60 + int(minutes)
            else:
                return 0
        except:
            return 0

    # Выводим график
    sorted_dates = sorted(shifts_by_date.keys(), key=parse_date)
    current_year = datetime.now().year

    for date in sorted_dates:
        try:
            day, month = date.split('.')
            date_obj = datetime(current_year, int(month), int(day))
            weekday_index = date_obj.weekday()
            weekday = weekdays[weekday_index]
        except:
            weekday = "День"

        text += f"{weekday} {date}\n"
        sorted_shifts = sorted(shifts_by_date[date], key=lambda x: time_to_minutes(x[0]))
        for shift_time, user_name in sorted_shifts:
            text += f"{shift_time} {user_name}\n"
        text += "\n"

    await update.message.reply_text(text)

# Обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name
    text = update.message.text.strip()

    parts = text.split()
    if len(parts) != 2:
        await update.message.reply_text(
            "❌ Неправильный формат!\n\n"
            "✅ Правильный формат: ДД.ММ ЧЧ.ММ-ЧЧ.ММ\n\n"
            "Примеры:\n• 25.12 08.30-22.00\n• 1.12 8.30-22.00\n• 01.01 14.00-20.30\n• 5.12 9.00-17.00"
        )
        return

    date_part, time_part = parts

    # Проверяем дату
    date_valid = True
    if '.' in date_part:
        date_parts = date_part.split('.')
        if len(date_parts) != 2:
            date_valid = False
        else:
            day, month = date_parts
            if not (day.isdigit() and month.isdigit()):
                date_valid = False
            elif not (1 <= int(day) <= 31 and 1 <= int(month) <= 12):
                date_valid = False
    else:
        date_valid = False

    # Проверяем время
    time_valid = True
    if '-' in time_part:
        time_parts = time_part.split('-')
        if len(time_parts) != 2:
            time_valid = False
        else:
            start_time, end_time = time_parts
            def check_single_time(time_str):
                if '.' in time_str:
                    time_parts = time_str.split('.')
                    if len(time_parts) != 2:
                        return False
                    hours, minutes = time_parts
                    if not (hours.isdigit() and minutes.isdigit()):
                        return False
                    if not (0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59):
                        return False
                    return True
                return False

            if not check_single_time(start_time) or not check_single_time(end_time):
                time_valid = False
    else:
        time_valid = False

    if date_valid and time_valid:
        shifts[text] = user_name
        save_shifts()
        
        # ⬇️ УВЕДОМЛЕНИЕ МЕНЕДЖЕРАМ О ДОБАВЛЕНИИ
        await notify_managers(
            f"📝 НОВАЯ ЗАПИСЬ\n"
            f"👤 {user_name}\n"
            f"📅 {text}\n"
            f"⏰ {datetime.now().strftime('%H:%M %d.%m.%Y')}",
            context.bot
        )
        
        await update.message.reply_text(f"✅ {user_name}, вы записаны на: {text}")
    else:
        await update.message.reply_text(
            "❌ Неправильный формат!\n\n"
            "✅ Правильный формат: ДД.ММ ЧЧ.ММ-ЧЧ.ММ\n\n"
            "Примеры:\n• 25.12 08.30-22.00\n• 1.12 8.30-22.00\n• 01.01 14.00-20.30\n• 5.12 9.00-17.00"
        )

# Команда /myshift
async def my_shift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name
    user_shifts = [f"• {date_time}" for date_time, name in shifts.items() if name == user_name]
    if user_shifts:
        await update.message.reply_text(f"📋 Ваши записи:\n" + "\n".join(user_shifts))
    else:
        await update.message.reply_text("У вас нет активных записей")

# Команда /cancel
async def cancel_shift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name
    
    # Сохраняем какие записи удаляем для уведомления
    deleted_shifts = [shift for shift, name in shifts.items() if name == user_name]
    
    global shifts
    shifts = {k: v for k, v in shifts.items() if v != user_name}
    save_shifts()
    
    # ⬇️ УВЕДОМЛЕНИЕ МЕНЕДЖЕРАМ ОБ УДАЛЕНИИ
    if deleted_shifts:
        await notify_managers(
            f"❌ УДАЛЕНЫ ЗАПИСИ\n"
            f"👤 {user_name}\n"
            f"🗑️ Удалено записей: {len(deleted_shifts)}\n"
            f"⏰ {datetime.now().strftime('%H:%M %d.%m.%Y')}",
            context.bot
        )
    
    await update.message.reply_text("❌ Все ваши записи отменены")

# Основная функция
def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("record", record_shift))
    application.add_handler(CommandHandler("graph", show_graph))
    application.add_handler(CommandHandler("myshift", my_shift))
    application.add_handler(CommandHandler("cancel", cancel_shift))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Бот запущен на Railway с уведомлениями для менеджеров!")
    application.run_polling()

if __name__ == "__main__":
    main()
