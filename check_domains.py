#!/usr/bin/env python3
"""
Skrypt do sprawdzania dostępności domen .com
"""

import socket
import subprocess
import sys
import time
from datetime import datetime
import socket

# Lista nazw do sprawdzenia
DOMAIN_NAMES = [
    "corevo", "evolix", "duobot", "devomy", "devtwo", "aicode", "devkit",
    "twinai", "aivolt", "codeai", "dualix", "sysbak", "aicore", "coretwo",
    "devcor", "aipair", "coredu", "twinix", "duodev", "corely", "aiback",
    "airity", "dualgo", "coredy", "twince", "koredo", "neocor", "devmir",
    "mirrex", "zencor", "vimeo", "duozen", "cortex", "nixdup", "corefy",
    "redevo", "devduo", "corabi", "daitwo", "airbak", "twinly", "evocor",
    "coreio", "twiner", "duolix", "codedy", "bakdev", "coretx", "duplix",
    "aiback", "mirrai", "twinix", "corely", "devsys", "aitwin", "corein"
]

def check_domain(domain_name):
    """Sprawdza czy domena jest dostępna za pomocą nslookup i socket"""
    domain = f"{domain_name}.com"
    
    # Metoda 1: Sprawdź przez socket
    try:
        socket.gethostbyname(domain)
        return False, "Domena jest zarejestrowana (znaleziono rekord DNS)"
    except socket.gaierror:
        # Domena może być dostępna, ale sprawdźmy dokładniej przez nslookup
        pass
    
    # Metoda 2: Sprawdź przez nslookup
    try:
        result = subprocess.run(['nslookup', domain], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        
        output = result.stdout.lower()
        
        if "can't find" in output or "non-existent domain" in output:
            return True, "Domena prawdopodobnie dostępna (brak rekordu DNS)"
        elif "name" in output and "address" in output:
            return False, "Domena jest zarejestrowana (znaleziono rekord DNS)"
        else:
            # Sprawdźmy jeszcze przez dig
            result = subprocess.run(['dig', domain], 
                                   capture_output=True, 
                                   text=True, 
                                   timeout=5)
            output = result.stdout.lower()
            
            if "status: nxdomain" in output:
                return True, "Domena prawdopodobnie dostępna (NXDOMAIN)"
            elif "answer section" in output and not "0 answer" in output:
                return False, "Domena jest zarejestrowana (znaleziono rekord DNS)"
            else:
                return True, "Domena prawdopodobnie dostępna (brak pozytywnych rekordów)"
    except subprocess.TimeoutExpired:
        return False, "Timeout podczas sprawdzania"
    except Exception as e:
        return False, f"Błąd: {str(e)}"

def main():
    """Główna funkcja programu"""
    print("\n=========================================")
    print("     Sprawdzanie dostępności domen      ")
    print("=========================================\n")
    
    available_domains = []
    unavailable_domains = []
    
    for domain in DOMAIN_NAMES:
        print(f"Sprawdzanie {domain}.com...", end="", flush=True)
        is_available, message = check_domain(domain)
        
        if is_available:
            available_domains.append(domain)
            print(f" ✓ DOSTĘPNA: {message}")
        else:
            unavailable_domains.append(domain)
            print(f" ✗ NIEDOSTĘPNA: {message}")
        
        # Opóźnienie, aby uniknąć ograniczeń zapytań
        time.sleep(1)
    
    print("\n=========================================")
    print(f"Znaleziono {len(available_domains)} dostępnych domen:")
    print("=========================================\n")
    
    for idx, domain in enumerate(available_domains, 1):
        print(f"{idx}. {domain}.com")
    
    print("\n=========================================\n")

if __name__ == "__main__":
    main()
