import pandas as pd
from backtest import backtest_bollinger
from graficos import gerar_grafico_csv
from db_utils import listar_pares_disponiveis, listar_intervalos_disponiveis, carregar_candles
from relatorio_ia import gerar_relatorio_performance
from datetime import datetime, timedelta
import config
import os
import sqlite3

# === Pergunta/Atualiza configuração de bandas Bollinger ===
def definir_bollinger_distancia(db_path):
    valor_atual = config.obter_bollinger_distancia(db_path)
    print(f"\n⚙️  Distância atual das bordas de Bollinger: {valor_atual}%")
    alterar = input("Deseja alterar este valor? (S/N): ").strip().lower()

    if alterar == "s":
        try:
            novo_valor = float(input("Informe a nova distância percentual (ex: 0.5 para 0,5%): ").strip())
            config.atualizar_bollinger_distancia(db_path, novo_valor)
            print(f"✅ Novo valor salvo: {novo_valor}%")
            return novo_valor
        except ValueError:
            print("❌ Valor inválido. Mantendo valor anterior.")
            return valor_atual
    else:
        return valor_atual


# === Pergunta/Atualiza configuração de Stop Loss ===
def definir_stop_loss(db_path):
    valor_atual = config.obter_stop_loss(db_path)
    print(f"🛑 Stop Loss atual: {valor_atual}%")
    alterar = input("Deseja alterar este valor? (S/N): ").strip().lower()

    if alterar == "s":
        try:
            novo_valor = float(input("Informe o novo Stop Loss percentual (ex: 2.0 para 2%): ").strip())
            config.atualizar_stop_loss(db_path, novo_valor)
            print(f"✅ Novo Stop Loss salvo: {novo_valor}%")
            return novo_valor
        except ValueError:
            print("❌ Valor inválido. Mantendo valor anterior.")
            return valor_atual
    else:
        return valor_atual


# === Pergunta/Atualiza configuração de Taxa de Corretagem ===
def definir_taxa_corretagem(db_path):
    valor_atual = config.obter_taxa_corretagem(db_path)
    print(f"💸 Taxa de Corretagem atual (por ordem): {valor_atual}%")
    alterar = input("Deseja alterar este valor? (S/N): ").strip().lower()

    if alterar == "s":
        try:
            novo_valor = float(input("Informe a nova taxa percentual (ex: 0.1 para Binance Padrao): ").strip())
            config.atualizar_taxa_corretagem(db_path, novo_valor)
            print(f"✅ Nova Taxa salva: {novo_valor}%")
            return novo_valor
        except ValueError:
            print("❌ Valor inválido. Mantendo valor anterior.")
            return valor_atual
    else:
        return valor_atual


# === Pergunta sobre Filtro de Tendência ===
def definir_filtro_tendencia():
    print(f"\n📈 Filtro de Tendência (EMA)")
    print("Deseja ativar o filtro de tendência para esta análise?")
    print("Isso impedirá compras se o preço estiver abaixo da Média Móvel.")
    escolha = input("Digite 'S' para ativar ou ENTER para pular: ").strip().lower()
    
    if escolha == 's':
        periodo_str = input("Informe o período da EMA (Padrão 200): ").strip()
        if periodo_str.isdigit():
            return int(periodo_str)
        else:
            print("ℹ️ Usando padrão EMA 200.")
            return 200
    return None


# === Execução da análise ===
def executar_analise(caminho_db):
    try:
        # === Seleção do par ===
        pares = listar_pares_disponiveis(caminho_db)
        if not pares:
            print("⚠️ Nenhum par disponível no banco. Importe candles primeiro.")
            return

        print("\n📊 Pares disponíveis no banco:")
        for i, par in enumerate(pares, start=1):
            print(f"{i} - {par}")
        print("0 - Retornar ao menu")

        while True:
            escolha_par = input("Escolha o par: ").strip()
            if escolha_par == "0":
                return
            elif escolha_par.isdigit() and 1 <= int(escolha_par) <= len(pares):
                simbolo = pares[int(escolha_par) - 1]
                break
            else:
                print("❌ Opção inválida.")

        # === Seleção do intervalo ===
        intervalos = listar_intervalos_disponiveis(caminho_db, simbolo)
        if not intervalos:
            print("⚠️ Nenhum intervalo disponível para este par.")
            return

        print(f"\n⏱ Intervalos disponíveis para {simbolo}:")
        for i, inter in enumerate(intervalos, start=1):
            print(f"{i} - {inter}")
        print("0 - Retornar ao menu")

        while True:
            escolha_inter = input("Escolha o intervalo: ").strip()
            if escolha_inter == "0":
                return
            elif escolha_inter.isdigit() and 1 <= int(escolha_inter) <= len(intervalos):
                intervalo = intervalos[int(escolha_inter) - 1]
                break
            else:
                print("❌ Opção inválida.")

        # === Configurações da Estratégia ===
        distancia_bollinger = definir_bollinger_distancia(caminho_db)
        stop_loss_perc = definir_stop_loss(caminho_db)
        taxa_corretagem = definir_taxa_corretagem(caminho_db)
        
        # === Configuração da Estratégia Dinâmica ===
        print("\n🧠 --- ESTRATÉGIA DINÂMICA ---")
        
        # Input Lucro Mínimo (Filtro de Volatilidade)
        lucro_minimo = 0.0
        resp_lucro = input("Definir LUCRO MÍNIMO ESTIMADO por trade (ex: 0.5%) ou Enter p/ 0: ").strip()
        if resp_lucro:
            try:
                lucro_minimo = float(resp_lucro)
                print(f"ℹ️ Filtro ativo: Só entra se potencial > {lucro_minimo}% + taxas.")
            except:
                print("❌ Valor inválido. Usando 0.0%.")
        
        # --- ESTRATÉGIA ADAPTATIVA (RSI) ---
        print("\n🤖 [NOVO] Estratégia Adaptativa (RSI)")
        print("Se ativada, o robô decide automaticamente:")
        print(" - Nota < 20: Não entra (Hard Floor).")
        print(" - Nota 20 a 60: Sai na Banda Superior (Scalp).")
        print(" - Nota > 60: Ativa Trailing Stop e ignora Banda Superior (Surf).")
        
        usar_adaptativo = input("Ativar Estratégia Adaptativa? [S/N]: ").strip().upper() == "S"
        
        nota_minima = 0
        usar_trailing = False
        mover_alvo = False
        sair_banda = True
        
        if usar_adaptativo:
            print("✅ Estratégia Adaptativa ATIVADA. Parâmetros de saída serão automáticos.")
        else:
            # Configuração Manual Antiga
            resp_nota = input("Definir NOTA MÍNIMA de Tendência (0-100) para entrar (Ex: 30 para evitar Quedas): ").strip()
            if resp_nota.isdigit():
                nota_minima = int(resp_nota)
                print(f"🛡️ Filtro de Qualidade Ativo: Só compra se Nota >= {nota_minima}")
            
            usar_trailing = input("Usa Trailing Stop (Stop Móvel)? [S/N]: ").strip().upper() == "S"
            
            if usar_trailing:
                print("ℹ️ Com Trailing Stop ativo, você pode escolher como será a SAÍDA DE LUCRO:")
                print("1 - Sair na Banda Superior Fixa (Alvo Fixo)")
                print("2 - Sair na Banda Superior mas mover o alvo se preço subir (Alvo Móvel)")
                print("3 - Ignorar Banda e sair apenas pelo Stop Móvel (Trend Following)")
                
                tipo_saida = input("Escolha (1/2/3): ").strip()
                
                if tipo_saida == "3":
                    sair_banda = False
                    print("🚀 Modo TREND FOLLOWING ativado! Saída apenas pelo Stop Móvel.")
                elif tipo_saida == "2":
                    mover_alvo = True
                    print("🏃 Modo ALVO MÓVEL ativado! O alvo subirá junto com o preço.")
                else:
                    print("🎯 Modo ALVO FIXO padrão.")
        
        # Configuração Temporária (não salva no banco)
        periodo_ema = definir_filtro_tendencia()

        # === Seleção do período ===
        print(f"\n📅 Defina o intervalo de datas para análise ({simbolo} - {intervalo})")
        print("Formato: YYYY-MM-DD HH:MM:SS (exemplo: 2025-01-01 00:00:00)")

        while True:
            data_inicio_str = input("Data inicial (YYYY-MM-DD HH:MM:SS) ou 'R' para retornar: ").strip()
            if data_inicio_str.upper() == "R":
                return
            try:
                data_inicio_dt = datetime.strptime(data_inicio_str, "%Y-%m-%d %H:%M:%S")
                break
            except ValueError:
                print("❌ Formato inválido. Use: YYYY-MM-DD HH:MM:SS")

        # --- BUSCA A ÚLTIMA DATA DISPONÍVEL NO BANCO ---
        default_final_dt = data_inicio_dt + timedelta(hours=24) 
        try:
            conn_temp = sqlite3.connect(caminho_db)
            cursor_temp = conn_temp.cursor()
            tabela_alvo = f"candles_{simbolo.lower()}_{intervalo}"
            cursor_temp.execute(f"SELECT MAX(timestamp) FROM {tabela_alvo}")
            max_ts = cursor_temp.fetchone()[0]
            conn_temp.close()

            if max_ts:
                default_final_dt = datetime.fromtimestamp(max_ts / 1000)
        except Exception as e:
            pass

        data_final_str = input(f"Data final (ENTER = Máximo disponível → {default_final_dt.strftime('%Y-%m-%d %H:%M:%S')}): ").strip()
        
        if data_final_str == "":
            data_final_dt = default_final_dt
        else:
            try:
                data_final_dt = datetime.strptime(data_final_str, "%Y-%m-%d %H:%M:%S")
                if data_final_dt <= data_inicio_dt:
                    print("⚠️ A data final deve ser posterior à data inicial. Operação cancelada.")
                    return
            except ValueError:
                print("❌ Formato inválido para data final. Operação cancelada.")
                return

        data_inicio = data_inicio_dt.strftime("%Y-%m-%d %H:%M:%S")
        data_fim = data_final_dt.strftime("%Y-%m-%d %H:%M:%S")

        # === Carregar candles ===
        df = carregar_candles(caminho_db, simbolo, intervalo, data_inicio, data_fim)
        if df.empty:
            print("⚠️ Nenhum dado encontrado para o período.")
            return

        # === Salva na RAIZ (.) ===
        arquivo_csv_operacoes = f"operacoes_{simbolo}_{intervalo}.csv"
        saldo_inicial = 1000.0

        # === Backtest Bollinger com registro em CSV ===
        df, operacoes = backtest_bollinger(
            df, 
            distancia_bollinger, 
            stop_loss_perc=stop_loss_perc,
            taxa_corretagem=taxa_corretagem,
            periodo_ema=periodo_ema,
            saldo_inicial=saldo_inicial, 
            arquivo_operacoes=arquivo_csv_operacoes,
            usar_trailing_stop=usar_trailing,
            sair_na_banda_superior=sair_banda,
            mover_alvo_com_preco=mover_alvo,
            lucro_minimo_perc=lucro_minimo,
            nota_minima=nota_minima,
            estrategia_adaptativa=usar_adaptativo # Passando a nova flag
        )

        # === Gerar gráfico CSV ===
        gerar_grafico_csv(df, simbolo, intervalo, df['timestamp'].min(), df['timestamp'].max())
        
        # === EXIBIR RELATÓRIO E SALVAR NO ARQUIVO LOG ===
        if not operacoes:
            print("⚠️ Nenhuma operação realizada com estes parâmetros.")
        else:
            fechamentos = [op for op in operacoes if op[1] in ["VENDA", "STOP LOSS", "TRAILING STOP"]]
            
            total_ops_fechadas = len(fechamentos)
            wins = len([op for op in fechamentos if op[3] > 0])
            loss = len([op for op in fechamentos if op[3] <= 0])
            
            win_rate = (wins / total_ops_fechadas * 100) if total_ops_fechadas > 0 else 0.0
            
            saldo_final = operacoes[-1][4]
            lucro_total = saldo_final - 1000.0
            perc_lucro = (lucro_total / 1000.0) * 100

            timestamp_teste = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_completo = f"\n=== REGISTRO DE TESTE: {timestamp_teste} ===\n"
            log_completo += "█" * 50 + "\n"
            
            # --- SEÇÃO DE PARÂMETROS ---
            log_completo += "⚙️  PARÂMETROS UTILIZADOS:\n"
            log_completo += f"   - Par: {simbolo} | Intervalo: {intervalo}\n"
            log_completo += f"   - Período Analisado: {data_inicio} até {data_fim}\n"
            log_completo += f"   - Distância Bollinger: {distancia_bollinger}%\n"
            log_completo += f"   - Stop Loss Inicial: {stop_loss_perc}%\n"
            log_completo += f"   - Taxa Corretagem: {taxa_corretagem}%\n"
            log_completo += f"   - Filtro EMA: {'DESATIVADO' if not periodo_ema else f'ATIVO (Período {periodo_ema})'}\n"
            log_completo += f"   - Lucro Mínimo Exigido: {lucro_minimo}%\n"
            log_completo += f"   - Estratégia Adaptativa (RSI): {'ATIVADA' if usar_adaptativo else 'OFF'}\n"
            
            if not usar_adaptativo:
                log_completo += f"   - Nota Mínima (RSI): {nota_minima}\n"
                tipo_desc = "ALVO FIXO (Padrão)"
                if not sair_banda: tipo_desc = "TREND FOLLOWING (Sem Alvo)"
                elif mover_alvo: tipo_desc = "ALVO MÓVEL (Persegue Preço)"
                log_completo += f"   - Modo de Saída: {tipo_desc}\n"
                log_completo += f"   - Trailing Stop: {'ATIVO' if usar_trailing else 'DESATIVADO'}\n"
            else:
                log_completo += "   - Modos de Saída: Automático (Híbrido)\n"
                
            log_completo += "-" * 50 + "\n"
            # ---------------------------

            log_completo += f"📊 RELATÓRIO DE PERFORMANCE: {simbolo} ({intervalo})\n"
            log_completo += f"========================================\n"
            log_completo += f"💰 Saldo Inicial:    $ 1000.00\n"
            log_completo += f"💰 Saldo Final:      $ {saldo_final:.2f}\n"
            log_completo += f"📈 Lucro Líquido:    $ {lucro_total:.2f} ({perc_lucro:.2f}%)\n"
            log_completo += f"----------------------------------------\n"
            log_completo += f"🎲 Total Trades:     {total_ops_fechadas}\n"
            log_completo += f"✅ Acertos (Wins):   {wins} ({win_rate:.1f}%)\n"
            log_completo += f"❌ Erros (Losses):   {loss}\n"
            
            lucro_bruto = sum([op[3] for op in fechamentos if op[3] > 0])
            prejuizo_bruto = abs(sum([op[3] for op in fechamentos if op[3] < 0]))
            profit_factor = (lucro_bruto / prejuizo_bruto) if prejuizo_bruto > 0 else 0
            log_completo += f"⚖️ Profit Factor:     {profit_factor:.2f}\n"
            
            log_completo += f"========================================\n"
            log_completo += f"📄 Log detalhado salvo em: {arquivo_csv_operacoes}\n"
            
            log_completo += "\n📝 TODAS AS OPERAÇÕES REALIZADAS:\n"
            colunas = ["Data", "Ação", "Preço", "Lucro", "Saldo", "Nota", "Status"]
            df_ops = pd.DataFrame(operacoes, columns=colunas)
            
            # Exibir tudo
            log_completo += df_ops.to_string(index=False) + "\n"
            
            log_completo += "█" * 50 + "\n"

            print(log_completo)

            try:
                diretorio_atual = os.getcwd()
                caminho_log_geral = os.path.join(diretorio_atual, "outputTestes.log")
                print(f"📂 Tentando salvar log geral em: {caminho_log_geral}")
                with open(caminho_log_geral, "a", encoding="utf-8") as f:
                    f.write(log_completo + "\n")
                print(f"✅ Resultado salvo com sucesso em: {caminho_log_geral}")
            except Exception as e:
                print(f"⚠️ Erro ao salvar arquivo de log geral: {e}")

        print("\n✅ Análise concluída com sucesso!")

    except Exception as e:
        print("❌ Erro na análise técnica:", e)