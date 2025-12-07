import warnings
import os
import sys
from datetime import datetime, timedelta

# Suprimir avisos desnecessários
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Importações locais
from config import db_path, ler_config, salvar_config
from analise import executar_analise
from limpeza_backup import listar_e_apagar_backups
from exportar_excel import exportar_candles_para_excel
from atualizar_candles import alimentar_sqlite_com_candles
from db_utils import atualizar_banco, banco_possui_tabelas_candles, listar_pares_disponiveis
from exportar_json import exportar_candles_para_json_txt, listar_pares_e_periodos

# === Limpar Tela ===
def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

# === Entrada Segura com "R" para retorno ===
def entrada_segura(prompt):
    valor = input(prompt).strip()
    if valor.lower() == "r":
        raise SystemExit("MENU")
    return valor

# === Configurar Aplicativo ===
def configurar_aplicativo():
    print("\n⚙️ Configuração do Aplicativo")
    config = ler_config()
    caminho_atual = config.get("pasta_exports", "exports")
    print(f"📂 Caminho atual para exports: {caminho_atual}")
    novo_caminho = entrada_segura("Digite o novo caminho para salvar os exports: ").strip()
    if novo_caminho:
        config["pasta_exports"] = novo_caminho
        salvar_config(config)
        print(f"✅ Caminho atualizado para: {novo_caminho}")
    else:
        print("⚠️ Caminho não alterado.")

# === Menu Principal ===
def mostrar_menu():
    while True:
        try:
            limpar_tela()
            print("\n📋 MENU PRINCIPAL")
            print("1 - Análise Técnica (Suporte, Resistência e Backtest EMA9 x EMA21)")
            print("2 - Limpar Tabelas de Backup")
            print("3 - Exportar Candles para Excel com Gráfico")
            print("4 - Importar Candles Históricos (Binance → SQLite)")
            print("5 - Exportar Dados para JSON (.txt)")
            print("6 - Adicionar Novo Par de Moedas")
            print("7 - Configurar Aplicativo (caminho de exports)")
            print("0 - Sair")

            escolha = entrada_segura("\nEscolha uma opção: ")

            # === 1 - Análise Técnica ===
            if escolha == "1":
                limpar_tela()
                try:
                    executar_analise(db_path)
                except SystemExit as e:
                    if str(e) == "MENU":
                        continue
                    else:
                        raise
                entrada_segura("\nPressione Enter para voltar ao menu...")

            # === 2 - Limpeza de Backups ===
            elif escolha == "2":
                limpar_tela()
                listar_e_apagar_backups(db_path)
                entrada_segura("\nPressione Enter para voltar ao menu...")

            # === 3 - Exportar para Excel ===
            elif escolha == "3":
                limpar_tela()
                exportar_candles_para_excel(db_path)
                entrada_segura("\nPressione Enter para voltar ao menu...")

            # === 4 - Importar Candles Históricos ===
            elif escolha == "4":
                limpar_tela()
                alimentar_sqlite_com_candles(db_path)
                entrada_segura("\nPressione Enter para voltar ao menu...")

            # === 5 - Exportar para JSON (.txt) ===
            elif escolha == "5":
                limpar_tela()
                pares = listar_pares_e_periodos(db_path)

                if not pares:
                    print("⚠️ Nenhuma tabela de candles encontrada para exportação.")
                    entrada_segura("\nPressione Enter para voltar ao menu...")
                    continue

                # Seleção de par
                print("📊 Pares disponíveis:\n")
                pares_lista = list(pares.keys())
                for i, par in enumerate(pares_lista, start=1):
                    print(f"{i} - {par}")
                print("0 - Exportar TODOS os pares / Voltar ao menu")
                escolha_par = entrada_segura("\nEscolha o par: ")
                if escolha_par == "0":
                    exportar_candles_para_json_txt(db_path)
                    entrada_segura("\nPressione Enter para voltar ao menu...")
                    continue
                elif escolha_par.isdigit() and 1 <= int(escolha_par) <= len(pares_lista):
                    par_escolhido = pares_lista[int(escolha_par) - 1]
                else:
                    print("❌ Opção inválida.")
                    entrada_segura("\nPressione Enter para voltar ao menu...")
                    continue

                # Seleção de período
                periodos = pares[par_escolhido]
                print(f"\n⏱ Períodos disponíveis para {par_escolhido}:\n")
                for i, periodo in enumerate(periodos, start=1):
                    print(f"{i} - {periodo}")
                print("0 - Exportar TODOS os períodos / Voltar ao menu")
                escolha_periodo = entrada_segura("\nEscolha o período: ")
                if escolha_periodo == "0":
                    exportar_candles_para_json_txt(db_path, par=par_escolhido)
                    entrada_segura("\nPressione Enter para voltar ao menu...")
                    continue
                elif escolha_periodo.isdigit() and 1 <= int(escolha_periodo) <= len(periodos):
                    periodo_escolhido = periodos[int(escolha_periodo) - 1]
                else:
                    print("❌ Opção inválida.")
                    entrada_segura("\nPressione Enter para voltar ao menu...")
                    continue

                # Datas
                print(f"\n📅 Defina o intervalo de datas para exportação ({par_escolhido.upper()} - {periodo_escolhido})")
                data_inicio = entrada_segura("Data inicial (YYYY-MM-DD HH:MM:SS) [Enter para mínimo disponível]: ") or None
                data_fim = entrada_segura("Data final (YYYY-MM-DD HH:MM:SS) [Enter para máximo disponível]: ") or None

                exportar_candles_para_json_txt(
                    db_path,
                    par=par_escolhido,
                    periodo=periodo_escolhido,
                    data_inicio=data_inicio,
                    data_fim=data_fim
                )
                entrada_segura("\nPressione Enter para voltar ao menu...")

            # === 6 - Adicionar novo par ===
            elif escolha == "6":
                limpar_tela()
                novo_par = entrada_segura("Digite o novo par (ex: ADAUSDT) ou 0 para voltar: ").upper()
                if novo_par == "0":
                    continue
                if novo_par:
                    print(f"📡 Criando tabelas para {novo_par}...")
                    atualizar_banco(db_path, novo_par)
                else:
                    print("❌ Par inválido.")
                entrada_segura("\nPressione Enter para voltar ao menu...")

            # === 7 - Configurar Aplicativo ===
            elif escolha == "7":
                limpar_tela()
                configurar_aplicativo()
                entrada_segura("\nPressione Enter para voltar ao menu...")

            # === 0 - Sair ===
            elif escolha == "0":
                limpar_tela()
                print("👋 Encerrando o programa. Até mais!")
                break

            else:
                print("❌ Opção inválida. Pressione Enter para tentar novamente.")
                entrada_segura("")

        except SystemExit as e:
            if str(e) == "MENU":
                continue
            else:
                raise

# === Execução Inicial ===
def main():
    try:
        limpar_tela()
        print("🚀 Iniciando sistema...")

        if banco_possui_tabelas_candles(db_path):
            print("✅ Tabelas de candles encontradas.")
            print("📡 Atualizando automaticamente todas as tabelas de candles para todos os pares...")
            # Atualiza todas as tabelas de todos os pares
            pares = listar_pares_disponiveis(db_path)
            for par in pares:
                atualizar_banco(db_path, par)
        else:
            print("⚠️ Nenhuma tabela de candles encontrada.")
            simbolo = input("Digite o par de moedas inicial (ex: BTCUSDT): ").upper()
            if simbolo:
                atualizar_banco(db_path, simbolo)
            else:
                print("❌ Nenhum par informado. O programa iniciará sem dados.")

        entrada_segura("\nPressione Enter para continuar...")
        limpar_tela()
        mostrar_menu()

    except SystemExit as e:
        if str(e) == "MENU":
            limpar_tela()
            mostrar_menu()
        else:
            raise

if __name__ == "__main__":
    main()
