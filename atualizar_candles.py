from datetime import datetime
from config import interval_map
from db_utils import listar_pares_disponiveis, importar_candles_binance
import sqlite3

def alimentar_sqlite_com_candles(db_path):
    """
    Interface para importação manual de candles da Binance.
    Coleta parâmetros do usuário e chama db_utils.importar_candles_binance.
    """
    print("\n📥 Importação Manual de Candles Históricos")

    # Detecta símbolos existentes usando a função centralizada (nome corrigido)
    symbols = listar_pares_disponiveis(db_path)

    if not symbols:
        print("⚠️ Nenhuma tabela de candles existente no banco.")
        symbol = input("Digite o par de moedas para iniciar (ex: BTCUSDT): ").strip().upper()
        if not symbol:
            print("❌ Nenhum par informado. Operação cancelada.")
            return
        symbols = [symbol]
    else:
        print("💱 Símbolos disponíveis no banco:")
        for s in symbols:
            print(f" - {s}")

        opcao = input("\nDeseja adicionar novo par? (s/n): ").strip().lower()
        if opcao == "s":
            novo_symbol = input("Digite o novo par (ex: ADAUSDT): ").strip().upper()
            if novo_symbol:
                symbols.append(novo_symbol)
            else:
                print("❌ Par inválido. Nenhum adicionado.")

    # Escolha de intervalo
    print("\n⏱️ Intervalos disponíveis:")
    for k in interval_map:
        print(f" - {k}")
    user_choice = input("Digite o intervalo desejado (ex: 1m, 5m, 1h): ").lower()

    if user_choice not in interval_map:
        print("❌ Intervalo inválido.")
        return

    interval = interval_map[user_choice]

    # Data inicial
    print("📅 Digite a data inicial para a importação.")
    start_str = input("Formato YYYY-MM-DD HH:MM:SS (ex: 2024-01-01 00:00:00): ").strip()
    
    try:
        datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        print("❌ Data inválida. Use o formato YYYY-MM-DD HH:MM:SS.")
        return

    # Atualiza cada símbolo da lista
    symbol_to_update = None
    if len(symbols) > 1:
        target = input(f"Digite o par para atualizar ou ENTER para TODOS ({', '.join(symbols)}): ").strip().upper()
        if target:
            if target in symbols:
                symbols = [target]
            else:
                # Se for um novo par que não estava na lista, adiciona
                symbols = [target]
    
    for symbol in symbols:
        print(f"\n📡 Iniciando importação para {symbol} em {user_choice}...")
        
        qtd = importar_candles_binance(db_path, symbol, interval, start_str=start_str)
        
        print(f"✅ {symbol}: {qtd} candles inseridos.")

    print("\n🏁 Importação manual concluída!")