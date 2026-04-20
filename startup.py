#!/usr/bin/env python3
"""
NARY Terminal — Script d'entrée
- Animation de boot style Ubuntu
- Layout neofetch : ASCII art gauche + menu interactif droite
- Navigation clavier (↑↓ Entrée)
"""
import os, sys, signal, datetime, shutil, time, subprocess, socket, platform, curses

# ── Chemins ────────────────────────────────────────────────────────────────────
ASCII_PATH = os.path.expanduser("~/ascii.txt")
NARY_PATH  = os.path.expanduser("~/nary.txt")
MP3_PATH   = os.path.expanduser("~/mp3.py")

# ── Couleurs ANSI (pour les écrans hors-menu) ──────────────────────────────────
R    = "\033[0m"
W    = "\033[97m"
BLD = "\033[1m"
DIM = "\033[2m"
TOKYO_BLUE   = "\033[38;5;111m"
TOKYO_PURPLE = "\033[38;5;141m"
TOKYO_GREEN  = "\033[38;5;150m"
TOKYO_CYAN   = "\033[38;5;73m"
TOKYO_RED    = "\033[38;5;203m"
TOKYO_DIM    = "\033[38;5;61m"
TOKYO_ORANGE = "\033[38;5;215m"

# ── Chargement des fichiers ────────────────────────────────────────────────────
def load_lines(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().splitlines()
    except Exception:
        return default or []

# ── Infos système ──────────────────────────────────────────────────────────────
def get_sys_info():
    now      = datetime.datetime.now()
    username = os.environ.get("USER") or os.environ.get("LOGNAME") or "user"
    hostname = socket.gethostname()
    try:
        with open("/etc/os-release") as f:
            osr = {}
            for l in f:
                if "=" in l:
                    k,v = l.strip().split("=",1); osr[k] = v.strip('"')
        os_name = osr.get("PRETTY_NAME", platform.system())
    except Exception:
        os_name = platform.system()
    kernel  = platform.release()
    try:
        secs   = float(open("/proc/uptime").read().split()[0])
        h, m   = int(secs//3600), int((secs%3600)//60)
        uptime = f"{h}h {m}m"
    except Exception:
        uptime = "?"
    shell = os.path.basename(os.environ.get("SHELL","bash"))
    try:
        cpu = subprocess.check_output(
            "grep -m1 'model name' /proc/cpuinfo | cut -d: -f2",
            shell=True, text=True).strip() or platform.processor()
    except Exception:
        cpu = "?"
    try:
        mem = {l.split(":")[0]: int(l.split(":")[1].strip().split()[0])
               for l in open("/proc/meminfo") if ":" in l}
        used  = (mem.get("MemTotal",0) - mem.get("MemAvailable",0)) // 1024
        total = mem.get("MemTotal",0) // 1024
        ram   = f"{used}MiB / {total}MiB"
    except Exception:
        ram = "?"
    try:
        st   = shutil.disk_usage("/")
        disk = f"{st.used//(2**30)}GB / {st.total//(2**30)}GB"
        free = f"{st.free//(2**30)}GB"
    except Exception:
        disk = "?"; free = "?"
    pkgs = "?"
    for cmd in ["dpkg -l 2>/dev/null | tail -n+6 | wc -l",
                "pacman -Q 2>/dev/null | wc -l"]:
        try:
            n = subprocess.check_output(cmd, shell=True, text=True).strip()
            if n.isdigit() and int(n) > 0:
                pkgs = n; break
        except Exception:
            pass
    term = os.environ.get("TERM_PROGRAM") or os.environ.get("TERM","wezterm")
    return dict(user_host=f"{username}@{hostname}", time=now.strftime("%H:%M:%S"),
                os=os_name, kernel=kernel, uptime=uptime, shell=shell,
                cpu=cpu, ram=ram, disk=disk, free=free,
                packages=pkgs, terminal=term, username=username, hostname=hostname)

def boot_animation():
    os.system("clear")
    nary  = load_lines(NARY_PATH)
    if not nary:
        nary = ["NARY"]
    try:
        tw = shutil.get_terminal_size().columns
        th = shutil.get_terminal_size().lines
    except Exception:
        tw, th = 80, 24

    logo_w = max(len(l) for l in nary)
    logo_h = len(nary)
    top    = max(2, (th - logo_h - 7) // 2)
    left    = max(0, (tw - logo_w) // 2)
    sub    = "N A R Y   T E R M I N A L"
    sl     = max(0, (tw - len(sub)) // 2)

    def draw(color=TOKYO_BLUE, extra=""):
        os.system("clear")
        print("\n" * top, end="")
        for l in nary:
            print(" " * left + color + l + R)
        print(f"\n{' '*sl}{TOKYO_PURPLE}{BLD}{sub}{R}")
        if extra:
            print(extra)

    os.system("clear")
    print("\n" * top, end="")
    for i, l in enumerate(nary):
        col = TOKYO_DIM if i < len(nary)//2 else TOKYO_BLUE
        print(" " * left + col + l + R)
        time.sleep(0.03)
    time.sleep(0.2)

    draw(TOKYO_BLUE)
    time.sleep(0.3)

    init = "Initialisation"
    il   = max(0, (tw - len(init) - 12) // 2)
    dots_seq = ["·   ", "··  ", "···  ", "····"]
    for _ in range(4):
        for d in dots_seq:
            draw(TOKYO_BLUE,
                 f"\n{' '*il}{TOKYO_DIM}{init}{R}  {TOKYO_CYAN}{BLD}{d}{R}")
            time.sleep(0.14)

    draw(W)
    time.sleep(0.07)
    draw(TOKYO_BLUE, f"\n{' '*sl}{TOKYO_GREEN}{BLD}[ Système prêt ]{R}")
    time.sleep(0.5)

# ── MENU INTERACTIF ────────────────────────────────────────────────────────────

MENU_ITEMS = [
    ("── TERMINAL ──────────────────", None, True),
    ("󰞷  Entrer dans le terminal",    "terminal",  False),
    ("── MUSIQUE ───────────────────", None, True),
    ("󰝚  Lancer le lecteur MP3",      "mp3",        False),
    ("── SYSTÈME ───────────────────", None, True),
    ("󰋊  Informations système",       "sysinfo",    False),
    ("   Processus actifs",            "procs",      False),
    ("󰈀  Réseau",                      "network",    False),
    ("   Neofetch",                    "neofetch",   False),
    ("── HISTORIQUE ────────────────", None, True),
    ("   Historique zshrc",            "zshrc",      False),
    ("   Historique commandes",        "zsh_hist",   False),
    ("── GIT ───────────────────────", None, True),
    ("   Git status",                  "git",        False),
    ("── SESSION ───────────────────", None, True),
    ("󰗼  Quitter le terminal",         "quit",       False),
]

SELECTABLE = [i for i, (_, _, sep) in enumerate(MENU_ITEMS) if not sep]

def run_menu_curses(ascii_lines, info):
    result = [None]

    def _menu(stdscr):
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()

        curses.init_pair(1, curses.COLOR_BLACK,   111)  # highlight
        curses.init_pair(2, 61,  -1)                     # séparateur
        curses.init_pair(3, 255, -1)                     # texte normal
        curses.init_pair(4, 61,  -1)                     # dim
        curses.init_pair(5, 203, -1)                     # rouge (ascii)
        curses.init_pair(6, 111, -1)                     # bleu (header)
        curses.init_pair(7, 141, -1)                     # violet (pointer)

        cur_sel = 0
        ASCII_W = 63  
        GAP     = 2   
        menu_col = ASCII_W + GAP

        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            info_now = get_sys_info()
            
            stat = (f"  [ {info_now['time']} ]"
                    f"  [  {info_now['username']} ]"
                    f"  [ 󰋊 {info_now['free']} ]"
                    f"  [  {info_now['ram'].split('/')[0].strip()} ]")

            # ── BORDURES CORRIGÉES : On commence à menu_col pour protéger l'ASCII ──
            try:
                stdscr.attron(curses.color_pair(4))
                if w > menu_col:
                    stdscr.addstr(0, menu_col, "─" * (w - menu_col - 1))
                    stdscr.addstr(2, menu_col, "─" * (w - menu_col - 1))
                stdscr.attroff(curses.color_pair(4))
            except Exception: pass

            # Statut
            try:
                stdscr.attron(curses.color_pair(6))
                stdscr.addstr(1, 0, stat[:w-1])
                stdscr.attroff(curses.color_pair(6))
            except Exception: pass

            START_ROW = 3

            # ── ASCII Art ──
            for i, aline in enumerate(ascii_lines):
                row = START_ROW + i
                if row >= h - 1: break
                try:
                    stdscr.attron(curses.color_pair(5))
                    stdscr.addstr(row, 0, aline[: ASCII_W])
                    stdscr.attroff(curses.color_pair(5))
                except Exception: pass

            # ── Menu ──
            header = "SYSTEM_COMMANDER >_"
            hint   = "  (↑↓ naviguer, Entrée valider)"
            try:
                stdscr.attron(curses.color_pair(6) | curses.A_BOLD)
                stdscr.addstr(START_ROW, menu_col, header[:w - menu_col - 1])
                stdscr.attroff(curses.color_pair(6) | curses.A_BOLD)
                stdscr.attron(curses.color_pair(4))
                stdscr.addstr(START_ROW, menu_col + len(header), hint[:w - menu_col - len(header) - 1])
                stdscr.attroff(curses.color_pair(4))
            except Exception: pass

            cur_action_idx = SELECTABLE[cur_sel]
            for mi, (label, action, is_sep) in enumerate(MENU_ITEMS):
                row = START_ROW + 1 + mi
                if row >= h - 1: break
                max_len = max(0, w - menu_col - 1)
                
                if is_sep:
                    try:
                        stdscr.attron(curses.color_pair(2))
                        stdscr.addstr(row, menu_col, label[:max_len])
                        stdscr.attroff(curses.color_pair(2))
                    except Exception: pass
                else:
                    if mi == cur_action_idx:
                        try:
                            stdscr.attron(curses.color_pair(7) | curses.A_BOLD)
                            stdscr.addstr(row, menu_col, "» ")
                            stdscr.attroff(curses.color_pair(7) | curses.A_BOLD)
                            stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
                            text = label[:max_len - 2]
                            stdscr.addstr(row, menu_col + 2, text)
                            pad = max(0, 38 - len(text))
                            stdscr.addstr(" " * pad)
                            stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
                        except Exception: pass
                    else:
                        try:
                            stdscr.addstr(row, menu_col, "  ")
                            stdscr.attron(curses.color_pair(3))
                            stdscr.addstr(row, menu_col + 2, label[:max_len - 2])
                            stdscr.attroff(curses.color_pair(3))
                        except Exception: pass

            # Bordure basse corrigée
            try:
                last_row = START_ROW + 1 + len(MENU_ITEMS)
                if last_row < h - 1 and w > menu_col:
                    stdscr.attron(curses.color_pair(4))
                    stdscr.addstr(last_row, menu_col, "─" * (w - menu_col - 1))
                    stdscr.attroff(curses.color_pair(4))
            except Exception: pass

            stdscr.refresh()
            key = stdscr.getch()
            if key in (curses.KEY_UP, ord('k')):
                cur_sel = (cur_sel - 1) % len(SELECTABLE)
            elif key in (curses.KEY_DOWN, ord('j')):
                cur_sel = (cur_sel + 1) % len(SELECTABLE)
            elif key in (curses.KEY_ENTER, ord('\n'), ord('\r'), 10, 13):
                result[0] = MENU_ITEMS[SELECTABLE[cur_sel]][1]
                return
            elif key == ord('q'):
                result[0] = "quit"
                return

    curses.wrapper(_menu)
    return result[0]

# ── ACTIONS & MAIN (Inchangés) ──────────────────────────────────────────────────

def hdr(title, color=TOKYO_BLUE):
    try: tw = shutil.get_terminal_size().columns
    except Exception: tw = 80
    print(f"\n{color}{'━'*tw}{R}\n  {TOKYO_PURPLE}{BLD}{title}{R}\n{color}{'━'*tw}{R}\n")

def pause():
    input(f"\n  {TOKYO_DIM}Appuie sur Entrée pour revenir...{R}")

def action_sysinfo():
    os.system("clear"); hdr("󰋊  INFORMATIONS SYSTÈME")
    info = get_sys_info()
    for k, v in [("OS", info["os"]), ("Kernel", info["kernel"]), ("Uptime", info["uptime"]), 
                 ("Packages", info["packages"]), ("Shell", info["shell"]), ("CPU", info["cpu"]), 
                 ("RAM", info["ram"]), ("Disk", info["disk"])]:
        print(f"  {TOKYO_BLUE}{BLD}{k:<12}{R}  {v}")
    pause()

def action_procs():
    os.system("clear"); hdr("   PROCESSUS ACTIFS (top 10)")
    os.system("ps aux --sort=-%mem | head -11"); pause()

def action_network():
    os.system("clear"); hdr("󰈀  RÉSEAU")
    os.system("hostname -I | awk '{print \"  Local IP: \", $1}'"); os.system("ip -brief addr | head -8"); pause()

def action_neofetch():
    os.system("clear")
    if shutil.which("neofetch"): os.system("neofetch")
    else: print("Neofetch non trouvé.")
    pause()

ACTIONS = {
    "sysinfo": action_sysinfo, "procs": action_procs, "network": action_network,
    "neofetch": action_neofetch, "zshrc": lambda: (os.system("clear"), os.system("tail -n 20 ~/.zshrc"), pause()),
    "zsh_hist": lambda: (os.system("clear"), os.system("tail -n 20 ~/.zsh_history | sed 's/^.*;//'"), pause()),
    "git": lambda: (os.system("clear"), os.system("git -C ~ status 2>/dev/null"), pause()),
}

def main():
    if os.environ.get("NARY_BOOTED") != "1":
        boot_animation()
        os.environ["NARY_BOOTED"] = "1"
    ascii_lines = load_lines(ASCII_PATH, ["(ascii.txt introuvable)"])
    while True:
        info = get_sys_info()
        action = run_menu_curses(ascii_lines, info)
        if action is None or action == "terminal": os.system("clear"); return
        elif action == "quit":
            os.system(f"python3 {os.path.expanduser('~/nary_quit.py')}")
            sys.exit(0)
        elif action == "mp3": os.system(f"python3 {MP3_PATH}")
        elif action in ACTIONS: ACTIONS[action]()

if __name__ == "__main__":
    main()
