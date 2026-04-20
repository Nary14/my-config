#!/usr/bin/env python3
"""
Terminal Music Grid
- Visualiseur barres arc-en-ciel style vidéo
- Bouton Play/Pause
- Auto-next quand la musique se termine
- Mode background (q) : musique continue + mini visualiseur dans le terminal
"""
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.parse
import urllib.request

try:
	import urwid
except ImportError:
	print("pip install urwid")
	sys.exit(1)

try:
	import yt_dlp
except ImportError:
	print("pip install yt-dlp")
	sys.exit(1)

# ── Constantes ────────────────────────────────────────────────────────────────
ARCHIVE_SEARCH_URL   = "https://archive.org/advancedsearch.php"
ARCHIVE_METADATA_URL = "https://archive.org/metadata"
SOUNDCLOUD_SEARCH_URL = "https://api-v2.soundcloud.com/search/tracks"
DEFAULT_QUERY        = "electronic"
MAX_TRACKS           = 120
SOUNDCLOUD_CLIENT_ID = os.environ.get("SOUNDCLOUD_CLIENT_ID", "").strip()

# ── État global ───────────────────────────────────────────────────────────────
tracks         = []
current_track  = None
current_index  = -1
player_process = None
is_paused      = False
visual_frame   = 0
current_query  = DEFAULT_QUERY
current_page   = 1
has_next_page  = False
active_source  = "YouTube"
main_loop      = None
body_walker    = None

# ── Widgets globaux ───────────────────────────────────────────────────────────
header_text     = urwid.Text("Terminal Music Grid")
page_text       = urwid.Text("Page 1", align="center")
status_text     = urwid.Text("Ready")
waveform_widget = urwid.WidgetPlaceholder(
	urwid.Text("  Sélectionne une piste et clique sur ▶ Play")
)
search_edit   = urwid.Edit(caption="Search: ", edit_text=DEFAULT_QUERY)
playpause_btn = urwid.Button("▶ Play")

# ── Couleurs arc-en-ciel (valides en background urwid) ────────────────────────
RAINBOW_COLS = [
	"yellow",        # 0  jaune
	"yellow",        # 1
	"brown",         # 2  orange
	"brown",         # 3
	"dark green",    # 4  vert
	"dark green",    # 5
	"dark green",    # 6
	"dark cyan",     # 7  cyan
	"dark cyan",     # 8
	"dark blue",     # 9  bleu
	"dark blue",     # 10
	"dark magenta",  # 11 violet
	"dark magenta",  # 12
	"dark red",      # 13 rouge
	"dark red",      # 14
]

RAINBOW_DIM = [
	"brown",         # reflet jaune
	"brown",
	"dark red",      # reflet orange
	"dark red",
	"dark blue",     # reflet vert
	"dark blue",
	"dark blue",
	"dark blue",     # reflet cyan
	"dark blue",
	"dark blue",     # reflet bleu
	"dark blue",
	"dark blue",     # reflet violet
	"dark blue",
	"dark blue",     # reflet rouge
	"dark blue",
]


def _bar_attr(col_index, num_cols, dim=False):
	idx = int(col_index * (len(RAINBOW_COLS) - 1) / max(1, num_cols - 1))
	idx = max(0, min(len(RAINBOW_COLS) - 1, idx))
	return f"{'ref' if dim else 'bar'}_{idx}"


# ── YouTube ───────────────────────────────────────────────────────────────────
def fetch_tracks_youtube(query=DEFAULT_QUERY, max_tracks=MAX_TRACKS, page=1):
	offset = (page - 1) * max_tracks
	ydl_opts = {
		"quiet": True, "no_warnings": True,
		"extract_flat": True, "skip_download": True,
	}
	with yt_dlp.YoutubeDL(ydl_opts) as ydl:
		info = ydl.extract_info(
			f"ytsearch{max_tracks + offset}:{query}", download=False
		)
		entries = (info.get("entries") or [])[offset:]
	out = []
	for item in entries:
		vid_id = item.get("id", "")
		if not vid_id:
			continue
		out.append({
			"source": "youtube", "identifier": vid_id,
			"title": item.get("title", "?"),
			"artist": item.get("uploader") or item.get("channel", "?"),
			"stream_url": None,
		})
		if len(out) >= max_tracks:
			break
	return out, len(out) >= max_tracks


def resolve_stream_url_youtube(track):
	ydl_opts = {"quiet": True, "no_warnings": True, "format": "bestaudio/best"}
	with yt_dlp.YoutubeDL(ydl_opts) as ydl:
		info = ydl.extract_info(
			f"https://www.youtube.com/watch?v={track['identifier']}", download=False
		)
		return info.get("url")


# ── Archive.org ───────────────────────────────────────────────────────────────
def fetch_tracks_archive(query=DEFAULT_QUERY, max_tracks=MAX_TRACKS, page=1):
	qt = (query or "").strip() or DEFAULT_QUERY
	params = urllib.parse.urlencode(
		{"q": f"mediatype:(audio) AND (title:({qt}) OR creator:({qt}))",
		 "fl[]": ["identifier", "title", "creator"],
		 "rows": str(max_tracks), "page": str(page), "output": "json"},
		doseq=True,
	)
	req = urllib.request.Request(
		f"{ARCHIVE_SEARCH_URL}?{params}", headers={"User-Agent": "TMG/1.0"}
	)
	with urllib.request.urlopen(req, timeout=12) as r:
		resp = json.loads(r.read().decode()).get("response", {})
	docs, num_found = resp.get("docs", []), int(resp.get("numFound", 0))
	out, seen = [], set()
	for item in docs:
		ident = item.get("identifier")
		if not ident or ident in seen:
			continue
		seen.add(ident)
		out.append({"identifier": ident, "title": item.get("title", "?"),
					"artist": item.get("creator", "?"), "stream_url": None})
		if len(out) >= max_tracks:
			break
	return out, page * max_tracks < num_found


def resolve_stream_url_archive(identifier):
	req = urllib.request.Request(
		f"{ARCHIVE_METADATA_URL}/{urllib.parse.quote(identifier)}",
		headers={"User-Agent": "TMG/1.0"},
	)
	with urllib.request.urlopen(req, timeout=12) as r:
		payload = json.loads(r.read().decode())
	for f in payload.get("files", []):
		name, fmt = f.get("name", ""), (f.get("format") or "").lower()
		if "mp3" in fmt or name.lower().endswith(".mp3"):
			return (f"https://archive.org/download/"
					f"{urllib.parse.quote(identifier)}/{urllib.parse.quote(name)}")
	return None


# ── SoundCloud ────────────────────────────────────────────────────────────────
def fetch_tracks_soundcloud(query=DEFAULT_QUERY, max_tracks=MAX_TRACKS, page=1):
	qt = (query or "").strip() or DEFAULT_QUERY
	params = urllib.parse.urlencode({
		"q": qt, "limit": str(max_tracks),
		"offset": str(max(0, (page-1)*max_tracks)),
		"linked_partitioning": "1", "client_id": SOUNDCLOUD_CLIENT_ID,
	})
	req = urllib.request.Request(
		f"{SOUNDCLOUD_SEARCH_URL}?{params}", headers={"User-Agent": "TMG/1.0"}
	)
	with urllib.request.urlopen(req, timeout=12) as r:
		payload = json.loads(r.read().decode())
	out = []
	for item in payload.get("collection", []):
		tc = item.get("media", {}).get("transcodings", [])
		if not tc:
			continue
		out.append({
			"source": "soundcloud", "identifier": str(item.get("id", "")),
			"title": item.get("title", "?"),
			"artist": item.get("user", {}).get("username", "?"),
			"transcodings": tc, "stream_url": None,
		})
		if len(out) >= max_tracks:
			break
	return out


def resolve_stream_url_soundcloud(track):
	ordered = sorted(
		track.get("transcodings") or [],
		key=lambda t: 0 if t.get("format", {}).get("protocol") == "progressive" else 1,
	)
	for trans in ordered:
		ep = trans.get("url")
		if not ep:
			continue
		try:
			req = urllib.request.Request(
				f"{ep}?{urllib.parse.urlencode({'client_id': SOUNDCLOUD_CLIENT_ID})}",
				headers={"User-Agent": "TMG/1.0"},
			)
			with urllib.request.urlopen(req, timeout=12) as r:
				url = json.loads(r.read().decode()).get("url")
			if url:
				return url
		except Exception:
			continue
	return None


# ── Dispatch ──────────────────────────────────────────────────────────────────
def fetch_tracks(query=DEFAULT_QUERY, max_tracks=MAX_TRACKS, page=1):
	if SOUNDCLOUD_CLIENT_ID:
		try:
			sc = fetch_tracks_soundcloud(query=query, max_tracks=max_tracks, page=page)
			if sc:
				return sc, "SoundCloud", len(sc) >= max_tracks
		except Exception:
			pass
	try:
		yt, has_more = fetch_tracks_youtube(query=query, max_tracks=max_tracks, page=page)
		if yt:
			return yt, "YouTube", has_more
	except Exception:
		pass
	ar, has_more = fetch_tracks_archive(query=query, max_tracks=max_tracks, page=page)
	return ar, "Archive", has_more


def resolve_stream_url(track):
	src = track.get("source", "")
	if src == "soundcloud":
		return resolve_stream_url_soundcloud(track)
	if src == "youtube":
		return resolve_stream_url_youtube(track)
	return resolve_stream_url_archive(track.get("identifier", ""))


# ── Player ────────────────────────────────────────────────────────────────────
def short(text, n):
	return text if len(text) <= n else text[:n-3] + "..."


def stop_player():
	global player_process, is_paused
	if player_process and player_process.poll() is None:
		player_process.terminate()
	player_process = None
	is_paused = False


def pause_player():
	global is_paused
	if player_process and player_process.poll() is None:
		player_process.send_signal(signal.SIGSTOP)
		is_paused = True


def resume_player():
	global is_paused
	if player_process and player_process.poll() is None:
		player_process.send_signal(signal.SIGCONT)
		is_paused = False


def toggle_pause(_button=None):
	if player_process is None:
		return
	if is_paused:
		resume_player()
		playpause_btn.set_label("⏸ Pause")
		status_text.set_text(f"▶ {current_track['title']}")
	else:
		pause_player()
		playpause_btn.set_label("▶ Play")
		status_text.set_text(f"⏸ {current_track['title']}")


def _start_cvlc(stream_url):
	global player_process
	player_process = subprocess.Popen(
		["cvlc", "--play-and-exit", "--quiet", stream_url],
		stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
	)


def play_track(index):
	global current_track, current_index, visual_frame

	if not (0 <= index < len(tracks)):
		return
	stop_player()
	visual_frame   = 0
	current_index  = index
	current_track  = tracks[index]

	stream_url = current_track.get("stream_url")
	if stream_url is None:
		status_text.set_text("Résolution du flux…")
		try:
			stream_url = resolve_stream_url(current_track)
		except Exception as e:
			status_text.set_text(f"Erreur: {e}")
		current_track["stream_url"] = stream_url

	if not stream_url:
		status_text.set_text("Flux introuvable — piste suivante…")
		play_next()
		return

	try:
		_start_cvlc(stream_url)
		playpause_btn.set_label("⏸ Pause")
		status_text.set_text(f"▶ {current_track['title']}")
	except FileNotFoundError:
		status_text.set_text("cvlc introuvable — sudo apt install vlc")

	render_waveform()


def play_next(_button=None):
	global current_index
	nxt = current_index + 1
	if nxt >= len(tracks):
		status_text.set_text("✓ Fin de la liste.")
		return
	play_track(nxt)
	refresh_grid()


def on_play_button(_button, index):
	play_track(index)
	refresh_grid()


# ── Visualiseur arc-en-ciel ───────────────────────────────────────────────────
def _bar_heights(num_bars, max_height):
	t = visual_frame * 0.35
	base = abs(hash(current_track["title"] if current_track else "x")) % 50
	heights = []
	for i in range(num_bars):
		v = (
			abs(math.sin(t * 1.1 + i * 0.18 + base * 0.1))
			* abs(math.cos(t * 0.7 + i * 0.09))
			+ 0.4 * abs(math.sin(t * 2.3 + i * 0.25))
			+ 0.15 * abs(math.sin(t * 0.4 + i * 0.06))
		)
		heights.append(int(max(1, min(max_height, v * max_height / 1.55))))
	return heights


def render_waveform():
	global visual_frame

	if current_track is None:
		waveform_widget.original_widget = urwid.Text(
			"  Sélectionne une piste et clique sur ▶ Play"
		)
		return

	try:
		cols = main_loop.screen.get_cols_rows()[0] - 6
	except Exception:
		cols = 120

	bar_w    = 2          # largeur de chaque barre (caractères)
	gap      = 1          # espace entre barres
	num_bars = max(8, cols // (bar_w + gap))
	bar_max  = 16         # hauteur max des barres
	ref_rows = 5          # lignes de reflet
	BLOCK    = "█" * bar_w
	SPACE    = " " * bar_w

	if not is_paused:
		visual_frame += 1
	heights = _bar_heights(num_bars, bar_max)

	content = []

	# Titre
	title_str = (
		f"  ♪  {short(current_track['title'], 52)}"
		f"  —  {short(current_track['artist'], 28)}"
	)
	content.append(urwid.Text([("vis_title", title_str)]))
	content.append(urwid.Divider())

	# ── Barres (haut → bas) ──────────────────────────────────────────────────
	for row in range(bar_max, 0, -1):
		segs = []
		for ci, h in enumerate(heights):
			attr = _bar_attr(ci, num_bars)
			segs.append((attr if h >= row else "vis_bg", BLOCK))
			segs.append(("vis_bg", " " * gap))
		content.append(urwid.Text(segs))

	# ── Ligne de base ────────────────────────────────────────────────────────
	base_segs = []
	for ci in range(num_bars):
		base_segs.append((_bar_attr(ci, num_bars), "▄" * bar_w))
		base_segs.append(("vis_bg", " " * gap))
	content.append(urwid.Text(base_segs))

	# ── Reflet miroir (dégradé vers le bas) ──────────────────────────────────
	for ref in range(1, ref_rows + 1):
		segs = []
		for ci, h in enumerate(heights):
			attr = _bar_attr(ci, num_bars, dim=True)
			# Seuil : seules les barres hautes ont un reflet visible
			threshold = bar_max - ref * 2
			if h > threshold:
				char = ("▓" if ref <= 2 else ("▒" if ref == 3 else "░")) * bar_w
				segs.append((attr, char))
			else:
				segs.append(("vis_bg", SPACE))
			segs.append(("vis_bg", " " * gap))
		content.append(urwid.Text(segs))

	waveform_widget.original_widget = urwid.Pile(content)


# ── Tick ──────────────────────────────────────────────────────────────────────
def tick(loop, _):
	if player_process is not None and player_process.poll() is not None:
		play_next()
	render_waveform()
	loop.set_alarm_in(0.08, tick)


# ── Clavier ───────────────────────────────────────────────────────────────────
def on_key(key):
	if key in ("q", "Q"):
		raise urwid.ExitMainLoop()   # musique continue
	if key == "esc":
		stop_player()
		raise urwid.ExitMainLoop()
	if key == "enter":
		run_search()
	if key in ("n", "N"):
		next_page()
	if key in ("p", "P"):
		prev_page()
	if key == " ":
		toggle_pause()


# ── Grille ────────────────────────────────────────────────────────────────────
def build_grid_widgets():
	if not tracks:
		return urwid.Text("Aucune piste.")
	cards = []
	for i, track in enumerate(tracks):
		is_cur = (i == current_index)
		src    = track.get("source", "archive").upper()
		title  = short(f"[{src}] {track['title']}", 30)
		artist = short(track["artist"], 30)
		btn    = urwid.Button("⏹ Stop" if is_cur else "▶ Play")
		urwid.connect_signal(btn, "click", on_play_button, i)
		pile = urwid.Pile([
			urwid.Text(("active_title" if is_cur else "card_title", title)),
			urwid.Text(artist),
			urwid.Divider("-"),
			urwid.AttrMap(btn, None, focus_map="reversed"),
		])
		card = urwid.LineBox(pile)
		if is_cur:
			card = urwid.AttrMap(card, "active_card")
		cards.append(card)
	return urwid.GridFlow(cells=cards, cell_width=34, h_sep=2, v_sep=1, align="left")


def refresh_grid():
	if body_walker is None:
		return
	body_walker[7] = build_grid_widgets()


def refresh_header():
	header_text.set_text(
		f"♪ Terminal Music Grid [{active_source}] ({len(tracks)} pistes)  "
		f"|  Page {current_page}  |  Enter=chercher  |  n/p=pages  "
		f"|  Space=pause  |  q=fond  |  Esc=quitter"
	)
	page_text.set_text(f"Page {current_page}")


def load_page(page):
	global tracks, current_page, has_next_page, active_source
	current_page = max(1, page)
	status_text.set_text(f"Recherche : {current_query} (page {current_page})…")
	tracks, source_name, has_more = fetch_tracks(query=current_query, page=current_page)
	active_source = source_name
	has_next_page = has_more
	refresh_header()
	refresh_grid()
	status_text.set_text(
		f"✓ {len(tracks)} pistes  « {current_query} »  (page {current_page})"
	)


def run_search(_button=None):
	global current_query, current_page
	current_query = search_edit.get_edit_text().strip() or DEFAULT_QUERY
	current_page  = 1
	try:
		load_page(1)
	except Exception as e:
		status_text.set_text(f"Erreur: {e}")


def next_page(_button=None):
	if not has_next_page:
		status_text.set_text("Pas d'autre page.")
		return
	try:
		load_page(current_page + 1)
	except Exception as e:
		status_text.set_text(f"Erreur: {e}")


def prev_page(_button=None):
	if current_page <= 1:
		status_text.set_text("Déjà à la première page.")
		return
	try:
		load_page(current_page - 1)
	except Exception as e:
		status_text.set_text(f"Erreur: {e}")


# ── Mini-visualiseur mode fond ─────────────────────────────────────────────────
ANSI_RAINBOW = [226, 214, 208, 46, 48, 51, 27, 93, 201, 196]
ANSI_BARS    = ["▁","▂","▃","▄","▅","▆","▇","█"]

def mini_visualizer_loop():
	global player_process, current_index, current_track, is_paused

	if not shutil.which("cvlc"):
		print("cvlc introuvable.")
		return

	print("\033[2J\033[H", end="")
	print("  🎵 Mode arrière-plan  ─  p=pause  n=suivant  q=quitter\n")

	import termios, tty, select

	old = termios.tcgetattr(sys.stdin)
	frame  = 0
	paused = False

	def _next_track():
		global player_process, current_index, current_track
		stop_player()
		current_index += 1
		if current_index >= len(tracks):
			return False
		current_track = tracks[current_index]
		url = current_track.get("stream_url")
		if url is None:
			try:
				url = resolve_stream_url(current_track)
				current_track["stream_url"] = url
			except Exception:
				url = None
		if url:
			player_process = subprocess.Popen(
				["cvlc", "--play-and-exit", "--quiet", url],
				stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
			)
		return True

	try:
		tty.setcbreak(sys.stdin.fileno())
		while True:
			# Auto-next
			if player_process is not None and player_process.poll() is not None:
				if not _next_track():
					print("\n  ✅ Fin de la liste.")
					break

			# Touche non-bloquante
			dr, _, _ = select.select([sys.stdin], [], [], 0)
			if dr:
				key = sys.stdin.read(1)
				if key == "q":
					break
				elif key == "p":
					if paused:
						resume_player()
						paused = False
					else:
						pause_player()
						paused = True
				elif key == "n":
					if not _next_track():
						print("\n  ✅ Fin de la liste.")
						break

			if not paused:
				frame += 1

			# Mini-visu une ligne
			term_w = shutil.get_terminal_size().columns
			nb     = max(8, (term_w - 40) // 2)
			t      = frame * 0.35
			base   = abs(hash(current_track["title"] if current_track else "x")) % 50
			bar_line = ""
			for i in range(nb):
				v = (
					abs(math.sin(t*1.1 + i*0.18 + base*0.1))
					* abs(math.cos(t*0.7 + i*0.09))
					+ 0.3 * abs(math.sin(t*2.3 + i*0.25))
				)
				h  = int(max(0, min(7, v * 7 / 1.3)))
				ci = int(i * (len(ANSI_RAINBOW)-1) / max(1, nb-1))
				c  = ANSI_RAINBOW[ci]
				bar_line += f"\033[38;5;{c}m{ANSI_BARS[h]}\033[0m"

			state = "⏸" if paused else "▶"
			title = short(current_track["title"] if current_track else "?", 32)
			line  = f"\r  {state} {bar_line}  {title}  [p=pause n=suiv q=quit]"
			print(line.ljust(term_w - 1), end="", flush=True)
			time.sleep(0.08)

	except KeyboardInterrupt:
		pass
	finally:
		termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
		stop_player()
		print("\n\n  👋 Au revoir !")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
	global current_query, main_loop, body_walker

	current_query = DEFAULT_QUERY
	try:
		load_page(1)
	except Exception as exc:
		print(f"Échec du chargement : {exc}")
		sys.exit(1)

	# Recherche
	search_btn = urwid.Button("🔍 Chercher")
	urwid.connect_signal(search_btn, "click", run_search)
	search_field = urwid.LineBox(
		urwid.AttrMap(search_edit, "search_box"),
		tlcorner="╭", trcorner="╮", blcorner="╰", brcorner="╯",
	)
	search_row = urwid.Columns(
		[
			("weight", 4, urwid.AttrMap(search_field, "search_border")),
			("fixed", 15, urwid.AttrMap(search_btn, None, focus_map="reversed")),
		],
		dividechars=1,
	)

	# Contrôles lecture
	urwid.connect_signal(playpause_btn, "click", toggle_pause)
	next_btn = urwid.Button("⏭ Suivant")
	urwid.connect_signal(next_btn, "click", play_next)
	ctrl_row = urwid.Columns(
		[
			("fixed", 14, urwid.AttrMap(playpause_btn, "ctrl_btn", focus_map="reversed")),
			("fixed", 14, urwid.AttrMap(next_btn,      "ctrl_btn", focus_map="reversed")),
			("weight", 1, status_text),
		],
		dividechars=1,
	)

	# Pagination
	prev_btn = urwid.Button("◀ Préc")
	nxt_btn  = urwid.Button("Suiv ▶")
	urwid.connect_signal(prev_btn, "click", prev_page)
	urwid.connect_signal(nxt_btn,  "click", next_page)
	pager_row = urwid.Columns(
		[
			("fixed", 10, urwid.AttrMap(prev_btn, None, focus_map="reversed")),
			("weight",  1, page_text),
			("fixed", 10, urwid.AttrMap(nxt_btn,  None, focus_map="reversed")),
		],
		dividechars=2,
	)

	waveform_box = urwid.LineBox(waveform_widget, title="═ Visualiseur ═")
	grid         = build_grid_widgets()

	body = urwid.ListBox(
		urwid.SimpleFocusListWalker([
			header_text,         # 0
			search_row,          # 1
			ctrl_row,            # 2
			urwid.Divider("─"),  # 3
			waveform_box,        # 4
			urwid.Divider("─"),  # 5
			pager_row,           # 6
			grid,                # 7
		])
	)
	body_walker = body.body

	frame = urwid.Frame(
		body=urwid.Padding(body, left=1, right=1),
		footer=urwid.AttrMap(
			urwid.Text(
				"  q=musique en fond  Esc=stop+quitter  "
				"Space=pause  n/p=pages"
			),
			"footer",
		),
	)

	# ── Palette ───────────────────────────────────────────────────────────────
	palette = [
		("reversed",     "standout",        ""),
		("vis_title",    "light cyan,bold",  ""),
		("vis_bg",       "default",          ""),
		("title",        "light cyan,bold",  ""),
		("active_title", "yellow,bold",      ""),
		("active_card",  "yellow",           ""),
		("card_title",   "white",            ""),
		("ctrl_btn",     "black",            "dark cyan"),
		("search_box",   "white",            "default"),
		("search_border", "light cyan",      "default"),
		("footer",       "black",            "dark blue"),
	]
	# Barres + reflets arc-en-ciel
	for i, (col, dim) in enumerate(zip(RAINBOW_COLS, RAINBOW_DIM)):
		palette.append((f"bar_{i}", "black", col))
		palette.append((f"ref_{i}", "dark blue", dim))

	screen = urwid.raw_display.Screen()
	screen.set_terminal_properties(colors=256)
	main_loop = urwid.MainLoop(
		frame, palette=palette,
		unhandled_input=on_key,
		handle_mouse=True,
		screen=screen,
	)
	main_loop.set_alarm_in(0.08, tick)

	try:
		main_loop.run()
	except Exception:
		pass

	# Après fermeture UI (q) → mini-visualiseur si musique en cours
	if player_process is not None and player_process.poll() is None:
		mini_visualizer_loop()
	else:
		stop_player()
		print("\n  👋 Au revoir !")


if __name__ == "__main__":
	main()