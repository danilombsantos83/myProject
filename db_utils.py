import sqlite3
import pandas as pd
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
import time
from config import api_key, api_secret, interval_map


def listar_pares_disponiveis(db_path):
    """Lista pares de moedas existentes no banco SQLite."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelas = [row[0] for row in cursor.fetchall()]

    pares = sorted(set(
        t.split("_")[1].upper()
        for t in tabelas
        if t.startswith("candles_") and len(t.split("_")) == 3
    ))

    conn.close()
    return pares


def listar_intervalos_disponiveis(db_path, simbolo):
    """
    Retorna os intervalos disponíveis para um par específico.
    Ex: ['1h', '1d']
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelas = [row[0] for row in cursor.fetchall()]
    conn.close()

    prefix = f"candles_{simbolo.lower()}_"
    intervalos = sorted({t.split("_")[2] for t in tabelas if t.startswith(prefix)})
    return intervalos


def listar_pares_e_periodos(db_path):
    """
    Retorna um dicionário com pares e seus respectivos períodos disponíveis.
    Ex: {'BTCUSDT': ['1h', '4h'], 'ETHUSDT': ['1h']}
    """
    pares = {}
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'candles_%'")
        tabelas = cursor.fetchall()

        for (tabela,) in tabelas:
            partes = tabela.split("_")
            if len(partes) == 3:
                _, par, periodo = partes
                par = par.upper()
                if par not in pares:
                    pares[par] = []
                pares[par].append(periodo)
        conn.close()
    except Exception as e:
        print(f"❌ Erro ao listar pares: {e}")

    for par in pares:
        pares[par] = sorted(pares[par], key=lambda x: (len(x), x))
    return pares


def selecionar_par_interativo(db_path):
    """Permite o usuário escolher interativamente um par de moedas."""
    pares = listar_pares_disponiveis(db_path)

    if not pares:
        print("⚠️ Nenhum par de moedas encontrado no banco.")
        novo = input("Digite o símbolo de um novo par (ex: BTCUSDT): ").strip().upper()
        return novo if novo else None

    print("\n📊 Pares disponíveis no banco de dados:")
    for i, par in enumerate(pares, start=1):
        print(f"{i} - {par}")
    print("0 - Digitar novo par manualmente")

    while True:
        escolha = input("\nEscolha o número do par ou digite o nome diretamente: ").strip()

        if escolha == "0":
            novo = input("Digite o novo par (ex: BTCUSDT): ").strip().upper()
            return novo if novo else None
        elif escolha.isdigit() and 1 <= int(escolha) <= len(pares):
            return pares[int(escolha) - 1]
        elif escolha.upper() in pares:
            return escolha.upper()
        else:
            print("❌ Opção inválida. Tente novamente.")


def banco_possui_tabelas_candles(db_path):
    """Verifica se existem tabelas de candles no banco."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'candles_%'")
    resultado = cursor.fetchall()
    conn.close()
    return len(resultado) > 0


def importar_candles_binance(db_path, symbol, interval, start_str=None, limit=1000):
    """
    Função central para buscar candles da Binance e salvar no SQLite.
    Se start_str for fornecido, busca a partir dessa data.
    Se não, busca a partir do último registro no banco (ou os últimos 1000 se vazio).
    """
    client = Client(api_key, api_secret)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    table_name = f"candles_{symbol.lower()}_{interval}"

    # Criar a tabela se não existir (Schema unificado)
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            timestamp INTEGER PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            close_time INTEGER,
            quote_asset_volume REAL,
            number_of_trades INTEGER,
            taker_buy_base_asset_volume REAL,
            taker_buy_quote_asset_volume REAL
        )
    ''')

    # Determinar data de início se não informada
    if not start_str:
        cursor.execute(f"SELECT MAX(timestamp) FROM {table_name}")
        max_ts = cursor.fetchone()[0]

        if max_ts:
            start_dt = datetime.fromtimestamp((max_ts + 1) / 1000)
            start_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')
            print(f"🔄 Atualizando {symbol} ({interval}) a partir de {start_str}")
        else:
            print(f"⬇️ Baixando {limit} candles iniciais para {symbol} ({interval})...")
            start_str = None  # Vai usar o limit do get_historical_klines

    try:
        if start_str:
            candles = client.get_historical_klines(symbol, interval, start_str=start_str)
        else:
            candles = client.get_historical_klines(symbol, interval, limit=limit)
    except (BinanceAPIException, BinanceRequestException) as e:
        print(f"❌ Erro na API da Binance para {symbol}: {e}")
        conn.close()
        return 0

    inserted = 0
    for candle in candles:
        try:
            cursor.execute(f'''
                INSERT INTO {table_name} (
                    timestamp, open, high, low, close, volume,
                    close_time, quote_asset_volume, number_of_trades,
                    taker_buy_base_asset_volume, taker_buy_quote_asset_volume
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', candle[:11])
            inserted += 1
        except sqlite3.IntegrityError:
            continue  # Ignorar duplicatas

    conn.commit()
    conn.close()
    return inserted


def gerenciar_rotatividade_backups(conn, table_name_base):
    """
    Mantém apenas os 3 backups mais recentes de uma tabela específica.
    Remove os backups mais antigos automaticamente.
    """
    cursor = conn.cursor()
    # Padrão de nome: candles_btc_1h_backup_YYYYMMDD_HHMMSS
    pattern = f"{table_name_base}_backup_%"
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?", (pattern,))
    backups = [row[0] for row in cursor.fetchall()]
    
    # Ordenar decrescente (o timestamp no nome garante que os mais recentes fiquem primeiro)
    backups.sort(reverse=True)
    
    # Se houver mais que 3, apaga os excedentes (do índice 3 em diante)
    if len(backups) > 3:
        excedentes = backups[3:]
        for table_to_drop in excedentes:
            try:
                cursor.execute(f"DROP TABLE {table_to_drop}")
                print(f"♻️  Rotatividade: Backup antigo removido: {table_to_drop}")
            except Exception as e:
                print(f"⚠️ Erro ao remover backup antigo {table_to_drop}: {e}")
        conn.commit()


def atualizar_banco(db_path, symbol=None):
    """
    Atualiza TODOS os intervalos configurados para um par (ou seleciona um).
    Realiza backup antes de atualizar e aplica rotatividade (Mantém 3 últimos).
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # === Selecionar símbolo interativamente, se não informado ===
    if not symbol:
        symbol = selecionar_par_interativo(db_path)
        if not symbol:
            print("❌ Nenhum par selecionado. Operação cancelada.")
            conn.close()
            return

    conn.close() # Fechar aqui pois importar_candles abre sua própria conexão
    symbols = [symbol.upper()]

    for sym in symbols:
        for interval_key, interval in interval_map.items():
            table_name = f"candles_{sym.lower()}_{interval_key}"
            
            # --- Lógica de Backup com Rotatividade ---
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            existe = cursor.fetchone()

            if existe:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]

                if row_count > 0:
                    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_table = f"{table_name}_backup_{timestamp_str}"
                    print(f"\n🗂️ Backup: {table_name} → {backup_table}")
                    cursor.execute(f"CREATE TABLE {backup_table} AS SELECT * FROM {table_name}")
                    conn.commit()
                    
                    # Chama a função de limpeza automática
                    gerenciar_rotatividade_backups(conn, table_name)
            
            conn.close()
            # ------------------------------------------------

            # Chama a função unificada de importação
            inseridos = importar_candles_binance(db_path, sym, interval)
            
            if inseridos > 0:
                print(f"✅ {sym} ({interval}): {inseridos} novos candles.")
            else:
                print(f"ℹ️ {sym} ({interval}): Sem novos dados.")

            time.sleep(1.2)  # Respeitar limite da Binance

    print("\n✅ Atualização automática concluída.")


def carregar_candles(db_path, simbolo, intervalo, data_inicial, data_final):
    """
    Carrega os candles da tabela correspondente ao par e intervalo.
    Converte automaticamente timestamps numéricos (epoch ms) para datetime.
    """
    nome_tabela = f"candles_{simbolo.lower()}_{intervalo}"

    try:
        conn = sqlite3.connect(db_path)
        query = f"""
            SELECT timestamp, open, high, low, close, volume
            FROM {nome_tabela}
            ORDER BY timestamp ASC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            return df

        # Detectar e converter epoch (em milissegundos) para datetime
        if pd.api.types.is_numeric_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", errors="coerce")
        else:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

        # Filtrar pelo intervalo de datas informado
        data_inicial_dt = pd.to_datetime(data_inicial)
        data_final_dt = pd.to_datetime(data_final)
        df = df[(df["timestamp"] >= data_inicial_dt) & (df["timestamp"] <= data_final_dt)]

        return df

    except Exception as e:
        print(f"❌ Erro ao carregar dados da tabela {nome_tabela}: {e}")
        return pd.DataFrame()