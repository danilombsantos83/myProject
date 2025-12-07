import os
import plotly.graph_objects as go

def gerar_grafico_csv(df, simbolo, intervalo, data_inicial, data_final):
    # Salva na raiz
    pasta_saida = "." 
    
    nome_base = f"{simbolo}_{intervalo}_{data_inicial.strftime('%Y%m%d')}_{data_final.strftime('%Y%m%d')}"
    caminho_csv = os.path.join(pasta_saida, nome_base + ".csv")
    df.to_csv(caminho_csv, index=False, encoding="utf-8-sig")

    print(f"\n💾 CSV salvo em: {caminho_csv}")

    fig = go.Figure()

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='Candles'
    ))

    # Bandas de Bollinger
    if 'BB_up' in df.columns and 'BB_down' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['BB_up'],
            name='Banda Superior',
            line=dict(color='rgba(0,255,0,0.5)', width=1)
        ))
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['BB_down'],
            name='Banda Inferior',
            line=dict(color='rgba(255,0,0,0.5)', width=1),
            fill='tonexty',
            fillcolor='rgba(200,200,200,0.1)'
        ))

    # Média
    if 'media' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['media'],
            name='Média (20)',
            line=dict(color='rgba(255,255,255,0.3)', width=1)
        ))

    # Volume de compra e venda
    if 'volume_compra' in df.columns and 'volume_venda' in df.columns:
        fig.add_trace(go.Bar(
            x=df['timestamp'],
            y=df['volume_compra'],
            name='Volume Compra',
            marker_color='green',
            yaxis='y2',
            opacity=0.5
        ))
        fig.add_trace(go.Bar(
            x=df['timestamp'],
            y=df['volume_venda'],
            name='Volume Venda',
            marker_color='red',
            yaxis='y2',
            opacity=0.5
        ))

    # Layout com eixo secundário
    fig.update_layout(
        title=f'{simbolo.upper()} - {intervalo} ({data_inicial:%d/%m/%Y} → {data_final:%d/%m/%Y})',
        xaxis_title='Timestamp',
        yaxis_title='Preço',
        yaxis2=dict(title='Volume', overlaying='y', side='right', showgrid=False),
        template='plotly_dark',
        hovermode='x unified',
        width=1200,
        height=700
    )

    # Salvar HTML na raiz
    caminho_html = os.path.join(pasta_saida, nome_base + ".html")
    fig.write_html(caminho_html)
    print(f"🌐 Gráfico salvo em HTML: {caminho_html}")

    fig.show()