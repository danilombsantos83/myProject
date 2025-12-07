import pandas as pd

def gerar_relatorio_performance(operacoes, saldo_inicial, simbolo, intervalo):
    """
    Gera um relatório estatístico textual formatado para análise de IA.
    Calcula Win Rate, Profit Factor, Drawdown e lista operações compactadas.
    """
    if not operacoes:
        return "⚠️ Nenhuma operação realizada no período."

    # Converter lista de tuplas em DataFrame (Agora com 7 colunas)
    df_ops = pd.DataFrame(operacoes, columns=["timestamp", "tipo", "preco", "lucro", "saldo", "nota", "status"])
    
    # Filtrar apenas as linhas de saída (onde o lucro/prejuízo é realizado)
    df_saidas = df_ops[df_ops['tipo'].isin(['VENDA', 'STOP LOSS', 'TRAILING STOP'])].copy()
    
    if df_saidas.empty:
        return "⚠️ Nenhuma operação fechada (apenas compras em aberto ou sem trades)."

    # === Cálculos Estatísticos ===
    qtd_trades = len(df_saidas)
    qtd_vitorias = len(df_saidas[df_saidas['lucro'] > 0])
    qtd_derrotas = len(df_saidas[df_saidas['lucro'] <= 0])
    win_rate = (qtd_vitorias / qtd_trades) * 100

    lucro_bruto = df_saidas[df_saidas['lucro'] > 0]['lucro'].sum()
    prejuizo_bruto = abs(df_saidas[df_saidas['lucro'] <= 0]['lucro'].sum())
    
    # Profit Factor (evita divisão por zero)
    profit_factor = lucro_bruto / prejuizo_bruto if prejuizo_bruto > 0 else float('inf')

    saldo_final = df_saidas.iloc[-1]['saldo']
    resultado_total = saldo_final - saldo_inicial
    resultado_perc = (resultado_total / saldo_inicial) * 100

    # === Cálculo de Drawdown Máximo ===
    # O Drawdown é calculado sobre o histórico de saldo trade a trade
    saldos = df_ops['saldo'].values
    pico = saldos[0]
    max_drawdown_perc = 0.0

    peak = saldo_inicial
    for s in saldos:
        if s > peak:
            peak = s
        dd = (peak - s) / peak
        if dd > max_drawdown_perc:
            max_drawdown_perc = dd
            
    max_drawdown_perc *= 100  # Converter para %

    # === Formatação do Relatório ===
    relatorio = []
    relatorio.append(f"📊 RELATÓRIO DE PERFORMANCE: {simbolo} ({intervalo})")
    relatorio.append("=" * 40)
    relatorio.append(f"💰 Saldo Inicial:   $ {saldo_inicial:.2f}")
    relatorio.append(f"💰 Saldo Final:     $ {saldo_final:.2f}")
    relatorio.append(f"📈 Lucro Líquido:   $ {resultado_total:.2f} ({resultado_perc:+.2f}%)")
    relatorio.append("-" * 40)
    relatorio.append(f"🎲 Total Trades:     {qtd_trades}")
    relatorio.append(f"✅ Acertos (Wins):   {qtd_vitorias} ({win_rate:.1f}%)")
    relatorio.append(f"❌ Erros (Losses):   {qtd_derrotas}")
    relatorio.append(f"⚖️ Profit Factor:    {profit_factor:.2f}")
    relatorio.append(f"📉 Max Drawdown:     {max_drawdown_perc:.2f}%")
    relatorio.append("=" * 40)
    
    # === Mini Log de Operações (CSV Compacto para Análise) ===
    relatorio.append("\n📋 LOG DE OPERAÇÕES (Copie para análise):")
    relatorio.append("timestamp;tipo;preco;lucro;saldo;nota;status")
    
    for _, row in df_ops.iterrows():
        # Formata timestamp para ficar curto
        ts_str = row['timestamp'].strftime('%Y-%m-%d %H:%M')
        tipo = row['tipo']
        preco = f"{row['preco']:.5f}" # 5 casas decimais para cripto
        lucro = f"{row['lucro']:.2f}"
        saldo_op = f"{row['saldo']:.2f}"
        nota = f"{row['nota']:.0f}"
        status = row['status']
        
        relatorio.append(f"{ts_str};{tipo};{preco};{lucro};{saldo_op};{nota};{status}")

    return "\n".join(relatorio)