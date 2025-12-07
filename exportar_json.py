import os
import sqlite3
import json
import pandas as pd
from datetime import datetime, timedelta
from db_utils import banco_possui_tabelas_candles, listar_pares_e_periodos

# === Exporta candles para JSON (.txt) ===
def exportar_candles_para_json_txt(db_path, par=None, periodo=None, data_inicio=None, data_fim=None):
    try:
        conn = sqlite3.connect(db_path)

        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'candles_%'")
        tabelas = [row[0] for row in cursor.fetchall()]

        if not tabelas:
            print("⚠️ Nenhuma tabela de candles encontrada no banco.")
            return

        if par:
            tabelas = [t for t in tabelas if f"candles_{par.lower()}_" in t]

        if periodo:
            tabelas = [t for t in tabelas if t.endswith(f"_{periodo}")]

        if not tabelas:
            print("⚠️ Nenhuma tabela correspondente aos filtros foi encontrada.")
            return

        # Salva na raiz do projeto (Diretório Atual de Trabalho)
        dir_saida = os.getcwd() 
        # os.makedirs(dir_saida, exist_ok=True) -> Não precisa pois raiz já existe

        for tabela in tabelas:
            partes = tabela.split("_")
            if len(partes) != 3:
                continue

            _, par_tabela, periodo_tabela = partes
            par_tabela = par_tabela.upper()

            print(f"\n📤 Exportando {par_tabela} ({periodo_tabela})...")

            query = f"SELECT * FROM {tabela}"
            params = []

            timestamp_inicio = None
            timestamp_fim = None
            if data_inicio:
                dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
                timestamp_inicio = int(dt_inicio.timestamp() * 1000)
            if data_fim:
                dt_fim = datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(hours=23, minutes=59, seconds=59)
                timestamp_fim = int(dt_fim.timestamp() * 1000)

            if timestamp_inicio and timestamp_fim:
                query += " WHERE timestamp BETWEEN ? AND ?"
                params = [timestamp_inicio, timestamp_fim]
            elif timestamp_inicio:
                query += " WHERE timestamp >= ?"
                params = [timestamp_inicio]
            elif timestamp_fim:
                query += " WHERE timestamp <= ?"
                params = [timestamp_fim]

            df = pd.read_sql_query(query, conn, params=params)

            if df.empty:
                print(f"⚠️ Nenhum registro encontrado para {par_tabela} ({periodo_tabela}) no intervalo informado.")
                continue

            # Adiciona coluna legível
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")

            # === Converte todos os Timestamps para string antes de exportar ===
            df_to_export = df.copy()
            for col in df_to_export.columns:
                if pd.api.types.is_datetime64_any_dtype(df_to_export[col]):
                    df_to_export[col] = df_to_export[col].dt.strftime("%Y-%m-%d %H:%M:%S")

            nome_arquivo = f"{par_tabela}_{periodo_tabela}.txt"
            caminho_arquivo = os.path.join(dir_saida, nome_arquivo)

            with open(caminho_arquivo, "w", encoding="utf-8") as f:
                json.dump(df_to_export.to_dict(orient="records"), f, indent=4, ensure_ascii=False)

            print(f"✅ Arquivo exportado com sucesso: {caminho_arquivo}")

        conn.close()

    except Exception as e:
        print(f"❌ Erro durante exportação: {e}")