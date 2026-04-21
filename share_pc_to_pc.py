#!/usr/bin/env python3
"""share_pc_to_pc.py

Peer-to-peer LAN file transfer tool with:
- UDP broadcast discovery
- TCP file/folder transfer
- optional password auth
- multi-target send
- transfer history
- simple progress output
"""

import argparse
import datetime
import hashlib
import json
import os
import socket
import threading
import time
from pathlib import Path


BROADCAST_PORT = 50000
TRANSFER_PORT = 50001
BUFFER_SIZE = 64 * 1024
DISCOVER_MSG = "DISCOVER_PC"
RESPONSE_MSG = "HERE_PC"
DEFAULT_HISTORY_FILE = Path("transfer_history.log")

print_lock = threading.Lock()


def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_transfer(message, history_file=DEFAULT_HISTORY_FILE):
    path = Path(history_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"[{now_str()}] {message}\n")


def hash_password(password):
    if not password:
        return "NO_PASS"
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def sha256_file(file_path):
    digest = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(BUFFER_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def human_size(num_bytes):
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num_bytes)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)}{unit}"
            return f"{value:.1f}{unit}"
        value /= 1024.0


def print_line(text):
    with print_lock:
        print(text, flush=True)


def print_progress(prefix, current, total, suffix=""):
    if total <= 0:
        total = 1
    percent = int((current / total) * 100)
    width = 24
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    with print_lock:
        print(f"\r{prefix} [{bar}] {percent:3d}% {suffix}", end="", flush=True)


def finish_progress(prefix, suffix=""):
    with print_lock:
        print(f"\r{prefix} [████████████████████████] 100% {suffix}")


def get_local_ips():
    ips = {"127.0.0.1"}
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, family=socket.AF_INET):
            ips.add(info[4][0])
    except Exception:
        pass
    return ips


def is_inside_base(base_dir, candidate_path):
    base_dir = Path(base_dir).resolve()
    candidate_path = Path(candidate_path).resolve()
    return candidate_path == base_dir or base_dir in candidate_path.parents


def sanitize_relative_path(rel_path):
    rel = Path(rel_path)
    if rel.is_absolute():
        raise ValueError("absolute path not allowed")
    parts = []
    for part in rel.parts:
        if part in ("", "."):
            continue
        if part == "..":
            raise ValueError("path traversal not allowed")
        parts.append(part)
    if not parts:
        raise ValueError("empty relative path")
    return Path(*parts)


def discover_local_files(source_path):
    src = Path(source_path).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"Chemin introuvable: {src}")

    if src.is_file():
        return [(src, Path(src.name))]

    root_name = Path(src.name)
    items = []
    for file_path in src.rglob("*"):
        if file_path.is_file():
            rel_path = root_name / file_path.relative_to(src)
            items.append((file_path, rel_path))
    return items


def recv_line(sock_file, max_len=8192):
    line = sock_file.readline(max_len + 1)
    if not line:
        return b""
    if len(line) > max_len:
        raise ValueError("protocol line too long")
    if not line.endswith(b"\n"):
        raise ValueError("protocol line incomplete")
    return line[:-1]


def listen_for_discovery(stop_event=None):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp.bind(("", BROADCAST_PORT))
        udp.settimeout(1.0)
        hostname = socket.gethostname()

        while True:
            if stop_event and stop_event.is_set():
                return
            try:
                data, addr = udp.recvfrom(1024)
            except socket.timeout:
                continue
            except Exception:
                continue

            if data.decode("utf-8", errors="ignore") != DISCOVER_MSG:
                continue

            payload = json.dumps(
                {
                    "msg": RESPONSE_MSG,
                    "host": hostname,
                    "port": TRANSFER_PORT,
                }
            ).encode("utf-8")

            try:
                udp.sendto(payload, addr)
            except Exception:
                pass


def discover_peers(timeout=2.0):
    peers = {}
    local_ips = get_local_ips()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp.settimeout(timeout)

        for target in ("<broadcast>", "255.255.255.255"):
            try:
                udp.sendto(DISCOVER_MSG.encode("utf-8"), (target, BROADCAST_PORT))
            except Exception:
                pass

        while True:
            try:
                data, addr = udp.recvfrom(2048)
            except socket.timeout:
                break
            except Exception:
                break

            ip = addr[0]
            if ip in local_ips:
                continue

            try:
                payload = json.loads(data.decode("utf-8", errors="ignore"))
            except Exception:
                continue

            if payload.get("msg") != RESPONSE_MSG:
                continue

            peers[ip] = {
                "ip": ip,
                "host": payload.get("host") or "unknown",
                "port": int(payload.get("port", TRANSFER_PORT)),
            }

    return list(peers.values())


def choose_targets_interactive(peers):
    if not peers:
        return []

    print_line("Machines detectees:")
    for idx, peer in enumerate(peers, 1):
        print_line(f"  {idx}. {peer['host']} ({peer['ip']})")

    raw = input("Selection (1,3 | all | ip:192.168.1.10) [defaut=all]: ").strip()
    if not raw or raw.lower() == "all":
        return [peer["ip"] for peer in peers]

    selected = []
    for token in [part.strip() for part in raw.split(",") if part.strip()]:
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(peers):
                selected.append(peers[idx]["ip"])
        elif token.startswith("ip:"):
            selected.append(token[3:])
        elif token.count(".") == 3:
            selected.append(token)

    return sorted(set(selected))


def send_one_file(sock, file_path, rel_path, target_ip):
    file_size = file_path.stat().st_size
    sent = 0

    header = {
        "type": "file",
        "name": str(rel_path),
        "size": file_size,
        "sha256": sha256_file(file_path),
    }
    sock.sendall((json.dumps(header) + "\n").encode("utf-8"))

    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(BUFFER_SIZE)
            if not chunk:
                break
            sock.sendall(chunk)
            sent += len(chunk)
            print_progress(
                f"[{target_ip}] {rel_path}",
                sent,
                file_size,
                suffix=f"{human_size(sent)}/{human_size(file_size)}",
            )

    finish_progress(
        f"[{target_ip}] {rel_path}",
        suffix=f"{human_size(file_size)} envoye",
    )


def send_files(target_ip, source_path, password=None, retry_count=2, history_file=DEFAULT_HISTORY_FILE):
    files = discover_local_files(source_path)
    auth_hash = hash_password(password)
    sender_host = socket.gethostname()

    last_error = None
    for attempt in range(1, retry_count + 2):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(20)
                sock.connect((target_ip, TRANSFER_PORT))

                auth_frame = {
                    "type": "auth",
                    "password_hash": auth_hash,
                    "sender": sender_host,
                }
                sock.sendall((json.dumps(auth_frame) + "\n").encode("utf-8"))

                for file_path, rel_path in files:
                    send_one_file(sock, file_path, rel_path, target_ip)
                    log_transfer(
                        f"SEND | target={target_ip} | file={rel_path} | size={file_path.stat().st_size}",
                        history_file,
                    )

                done_frame = {"type": "done", "count": len(files)}
                sock.sendall((json.dumps(done_frame) + "\n").encode("utf-8"))

            print_line(f"OK: envoye vers {target_ip} ({len(files)} fichier(s))")
            return True

        except Exception as exc:
            last_error = exc
            print_line(f"Echec envoi vers {target_ip} (tentative {attempt}/{retry_count + 1}): {exc}")
            log_transfer(
                f"SEND ERROR | target={target_ip} | attempt={attempt} | err={exc}",
                history_file,
            )
            if attempt <= retry_count:
                time.sleep(1.0)

    print_line(f"Abandon vers {target_ip}: {last_error}")
    return False


def multi_send(target_ips, source_path, password=None, retry_count=2, history_file=DEFAULT_HISTORY_FILE):
    threads = []
    results = {}
    results_lock = threading.Lock()

    def runner(ip):
        ok = send_files(
            ip,
            source_path,
            password=password,
            retry_count=retry_count,
            history_file=history_file,
        )
        with results_lock:
            results[ip] = ok

    for ip in target_ips:
        thread = threading.Thread(target=runner, args=(ip,), daemon=True)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    return results


def _receive_client(conn, addr, save_dir, password, history_file):
    expected_hash = hash_password(password)
    base_dir = Path(save_dir).expanduser().resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    sender_ip = addr[0]

    try:
        with conn:
            rf = conn.makefile("rb")

            auth_line = recv_line(rf)
            if not auth_line:
                return

            auth_frame = json.loads(auth_line.decode("utf-8"))
            if auth_frame.get("type") != "auth":
                log_transfer(f"RECV DENY | sender={sender_ip} | reason=missing_auth", history_file)
                return

            if auth_frame.get("password_hash", "") != expected_hash:
                print_line(f"Refus: mauvais mot de passe depuis {sender_ip}")
                log_transfer(f"RECV DENY | sender={sender_ip} | reason=bad_password", history_file)
                return

            sender_host = auth_frame.get("sender") or "unknown"
            print_line(f"Reception depuis {sender_host} ({sender_ip})")
            log_transfer(f"RECV START | sender={sender_ip} | host={sender_host}", history_file)

            while True:
                line = recv_line(rf)
                if not line:
                    break

                frame = json.loads(line.decode("utf-8"))
                frame_type = frame.get("type")
                if frame_type == "done":
                    break
                if frame_type != "file":
                    continue

                rel_name = sanitize_relative_path(frame.get("name", ""))
                file_size = int(frame.get("size", 0))
                expected_sha = frame.get("sha256") or ""

                final_path = (base_dir / rel_name).resolve()
                if not is_inside_base(base_dir, final_path):
                    log_transfer(
                        f"RECV BLOCK | sender={sender_ip} | path={rel_name}",
                        history_file,
                    )
                    return

                final_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path = final_path.with_name(final_path.name + ".part")

                received = 0
                digest = hashlib.sha256()
                with open(temp_path, "wb") as out:
                    while received < file_size:
                        chunk = rf.read(min(BUFFER_SIZE, file_size - received))
                        if not chunk:
                            raise ConnectionError("connexion interrompue")
                        out.write(chunk)
                        digest.update(chunk)
                        received += len(chunk)
                        print_progress(
                            f"[RECV {sender_ip}] {rel_name}",
                            received,
                            file_size,
                            suffix=f"{human_size(received)}/{human_size(file_size)}",
                        )

                if expected_sha and digest.hexdigest() != expected_sha:
                    print_line(f"Hash invalide: {final_path}")
                    try:
                        temp_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    log_transfer(
                        f"RECV HASH_MISMATCH | sender={sender_ip} | file={rel_name}",
                        history_file,
                    )
                    continue

                temp_path.replace(final_path)
                finish_progress(
                    f"[RECV {sender_ip}] {rel_name}",
                    suffix=f"{human_size(file_size)} recu",
                )
                print_line(f"Recu: {final_path}")
                log_transfer(
                    f"RECV OK | sender={sender_ip} | file={rel_name} | size={file_size}",
                    history_file,
                )

            print_line(f"Fin reception depuis {sender_ip}")

    except Exception as exc:
        print_line(f"Reception interrompue depuis {sender_ip}: {exc}")
        log_transfer(f"RECV ERROR | sender={sender_ip} | err={exc}", history_file)


def receive_files(save_dir="received", password=None, history_file=DEFAULT_HISTORY_FILE):
    print_line(f"Serveur actif sur 0.0.0.0:{TRANSFER_PORT}")
    print_line("En attente de fichiers...")
    log_transfer(f"LISTEN START | port={TRANSFER_PORT} | save_dir={save_dir}", history_file)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("", TRANSFER_PORT))
        server.listen(20)

        while True:
            conn, addr = server.accept()
            threading.Thread(
                target=_receive_client,
                args=(conn, addr, save_dir, password, history_file),
                daemon=True,
            ).start()


def print_history(history_file=DEFAULT_HISTORY_FILE, limit=40):
    path = Path(history_file)
    if not path.exists():
        print_line("Aucun historique.")
        return

    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for line in lines[-limit:]:
        print_line(line)


def parse_targets(raw_targets, peers):
    if not raw_targets:
        return choose_targets_interactive(peers)

    raw_targets = raw_targets.strip().lower()
    if raw_targets == "all":
        return [peer["ip"] for peer in peers]

    available = {peer["ip"] for peer in peers}
    targets = []
    for token in [part.strip() for part in raw_targets.split(",") if part.strip()]:
        if token in available:
            targets.append(token)
        elif token.startswith("ip:"):
            targets.append(token[3:])
        elif token.count(".") == 3:
            targets.append(token)
        elif token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(peers):
                targets.append(peers[idx]["ip"])

    return sorted(set(targets))


def main():
    parser = argparse.ArgumentParser(description="LAN file/folder transfer tool")
    parser.add_argument("--listen", action="store_true", help="Start TCP receiver")
    parser.add_argument("--send", type=str, help="File or folder to send")
    parser.add_argument("--discover", action="store_true", help="Only scan LAN peers")
    parser.add_argument("--targets", type=str, help="Comma-separated target IPs or 'all'")
    parser.add_argument("--password", type=str, help="Optional password")
    parser.add_argument("--save-dir", type=str, default="received", help="Receive directory")
    parser.add_argument("--retry", type=int, default=2, help="Retry count for send failures")
    parser.add_argument("--history", action="store_true", help="Show transfer history")
    parser.add_argument(
        "--history-file",
        type=str,
        default=str(DEFAULT_HISTORY_FILE),
        help="History log path",
    )

    args = parser.parse_args()
    history_file = Path(args.history_file)

    stop_event = threading.Event()
    discovery_thread = threading.Thread(
        target=listen_for_discovery,
        args=(stop_event,),
        daemon=True,
    )
    discovery_thread.start()

    try:
        if args.history:
            print_history(history_file=history_file)
            return

        if args.listen:
            receive_files(
                save_dir=args.save_dir,
                password=args.password,
                history_file=history_file,
            )
            return

        if args.discover and not args.send:
            peers = discover_peers()
            if not peers:
                print_line("Aucune machine detectee.")
                print_line("Verifier: meme reseau, firewall, ports UDP/TCP ouverts.")
                return

            print_line("Machines detectees:")
            for peer in peers:
                print_line(f"- {peer['host']} ({peer['ip']})")
            return

        if args.send:
            peers = discover_peers()
            if peers:
                print_line("Machines detectees:")
                for idx, peer in enumerate(peers, 1):
                    print_line(f"  {idx}. {peer['host']} ({peer['ip']})")
            else:
                print_line("Aucune machine detectee automatiquement.")
                print_line("Tu peux forcer une cible avec --targets 192.168.x.x")

            targets = parse_targets(args.targets, peers)
            if not targets:
                print_line("Aucune cible selectionnee.")
                return

            print_line(f"Targets: {', '.join(targets)}")
            results = multi_send(
                targets,
                args.send,
                password=args.password,
                retry_count=max(0, args.retry),
                history_file=history_file,
            )

            ok_count = sum(1 for ok in results.values() if ok)
            fail_count = len(results) - ok_count
            print_line(f"Termine: {ok_count} ok, {fail_count} echec(s)")
            return

        parser.print_help()

    finally:
        stop_event.set()


if __name__ == "__main__":
    main()