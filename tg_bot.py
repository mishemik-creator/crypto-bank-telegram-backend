import telebot
import csv
import requests
import pymysql
import random
import os
from telebot import types
from datetime import datetime





BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "8597715021:AAHQyJec-_jH_2uqn9YtM5Y4cvTFJCaq1gA")

db_config = {
    "host": os.getenv("MYSQL_HOST", "195.2.74.50"),       
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "rootpassword2026"), 
    "database": os.getenv("MYSQL_DATABASE", "crypto_bank"),
    "charset": "utf8mb4",
    "use_unicode": True,
    "cursorclass": pymysql.cursors.DictCursor
}


bot = telebot.TeleBot(BOT_TOKEN)





def init_db():
    try:
        
        conn = pymysql.connect(
            host=db_config["host"],
            user=db_config["user"],
            password=db_config["password"],
            charset="utf8mb4" 
        )
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS crypto_bank")
        
        conn.commit()
        conn.close()
        
        
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(255),
                balance DOUBLE DEFAULT 10000.0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sender_id BIGINT,
                receiver_id BIGINT,
                amount DOUBLE,
                timestamp DATETIME
            )
        """)
        conn.commit()
        conn.close()
        print("🐬 [MYSQL SERVER]: База данных и Enterprise-таблицы успешно развернуты на сервере!")
    except Exception as error:
        print(f"🚨 [ОШИБКА ПОДКЛЮЧЕНИЯ К MYSQL]: {error}")

init_db()

def get_live_market_data():
    try:
        url = "https://coingecko.com"
        response = requests.get(url, timeout=5)
        data = response.json()
        btc_rub = data["bitcoin"]["rub"]
        sol_rub = data["solana"]["rub"]
    except Exception:
        btc_rub = 7900000.00 
        sol_rub = 10000.00   
        
    return [
        {"asset": "USD", "category": "fiat", "price_rub": 94.50, "status": "open"},
        {"asset": "EUR", "category": "fiat", "price_rub": 102.20, "status": "closed"},
        {"asset": "BTC", "category": "crypto", "price_rub": btc_rub, "status": "open"},
        {"asset": "SOL", "category": "crypto", "price_rub": sol_rub, "status": "open"}
    ]


def register_user(user_id, username):
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    
    if user is None:
        cursor.execute("INSERT INTO users (user_id, username, balance) VALUES (%s, %s, %s)", (user_id, username, 10000.0))
        conn.commit()
        is_new = True
    else:
        is_new = False
    conn.close()
    return is_new

def get_user_balance(user_id):
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = %s", (user_id,))
    result = cursor.fetchone() 
    conn.close()
    return result["balance"] if result else 0.0

def update_user_balance(user_id, amount_change):
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    current_balance = result["balance"] if result else 0.0
    
    if current_balance < 300.0 and amount_change < 0:
        conn.close()
        return None 
        
    new_balance = current_balance + amount_change
    cursor.execute("UPDATE users SET balance = %s WHERE user_id = %s", (new_balance, user_id))
    conn.commit()
    conn.close()
    return new_balance

def transfer_money(sender_id, receiver_id, amount):
    amount = abs(float(amount))
    if int(sender_id) == int(receiver_id):
        return "❌ Ошибка: Вы не можете переводить средства самому себе!"
        
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    
    cursor.execute("SELECT balance FROM users WHERE user_id = %s", (sender_id,))
    sender_result = cursor.fetchone()
    sender_balance = sender_result["balance"] if sender_result else 0.0
    
    if sender_balance < amount:
        conn.close()
        return "❌ Ошибка: На вашем счету недостаточно средств!"
        
    cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (receiver_id,))
    receiver_exists = cursor.fetchone()
    
    if not receiver_exists:
        conn.close()
        return "❌ Ошибка: Пользователь с таким ID не найден в MySQL!"
        
    new_sender_balance = sender_balance - amount
    cursor.execute("UPDATE users SET balance = %s WHERE user_id = %s", (new_sender_balance, sender_id))
    
    cursor.execute("SELECT balance FROM users WHERE user_id = %s", (receiver_id,))
    receiver_result = cursor.fetchone()
    receiver_balance = receiver_result["balance"] if receiver_result else 0.0
    
    new_receiver_balance = receiver_balance + amount
    cursor.execute("UPDATE users SET balance = %s WHERE user_id = %s", (new_receiver_balance, receiver_id))
    
    tx_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO transactions (sender_id, receiver_id, amount, timestamp) VALUES (%s, %s, %s, %s)", 
                   (sender_id, receiver_id, amount, tx_time))
    
    conn.commit()
    conn.close()
    return f"✅ Успешно! Переведено {amount:,.2f} руб. пользователю ID {receiver_id}"

def export_transactions_to_excel(user_id):
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sender_id, receiver_id, amount, timestamp 
        FROM transactions 
        WHERE sender_id = %s OR receiver_id = %s
        ORDER BY id DESC LIMIT 5
    """, (user_id, user_id))
    rows = cursor.fetchall() 
    conn.close()
    
    with open("transfers.csv", "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["Отправитель", "Получатель", "Сумма (руб.)", "Дата и время"])
        
        for row in rows:
            sender_text = f"'{row['sender_id']}'"
            receiver_text = f"'{row['receiver_id']}'"
            
            time_text = row['timestamp'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(row['timestamp'], datetime) else row['timestamp']
            writer.writerow([sender_text, receiver_text, f"{row['amount']:,.2f}", time_text])
               
    return len(rows)

def export_to_excel(data_to_save):
    with open("summary.csv", "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["Ассет", "Категория", "Статус", "Инвестиция"])
    for coin in data_to_save:
        verdict = "Рекомендовано" if coin["category"] == "crypto" and coin["status"] == "open" else "Стабильно" if coin["category"] == "fiat" and coin["status"] == "open" else "Игнорировать"
        with open("summary.csv", "a", newline="", encoding="utf-8-sig") as summary_file:
            summary_writer = csv.writer(summary_file, delimiter=";")
            summary_writer.writerow([coin["asset"], coin["category"], coin["status"], verdict])



@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else "Инвестор"
    is_new = register_user(user_id, username)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_market = types.KeyboardButton("📊 Показать рынок")
    btn_alerts = types.KeyboardButton("🚨 Критические риски")
    btn_balance = types.KeyboardButton("💰 Мой баланс")
    btn_luck = types.KeyboardButton("🎲 Испытать удачу")
    btn_transfer = types.KeyboardButton("💸 Перевести средства")
    btn_history = types.KeyboardButton("📜 Выписка по счету")
    
    markup.add(btn_market, btn_alerts)
    markup.add(btn_balance, btn_luck)
    markup.add(btn_transfer, btn_history)
    
    welcome_text = f"Привет, {username}! 👋\n\nВы успешно зарегистрированы в MySQL сервере! 🎉\nБаланс: 💰 *10 000 рублей*." if is_new else f"С возвращением на MySQL, {username}! 📈\n\nВыберите действие:"
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['setzero'])
def handle_set_zero(message):
    user_id = message.from_user.id
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("security_audit.txt", "a", encoding="utf-8") as audit_file:
        audit_file.write(f"[{current_time}] АДМИН {message.from_user.username} (ID: {user_id}) обнулил свой баланс в MySQL!\n")
        
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = 0.0 WHERE user_id = %s", (user_id,))
    conn.commit()
    conn.close()
    bot.reply_to(message, "⚠️ *ВНИМАНИЕ, АДМИНИСТРАТОР!*\n\nСработал скрытый скрипт. Ваш баланс в MySQL успешно **ОБНУЛЕН (0.00 руб.)**. 💸❌", parse_mode="Markdown")

@bot.message_handler(commands=['createfriend'])
def handle_create_friend(message):
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("INSERT IGNORE INTO users (user_id, username, balance) VALUES (%s, %s, %s)", (77777, "Test_Receiver", 0.0))
    conn.commit()
    conn.close()
    bot.reply_to(message, "🤖 Тестовый кошелек создан в MySQL успешно!\n\nID получателя: 77777\nВы можете переводить ему деньги! 💸", parse_mode="Markdown")
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_text = message.text.lower().strip()
    fresh_market_data = get_live_market_data()
    if "рынок" in user_text or user_text == "📊 показать рынок":
                
        export_to_excel(fresh_market_data)
        inline_markup = types.InlineKeyboardMarkup()
        btn_url = types.InlineKeyboardButton(text="🔗 Сайт биржи", url="https://coinmarketcap.com")
        btn_hide = types.InlineKeyboardButton(text="🧹 Скрыть отчет", callback_data="hide_report")
        inline_markup.add(btn_url, btn_hide)
        with open("summary.csv", "rb") as excel_file:
            bot.send_document(message.chat.id, excel_file, caption="📊 Свежий аналитический отчет готов!", reply_markup=inline_markup)
            
    elif "риск" in user_text or "критическ" in user_text or user_text == "🚨 критические риски":
        bot.send_chat_action(message.chat.id, 'typing')
        closed_coins = [f"❌ {coin['asset']}: {coin['price_rub']} руб." for coin in fresh_market_data if coin["status"] == "closed"]
        response_text = "⚠️ ОБНАРУЖЕНЫ ОСТАНОВЛЕННЫЕ ТОРГИ:\n" + "\n".join(closed_coins) if closed_coins else "✅ На рынке всё спокойно. Остановленных торгов нет!"
        bot.send_message(message.chat.id, response_text)
        
    elif "баланс" in user_text or user_text == "💰 мой баланс":
        bot.send_chat_action(message.chat.id, 'typing')
        current_balance = get_user_balance(message.from_user.id)
        bot.send_message(message.chat.id, f"💳 *Ваш личный счет в MySQL:*\n\n💰 Доступно: `{current_balance:,.2f}` руб.\n🟢 Статус: Активен", parse_mode="Markdown")
        
    elif "улицу" in user_text or "удача" in user_text or user_text == "🎲 испытать удачу":
        bot.send_chat_action(message.chat.id, 'typing')
        user_id = message.from_user.id
        change = random.choice([500.0, -300.0])
        final_balance = update_user_balance(user_id, change)
        
        if final_balance is None:
            inline_markup = types.InlineKeyboardMarkup()
            btn_subsidy = types.InlineKeyboardButton(text="🎁 Получить субсидию 1,500 руб.", callback_data="get_subsidy")
            inline_markup.add(btn_subsidy)
            bot.send_message(message.chat.id, "🛑 *ОПЕРАЦИЯ ЗАБЛОКИРОВАНА!*\n\n⚠️ На вашем счету недостаточно средств в MySQL (минимум 300 руб.).", reply_markup=inline_markup, parse_mode="Markdown")
        else:
            result_text = f"🔥 *УДАЧА НА ВАШЕЙ СТОРОНЕ!*\n\n📈 Вы выиграли: `+500.00` руб.\n💰 Новый баланс: `{final_balance:,.2f}` руб." if change > 0 else f"📉 *ОЙ, НЕ ПОВЕЗЛО...*\n\n💸 Списание со счета в MySQL: `-300.00` руб.\n💰 Новый баланс: `{final_balance:,.2f}` руб."
            bot.send_message(message.chat.id, result_text, parse_mode="Markdown")
            
    elif "перевод" in user_text or user_text == "💸 перевести средства":
        bot.send_message(message.chat.id, "Введите Telegram ID пользователя, которому вы хотите перевести деньги в MySQL: 🔍")
        bot.register_next_step_handler(message, process_receiver_id)
        
    elif "выписка" in user_text or user_text == "📜 выписка по счету":
        bot.send_chat_action(message.chat.id, 'upload_document')
        user_id = message.from_user.id
        tx_count = export_transactions_to_excel(user_id)
        
        if tx_count == 0:
            bot.send_message(message.chat.id, "ℹ️ *У вас пока нет истории переводов в MySQL.*\nСделайте перевод! 💸", parse_mode="Markdown")
        else:
            with open("transfers.csv", "rb") as excel_file:
                bot.send_document(message.chat.id, excel_file, caption=f"📜 Ваша financial выписка из MySQL готова!\nВыгружено последних операций: *{tx_count}*", parse_mode="Markdown")
                
    else:
        bot.send_message(message.chat.id, "Пожалуйста, нажимайте только на кнопки в меню! 🧠")
def process_receiver_id(message):
    try:
        receiver_id = int(message.text.strip())
        bot.send_message(message.chat.id, f"ID принят. Какую сумму вы хотите перевести пользователю `{receiver_id}`? 💰", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_transfer_amount, receiver_id)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Ошибка: ID должен состоять только из цифр.")

def process_transfer_amount(message, receiver_id):
    try:
        amount = float(message.text.strip())
        sender_id = message.from_user.id
        result = transfer_money(sender_id, receiver_id, amount)
        bot.send_message(message.chat.id, result)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Ошибка: Сумма должна быть числом.")
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    
    if call.data == "hide_report":
        bot.answer_callback_query(call.id, text="Отчет успешно заархивирован!")
        try:
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.send_message(call.message.chat.id, "🔒 Данные скрыты. Файл summary.csv успешно передан в локальный архив! 📁")
        except Exception as e:
            print(f"⚠️ [ПЕРЕХВАТ ИСКЛЮЧЕНИЯ]: Ошибка: {e}")
            
    elif call.data == "get_subsidy":
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        
        current_balance = result["balance"] if result else 0.0
        new_balance = current_balance + 1500.0
        
        cursor.execute("UPDATE users SET balance = %s WHERE user_id = %s", (new_balance, user_id))
        conn.commit()
        conn.close()
        
        bot.answer_callback_query(call.id, text="Субсидия начислена в MySQL!")
        try:
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        except Exception:
            pass
            
        bot.send_message(call.message.chat.id, f"✅ *Антикризисная помощь в MySQL оказана!*\n\n💰 Вам начислено: `+1,500.00` руб.\n💳 Текущий баланс: `{new_balance:,.2f}` руб.", parse_mode="Markdown")

print("=== БОЕВОЙ ФИНАНСОВЫЙ БОТ ЗАПУЩЕН И НАСТРОЕН НА 100% ===")
bot.infinity_polling()
