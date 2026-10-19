import pandas as pd
import pymysql
from sqlalchemy import create_engine

# 1. Создаем защищенное подключение к удаленной СУБД MySQL в Москве
# Формат: mysql+pymysql://USER:PASSWORD@HOST/DATABASE
db_url = "mysql+pymysql://root:YOUR_PASSWORD_HERE@195.2.74.50/crypto_bank"
engine = create_engine(db_url)

# 2. МАТЕМАТИЧЕСКИЙ ПРОРЫВ: выкачиваем историю транзакций напрямую в матрицу Pandas!
try:
    query = "SELECT * FROM transactions"  # Заменили ручной список колонок на звёздочку!
    df = pd.read_sql_query(query, engine)
    
    if df.empty:
        print("ℹ️ В облачной таблице транзакций пока нет данных для анализа.")
    else:
        print("=== РЕЗУЛЬТАТЫ СИНХРОНИЗАЦИИ MYSQL + PANDAS ===")
        print(f"📊 Успешно импортировано строк из Москвы: {len(df)}")
        
        # 3. Считаем матожидание и сигму для реальных сумм переводов
        mean_amount = df["amount"].mean()
        std_amount = df["amount"].std()
        
        print(f"💰 Средний чек транзакции (Мат. ожидание): {mean_amount:.2f} руб.")
        print(f"📉 Волатильность переводов (σ): {std_amount:.2f} руб.")
        
        # Выводим матрицу на экран
        print("\n📝 Последние строки реальной матрицы из облака:")
        print(df.tail(5))
        
except Exception as e:
    print(f"🚨 Ошибка подключения к удаленной СУБД: {e}")
