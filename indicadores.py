import pandas as pd
import numpy as np

def calcular_bollinger(df, periodo=20, num_desvios=2):
    """
    Calcula as Bandas de Bollinger e a Media Movel (SMA).

    Parametros:
        df: DataFrame com colunas 'close' para preco de fechamento.
        periodo: Periodo da Media Movel Simples (SMA). Padrao 20.
        num_desvios: Numero de desvios padrao para as bandas. Padrao 2.

    Retorna:
        DataFrame com colunas adicionais 'media', 'desvio', 'BB_up' e 'BB_down'.
    """
    # 1. Calcular a Media Movel Simples (SMA)
    df['media'] = df['close'].rolling(window=periodo).mean()

    # 2. Calcular o Desvio Padrao
    df['desvio'] = df['close'].rolling(window=periodo).std()

    # 3. Calcular Bandas de Bollinger
    df['BB_up'] = df['media'] + (df['desvio'] * num_desvios)
    df['BB_down'] = df['media'] - (df['desvio'] * num_desvios)

    return df

def adicionar_ema_tendencia(df, periodo_ema):
    """
    Calcula a Media Movel Exponencial (EMA) para filtro de tendencia.
    """
    col_name = f'ema_{periodo_ema}'
    df[col_name] = df['close'].ewm(span=periodo_ema, adjust=False).mean()
    return df

def calcular_rsi(df, periodo=14):
    """
    Calcula o RSI (Indice de Forca Relativa) padrao de 14 periodos.
    O RSI varia de 0 a 100 e sera usado como 'Nota' da tendencia.
    """
    delta = df['close'].diff()

    # Separa ganhos e perdas
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)

    # Media Movel Exponencial (Wilder's Smoothing)
    ewm_up = up.ewm(com=periodo - 1, adjust=False).mean()
    ewm_down = down.ewm(com=periodo - 1, adjust=False).mean()

    # Calculo do RS
    rs = ewm_up / ewm_down

    # Calculo do RSI (0 a 100)
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Preencher NaN iniciais com 50 (neutro) para nao quebrar logica
    df['rsi'] = df['rsi'].fillna(50)
    
    return df

def avaliar_tendencia_nota(df):
    """
    Atribui uma nota e um status ao mercado baseado no RSI.
    
    Classificacao solicitada:
    - 01 a 20: Franca Queda
    - 21 a 40: Queda
    - 41 a 60: Lateralizando
    - 61 a 80: Subida
    - 81 a 99: Franca Subida
    """
    # Define a nota como o valor arredondado do RSI
    df['nota_tendencia'] = df['rsi'].round(2)

    # Logica de classificacao vetorial (numpy select para performance)
    condicoes = [
        (df['nota_tendencia'] <= 20),
        (df['nota_tendencia'] > 20) & (df['nota_tendencia'] <= 40),
        (df['nota_tendencia'] > 40) & (df['nota_tendencia'] <= 60),
        (df['nota_tendencia'] > 60) & (df['nota_tendencia'] <= 80),
        (df['nota_tendencia'] > 80)
    ]

    escolhas = [
        "Franca Queda",
        "Queda",
        "Lateralizando",
        "Subida",
        "Franca Subida"
    ]

    df['status_tendencia'] = np.select(condicoes, escolhas, default="Indefinido")
    
    return df

def enriquecer_dados_analise(df):
    """
    Calcula indicadores adicionais para analise (ex: separacao de volume e nota de tendencia).
    Usa operacoes vetorizadas (numpy) para alta performance.
    """
    # Evita Warning de SettingWithCopy
    df = df.copy()

    # Separacao de volume baseada na cor do candle (Close > Open = Compra)
    # np.where eh muito mais rapido que apply
    df['volume_compra'] = np.where(df['close'] > df['open'], df['volume'], 0)
    df['volume_venda'] = np.where(df['close'] < df['open'], df['volume'], 0)
    
    # === NOVOS CALCULOS DE NOTA DE MERCADO ===
    df = calcular_rsi(df)
    df = avaliar_tendencia_nota(df)
    
    return df