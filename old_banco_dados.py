import sqlite3
import pandas as pd

# === Carregar candles do banco ===
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