#!/usr/bin/env python3
"""
github_cleanup.py - Robot pembersih repo GitHub (dengan pengesahan)

Cara guna:
    python github_cleanup.py                    # senarai semua repo milik anda
    python github_cleanup.py --older-than 12    # hanya repo tiada push > 12 bulan
    python github_cleanup.py --forks-only       # hanya repo fork
    python github_cleanup.py --backup           # clone --mirror dulu sebelum padam
    python github_cleanup.py --dry-run          # simulasi sahaja, tiada apa dipadam

Token:
    Set pemboleh ubah GITHUB_TOKEN, atau skrip akan minta token semasa dijalankan.
    - Classic token : scope "repo" + "delete_repo"
    - Fine-grained  : Repository permission "Administration: Read and write"
"""

import argparse
import datetime as dt
import getpass
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
LOG_FILE = "github_cleanup_log.txt"


# ---------------------------------------------------------------- API helpers
def api(method, path, token, body=None):
    url = path if path.startswith("http") else API + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "github-cleanup-script")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            link = r.headers.get("Link", "")
            return r.status, (json.loads(raw) if raw else None), link
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read()).get("message", "")
        except Exception:
            msg = ""
        return e.code, {"message": msg}, ""


def next_link(link_header):
    for part in link_header.split(","):
        if 'rel="next"' in part:
            return part[part.find("<") + 1 : part.find(">")]
    return None


def get_all_repos(token):
    repos, url = [], "/user/repos?affiliation=owner&per_page=100&sort=pushed&direction=asc"
    while url:
        status, data, link = api("GET", url, token)
        if status != 200:
            sys.exit(f"Gagal ambil senarai repo ({status}): {data.get('message')}")
        repos.extend(data)
        url = next_link(link)
    return repos


# ---------------------------------------------------------------- utilities
def parse_date(s):
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ") if s else None


def months_ago(d):
    if not d:
        return 999
    return (dt.datetime.utcnow() - d).days / 30.44


def parse_selection(text, max_n):
    text = text.strip().lower()
    if text in ("all", "semua"):
        return list(range(1, max_n + 1))
    picked = set()
    for part in text.replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            picked.update(range(int(a), int(b) + 1))
        else:
            picked.add(int(part))
    return sorted(n for n in picked if 1 <= n <= max_n)


def log(line):
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {line}\n")


def backup_repo(repo, token, folder="backup_repos"):
    os.makedirs(folder, exist_ok=True)
    target = os.path.join(folder, repo["name"] + ".git")
    if os.path.exists(target):
        print(f"   Backup sudah wujud: {target}")
        return True
    url = repo["clone_url"].replace("https://", f"https://x-access-token:{token}@")
    print(f"   Backup -> {target} ...")
    r = subprocess.run(["git", "clone", "--mirror", "--quiet", url, target],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"   ✗ Backup gagal: {r.stderr.strip().replace(token, '***')}")
        return False
    print("   ✓ Backup siap")
    return True


# ---------------------------------------------------------------- main
def parse_args():
    p = argparse.ArgumentParser(description="Padam / archive repo GitHub lama dengan pengesahan.")
    p.add_argument("--older-than", type=int, default=0, metavar="BULAN",
                   help="Hanya tunjuk repo yang tiada push melebihi N bulan")
    p.add_argument("--forks-only", action="store_true", help="Hanya tunjuk repo fork")
    p.add_argument("--hide-archived", action="store_true", help="Sembunyikan repo yang sudah di-archive")
    p.add_argument("--backup", action="store_true", help="git clone --mirror sebelum padam")
    p.add_argument("--dry-run", action="store_true", help="Simulasi sahaja, tiada perubahan")
    return p.parse_args()


def get_token():
    token = os.environ.get("GITHUB_TOKEN") or getpass.getpass("GitHub token: ").strip()
    if not token:
        sys.exit("Token diperlukan.")
    return token


def run_once(args, token):
    status, me, _ = api("GET", "/user", token)
    if status != 200:
        sys.exit(f"Token tidak sah ({status}): {me.get('message')}")
    username = me["login"]
    print(f"\nLog masuk sebagai: {username}")
    if args.dry_run:
        print(">>> MOD DRY-RUN: tiada repo akan dipadam/di-archive <<<")

    repos = get_all_repos(token)
    if args.older_than:
        repos = [r for r in repos if months_ago(parse_date(r["pushed_at"])) >= args.older_than]
    if args.forks_only:
        repos = [r for r in repos if r["fork"]]
    if args.hide_archived:
        repos = [r for r in repos if not r["archived"]]

    if not repos:
        print("Tiada repo yang padan dengan tapisan.")
        return

    # Paparan senarai
    print(f"\n{'No':>3}  {'Nama repo':<40} {'Jenis':<8} {'Push terakhir':<13} {'★':>3} {'Saiz':>8}  Nota")
    print("-" * 95)
    for i, r in enumerate(repos, 1):
        pushed = parse_date(r["pushed_at"])
        notes = []
        if r["fork"]:
            notes.append("fork")
        if r["archived"]:
            notes.append("archived")
        print(f"{i:>3}  {r['name'][:40]:<40} {'private' if r['private'] else 'public':<8} "
              f"{pushed.strftime('%Y-%m-%d') if pushed else '-':<13} "
              f"{r['stargazers_count']:>3} {r['size']/1024:>6.1f}MB  {', '.join(notes)}")
    print(f"\nJumlah: {len(repos)} repo")

    sel = input("\nPilih nombor repo (cth: 1,3,5-9 | semua | kosong = batal): ")
    if not sel.strip():
        print("Dibatalkan.")
        return
    try:
        chosen = [repos[n - 1] for n in parse_selection(sel, len(repos))]
    except ValueError:
        sys.exit("Format pilihan tidak sah.")
    if not chosen:
        print("Tiada repo dipilih.")
        return

    # Pengesahan satu per satu
    to_delete, to_archive = [], []
    print("\nSahkan setiap repo:  [p] padam   [a] archive sahaja   [l] langkau   [q] berhenti")
    for r in chosen:
        while True:
            ans = input(f"  {r['full_name']}  ->  ").strip().lower()
            if ans in ("p", "a", "l", "q"):
                break
            print("    Sila taip p / a / l / q")
        if ans == "q":
            break
        if ans == "p":
            to_delete.append(r)
        elif ans == "a":
            to_archive.append(r)

    if not to_delete and not to_archive:
        print("Tiada tindakan dipilih. Selesai.")
        return

    # Ringkasan + pengesahan akhir
    print("\n================ RINGKASAN ================")
    if to_delete:
        print(f"AKAN DIPADAM KEKAL ({len(to_delete)}):")
        for r in to_delete:
            print(f"   ✗ {r['full_name']}")
    if to_archive:
        print(f"AKAN DI-ARCHIVE ({len(to_archive)}):")
        for r in to_archive:
            print(f"   ▣ {r['full_name']}")
    print("===========================================")

    phrase = f"SAH {len(to_delete) + len(to_archive)}"
    confirm = input(f"\nTindakan PADAM tidak boleh diundur.\nTaip '{phrase}' untuk teruskan: ").strip()
    if confirm != phrase:
        print("Pengesahan tidak sepadan. Dibatalkan — tiada apa-apa diubah.")
        return

    # Laksana
    ok = fail = 0
    for r in to_archive:
        name = r["full_name"]
        if args.dry_run:
            print(f"[dry-run] archive {name}")
            continue
        status, data, _ = api("PATCH", f"/repos/{name}", token, {"archived": True})
        if status == 200:
            print(f"✓ Archived: {name}")
            log(f"ARCHIVED {name}")
            ok += 1
        else:
            print(f"✗ Gagal archive {name} ({status}): {data.get('message')}")
            fail += 1

    for r in to_delete:
        name = r["full_name"]
        if args.backup and not args.dry_run:
            if not backup_repo(r, token):
                print(f"   Langkau padam {name} kerana backup gagal.")
                fail += 1
                continue
        if args.dry_run:
            print(f"[dry-run] padam {name}")
            continue
        status, data, _ = api("DELETE", f"/repos/{name}", token)
        if status == 204:
            print(f"✓ Dipadam: {name}")
            log(f"DELETED {name}")
            ok += 1
        elif status == 403:
            print(f"✗ Tiada kebenaran padam {name}. Token perlukan scope 'delete_repo'.")
            fail += 1
        else:
            print(f"✗ Gagal padam {name} ({status}): {data.get('message')}")
            fail += 1

    print(f"\nSelesai. Berjaya: {ok}  Gagal: {fail}")
    if not args.dry_run and ok:
        print(f"Log disimpan dalam {LOG_FILE}")


def pause():
    try:
        input("\nTekan Enter untuk keluar...")
    except (KeyboardInterrupt, EOFError):
        pass


def main():
    args = parse_args()
    try:
        token = get_token()
    except SystemExit as e:
        print(e.code)
        return

    while True:
        try:
            run_once(args, token)
        except SystemExit as e:          # ralat dalam run_once: papar, jangan tutup
            if e.code:
                print(f"\n{e.code}")
        except KeyboardInterrupt:
            print("\nDibatalkan oleh pengguna.")
        except Exception as e:           # ralat tak dijangka: papar, jangan tutup
            print(f"\nRalat: {e}")

        try:
            again = input("\nUlang lagi (senarai dikemas kini)? [y/N]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break
        if again not in ("y", "ya"):
            break


if __name__ == "__main__":
    try:
        main()
    finally:
        pause()
