import sqlite3
import pandas as pd
import os
import re

def exportar_candles_para_excel(db_path):
    os.system('cls' if os.name == 'nt' else 'clear')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Detectar tabelas do tipo candles_<symbol>_<interval>
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelas = [row[0] for row in cursor.fetchall()]

    padrao = re.compile(r'^candles_([a-z0-9]+)_([a-z0-9]+)$')
    disponiveis = []

    for nome in tabelas:
        match = padrao.match(nome)
        if match:
            symbol, intervalo = match.groups()
            disponiveis.append((symbol.upper(), intervalo))

    if not disponiveis:
        print("⚠️ Nenhuma tabela de candles encontrada no banco.")
        conn.close()
        return

    # Filtrar opções únicas
    symbols = sorted(set(s for s, _ in disponiveis))
    intervalos = sorted(set(i for _, i in disponiveis))

    if len(symbols) == 1:
        symbol_escolhido = symbols[0]
        print(f"💱 Par encontrado: {symbol_escolhido}")
    else:
        print("💱 Pares disponíveis:")
        for s in symbols:
            print(f" - {s}")
        symbol_escolhido = input("Digite o par desejado (ex: BTCUSDT): ").strip().upper()
        if symbol_escolhido not in symbols:
            print("❌ Par inválido.")
            conn.close()
            return

    if len(intervalos) == 1:
        intervalo_escolhido = intervalos[0]
        print(f"⏱️ Intervalo encontrado: {intervalo_escolhido}")
    else:
        print("⏱️ Intervalos disponíveis:")
        for i in intervalos:
            print(f" - {i}")
        intervalo_escolhido = input("Digite o intervalo desejado (ex: 1m, 5m): ").strip().lower()
        if intervalo_escolhido not in intervalos:
            print("❌ Intervalo inválido.")
            conn.close()
            return

    nome_tabela = f"candles_{symbol_escolhido.lower()}_{intervalo_escolhido}"

    try:
        query = f"""
            SELECT timestamp, open, high, low, close, volume
            FROM {nome_tabela}
            ORDER BY timestamp DESC
            LIMIT 100
        """
        df = pd.read_sql_query(query, conn)
    except Exception as e:
        print(f"❌ Erro ao consultar a tabela: {e}")
        conn.close()
        return

    conn.close()

    if df.empty:
        print("⚠️ Nenhum dado encontrado para exportação.")
        return

    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.sort_values('timestamp')

    excel_filename = f"{nome_tabela}_candles.xlsx"
    writer = pd.ExcelWriter(excel_filename, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Candles', index=False)

    workbook = writer.book
    worksheet = writer.sheets['Candles']

    # Gráfico de candles
    chart = workbook.add_chart({'type': 'stock'})
    chart.add_series({
        'name': 'Candles',
        'categories': ['Candles', 1, 0, len(df), 0],
        'values': ['Candles', 1, 4, len(df), 4],
        'open': ['Candles', 1, 1, len(df), 1],
        'high': ['Candles', 1, 2, len(df), 2],
        'low': ['Candles', 1, 3, len(df), 3],
        'close': ['Candles', 1, 4, len(df), 4],
    })

    chart.set_title({'name': f'Candles – {symbol_escolhido} ({intervalo_escolhido})'})
    chart.set_x_axis({'name': 'Tempo'})
    chart.set_y_axis({'name': 'Preço'})
    chart.set_size({'width': 800, 'height': 400})

    worksheet.insert_chart('H2', chart)

    # Novo gráfico de volume
    chart_vol = workbook.add_chart({'type': 'column'})
    chart_vol.add_series({
        'name': 'Volume',
        'categories': ['Candles', 1, 0, len(df), 0],
        'values': ['Candles', 1, 5, len(df), 5],
    })
    chart_vol.set_title({'name': 'Volume por Candle'})
    chart_vol.set_x_axis({'name': 'Tempo'})
    chart_vol.set_y_axis({'name': 'Volume'})
    chart_vol.set_size({'width': 800, 'height': 300})
    worksheet.insert_chart('H25', chart_vol)

    writer.close()

    full_path = os.path.abspath(excel_filename)
    print(f"✅ Dados exportados para '{excel_filename}' com gráficos de candles e volume incluídos.")
    print(f"📁 Caminho completo: {full_path}")

    if os.name == 'nt':
        os.startfile(full_path)
