from binance.client import Client
import json
import os
import sqlite3

# === Chaves da API Binance ===
api_key = 'SUA_API_KEY'        # 🔐 Substitua pela sua chave real
api_secret = 'SUA_API_SECRET'  # 🔐 Substitua pela sua chave real

# === Caminho para o banco de dados SQLite (FIXO) ===
# O banco fica na pasta específica solicitada, fora da raiz do app
base_dir_db = r"C:\db_sqlite"
if not os.path.exists(base_dir_db):
    try:
        os.makedirs(base_dir_db)
    except OSError:
        pass # Se não der para criar, vai tentar salvar onde der ou dar erro de SQLite depois

db_name = "candles_data.db"
db_path = os.path.join(base_dir_db, db_name)

# === Mapeamento de intervalos da Binance ===
interval_map = {
    "1m": Client.KLINE_INTERVAL_1MINUTE,
    "5m": Client.KLINE_INTERVAL_5MINUTE,
    "30m": Client.KLINE_INTERVAL_30MINUTE,
    "1h": Client.KLINE_INTERVAL_1HOUR,
    "4h": Client.KLINE_INTERVAL_4HOUR,
    "1d": Client.KLINE_INTERVAL_1DAY
}

# === Mapeamento de tabelas do banco de dados ===
table_map = {
    "1m": "candles_1m",
    "5m": "candles_5m",
    "30m": "candles_30m",
    "1h": "candles_1h",
    "4h": "candles_4h",
    "1d": "candles_1d"
}

# === Configuração via JSON ===
config_file = "app_config.json"

def ler_config():
    """Lê configuração do aplicativo via JSON."""
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            config = {}
    else:
        config = {}
    return config


def salvar_config(config: dict):
    """Salva configuração geral em JSON."""
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)


# === Configuração de Estratégia (armazenada no SQLite) ===

def inicializar_tabela_configuracoes(db_path):
    """Garante que a tabela de configurações exista com valores padrão."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor REAL
        )
    """)
    # Valores padrão
    configs_iniciais = [
        ('bollinger_distancia', 0.5),
        ('stop_loss_perc', 2.0),
        ('trading_fee_perc', 0.1)
    ]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO configuracoes (chave, valor)
        VALUES (?, ?)
    """, configs_iniciais)
    
    conn.commit()
    conn.close()


def obter_bollinger_distancia(db_path):
    inicializar_tabela_configuracoes(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM configuracoes WHERE chave='bollinger_distancia'")
    row = cursor.fetchone()
    conn.close()
    return float(row[0]) if row else 0.5


def atualizar_bollinger_distancia(db_path, novo_valor: float):
    inicializar_tabela_configuracoes(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO configuracoes (chave, valor)
        VALUES ('bollinger_distancia', ?)
        ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor
    """, (novo_valor,))
    conn.commit()
    conn.close()


def obter_stop_loss(db_path):
    inicializar_tabela_configuracoes(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM configuracoes WHERE chave='stop_loss_perc'")
    row = cursor.fetchone()
    conn.close()
    return float(row[0]) if row else 2.0


def atualizar_stop_loss(db_path, novo_valor: float):
    inicializar_tabela_configuracoes(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO configuracoes (chave, valor)
        VALUES ('stop_loss_perc', ?)
        ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor
    """, (novo_valor,))
    conn.commit()
    conn.close()


def obter_taxa_corretagem(db_path):
    inicializar_tabela_configuracoes(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM configuracoes WHERE chave='trading_fee_perc'")
    row = cursor.fetchone()
    conn.close()
    return float(row[0]) if row else 0.1


def atualizar_taxa_corretagem(db_path, novo_valor: float):
    inicializar_tabela_configuracoes(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO configuracoes (chave, valor)
        VALUES ('trading_fee_perc', ?)
        ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor
    """, (novo_valor,))
    conn.commit()
    conn.close()