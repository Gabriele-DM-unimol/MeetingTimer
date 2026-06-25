import datetime
import requests
import re
from bs4 import BeautifulSoup

def ottieni_url_sito_ufficiale():
    """Genera l'URL ufficiale di jw.org per la settimana corrente."""
    mesi_ita = {
        1: "gennaio", 2: "febbraio", 3: "marzo", 4: "aprile",
        5: "maggio", 6: "giugno", 7: "luglio", 8: "agosto",
        9: "settembre", 10: "ottobre", 11: "novembre", 12: "dicembre"
    }
    
    oggi = datetime.date.today()
    lunedi = oggi - datetime.timedelta(days=oggi.weekday())
    domenica = lunedi + datetime.timedelta(days=6)
    
    mese_start_blocco = lunedi.month if lunedi.month % 2 != 0 else lunedi.month - 1
    mese_end_blocco = mese_start_blocco + 1
    
    anno_blocco = lunedi.year
    if mese_start_blocco == 11 and domenica.month == 1:
        blocco_dispensa = f"mwb-novembre-dicembre-{anno_blocco}"
    else:
        blocco_dispensa = f"mwb-{mesi_ita[mese_start_blocco]}-{mesi_ita[mese_end_blocco]}-{anno_blocco}"
    
    giorno_lun = lunedi.day
    giorno_dom = domenica.day
    mese_lun_nome = mesi_ita[lunedi.month]
    mese_dom_nome = mesi_ita[domenica.month]
    
    if lunedi.month != domenica.month:
        stringa_settimana = f"Programma-adunanza-Vita-e-ministero-dal-{giorno_lun}-{mese_lun_nome}-al-{giorno_dom}-{mese_dom_nome}-{domenica.year}"
    else:
        stringa_settimana = f"Programma-adunanza-Vita-e-ministero-dal-{giorno_lun}-al-{giorno_dom}-{mese_dom_nome}-{domenica.year}"
        
    return f"https://www.jw.org/it/biblioteca-digitale/guida-attivita-adunanza/{blocco_dispensa}/{stringa_settimana}/"

def estrai_programma_con_titoli():
    url = ottieni_url_sito_ufficiale()
    print(f"Collegamento a: {url}\n")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Errore di connessione: {response.status_code}")
        return []
        
    soup = BeautifulSoup(response.text, 'html.parser')
    corpo = soup.find(id="regionMain") or soup.find("article") or soup.body
    testo_completo = corpo.get_text(" ", strip=True)
    
    # 1. Trova tutti i titoli numerati (es. "3. Sii grato")
    match_titoli_numerati = re.findall(r'\b\d+\.\s+(.+?)\s*[\(\[]\s*\d+\s*min\.?\s*[\)\]]', testo_completo, re.IGNORECASE)
    
    # 2. La TUA vecchia regex originale per estrarre i minuti
    match_minuti_grezzi = re.findall(r'[\(\[]\s*(\d+)\s*min\.?\s*[\)\]]', testo_completo, re.IGNORECASE)
    
    # IGNORIAMO IL PRIMO E L'ULTIMO RISULTATO (Slicing da indice 1 a penultimo)
    # Rrisolve lo slittamento causato dai minuti dei commenti scritti nella pagina
    match_minuti = match_minuti_grezzi[1:-1]
    
    # Costruiamo l'array finale inserendo manualmente le parti fisse esterne che gestisci tu
    programma = [
        {"titolo": "Cantico iniziale e preghiera", "minuti": 5},
        {"titolo": "Commenti introduttivi", "minuti": 1}
    ]
    
    durate_controllo = [5] # Serve per attivare matematicamente il cantico intermedio a 42 minuti
    indice_titolo_corrente = 0
    
    for m in match_minuti:
        minuti_int = int(m)
        durate_controllo.append(minuti_int)
        
        # Assegniamo il titolo recuperato in modo speculare
        if indice_titolo_corrente < len(match_titoli_numerati):
            titolo_assegnato = match_titoli_numerati[indice_titolo_corrente].rstrip(':- ').strip()
            indice_titolo_corrente += 1
        else:
            titolo_assegnato = "Parte Adunanza"
            
        programma.append({
            "titolo": titolo_assegnato,
            "minuti": minuti_int if 'minutes_int' in locals() else minuti_int
        })
        
        if sum(durate_controllo) < 46 and sum(durate_controllo) > 24:
            durate_controllo.append(1)
            programma.append({
                "titolo": "Consigli",
                "minuti": 1
            })

        # Regola storica: se la somma tocca 42 inseriamo il Cantico Intermedio fisso (41 + 1(commenti introduttivi) = 42)
        if sum(durate_controllo) == 46:
            durate_controllo.append(5)
            programma.append({
                "titolo": "Cantico intermedio",
                "minuti": 5
            })
            
    # Aggiungiamo la chiusura fissa manuale
    programma.append({"titolo": "Commenti conclusivi", "minuti": 3})
    programma.append({"titolo": "Cantico finale e preghiera", "minuti": 5})
    
    return programma

#if __name__ == "__main__":
    print("=== ESTRAZIONE PROGRAMMA ALLINEATO ===")
    lista_programma = estrai_programma_con_titoli()
    
    print("-" * 70)
    for i, parte in enumerate(lista_programma, 1):
        print(f"⏱️ {str(i).zfill(2)}: {parte['titolo'].ljust(50)} -> {parte['minuti']} min")
    print("-" * 70)
    
    print("\nArray finale pronto per il tuo software:")
    print(lista_programma)