#!/usr/bin/env python3
import os
import time
import subprocess

def quit_nary():
    # Petit message de déconnexion stylé avant la fermeture
    TOKYO_RED = "\033[38;5;203m"
    BLD = "\033[1m"
    R = "\033[0m"
    
    os.system("clear")
    print(f"\n  {TOKYO_RED}{BLD}Terminating WezTerm session...{R}")
    time.sleep(0.5)
    
    # Commande pour pkill WezTerm
    # On utilise -u $USER pour ne pas tuer les sessions des autres sur le cluster
    try:
        subprocess.run(["pkill", "-u", os.getlogin(), "wezterm"])
    except Exception:
        # Fallback si os.getlogin() échoue
        os.system("pkill wezterm")

if __name__ == "__main__":
    quit_nary()