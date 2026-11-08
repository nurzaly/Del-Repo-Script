#!/usr/bin/env python3
"""
github_cleanup.py - GitHub repo cleanup bot (with confirmation)

Usage:
    python github_cleanup.py                    # list all repos you own
    python github_cleanup.py --older-than 12    # only repos with no push > 12 months
    python github_cleanup.py --forks-only       # forks only
    python github_cleanup.py --backup           # clone --mirror before deleting
    python github_cleanup.py --dry-run          # simulate only, nothing is deleted

Token:
    Set the GITHUB_TOKEN environment variable, or the script will prompt for it.
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
            sys.exit(f"Failed to fetch repo list ({status}): {data.get('message')}")
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
    if text == "all":
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
        print(f"   Backup already exists: {target}")
        return True
    url = repo["clone_url"].replace("https://", f"https://x-access-token:{token}@")
    print(f"   Backup -> {target} ...")
    r = subprocess.run(["git", "clone", "--mirror", "--quiet", url, target],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"   ✗ Backup failed: {r.stderr.strip().replace(token, '***')}")
        return False
    print("   ✓ Backup complete")
    return True


# ---------------------------------------------------------------- main
def parse_args():
    p = argparse.ArgumentParser(description="Delete / archive old GitHub repos with confirmation.")
    p.add_argument("--older-than", type=int, default=0, metavar="MONTHS",
                   help="Only show repos with no push in the last N months")
    p.add_argument("--forks-only", action="store_true", help="Only show forked repos")
    p.add_argument("--hide-archived", action="store_true", help="Hide repos that are already archived")
    p.add_argument("--backup", action="store_true", help="git clone --mirror before deleting")
    p.add_argument("--dry-run", action="store_true", help="Simulate only, make no changes")
    return p.parse_args()


def get_token():
    token = os.environ.get("GITHUB_TOKEN") or getpass.getpass("GitHub token: ").strip()
    if not token:
        sys.exit("A token is required.")
    return token


def run_once(args, token):
    status, me, _ = api("GET", "/user", token)
    if status != 200:
        sys.exit(f"Invalid token ({status}): {me.get('message')}")
    username = me["login"]
    print(f"\nLogged in as: {username}")
    if args.dry_run:
        print(">>> DRY-RUN MODE: no repos will be deleted or archived <<<")

    repos = get_all_repos(token)
    if args.older_than:
        repos = [r for r in repos if months_ago(parse_date(r["pushed_at"])) >= args.older_than]
    if args.forks_only:
        repos = [r for r in repos if r["fork"]]
    if args.hide_archived:
        repos = [r for r in repos if not r["archived"]]

    if not repos:
        print("No repos match the filters.")
        return

    # Show list
    print(f"\n{'No':>3}  {'Repo name':<40} {'Type':<8} {'Last push':<13} {'★':>3} {'Size':>8}  Notes")
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
    print(f"\nTotal: {len(repos)} repos")

    sel = input("\nSelect repo numbers (e.g. 1,3,5-9 | all | empty = cancel): ")
    if not sel.strip():
        print("Cancelled.")
        return
    try:
        chosen = [repos[n - 1] for n in parse_selection(sel, len(repos))]
    except ValueError:
        sys.exit("Invalid selection format.")
    if not chosen:
        print("No repos selected.")
        return

    # Confirm one by one
    to_delete, to_archive = [], []
    print("\nConfirm each repo:  [d] delete   [a] archive only   [s] skip   [q] quit")
    for r in chosen:
        while True:
            ans = input(f"  {r['full_name']}  ->  ").strip().lower()
            if ans in ("d", "a", "s", "q"):
                break
            print("    Please type d / a / s / q")
        if ans == "q":
            break
        if ans == "d":
            to_delete.append(r)
        elif ans == "a":
            to_archive.append(r)

    if not to_delete and not to_archive:
        print("No actions selected. Done.")
        return

    # Summary + final confirmation
    print("\n================= SUMMARY =================")
    if to_delete:
        print(f"WILL BE PERMANENTLY DELETED ({len(to_delete)}):")
        for r in to_delete:
            print(f"   ✗ {r['full_name']}")
    if to_archive:
        print(f"WILL BE ARCHIVED ({len(to_archive)}):")
        for r in to_archive:
            print(f"   ▣ {r['full_name']}")
    print("===========================================")

    phrase = f"CONFIRM {len(to_delete) + len(to_archive)}"
    confirm = input(f"\nDELETE cannot be undone.\nType '{phrase}' to continue: ").strip()
    if confirm != phrase:
        print("Confirmation did not match. Cancelled — nothing was changed.")
        return

    # Execute
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
            print(f"✗ Failed to archive {name} ({status}): {data.get('message')}")
            fail += 1

    for r in to_delete:
        name = r["full_name"]
        if args.backup and not args.dry_run:
            if not backup_repo(r, token):
                print(f"   Skipping delete of {name} because the backup failed.")
                fail += 1
                continue
        if args.dry_run:
            print(f"[dry-run] delete {name}")
            continue
        status, data, _ = api("DELETE", f"/repos/{name}", token)
        if status == 204:
            print(f"✓ Deleted: {name}")
            log(f"DELETED {name}")
            ok += 1
        elif status == 403:
            print(f"✗ No permission to delete {name}. Token needs the 'delete_repo' scope.")
            fail += 1
        else:
            print(f"✗ Failed to delete {name} ({status}): {data.get('message')}")
            fail += 1

    print(f"\nDone. Succeeded: {ok}  Failed: {fail}")
    if not args.dry_run and ok:
        print(f"Log saved to {LOG_FILE}")


def pause():
    try:
        input("\nPress Enter to exit...")
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
        except SystemExit as e:          # error in run_once: show it, keep console open
            if e.code:
                print(f"\n{e.code}")
        except KeyboardInterrupt:
            print("\nCancelled by user.")
        except Exception as e:           # unexpected error: show it, keep console open
            print(f"\nError: {e}")

        try:
            again = input("\nRun again (refreshed list)? [y/N]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break
        if again not in ("y", "yes"):
            break


if __name__ == "__main__":
    try:
        main()
    finally:
        pause()
