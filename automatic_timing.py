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
    
    match_titoli_numerati = re.findall(r'\b\d+\.\s+(.+?)\s*[\(\[]\s*\d+\s*min\.?\s*[\)\]]', testo_completo, re.IGNORECASE)
    match_minuti_grezzi = re.findall(r'[\(\[]\s*(\d+)\s*min\.?\s*[\)\]]', testo_completo, re.IGNORECASE)
    match_minuti = match_minuti_grezzi[1:-1]
    
    # Struttura coerente con il FE (In secondi, ore inizializzate a 19:00 standard)
    programma = [
        {"id": 1, "name": "Cantico e preghiera", "start": "19:00:00", "end": "19:05:00", "maxDuration": 300, "duration": 300, "active": False},
        {"id": 2, "name": "Commenti introduttivi", "start": "19:05:00", "end": "19:06:00", "maxDuration": 60, "duration": 60, "active": False}
    ]
    
    durate_controllo = [5] 
    indice_titolo_corrente = 0
    
    for m in match_minuti:
        minuti_int = int(m)
        durate_controllo.append(minuti_int)
        
        if indice_titolo_corrente < len(match_titoli_numerati):
            titolo_assegnato = match_titoli_numerati[indice_titolo_corrente].rstrip(':- ').strip()
            indice_titolo_corrente += 1
        else:
            titolo_assegnato = "Parte Adunanza"
            
        programma.append({
            "id": len(programma) + 1,
            "name": titolo_assegnato,
            "start": "19:00:00",
            "end": "19:00:00",
            "maxDuration": minuti_int * 60,
            "duration": minuti_int * 60,
            "active": False
        })
        
        # LA TUA LOGICA ORIGINALE (Invariata, cambiano solo i campi del dizionario di output)
        if sum(durate_controllo) < 46 and sum(durate_controllo) > 29:
            durate_controllo.append(1)
            programma.append({
                "id": len(programma) + 1,
                "name": "Consigli",
                "start": "19:00:00",
                "end": "19:00:00",
                "maxDuration": 60,
                "duration": 60,
                "active": False
            })

        # LA TUA LOGICA ORIGINALE
        if sum(durate_controllo) == 46:
            durate_controllo.append(5)
            programma.append({
                "id": len(programma) + 1,
                "name": "Cantico",
                "start": "19:00:00",
                "end": "19:00:00",
                "maxDuration": 300,
                "duration": 300,
                "active": False
            })
            
    programma.append({"id": len(programma) + 1, "name": "Commenti", "start": "19:00:00", "end": "19:00:00", "maxDuration": 180, "duration": 180, "active": False})
    programma.append({"id": len(programma) + 1, "name": "Cantico e preghiera", "start": "19:00:00", "end": "19:00:00", "maxDuration": 300, "duration": 300, "active": False})
    
    return programma