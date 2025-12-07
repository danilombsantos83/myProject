# limpeza_backup.py

import sqlite3

def listar_e_apagar_backups(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Buscar nomes de todas as tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelas = [row[0] for row in cursor.fetchall()]

    # Filtrar as que são de backup
    tabelas_backup = [t for t in tabelas if "_backup_" in t]

    if not tabelas_backup:
        print("ℹ️ Nenhuma tabela de backup encontrada.")
        conn.close()
        return

    print("\n📦 Tabelas de backup encontradas:")
    for t in tabelas_backup:
        print(f" - {t}")

    confirmacao = input("⚠️ Deseja apagar todas essas tabelas de backup? (s/n): ").lower()
    if confirmacao != 's':
        print("❌ Operação cancelada.")
        conn.close()
        return

    # Deletar tabelas de backup
    for t in tabelas_backup:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {t}")
            print(f"🧹 Tabela '{t}' removida com sucesso.")
        except Exception as e:
            print(f"❌ Erro ao remover '{t}': {e}")

    conn.commit()
    conn.close()
    print("✅ Limpeza concluída.")
