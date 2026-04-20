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
R   = "\033[0m"
W   = "\033[97m"
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

# ══════════════════════════════════════════════════════════════════════════════
# ANIMATION DE BOOT
# ══════════════════════════════════════════════════════════════════════════════
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
    left   = max(0, (tw - logo_w) // 2)
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

    # Phase 1 : fade-in ligne par ligne
    os.system("clear")
    print("\n" * top, end="")
    for i, l in enumerate(nary):
        col = TOKYO_DIM if i < len(nary)//2 else TOKYO_BLUE
        print(" " * left + col + l + R)
        time.sleep(0.03)
    time.sleep(0.2)

    # Phase 2 : logo + subtitle
    draw(TOKYO_BLUE)
    time.sleep(0.3)

    # Phase 3 : dots animés
    init = "Initialisation"
    il   = max(0, (tw - len(init) - 12) // 2)
    dots_seq = ["·   ", "··  ", "···  ", "····"]
    for _ in range(4):
        for d in dots_seq:
            draw(TOKYO_BLUE,
                 f"\n{' '*il}{TOKYO_DIM}{init}{R}  {TOKYO_CYAN}{BLD}{d}{R}")
            time.sleep(0.14)

    # Phase 4 : flash + prêt
    draw(W)
    time.sleep(0.07)
    draw(TOKYO_BLUE, f"\n{' '*sl}{TOKYO_GREEN}{BLD}[ Système prêt ]{R}")
    time.sleep(0.5)

# ══════════════════════════════════════════════════════════════════════════════
# BARRE DE STATUT
# ══════════════════════════════════════════════════════════════════════════════
def status_bar(info):
    try:
        tw = shutil.get_terminal_size().columns
    except Exception:
        tw = 80
    line = (
        f"  {TOKYO_DIM}[{R} {TOKYO_CYAN} {info['time']}{R} {TOKYO_DIM}]"
        f"  [{R} {TOKYO_BLUE} {info['username']}{R} {TOKYO_DIM}]"
        f"  [{R} {TOKYO_GREEN}󰋊 {info['free']}{R} {TOKYO_DIM}]"
        f"  [{R} {TOKYO_PURPLE} {info['ram'].split('/')[0].strip()}{R} {TOKYO_DIM}]{R}"
    )
    sep = f"{TOKYO_BLUE}{'━' * tw}{R}"
    return sep + "\n" + line + "\n" + sep

# ══════════════════════════════════════════════════════════════════════════════
# MENU INTERACTIF CURSES — ASCII gauche + menu droite
# ══════════════════════════════════════════════════════════════════════════════

# Définition du menu : (label_affiché, clé_action, is_separator)
MENU_ITEMS = [
    ("── TERMINAL ──────────────────", None, True),
    ("󰞷  Entrer dans le terminal",    "terminal",  False),
    ("── MUSIQUE ───────────────────", None, True),
    ("󰝚  Lancer le lecteur MP3",      "mp3",       False),
    ("── SYSTÈME ───────────────────", None, True),
    ("󰋊  Informations système",       "sysinfo",   False),
    ("   Processus actifs",           "procs",     False),
    ("󰈀  Réseau",                     "network",   False),
    ("   Neofetch",                   "neofetch",  False),
    ("── HISTORIQUE ────────────────", None, True),
    ("   Historique zshrc",           "zshrc",     False),
    ("   Historique commandes",       "zsh_hist",  False),
    ("── GIT ───────────────────────", None, True),
    ("   Git status",                 "git",       False),
    ("── SESSION ───────────────────", None, True),
    ("󰗼  Quitter le terminal",        "quit",      False),
]

SELECTABLE = [i for i, (_, _, sep) in enumerate(MENU_ITEMS) if not sep]


def run_menu_curses(ascii_lines, info):
    """Affiche ASCII gauche + menu droite via curses. Retourne la clé d'action."""

    result = [None]

    def _menu(stdscr):
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()

        # Paires de couleurs
        # 1=bleu sélection, 2=violet sep, 3=texte normal, 4=dim,
        # 5=rouge ascii, 6=cyan header, 7=bleu highlight bg
        curses.init_pair(1, curses.COLOR_BLACK,   111)   # highlight (bg bleu)
        curses.init_pair(2, 61,  -1)                     # séparateur (dim violet)
        curses.init_pair(3, 255, -1)                     # texte normal blanc
        curses.init_pair(4, 61,  -1)                     # dim
        curses.init_pair(5, 203, -1)                     # rouge (ascii)
        curses.init_pair(6, 111, -1)                     # bleu clair (header)
        curses.init_pair(7, 141, -1)                     # violet (pointer)
        curses.init_pair(8, 150, -1)                     # vert

        # Essaie les couleurs 256 si dispo
        try:
            curses.init_pair(1, curses.COLOR_BLACK, 111)
        except Exception:
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_BLUE)

        cur_sel = 0   # index dans SELECTABLE

        ASCII_W = 63  # largeur colonne ASCII (61 chars + 2 marge)
        GAP     = 2   # espace entre les colonnes

        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()

            # ── Ligne de statut (ligne 0) ─────────────────────────────────────
            info_now = get_sys_info()
            stat = (f"  [ {info_now['time']} ]"
                    f"  [  {info_now['username']} ]"
                    f"  [ 󰋊 {info_now['free']} ]"
                    f"  [  {info_now['ram'].split('/')[0].strip()} ]")
            # Séparatrice haute
            try:
                stdscr.attron(curses.color_pair(4))
                stdscr.addstr(0, 0, "─" * min(w-1, w))
                stdscr.attroff(curses.color_pair(4))
            except Exception:
                pass

            # Statut ligne 1
            try:
                stdscr.attron(curses.color_pair(6))
                stdscr.addstr(1, 0, stat[:w-1])
                stdscr.attroff(curses.color_pair(6))
            except Exception:
                pass

            # Séparatrice basse statut
            try:
                stdscr.attron(curses.color_pair(4))
                stdscr.addstr(2, 0, "─" * min(w-1, w))
                stdscr.attroff(curses.color_pair(4))
            except Exception:
                pass

            START_ROW = 3   # les lignes de contenu commencent ici

            # ── ASCII art (colonne gauche) ────────────────────────────────────
            for i, aline in enumerate(ascii_lines):
                row = START_ROW + i
                if row >= h - 1:
                    break
                try:
                    stdscr.attron(curses.color_pair(5))
                    stdscr.addstr(row, 0, aline[: ASCII_W])
                    stdscr.attroff(curses.color_pair(5))
                except Exception:
                    pass

            # ── Colonne menu (droite de l'ASCII) ─────────────────────────────
            menu_col = ASCII_W + GAP

            # Header "SYSTEM_COMMANDER"
            header = "SYSTEM_COMMANDER >_"
            hint   = "  (↑↓ naviguer, Entrée valider)"
            try:
                stdscr.attron(curses.color_pair(6) | curses.A_BOLD)
                stdscr.addstr(START_ROW, menu_col, header[:w - menu_col - 1])
                stdscr.attroff(curses.color_pair(6) | curses.A_BOLD)
                stdscr.attron(curses.color_pair(4))
                stdscr.addstr(START_ROW, menu_col + len(header),
                              hint[:w - menu_col - len(header) - 1])
                stdscr.attroff(curses.color_pair(4))
            except Exception:
                pass

            # Items du menu
            cur_action_idx = SELECTABLE[cur_sel]   # index réel dans MENU_ITEMS
            for mi, (label, action, is_sep) in enumerate(MENU_ITEMS):
                row = START_ROW + 1 + mi
                if row >= h - 1:
                    break
                col = menu_col
                max_len = max(0, w - col - 1)
                if is_sep:
                    try:
                        stdscr.attron(curses.color_pair(2))
                        stdscr.addstr(row, col, label[:max_len])
                        stdscr.attroff(curses.color_pair(2))
                    except Exception:
                        pass
                else:
                    is_cur = (mi == cur_action_idx)
                    if is_cur:
                        try:
                            # Pointer »
                            stdscr.attron(curses.color_pair(7) | curses.A_BOLD)
                            stdscr.addstr(row, col, "» ")
                            stdscr.attroff(curses.color_pair(7) | curses.A_BOLD)
                            # Ligne surlignée
                            stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
                            text = label[:max_len - 2]
                            stdscr.addstr(row, col + 2, text)
                            # Remplis le reste de la ligne jusqu'à 40 chars
                            pad = max(0, 38 - len(text))
                            stdscr.addstr(" " * pad)
                            stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
                        except Exception:
                            pass
                    else:
                        try:
                            stdscr.addstr(row, col, "  ")
                            stdscr.attron(curses.color_pair(3))
                            stdscr.addstr(row, col + 2, label[:max_len - 2])
                            stdscr.attroff(curses.color_pair(3))
                        except Exception:
                            pass

            # Séparatrice basse
            try:
                last_row = START_ROW + 1 + len(MENU_ITEMS)
                if last_row < h - 1:
                    stdscr.attron(curses.color_pair(4))
                    stdscr.addstr(last_row, 0, "─" * min(w-1, w))
                    stdscr.attroff(curses.color_pair(4))
            except Exception:
                pass

            stdscr.refresh()

            # ── Input ─────────────────────────────────────────────────────────
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


# ══════════════════════════════════════════════════════════════════════════════
# ACTIONS
# ══════════════════════════════════════════════════════════════════════════════
def hdr(title, color=TOKYO_BLUE):
    try:
        w = shutil.get_terminal_size().columns
    except Exception:
        w = 80
    print(f"\n{color}{'━'*w}{R}")
    print(f"  {TOKYO_PURPLE}{BLD}{title}{R}")
    print(f"{color}{'━'*w}{R}\n")

def pause():
    input(f"\n  {TOKYO_DIM}Appuie sur Entrée pour revenir...{R}")

def action_sysinfo():
    os.system("clear")
    hdr("󰋊  INFORMATIONS SYSTÈME")
    info = get_sys_info()
    fields = [("OS", info["os"]), ("Kernel", info["kernel"]),
              ("Uptime", info["uptime"]), ("Packages", info["packages"]),
              ("Shell", info["shell"]), ("Terminal", info["terminal"]),
              ("CPU", info["cpu"]), ("RAM", info["ram"]), ("Disk", info["disk"])]
    for k, v in fields:
        print(f"  {TOKYO_BLUE}{BLD}{k:<12}{R}  {v}")
    pause()

def action_procs():
    os.system("clear")
    hdr("   PROCESSUS ACTIFS (top 10)")
    os.system("ps aux --sort=-%mem | head -11")
    pause()

def action_network():
    os.system("clear")
    hdr("󰈀  RÉSEAU")
    try:
        ip = subprocess.check_output("hostname -I 2>/dev/null | awk '{print $1}'",
                                     shell=True, text=True).strip()
        print(f"  {TOKYO_BLUE}IP locale    {R}  {ip}")
    except Exception:
        pass
    try:
        pub = subprocess.check_output("curl -s --max-time 3 ifconfig.me 2>/dev/null",
                                      shell=True, text=True).strip()
        print(f"  {TOKYO_BLUE}IP publique  {R}  {pub}")
    except Exception:
        pass
    os.system("ip -brief addr 2>/dev/null | head -8")
    pause()

def action_neofetch():
    os.system("clear")
    if shutil.which("neofetch"):
        os.system("neofetch")
    else:
        # Version maison
        ascii_lines = load_lines(ASCII_PATH)
        info = get_sys_info()
        sep = "─" * len(info["user_host"])
        info_lines = [
            f"{TOKYO_BLUE}{BLD}{info['user_host']}{R}",
            f"{TOKYO_DIM}{sep}{R}",
            f"{TOKYO_BLUE}{BLD}OS{R}         {info['os']}",
            f"{TOKYO_PURPLE}{BLD}Kernel{R}     {info['kernel']}",
            f"{TOKYO_CYAN}{BLD}Uptime{R}     {info['uptime']}",
            f"{TOKYO_GREEN}{BLD}Packages{R}   {info['packages']}",
            f"{TOKYO_RED}{BLD}Shell{R}      {info['shell']}",
            f"{TOKYO_BLUE}{BLD}CPU{R}        {info['cpu']}",
            f"{TOKYO_GREEN}{BLD}RAM{R}        {info['ram']}",
            f"{TOKYO_RED}{BLD}Disk{R}       {info['disk']}",
        ]
        for i in range(max(len(ascii_lines), len(info_lines))):
            a = ascii_lines[i] if i < len(ascii_lines) else ""
            d = info_lines[i]  if i < len(info_lines)  else ""
            pad = 63 - len(a) + 2
            print(f"{TOKYO_RED}{a}{R}{' '*pad}{d}")
    pause()

def action_zshrc():
    os.system("clear")
    hdr("   HISTORIQUE ZSHRC (20 dernières lignes)")
    os.system("tail -n 20 ~/.zshrc 2>/dev/null || echo '  ~/.zshrc introuvable'")
    pause()

def action_zsh_hist():
    os.system("clear")
    hdr("   HISTORIQUE COMMANDES (20 dernières)")
    os.system("tail -n 20 ~/.zsh_history 2>/dev/null | sed 's/^.*;//' || echo '  Introuvable'")
    pause()

def action_git():
    os.system("clear")
    hdr("   GIT STATUS")
    os.system("git -C ~ status 2>/dev/null || echo '  Pas de dépôt git dans ~'")
    pause()

ACTIONS = {
    "sysinfo":  action_sysinfo,
    "procs":    action_procs,
    "network":  action_network,
    "neofetch": action_neofetch,
    "zshrc":    action_zshrc,
    "zsh_hist": action_zsh_hist,
    "git":      action_git,
}

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    # Boot animation une seule fois
    if os.environ.get("NARY_BOOTED") != "1":
        boot_animation()
        os.environ["NARY_BOOTED"] = "1"

    ascii_lines = load_lines(ASCII_PATH)
    if not ascii_lines:
        ascii_lines = ["  (ascii.txt introuvable)"]

    while True:
        info   = get_sys_info()
        action = run_menu_curses(ascii_lines, info)

        if action is None or action == "terminal":
            os.system("clear")
            return   # retourne au shell

        elif action == "quit":
            os.system("clear")
            print(f"\n  {TOKYO_RED}{BLD}Disconnecting NARY...{R}\n")
            time.sleep(0.4)
            os.kill(os.getppid(), signal.SIGTERM)
            sys.exit(0)

        elif action == "mp3":
            os.system(f"python3 {MP3_PATH}")

        elif action in ACTIONS:
            ACTIONS[action]()

if __name__ == "__main__":
    main()
