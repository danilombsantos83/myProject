import pandas as pd
import numpy as np
from backtest import backtest_bollinger
from db_utils import listar_pares_disponiveis, listar_intervalos_disponiveis, carregar_candles
from datetime import datetime, timedelta
import sqlite3
import os
import time

def inicializar_tabela_resultados(db_path):
    """Cria a tabela de resultados se não existir."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resultados_otimizacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_execucao TEXT,
            simbolo TEXT,
            intervalo TEXT,
            distancia_banda REAL,
            stop_loss REAL,
            nota_minima INTEGER,
            ema_periodo INTEGER,
            lucro_minimo REAL,
            lucro_liquido REAL,
            win_rate REAL,
            total_trades INTEGER,
            profit_factor REAL
        )
    """)
    conn.commit()
    conn.close()

def salvar_lote_resultados(db_path, dados):
    """Salva uma lista de resultados no banco de uma só vez."""
    if not dados:
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = """
        INSERT INTO resultados_otimizacao (
            data_execucao, simbolo, intervalo, 
            distancia_banda, stop_loss, nota_minima, ema_periodo, lucro_minimo,
            lucro_liquido, win_rate, total_trades, profit_factor
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    cursor.executemany(query, dados)
    conn.commit()
    conn.close()

def executar_otimizacao(db_path):
    print("\n🚀 === OTIMIZADOR DE PARÂMETROS (GRID SEARCH 5D -> SQL) ===")
    print("Testando variáveis e salvando em BANCO DE DADOS.\n")

    # === 1. Seleção do Par e Intervalo ===
    pares = listar_pares_disponiveis(db_path)
    if not pares:
        print("⚠️ Nenhum dado disponível.")
        return

    print("📊 Escolha o Par:")
    for i, par in enumerate(pares, start=1):
        print(f"{i} - {par}")
    
    escolha_par = input("Opção: ").strip()
    if not escolha_par.isdigit() or int(escolha_par) < 1 or int(escolha_par) > len(pares):
        print("❌ Opção inválida.")
        return
    simbolo = pares[int(escolha_par) - 1]

    intervalos = listar_intervalos_disponiveis(db_path, simbolo)
    print(f"\n⏱ Escolha o Intervalo (Recomendado: 1h):")
    for i, inter in enumerate(intervalos, start=1):
        print(f"{i} - {inter}")
    
    escolha_inter = input("Opção: ").strip()
    if not escolha_inter.isdigit() or int(escolha_inter) < 1 or int(escolha_inter) > len(intervalos):
        print("❌ Opção inválida.")
        return
    intervalo = intervalos[int(escolha_inter) - 1]

    # === 2. Seleção de Datas ===
    print(f"\n📅 Período de Teste para {simbolo} - {intervalo}")
    data_inicio_str = input("Data Inicial (YYYY-MM-DD HH:MM:SS) ou Enter para Automático: ").strip()
    
    if not data_inicio_str:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            tbl = f"candles_{simbolo.lower()}_{intervalo}"
            cursor.execute(f"SELECT MIN(timestamp) FROM {tbl}")
            min_ts = cursor.fetchone()[0]
            conn.close()
            data_inicio = datetime.fromtimestamp(min_ts/1000).strftime("%Y-%m-%d %H:%M:%S")
        except:
            print("❌ Erro ao buscar datas.")
            return
    else:
        data_inicio = data_inicio_str

    data_fim = input("Data Final (YYYY-MM-DD HH:MM:SS) ou Enter para Hoje: ").strip()
    if not data_fim:
        data_fim = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # === 3. Definição dos Ranges de Teste ===
    print("\n⚙️  Configurando Grade de Testes Completa...")
    
    # 5 DIMENSÕES DE TESTE (Conforme solicitado)
    # Incluindo distâncias negativas e positivas
    distancias = [-2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    stops = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    notas = [20, 30, 40, 50, 60]
    emas = [70, 80, 90, 100, 110]
    lucros = [0.0, 0.1, 0.2, 0.3]
    
    total_combinacoes = len(distancias) * len(stops) * len(notas) * len(emas) * len(lucros)
    print(f"🔄 Total de simulações a executar: {total_combinacoes}")
    print("⚠️  Isso pode levar alguns minutos. Os resultados serão salvos no DB.")
    input("Pressione Enter para iniciar...")

    # === 4. Carregamento dos Dados ===
    print("\n⏳ Carregando candles na memória...")
    df_base = carregar_candles(db_path, simbolo, intervalo, data_inicio, data_fim)
    
    if df_base.empty:
        print("❌ Nenhum candle encontrado.")
        return

    # Inicializa tabela no banco
    inicializar_tabela_resultados(db_path)

    # === 5. Loop de Otimização ===
    dados_para_salvar = []
    resultados_memoria = [] # Apenas para exibir o top 3 no final no console
    
    print("\n▶️  Iniciando execuções...")
    print(f"{'Dist':<4} | {'Stop':<4} | {'Nota':<4} | {'EMA':<4} | {'Min%':<4} | {'Lucro($)':<10} | {'Win%':<6}")
    print("-" * 65)

    start_time = time.time()
    contador = 0
    data_execucao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for dist in distancias:
        for stop in stops:
            for nota in notas:
                for ema in emas:
                    for lucro_min in lucros:
                        contador += 1
                        
                        # Executa o backtest
                        _, operacoes = backtest_bollinger(
                            df_base.copy(),
                            distancia_bollinger=float(dist),
                            stop_loss_perc=stop,
                            taxa_corretagem=0.1,
                            periodo_ema=int(ema),
                            saldo_inicial=1000.0,
                            arquivo_operacoes=None,
                            usar_trailing_stop=True,
                            sair_na_banda_superior=True,
                            mover_alvo_com_preco=False,
                            lucro_minimo_perc=lucro_min,
                            nota_minima=nota,
                            estrategia_adaptativa=True
                        )
                        
                        # Calcula métricas
                        if operacoes:
                            saldo_final = operacoes[-1][4]
                            lucro = saldo_final - 1000.0
                            
                            fechamentos = [op for op in operacoes if op[1] in ["VENDA", "STOP LOSS", "TRAILING STOP"]]
                            total_trades = len(fechamentos)
                            wins = len([op for op in fechamentos if op[3] > 0])
                            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
                            
                            lucro_bruto = sum([op[3] for op in fechamentos if op[3] > 0])
                            prejuizo_bruto = abs(sum([op[3] for op in fechamentos if op[3] < 0]))
                            profit_factor = (lucro_bruto / prejuizo_bruto) if prejuizo_bruto > 0 else 0
                        else:
                            lucro = 0.0
                            win_rate = 0.0
                            total_trades = 0
                            profit_factor = 0.0
                        
                        # Se houve trades, prepara para salvar
                        if total_trades > 0:
                            # Tupla para o SQLite
                            registro_db = (
                                data_execucao, simbolo, intervalo,
                                float(dist), stop, nota, int(ema), lucro_min,
                                lucro, win_rate, total_trades, profit_factor
                            )
                            dados_para_salvar.append(registro_db)
                            
                            # Dicionário para ranking em memória (console)
                            registro_memoria = {
                                "dist": dist, "stop": stop, "nota": nota,
                                "ema": ema, "lucro_min": lucro_min,
                                "lucro": lucro, "win_rate": win_rate,
                                "trades": total_trades
                            }
                            resultados_memoria.append(registro_memoria)
                            
                            # Feedback visual se for lucrativo
                            if lucro > 0:
                                 print(f"{dist:<4} | {stop:<4} | {nota:<4} | {ema:<4} | {lucro_min:<4.1f} | {lucro:<10.2f} | {win_rate:<6.1f}")

                        # Salva em lotes de 500 para não ocupar muita memória RAM
                        if len(dados_para_salvar) >= 500:
                            salvar_lote_resultados(db_path, dados_para_salvar)
                            dados_para_salvar = []

    # Salva o restante
    if dados_para_salvar:
        salvar_lote_resultados(db_path, dados_para_salvar)

    tempo_total = time.time() - start_time
    print(f"\n✅ Finalizado em {tempo_total:.2f} segundos.")
    print("💾 Todos os resultados foram salvos na tabela 'resultados_otimizacao'.")

    # === 6. Exibição Rápida dos Campeões (Console) ===
    print("\n" + "="*50)
    print("🏆 TOP 3 DESTA EXECUÇÃO")
    print("="*50)
    
    if not resultados_memoria:
        print("⚠️ Nenhum trade realizado.")
        return

    ranking = sorted(resultados_memoria, key=lambda x: x['lucro'], reverse=True)
    
    def print_setup(rank, r):
        print(f"\n{rank} LUGAR (Lucro: $ {r['lucro']:.2f} | Win: {r['win_rate']:.1f}%)")
        print(f"   ➤ Parâmetros: Dist {r['dist']}% | Stop {r['stop']}% | Nota {r['nota']} | EMA {r['ema']} | Min {r['lucro_min']}%")

    print_setup("🥇 PRIMEIRO", ranking[0])
    
    if len(ranking) > 1:
        print_setup("🥈 SEGUNDO", ranking[1])

    if len(ranking) > 2:
        print_setup("🥉 TERCEIRO", ranking[2])

    input("\nPressione Enter para voltar ao menu...")