"""
Controllo disponibilità domini via WHOIS.

Uso:
    python check_domains.py

Requisiti:
    Nessuna libreria esterna richiesta (usa solo socket, standard library).
    Funziona su Windows, Mac e Linux.

Il risultato viene stampato a schermo e salvato anche in "domain_report.txt".
"""

import socket
import time

# ---------------------------------------------------------------------------
# 1) Lista dei nomi da controllare (modifica liberamente questa lista)
# ---------------------------------------------------------------------------
NAMES = [
    "example",
]

# Estensioni da controllare per ogni nome
TLDS = ["com", "io", "co"]

# ---------------------------------------------------------------------------
# 2) Server WHOIS ufficiali per ciascuna estensione
# ---------------------------------------------------------------------------
WHOIS_SERVERS = {
    "com": "whois.verisign-grs.com",
    "io": "whois.nic.io",
    "co": "whois.nic.co",
}

# Frasi che, se presenti nella risposta WHOIS, indicano che il dominio
# NON è registrato (quindi probabilmente disponibile).
AVAILABLE_MARKERS = [
    "no match",
    "not found",
    "no data found",
    "no entries found",
    "domain not found",
    "status: available",
    "no matching record",
    "is available for registration",
]


def whois_query(domain: str, server: str, timeout: int = 10) -> str:
    """Esegue una query WHOIS grezza (protocollo su porta 43) e ritorna il testo di risposta."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect((server, 43))
        s.sendall((domain + "\r\n").encode("utf-8"))
        response = b""
        while True:
            try:
                chunk = s.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            response += chunk
    return response.decode("utf-8", errors="ignore")


def is_available(whois_text: str) -> bool:
    """Determina euristicamente se il dominio è libero in base al testo WHOIS."""
    text_lower = whois_text.lower()
    return any(marker in text_lower for marker in AVAILABLE_MARKERS)


def check_domain(name: str, tld: str) -> dict:
    domain = f"{name}.{tld}"
    server = WHOIS_SERVERS[tld]
    result = {"domain": domain, "status": "?", "note": ""}
    try:
        raw = whois_query(domain, server)
        if not raw.strip():
            result["status"] = "SCONOSCIUTO"
            result["note"] = "Risposta vuota dal server WHOIS"
        elif is_available(raw):
            result["status"] = "LIBERO"
        else:
            result["status"] = "OCCUPATO"
    except socket.timeout:
        result["status"] = "ERRORE"
        result["note"] = "Timeout nella connessione al server WHOIS"
    except Exception as e:
        result["status"] = "ERRORE"
        result["note"] = str(e)
    return result


def main():
    results = []
    print(f"{'DOMINIO':<25} {'STATO':<12} NOTE")
    print("-" * 60)

    for name in NAMES:
        for tld in TLDS:
            res = check_domain(name, tld)
            results.append(res)
            print(f"{res['domain']:<25} {res['status']:<12} {res['note']}")
            time.sleep(1)  # piccola pausa per non sovraccaricare i server WHOIS

    # Salva anche un report su file
    with open("domain_report.txt", "w", encoding="utf-8") as f:
        f.write(f"{'DOMINIO':<25} {'STATO':<12} NOTE\n")
        f.write("-" * 60 + "\n")
        for res in results:
            f.write(f"{res['domain']:<25} {res['status']:<12} {res['note']}\n")

    print("\nReport salvato in 'domain_report.txt' nella cartella corrente.")
    print("NOTA: il controllo è euristico (basato su parole chiave nella risposta WHOIS).")
    print("Per i domini segnati 'OCCUPATO' o 'SCONOSCIUTO', verifica sempre manualmente")
    print("su un registrar (Namecheap, GoDaddy, ecc.) prima di procedere all'acquisto.")


if __name__ == "__main__":
    main()
