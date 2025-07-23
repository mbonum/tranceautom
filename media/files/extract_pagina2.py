#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per convertire la SECONDA PAGINA di Pianificazione_MARE25.xlsx in CSV
"""

import pandas as pd
from pathlib import Path


def excel_pagina2_to_csv(nome_file_excel, nome_csv="pianificazione_MARE25_pagina2.csv"):
    """
    Converte la seconda pagina del file Excel in CSV

    Args:
        nome_file_excel (str): Nome del file Excel
        nome_csv (str): Nome del file CSV di output
    """

    try:
        print(f"📊 CONVERSIONE SECONDA PAGINA: {nome_file_excel} → {nome_csv}")
        print("=" * 60)

        # Verifica che il file esista
        if not Path(nome_file_excel).exists():
            print(f"❌ ERRORE: Il file {nome_file_excel} non esiste!")
            return False

        # Prima vediamo quali pagine ci sono
        xl_file = pd.ExcelFile(nome_file_excel)
        print("📋 PAGINE DISPONIBILI:")
        for i, sheet in enumerate(xl_file.sheet_names):
            print(f"   {i + 1}. {sheet}")

        # Verifica che ci sia una seconda pagina
        if len(xl_file.sheet_names) < 2:
            print(f"❌ ERRORE: Il file ha solo {len(xl_file.sheet_names)} pagina/e!")
            return False

        # Legge la SECONDA pagina (indice 1)
        nome_seconda_pagina = xl_file.sheet_names[1]
        print(f"\n🎯 LETTURA DELLA SECONDA PAGINA: '{nome_seconda_pagina}'")

        df = pd.read_excel(
            nome_file_excel, sheet_name=1
        )  # sheet_name=1 per la seconda pagina

        print(f"📏 Dati letti: {df.shape[0]} righe × {df.shape[1]} colonne")

        # Mostra le prime colonne per verificare
        print("\n📋 COLONNE TROVATE:")
        for i, col in enumerate(df.columns):
            print(f"   {i + 1:2d}. {col}")

        # Esporta in CSV
        df.to_csv(nome_csv, index=False, encoding="utf-8")

        print("\n✅ CONVERSIONE COMPLETATA!")
        print(f"   📁 File CSV creato: {nome_csv}")
        print(f"   📄 Pagina convertita: {nome_seconda_pagina}")

        return True

    except Exception as e:
        print(f"❌ ERRORE durante la conversione: {e}")
        return False


def main():
    """
    Funzione principale
    """

    file_excel = "Pianificazione_MARE25.xlsx"
    file_csv = "pianificazione_MARE25_pagina2.csv"

    print("🚀 CONVERSIONE SECONDA PAGINA EXCEL → CSV")
    print("=" * 45)

    # Converte la seconda pagina
    successo = excel_pagina2_to_csv(file_excel, file_csv)

    if successo:
        print("\n🎉 FATTO! La seconda pagina è stata convertita in CSV!")
    else:
        print("\n💥 ERRORE nella conversione!")


if __name__ == "__main__":
    main()
