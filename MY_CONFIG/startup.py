#!/usr/bin/env python3
"""
NARY Terminal — Script d'entrée
- Animation de boot style Ubuntu
- Layout split : ASCII art gauche + menu interactif droite
- Navigation clavier (↑↓ Entrée)
"""
import os, sys, signal, datetime, shutil, time, subprocess, socket, platform, curses, shlex, json, urllib.request, urllib.error, random, re

# ── Chemins ────────────────────────────────────────────────────────────────────
ASCII_PATH = os.path.expanduser("~/ascii.txt")
NARY_PATH  = os.path.expanduser("~/nary.txt")
MP3_PATH   = os.path.expanduser("~/mp3.py")
PROJECTS_PATH = "/home/traomeli/MY_PROJECTS"
NOTES_PATH = os.path.expanduser("~/.nary_notes.txt")
SCRIPT_DIR_CANDIDATES = [
    os.path.expanduser("~/MY_SCRIPTS"),
    os.path.expanduser("~/scripts"),
    os.path.expanduser("~/automations"),
    os.path.join(PROJECTS_PATH, "scripts"),
]

CRYPTO_CACHE = {"ts": 0.0, "data": None}

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
    sub    = "powered by Raomelinary Tsiresy"
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
    draw(TOKYO_BLUE, f"\n{' '*sl}{TOKYO_GREEN}{BLD}[ System ready ]{R}")
    time.sleep(0.5)

# ── MENU INTERACTIF ────────────────────────────────────────────────────────────

MENU_ITEMS = [
    ("── TERMINAL ──────────────────", None, True),
    ("󰞷  Entrer dans le terminal",    "terminal",  False),
    ("── MUSIQUE ───────────────────", None, True),
    ("󰝚  Lancer le lecteur MP3",      "mp3",        False),
    ("━━ STATION DE PILOTAGE ━━━━━━━", None, True),
    ("── SYSTÈME ───────────────────", None, True),
    ("󰇄  Dashboard système stylé",     "dashboard",  False),
    ("󰋊  Informations système",       "sysinfo",    False),
    ("󰍛  Processus actifs",            "procs",      False),
    ("── OUTILS ────────────────────", None, True),
    ("󰉋  Gestionnaire de projets",     "projects",   False),
    ("󰈀  Test réseau rapide",          "network",    False),
    ("󰒃  Check sécurité",              "security",   False),
    ("󰎞  Notes rapides",               "notes",      False),
    ("󰆍  Launcher scripts perso",      "scripts",    False),
    ("── TRADING ───────────────────", None, True),
    ("󰭹  Tracker crypto/trading",      "crypto",     False),
    ("── FUN ───────────────────────", None, True),
    ("🎲  Daily briefing / motivation", "fun",        False),
    ("━━ MODE DANGER ━━━━━━━━━━━━━━━", None, True),
    ("󱐋  Kill process",                "danger_kill", False),
    ("󰑓  Reset réseau",                "danger_net",  False),
    ("󰆴  Clear logs",                  "danger_logs", False),
    ("󰌾  Lock PC (ft_lock)",           "danger_lock", False),
    ("── HISTORIQUE ────────────────", None, True),
    ("󰛮  Historique zshrc",            "zshrc",      False),
    ("󱃔  Historique commandes",        "zsh_hist",   False),
    ("── GIT ───────────────────────", None, True),
    ("󰊢  Git status",                  "git",        False),
    ("── SESSION ───────────────────", None, True),
    ("󰗼  Quitter le terminal",         "quit",       False),
]

SELECTABLE = [i for i, (_, _, sep) in enumerate(MENU_ITEMS) if not sep]

def run_menu_curses(ascii_lines, info):
    result = [None]

    def _find_selection(query):
        q = query.strip().lower()
        if len(q) < 2:
            return None
        for idx, (label, action, is_sep) in enumerate(MENU_ITEMS):
            if is_sep:
                continue
            hay = f"{label} {action}".lower()
            if q in hay:
                return SELECTABLE.index(idx)
        return None

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
        curses.init_pair(8, 150, -1)                     # vert
        curses.init_pair(9, 203, -1)                     # rouge
        curses.init_pair(10, 215, -1)                    # orange

        cur_sel = 0
        ASCII_W = 63  
        GAP     = 2   
        menu_col = ASCII_W + GAP
        search_buffer = ""
        search_expire = 0.0

        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            info_now = get_sys_info()

            # Reset buffer de recherche si inactif
            if search_buffer and time.time() > search_expire:
                search_buffer = ""

            # Header trading live (cache 25s)
            price = "?"
            change = None
            now_ts = time.time()
            if now_ts - CRYPTO_CACHE["ts"] > 25:
                try:
                    url = (
                        "https://api.coingecko.com/api/v3/simple/price"
                        "?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
                    )
                    with urllib.request.urlopen(url, timeout=0.8) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                    CRYPTO_CACHE["ts"] = now_ts
                    CRYPTO_CACHE["data"] = data
                except Exception:
                    pass

            d = CRYPTO_CACHE.get("data") or {}
            if isinstance(d, dict):
                b = d.get("bitcoin", {})
                if isinstance(b, dict):
                    if b.get("usd") is not None:
                        price = str(b.get("usd"))
                    if b.get("usd_24h_change") is not None:
                        change = float(b.get("usd_24h_change"))

            ram_used = info_now['ram'].split('/')[0].strip() if '/' in info_now['ram'] else info_now['ram']
            ram_pct = None
            m = re.search(r"(\d+)MiB\s*/\s*(\d+)MiB", info_now["ram"])
            if m:
                total = max(1, int(m.group(2)))
                ram_pct = (int(m.group(1)) / total) * 100.0
            
            stat_left = (
                f"  󰥔 {info_now['time']}"
                f"   {info_now['username']}"
                f"   {info_now['free']}"
            )

            stat_ram = f"   {ram_used}"
            stat_btc = f"  󰟗 BTC ${price}"
            if change is None:
                stat_chg = "  24h ?"
            else:
                arrow = "▲" if change >= 0 else "▼"
                stat_chg = f"  {arrow} {change:+.2f}%"

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
                stdscr.addstr(1, 0, stat_left[:w-1])
                stdscr.attroff(curses.color_pair(6))

                col = len(stat_left)
                if ram_pct is None:
                    stdscr.attron(curses.color_pair(6))
                elif ram_pct >= 80:
                    stdscr.attron(curses.color_pair(9) | curses.A_BOLD)
                elif ram_pct >= 60:
                    stdscr.attron(curses.color_pair(10) | curses.A_BOLD)
                else:
                    stdscr.attron(curses.color_pair(8) | curses.A_BOLD)
                if col < w - 1:
                    stdscr.addstr(1, col, stat_ram[: max(0, w - col - 1)])
                stdscr.attroff(curses.color_pair(9) | curses.A_BOLD)
                stdscr.attroff(curses.color_pair(10) | curses.A_BOLD)
                stdscr.attroff(curses.color_pair(8) | curses.A_BOLD)
                stdscr.attroff(curses.color_pair(6))

                col += len(stat_ram)
                stdscr.attron(curses.color_pair(6))
                if col < w - 1:
                    stdscr.addstr(1, col, stat_btc[: max(0, w - col - 1)])
                stdscr.attroff(curses.color_pair(6))

                col += len(stat_btc)
                if change is None:
                    stdscr.attron(curses.color_pair(4))
                elif change >= 0:
                    stdscr.attron(curses.color_pair(8) | curses.A_BOLD)
                else:
                    stdscr.attron(curses.color_pair(9) | curses.A_BOLD)
                if col < w - 1:
                    stdscr.addstr(1, col, stat_chg[: max(0, w - col - 1)])
                stdscr.attroff(curses.color_pair(8) | curses.A_BOLD)
                stdscr.attroff(curses.color_pair(9) | curses.A_BOLD)
                stdscr.attroff(curses.color_pair(4))
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
            header = "ALL COMMANDS >_"
            hint   = "  (↑↓ navigate, Enter = valider, tape 2 lettres for search)"
            try:
                stdscr.attron(curses.color_pair(6) | curses.A_BOLD)
                stdscr.addstr(START_ROW, menu_col, header[:w - menu_col - 1])
                stdscr.attroff(curses.color_pair(6) | curses.A_BOLD)
                stdscr.attron(curses.color_pair(4))
                stdscr.addstr(START_ROW, menu_col + len(header), hint[:w - menu_col - len(header) - 1])
                stdscr.attroff(curses.color_pair(4))
                if search_buffer:
                    q = f"  ⌕ {search_buffer}"
                    stdscr.attron(curses.color_pair(7) | curses.A_BOLD)
                    stdscr.addstr(START_ROW, max(menu_col, w - len(q) - 2), q)
                    stdscr.attroff(curses.color_pair(7) | curses.A_BOLD)
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
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                if search_buffer:
                    search_buffer = search_buffer[:-1]
            elif key in (curses.KEY_ENTER, ord('\n'), ord('\r'), 10, 13):
                result[0] = MENU_ITEMS[SELECTABLE[cur_sel]][1]
                return
            elif key == ord('q'):
                result[0] = "quit"
                return
            elif 32 <= key <= 126:
                ch = chr(key).lower()
                if ch.isalnum() or ch in "_-":
                    search_buffer = (search_buffer + ch)[-12:]
                    search_expire = time.time() + 4.0
                    found = _find_selection(search_buffer)
                    if found is not None:
                        cur_sel = found

    curses.wrapper(_menu)
    return result[0]

# ── ACTIONS & MAIN (Inchangés) ──────────────────────────────────────────────────

def hdr(title, color=TOKYO_BLUE):
    try: tw = shutil.get_terminal_size().columns
    except Exception: tw = 80
    print(f"\n{color}{'━'*tw}{R}\n  {TOKYO_PURPLE}{BLD}{title}{R}\n{color}{'━'*tw}{R}\n")

def pause():
    input(f"\n  {TOKYO_DIM}Appuie sur Entrée pour revenir...{R}")

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e:
        return f"Erreur: {e}"

def cpu_usage_percent(interval=0.22):
    def _read_cpu_times():
        with open("/proc/stat", encoding="utf-8") as f:
            line = f.readline().strip().split()[1:]
        vals = [int(x) for x in line]
        idle = vals[3] + vals[4]
        total = sum(vals)
        return idle, total

    idle_1, total_1 = _read_cpu_times()
    time.sleep(interval)
    idle_2, total_2 = _read_cpu_times()
    total_delta = max(1, total_2 - total_1)
    idle_delta = max(0, idle_2 - idle_1)
    return round(100 * (1 - (idle_delta / total_delta)), 1)

def ram_usage_percent():
    mem = {}
    with open("/proc/meminfo", encoding="utf-8") as f:
        for line in f:
            if ":" in line:
                k, v = line.split(":", 1)
                mem[k] = int(v.strip().split()[0])
    total = mem.get("MemTotal", 1)
    avail = mem.get("MemAvailable", 0)
    return round(((total - avail) / total) * 100, 1)

def disk_usage_percent(path="/"):
    du = shutil.disk_usage(path)
    return round((du.used / du.total) * 100, 1)

def bar(pct, width=28):
    pct = max(0.0, min(100.0, float(pct)))
    fill = int((pct / 100.0) * width)
    return f"{'█' * fill}{'░' * (width - fill)}"

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

def action_dashboard():
    os.system("clear"); hdr("󰇄  DASHBOARD SYSTÈME")
    if shutil.which("btop"):
        print(f"  {TOKYO_GREEN}btop détecté -> ouverture du dashboard interactif...{R}\n")
        os.system("btop")
        return
    if shutil.which("htop"):
        print(f"  {TOKYO_GREEN}htop détecté -> ouverture du dashboard interactif...{R}\n")
        os.system("htop")
        return

    try:
        cpu = cpu_usage_percent()
        ram = ram_usage_percent()
        dsk = disk_usage_percent("/")
        print(f"  {TOKYO_BLUE}{BLD}CPU  {R} [{bar(cpu)}] {cpu:>5}%")
        print(f"  {TOKYO_BLUE}{BLD}RAM  {R} [{bar(ram)}] {ram:>5}%")
        print(f"  {TOKYO_BLUE}{BLD}DISK {R} [{bar(dsk)}] {dsk:>5}%")
        print(f"\n  {TOKYO_PURPLE}{BLD}Top process CPU{R}")
        print(run_cmd("ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -8"))
        print(f"\n  {TOKYO_PURPLE}{BLD}Top process RAM{R}")
        print(run_cmd("ps -eo pid,comm,%cpu,%mem --sort=-%mem | head -8"))
    except Exception as e:
        print(f"  {TOKYO_RED}Erreur dashboard: {e}{R}")
    pause()

def action_projects():
    os.system("clear"); hdr("󰉋  GESTIONNAIRE DE PROJETS")
    if not os.path.isdir(PROJECTS_PATH):
        print(f"  Dossier introuvable: {PROJECTS_PATH}")
        pause()
        return

    projects = [
        p for p in sorted(os.listdir(PROJECTS_PATH))
        if os.path.isdir(os.path.join(PROJECTS_PATH, p))
    ]
    if not projects:
        print("  Aucun projet détecté.")
        pause()
        return

    print(f"  Base projets: {PROJECTS_PATH}\n")
    for i, p in enumerate(projects, 1):
        print(f"  {TOKYO_BLUE}{i:>2}.{R} {p}")

    choice = input(f"\n  {TOKYO_DIM}Numéro du projet (Entrée pour annuler): {R}").strip()
    if not choice:
        return
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(projects):
        print("\n  Sélection invalide.")
        pause()
        return

    target = os.path.join(PROJECTS_PATH, projects[int(choice) - 1])
    shell = os.environ.get("SHELL", "bash")
    print(f"\n  {TOKYO_GREEN}Ouverture d'un shell dans:{R} {target}")
    os.system(f"cd {shlex.quote(target)} && {shlex.quote(shell)}")

def action_network():
    os.system("clear"); hdr("󰈀  TEST RÉSEAU RAPIDE")
    print(f"  {TOKYO_PURPLE}{BLD}IP locale{R}")
    print("  " + run_cmd("hostname -I | awk '{print $1}'"))

    print(f"\n  {TOKYO_PURPLE}{BLD}IP publique{R}")
    pub = "?"
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=4) as resp:
            pub = resp.read().decode("utf-8").strip()
    except Exception:
        pub = run_cmd("curl -s https://api.ipify.org || wget -qO- https://api.ipify.org")
    print(f"  {pub}")

    print(f"\n  {TOKYO_PURPLE}{BLD}Ping 8.8.8.8 (4 paquets){R}")
    os.system("ping -c 4 8.8.8.8")

    print(f"\n  {TOKYO_PURPLE}{BLD}Vitesse réseau{R}")
    if shutil.which("speedtest"):
        os.system("speedtest --accept-license --accept-gdpr --progress=no 2>/dev/null | egrep 'Latency|Download|Upload|Server'")
    elif shutil.which("speedtest-cli"):
        os.system("speedtest-cli --simple")
    else:
        print("  speedtest non installé (installe 'speedtest' ou 'speedtest-cli').")
    pause()

def action_security():
    os.system("clear"); hdr("󰒃  CHECK SÉCURITÉ")
    print(f"  {TOKYO_PURPLE}{BLD}Ports ouverts (LISTEN){R}")
    os.system("ss -tuln | sed -n '1,12p'")

    print(f"\n  {TOKYO_PURPLE}{BLD}Statut SSH{R}")
    ssh_status = run_cmd("systemctl is-active ssh || systemctl is-active sshd")
    print(f"  {ssh_status}")

    print(f"\n  {TOKYO_PURPLE}{BLD}Firewall{R}")
    if shutil.which("ufw"):
        os.system("ufw status")
    elif shutil.which("firewall-cmd"):
        os.system("firewall-cmd --state; firewall-cmd --list-all")
    else:
        print("  Aucun gestionnaire firewall standard détecté (ufw/firewalld).")
    pause()

def action_notes():
    os.system("clear"); hdr("󰎞  NOTES RAPIDES")
    os.makedirs(os.path.dirname(NOTES_PATH), exist_ok=True)
    if not os.path.exists(NOTES_PATH):
        open(NOTES_PATH, "a", encoding="utf-8").close()

    print(f"  Fichier: {NOTES_PATH}\n")
    print(f"  {TOKYO_PURPLE}{BLD}Dernières notes{R}")
    print(run_cmd(f"tail -n 8 {shlex.quote(NOTES_PATH)}") or "(vide)")

    note = input(f"\n  {TOKYO_DIM}Nouvelle note (Entrée pour annuler): {R}").strip()
    if not note:
        return
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(NOTES_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{now}] {note}\n")
    print(f"\n  {TOKYO_GREEN}Note enregistrée.{R}")
    pause()

def action_crypto():
    os.system("clear"); hdr("󰭹  TRACKER CRYPTO / TRADING")
    print(f"  {TOKYO_DIM}Rafraîchissement toutes les 8 secondes (Ctrl+C pour quitter).{R}\n")
    url = (
        "https://api.coingecko.com/api/v3/simple/price"
        "?ids=bitcoin,ethereum,solana,binancecoin,xrp&vs_currencies=usd,eur"
    )
    try:
        while True:
            os.system("clear")
            hdr("󰭹  TRACKER CRYPTO / TRADING")
            try:
                with urllib.request.urlopen(url, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                print(f"  Snapshot: {ts}\n")
                rows = [
                    ("BTC", "bitcoin"),
                    ("ETH", "ethereum"),
                    ("SOL", "solana"),
                    ("BNB", "binancecoin"),
                    ("XRP", "xrp"),
                ]
                for sym, key in rows:
                    usd = data.get(key, {}).get("usd", "?")
                    eur = data.get(key, {}).get("eur", "?")
                    print(f"  {TOKYO_BLUE}{BLD}{sym:<4}{R}  USD: {usd:<12} EUR: {eur}")
            except Exception as e:
                print(f"  {TOKYO_RED}Erreur API: {e}{R}")
            time.sleep(8)
    except KeyboardInterrupt:
        pass
    pause()

def action_scripts():
    os.system("clear"); hdr("󰆍  LAUNCHER SCRIPTS PERSO")
    files = []
    for base in SCRIPT_DIR_CANDIDATES:
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            full = os.path.join(base, name)
            if not os.path.isfile(full):
                continue
            if (
                os.access(full, os.X_OK)
                or name.endswith((".py", ".sh", ".zsh", ".bash"))
            ):
                files.append(full)

    if not files:
        print("  Aucun script détecté.")
        print("  Dossiers testés:")
        for d in SCRIPT_DIR_CANDIDATES:
            print(f"   - {d}")
        pause()
        return

    for i, fp in enumerate(files, 1):
        print(f"  {TOKYO_BLUE}{i:>2}.{R} {fp}")

    choice = input(f"\n  {TOKYO_DIM}Script à lancer (Entrée pour annuler): {R}").strip()
    if not choice:
        return
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(files):
        print("\n  Sélection invalide.")
        pause()
        return

    target = files[int(choice) - 1]
    print(f"\n  {TOKYO_GREEN}Exécution:{R} {target}\n")
    if target.endswith(".py"):
        os.system(f"python3 {shlex.quote(target)}")
    elif target.endswith(".zsh"):
        os.system(f"zsh {shlex.quote(target)}")
    elif target.endswith(".bash"):
        os.system(f"bash {shlex.quote(target)}")
    elif target.endswith(".sh"):
        os.system(f"sh {shlex.quote(target)}")
    else:
        os.system(shlex.quote(target))
    pause()

def confirm_danger(label):
    print(f"\n  {TOKYO_RED}{BLD}⚠ Action sensible:{R} {label}")
    answer = input(f"  {TOKYO_DIM}Tape o pour confirmer: {R}").strip()
    return answer == "o"

def action_danger_kill():
    os.system("clear"); hdr("󱐋  MODE DANGER — KILL PROCESS", TOKYO_RED)
    os.system("ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -12")
    pid = input(f"\n  {TOKYO_DIM}PID à tuer (Entrée annule): {R}").strip()
    if not pid:
        return
    if not pid.isdigit():
        print("\n  PID invalide.")
        pause()
        return
    if not confirm_danger(f"kill -9 {pid}"):
        print("\n  Annulé.")
        pause()
        return
    rc = os.system(f"kill -9 {shlex.quote(pid)}")
    print("\n  Process tué." if rc == 0 else "\n  Échec kill (permissions ?).")
    pause()

def action_danger_net():
    os.system("clear"); hdr("󰑓  MODE DANGER — RESET RÉSEAU", TOKYO_RED)
    if not confirm_danger("reset réseau"):
        print("\n  Annulé.")
        pause()
        return

    if shutil.which("nmcli"):
        os.system("nmcli networking off")
        time.sleep(2)
        os.system("nmcli networking on")
        print("\n  Reset réseau via nmcli terminé.")
    elif shutil.which("systemctl"):
        rc = os.system("sudo systemctl restart NetworkManager || sudo systemctl restart networking")
        print("\n  Réseau relancé." if rc == 0 else "\n  Échec reset réseau (sudo/permissions).")
    else:
        print("\n  Outil de reset réseau non détecté.")
    pause()

def action_danger_logs():
    os.system("clear"); hdr("󰆴  MODE DANGER — CLEAR LOGS", TOKYO_RED)
    if not confirm_danger("clear logs système"):
        print("\n  Annulé.")
        pause()
        return

    rc1 = os.system("sudo journalctl --rotate && sudo journalctl --vacuum-time=2d")
    rc2 = os.system("sudo find /var/log -type f -name '*.log' -exec truncate -s 0 {} \\;")
    if rc1 == 0 or rc2 == 0:
        print("\n  Nettoyage logs exécuté (partiel ou complet selon permissions).")
    else:
        print("\n  Échec nettoyage logs (sudo/permissions).")
    pause()

def action_danger_lock():
    os.system("clear"); hdr("󰌾  MODE DANGER — LOCK PC", TOKYO_RED)
    if not confirm_danger("lock PC via ft_lock"):
        print("\n  Annulé.")
        pause()
        return
    if shutil.which("ft_lock"):
        os.system("ft_lock")
    else:
        print("\n  ft_lock introuvable dans le PATH.")
        pause()

def action_fun():
    os.system("clear"); hdr("🎲  DAILY BRIEFING / MOTIVATION", TOKYO_ORANGE)
    quotes = [
        "Focus on process, profit follows.",
        "La discipline bat l'inspiration quand la fatigue arrive.",
        "Small wins stack into big months.",
        "Code propre, esprit propre.",
        "Tu n'as pas besoin d'etre motive, juste coherent.",
    ]
    memes = [
        [
            "  (\"-_-)  ",
            "  /|   |\\  ",
            "   /   \\   ",
            "  market opens.",
        ],
        [
            "  ┌( ಠ_ಠ)┘  ",
            "  └(┐\" )┐  ",
            "   algo dance ",
            "  while tests pass.",
        ],
        [
            "  [====]   ",
            "  |LOGS|   ",
            "  |____|   ",
            "  powered by coffee.",
        ],
    ]
    info = get_sys_info()
    quote = random.choice(quotes)
    meme = random.choice(memes)
    weekday = datetime.datetime.now().strftime("%A %d %B %Y")
    print(f"  {TOKYO_BLUE}{BLD}Briefing:{R} {weekday}")
    print(f"  {TOKYO_BLUE}{BLD}Uptime:{R} {info['uptime']}")
    print(f"  {TOKYO_BLUE}{BLD}Mission:{R} ship du code + garder le risk management propre")
    print(f"\n  {TOKYO_PURPLE}{BLD}Quote du jour{R}")
    print(f"  \"{quote}\"")
    print(f"\n  {TOKYO_PURPLE}{BLD}Meme ASCII{R}")
    for line in meme:
        print(f"  {line}")
    pause()

ACTIONS = {
    "sysinfo": action_sysinfo, "procs": action_procs, "network": action_network,
    "dashboard": action_dashboard, "projects": action_projects, "security": action_security,
    "notes": action_notes, "crypto": action_crypto, "scripts": action_scripts,
    "danger_kill": action_danger_kill, "danger_net": action_danger_net,
    "danger_logs": action_danger_logs, "danger_lock": action_danger_lock,
    "fun": action_fun,
    "zshrc": lambda: (os.system("clear"), os.system("tail -n 20 ~/.zshrc"), pause()),
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
