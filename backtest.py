from indicadores import calcular_bollinger, enriquecer_dados_analise, adicionar_ema_tendencia
import pandas as pd
import os

def backtest_bollinger(df, distancia_bollinger=0.5, stop_loss_perc=None, taxa_corretagem=0.0, periodo_ema=None, saldo_inicial=1000.0, arquivo_operacoes=None, usar_trailing_stop=False, sair_na_banda_superior=True, mover_alvo_com_preco=False, lucro_minimo_perc=0.0, nota_minima=0, estrategia_adaptativa=False):
    """
    Realiza backtest de Bollinger.
    Se estrategia_adaptativa=True, ignora os parametros fixos de saida e decide baseado no RSI.
    """
    # === Preparação dos Dados ===
    df = calcular_bollinger(df)
    
    # Se houver filtro de tendência configurado para esta execução
    col_ema = None
    if periodo_ema:
        df = adicionar_ema_tendencia(df, periodo_ema)
        col_ema = f'ema_{periodo_ema}'
        
    # Aqui os dados ganham RSI, Nota e Status de Tendência
    df = enriquecer_dados_analise(df)
    
    operacoes = []
    logs_para_csv = []
    
    posicao = None
    preco_entrada = 0
    preco_stop = 0
    preco_alvo_dinamico = 0 
    maximo_atingido = 0     
    
    saldo = saldo_inicial
    quantidade_ativos = 0.0
    
    margem = distancia_bollinger / 100
    fator_stop = 1 - (stop_loss_perc / 100) if stop_loss_perc else 0
    taxa_multiplier = taxa_corretagem / 100 

    # Variáveis de controle de estado da estratégia (para quando já estiver comprado)
    modo_saida_atual = "PADRAO" # Apenas para log

    # === Loop Único de Execução ===
    for i in range(1, len(df)):
        candle = df.iloc[i]
        preco = candle["close"]
        timestamp = candle["timestamp"]
        
        # Captura dados de tendência
        nota_tendencia = candle.get("nota_tendencia", 50)
        status_tendencia = candle.get("status_tendencia", "Indefinido")
        
        # === DEFINIÇÃO DINÂMICA DE COMPORTAMENTO ===
        if estrategia_adaptativa:
            # 1. Filtro de Segurança (Hard Floor)
            # Se adaptativo, nunca compra abaixo de 20 (Franca Queda) - AJUSTADO PARA 20
            filtro_adaptativo_ok = (nota_tendencia >= 20)
            
            # 2. Definição de Saída baseada na força atual
            if nota_tendencia > 60:
                # Tendência Forte: Tenta alongar o trade
                usar_trailing_agora = True
                sair_banda_agora = False # Ignora o teto da banda para deixar subir
                modo_log = "TREND"
            else:
                # Mercado Lateral ou Fraco: Garante o lucro na banda
                usar_trailing_agora = False
                sair_banda_agora = True
                modo_log = "SCALP"
        else:
            # Usa os parâmetros fixos escolhidos pelo usuário
            filtro_adaptativo_ok = True
            usar_trailing_agora = usar_trailing_stop
            sair_banda_agora = sair_na_banda_superior
            modo_log = "FIXO"

        acao = "N/A"
        lucro_operacao = 0
        
        # --- ATUALIZAÇÃO DINÂMICA (Se comprado) ---
        if posicao == "COMPRA":
            # 1. Trailing Stop (Se ativo neste momento)
            if stop_loss_perc and usar_trailing_agora:
                novo_stop_calculado = preco * fator_stop
                if novo_stop_calculado > preco_stop:
                    preco_stop = novo_stop_calculado
            
            # 2. Alvo Móvel
            if mover_alvo_com_preco and sair_banda_agora:
                if preco > maximo_atingido:
                    diferenca = preco - maximo_atingido
                    preco_alvo_dinamico += diferenca 
                    maximo_atingido = preco           

        # --- VERIFICAÇÃO DE SAÍDA PELO STOP ---
        if posicao == "COMPRA" and stop_loss_perc:
            if preco <= preco_stop:
                valor_bruto = quantidade_ativos * preco
                custo_taxa = valor_bruto * taxa_multiplier
                valor_liquido = valor_bruto - custo_taxa
                
                lucro_operacao = valor_liquido - (quantidade_ativos * preco_entrada) 
                saldo = valor_liquido
                
                posicao = None
                acao = "STOP LOSS" if lucro_operacao < 0 else "TRAILING STOP" 
                
                operacoes.append((timestamp, acao, preco, lucro_operacao, saldo, nota_tendencia, status_tendencia))
                
                if arquivo_operacoes:
                    logs_para_csv.append({
                        "timestamp": timestamp, "acao": acao, "preco": preco, 
                        "lucro": lucro_operacao, "saldo": saldo, 
                        "volume_compra": candle["volume_compra"], "volume_venda": candle["volume_venda"],
                        "nota_tendencia": nota_tendencia, "status_tendencia": status_tendencia
                    })
                continue 

        # --- Lógica de COMPRA ---
        if posicao is None and preco <= candle["BB_down"] * (1 + margem):
            
            tendencia_ok = True
            
            # Filtros Fixos
            if col_ema and preco <= candle[col_ema]:
                tendencia_ok = False
            
            if nota_tendencia < nota_minima:
                tendencia_ok = False
                
            # Filtro Adaptativo
            if estrategia_adaptativa and not filtro_adaptativo_ok:
                tendencia_ok = False
            
            # Cálculos de Potencial
            alvo_estimado = candle["BB_up"] * (1 - margem)
            lucro_bruto_potencial_valor = alvo_estimado - preco
            custo_total_est = (preco * taxa_multiplier) + (alvo_estimado * taxa_multiplier)
            margem_lucro_exigida = preco * (lucro_minimo_perc / 100.0)
            
            valida_lucro = lucro_bruto_potencial_valor > (custo_total_est + margem_lucro_exigida)

            if tendencia_ok and valida_lucro:
                custo_taxa = saldo * taxa_multiplier
                valor_para_investir = saldo - custo_taxa
                quantidade_ativos = valor_para_investir / preco
                
                posicao = "COMPRA"
                preco_entrada = preco
                maximo_atingido = preco 
                
                if stop_loss_perc:
                    preco_stop = preco_entrada * fator_stop
                
                preco_alvo_dinamico = alvo_estimado

                acao = "COMPRA"
                operacoes.append((timestamp, "COMPRA", preco, 0, valor_para_investir, nota_tendencia, status_tendencia))
                
                if arquivo_operacoes:
                    logs_para_csv.append({
                        "timestamp": timestamp, "acao": acao, "preco": preco, 
                        "lucro": 0, "saldo": valor_para_investir, 
                        "volume_compra": candle["volume_compra"], "volume_venda": candle["volume_venda"],
                        "nota_tendencia": nota_tendencia, "status_tendencia": status_tendencia
                    })
        
        # --- Lógica de VENDA (Alvo / Banda) ---
        elif sair_banda_agora and posicao == "COMPRA":
            # Se estiver no modo adaptativo de tendência, sair_banda_agora será False, então ele não entra aqui
            # e só sai pelo Stop Móvel (Trailing).
            
            target_check = preco_alvo_dinamico if mover_alvo_com_preco else (candle["BB_up"] * (1 - margem))
            
            if preco >= target_check:
                valor_bruto = quantidade_ativos * preco
                custo_taxa = valor_bruto * taxa_multiplier
                valor_liquido = valor_bruto - custo_taxa
                
                lucro_operacao = valor_liquido - (quantidade_ativos * preco_entrada)
                saldo = valor_liquido
                
                posicao = None
                acao = "VENDA"
                
                operacoes.append((timestamp, "VENDA", preco, lucro_operacao, saldo, nota_tendencia, status_tendencia))
        
                if arquivo_operacoes:
                    logs_para_csv.append({
                        "timestamp": timestamp, "acao": acao, "preco": preco, 
                        "lucro": lucro_operacao, "saldo": saldo, 
                        "volume_compra": candle["volume_compra"], "volume_venda": candle["volume_venda"],
                        "nota_tendencia": nota_tendencia, "status_tendencia": status_tendencia
                    })

    # === Escrita do CSV ===
    if arquivo_operacoes and logs_para_csv:
        pasta = os.path.dirname(arquivo_operacoes)
        if pasta and not os.path.exists(pasta):
            os.makedirs(pasta, exist_ok=True)
        df_logs = pd.DataFrame(logs_para_csv)
        
        colunas_ordem = ["timestamp", "acao", "preco", "lucro", "saldo", "nota_tendencia", "status_tendencia", "volume_compra", "volume_venda"]
        
        cols_existentes = [c for c in colunas_ordem if c in df_logs.columns]
        df_logs = df_logs[cols_existentes]
        
        df_logs.to_csv(arquivo_operacoes, index=False, sep=";", encoding="utf-8-sig")

    return df, operacoes