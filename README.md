# MeetingTimer ⏱️

**MeetingTimer** è un'applicazione basata su **Flask** (Python) progettata per la gestione sincronizzata e l'automazione dei tempi durante i meeting, le conferenze o le agende aziendali/culturali. 

Il sistema permette a un amministratore di controllare la timeline e le durate dei singoli interventi in tempo reale, distribuendo gli aggiornamenti a tutti i client connessi tramite una comunicazione fluida in **Server-Sent Events (SSE)**.

---

## ✨ Funzionalità Principali

*   **Sincronizzazione in Tempo Reale**: Aggiornamento istantaneo di tutti i client connessi (schermi della regia, podio, visualizzatori) tramite SSE (Server-Sent Events).
*   **Algoritmo di Compensazione Proporzionale**: Se un intervento supera il tempo stabilito, il sistema ricalcola automaticamente e proporzionalmente la durata dei timer futuri (superiori a 5 minuti) per garantire il rispetto del limite massimo del meeting (es. 105 minuti nominali).
*   **Gestione Template**: Caricamento di agende predefinite basate sul giorno della settimana (`infrasettimanale_std` / `fine_settimana_std`) tramite file JSON di configurazione.
*   **Scraping Automatizzato**: Integrazione per l'estrazione dinamica del programma e dei titoli degli interventi all'avvio.
*   **Architettura Portabile**: Predisposto per funzionare sia come script Python sia come eseguibile autonomo "congelato" (es. tramite PyInstaller), salvando lo stato dell'applicazione nella cartella `AppData` (Windows) o nella `Home` (Linux/macOS).
*   **Multi-Interfaccia**: 
    *   `http://127.0.0.1:1914/admin` - Pannello di controllo per la regia.
    *   `http://127.0.0.1:1914/` - Visualizzazione pulita del timer per i relatori/pubblico.

---

## 🛠️ Tecnologia e Stack

*   **Backend**: Python, Flask, Regia multithreaded (Queue/Timer).
*   **Frontend**: HTML5, CSS3, JavaScript (Vanilla ES6).
*   **Protocollo di Rete**: Server-Sent Events (SSE) per il flusso dati unidirezionale a bassa latenza.

---

## 🚀 Installazione e Avvio Rapido

### Requisiti
*   Python 3.8 o superiore

### Procedura
1. Clonare il repository:
   ```bash
   git clone [https://github.com/tuo-username/MeetingTimer.git](https://github.com/tuo-username/MeetingTimer.git)
   cd MeetingTimer