import re
import os


def dividi_csv_per_tranche(percorso_file, nome_cartella_output):
    """
    Legge un file CSV, crea una cartella di output e salva ogni "tranche"
    in un file CSV separato all'interno di quella cartella.

    Args:
        percorso_file (str): Il percorso del file CSV da leggere.
        nome_cartella_output (str): Il nome della cartella dove salvare i file.
    """
    # 1. Controlla e legge il file di input
    try:
        with open(percorso_file, "r", encoding="latin1") as file_input:  # utf-8
            righe = file_input.readlines()
    except FileNotFoundError:
        print(f"ERRORE: File non trovato al percorso '{percorso_file}'")
        print(
            "Per favore, controlla che il nome e il percorso del file siano corretti."
        )
        return
    except Exception as e:
        print(f"Si è verificato un errore durante la lettura del file: {e}")
        return

    # 2. Crea la cartella di destinazione se non esiste
    if not os.path.exists(nome_cartella_output):
        print(f"La cartella '{nome_cartella_output}' non esiste. La creo...")
        os.makedirs(nome_cartella_output)
    else:
        print(f"La cartella '{nome_cartella_output}' esiste già.")

    # 3. Estrae l'intestazione e divide i dati in tranches
    intestazione = None
    for riga in righe:
        if "chiave articolo colore" in riga.lower():
            intestazione = riga.strip()
            break

    if not intestazione:
        print("ERRORE: Impossibile trovare una riga di intestazione valida nel file.")
        return

    tranches = {}
    tranche_corrente = "prodotti_iniziali"
    tranches[tranche_corrente] = []

    for riga in righe:
        riga_pulita = riga.strip()

        if not riga_pulita or riga_pulita == intestazione:
            continue

        match = re.search(r",,TRANCHE\s+(\d+),", riga_pulita, re.IGNORECASE)
        if match:
            numero_tranche = match.group(1)
            tranche_corrente = f"tranche_{numero_tranche}"
            if tranche_corrente not in tranches:
                tranches[tranche_corrente] = []
            continue

        if not riga_pulita.startswith(","):
            tranches[tranche_corrente].append(riga_pulita)

    # 4. Scrive i dati di ogni tranche in un file separato dentro la nuova cartella
    file_creati = 0
    print("\nInizio la creazione dei file...")
    for nome_tranche, dati_tranche in tranches.items():
        if not dati_tranche:
            continue

        nome_file = f"{nome_tranche}.csv"
        percorso_completo_output = os.path.join(nome_cartella_output, nome_file)

        print(f"-> Scrittura di '{percorso_completo_output}'...")

        with open(
            percorso_completo_output, "w", newline="", encoding="utf-8"
        ) as file_output:
            file_output.write(intestazione + "\n")
            for riga_dati in dati_tranche:
                file_output.write(riga_dati + "\n")
        file_creati += 1

    print(
        f"\nProcesso completato. Sono stati creati {file_creati} file nella cartella '{nome_cartella_output}'."
    )


# --- CONFIGURAZIONE ---
# 1. Modifica questa variabile con il percorso del tuo file CSV di input.
file_da_leggere = "Pianificazione_MARE25.xlsx"  # _pagina2.csv"

# 2. Scegli il nome per la cartella che conterrà i file CSV creati.
cartella_output = "Tranches_CSV"
# --- FINE CONFIGURAZIONE ---


if __name__ == "__main__":
    if not os.path.exists(file_da_leggere):
        print(f"ATTENZIONE: Il file di input '{file_da_leggere}' non è stato trovato.")
        print(
            "Assicurati di aver salvato il tuo file CSV con questo nome nella stessa cartella dello script,"
        )
        print(
            "oppure modifica la variabile 'file_da_leggere' con il percorso corretto."
        )
    else:
        dividi_csv_per_tranche(file_da_leggere, cartella_output)
