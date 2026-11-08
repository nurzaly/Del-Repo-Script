# 🧹 GitHub Cleanup

A Python script for cleaning up old, unused GitHub repositories. You can **delete** or **archive** repos in bulk, and **nothing changes until you confirm it**.

It uses only the Python standard library, so there's nothing to `pip install`.

> ℹ️ The script's on-screen prompts are in Bahasa Melayu. This README explains each prompt in English.

---

## ✨ Features

- 📋 Lists all repos you own (public and private), oldest first
- 🔍 Filters by inactivity period or forks only, and can hide repos that are already archived
- ✅ **3 layers of confirmation** before anything changes
- 📦 Option to **archive** a repo (read-only, can be reopened) instead of deleting it
- 💾 Optional **backup** (`git clone --mirror`) before deleting
- 🧪 **Dry-run** mode to simulate a run without changing anything
- 📝 Logs every action to `github_cleanup_log.txt`
- 🔁 The console stays open when the script finishes, with an option to run it again

---

## 📦 Requirements

- Python 3.8 or newer
- `git` (only needed for `--backup`)
- A GitHub Personal Access Token

### Creating a token

Go to **GitHub → Settings → Developer settings → Personal access tokens**.

| Token type | Required permissions |
|---|---|
| Classic | `repo` and `delete_repo` |
| Fine-grained | Repository access: *All repositories*<br>Permission: **Administration → Read and write** |

> ⚠️ Keep your token safe. Never commit it to a repository.

---

## 🚀 Usage

### 1. Set the token (optional)

If `GITHUB_TOKEN` is not set, the script asks for the token when it starts. What you type stays hidden.

**Windows (PowerShell)**
```powershell
$env:GITHUB_TOKEN = "ghp_xxxxxxxxxxxx"
```

**Windows (CMD)**
```cmd
set GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

**Linux / macOS**
```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

### 2. Run it

```bash
python github_cleanup.py
```

On Windows you can also double-click `github_cleanup.py`. The console window stays open when it finishes.

### Options

| Flag | What it does |
|---|---|
| `--older-than N` | Only shows repos with no push in the last **N months** |
| `--forks-only` | Only shows forked repos |
| `--hide-archived` | Hides repos that are already archived |
| `--backup` | Runs `git clone --mirror` into `backup_repos/` before deleting |
| `--dry-run` | Simulates the run without changing any repos |
| `-h`, `--help` | Shows help |

### Examples

```bash
# Try it first: nothing is deleted
python github_cleanup.py --dry-run --older-than 12

# Repos inactive for more than 2 years, backed up before deletion
python github_cleanup.py --older-than 24 --backup

# Clean up forks only
python github_cleanup.py --forks-only --hide-archived
```

---

## 🔐 Confirmation flow

```
Repo list
   │
   ▼
[1] Pick repo numbers        →  1,3,5-9  |  semua (all)  |  (empty = cancel)
   │
   ▼
[2] Confirm each repo        →  p = delete (padam)
   │                            a = archive
   │                            l = skip (langkau)
   │                            q = quit
   ▼
[3] Summary + type "SAH <count>"   (e.g. SAH 7)
   │
   ▼
Execute → log → "Ulang lagi? [y/N]" (run again?)
```

If the text you type at step 3 doesn't match exactly, **everything is cancelled** and nothing changes.

### Sample output

```
 No  Nama repo                                Jenis    Push terakhir   ★     Saiz  Nota
-----------------------------------------------------------------------------------------------
  1  test-laravel-2019                        public   2019-04-12      0    1.2MB
  2  bootstrap-fork                           public   2020-01-03      0    8.4MB  fork
  3  old-portfolio                            private  2021-07-21      1    3.0MB  archived

Jumlah: 3 repo
```

*(Columns: No, Repo name, Visibility, Last push, Stars, Size, Notes. "Jumlah" = total.)*

---

## 💾 Backup & recovery

- With `--backup`, each repo is cloned as a full mirror (all branches and tags) into `backup_repos/<name>.git` **before** it is deleted. If the backup fails, that repo is **not** deleted.
- To restore a repo from a backup, first create an empty repo on GitHub, then run:
  ```bash
  cd backup_repos/repo-name.git
  git push --mirror https://github.com/USERNAME/repo-name.git
  ```
- GitHub also lets you restore deleted repos within **90 days** under **Settings → Repositories → Deleted repositories**. Not every repo can be restored this way (forks, for example).

> 💡 **Tip:** If you're unsure about a repo, choose **archive**. It becomes read-only but stays on GitHub, and you can unarchive it at any time.

---

## 🛠️ Troubleshooting

| Message | Fix |
|---|---|
| `Token tidak sah (401)` (invalid token) | The token is wrong or expired. Generate a new one. |
| `Tiada kebenaran padam ... delete_repo` (no delete permission) | Add the `delete_repo` scope (classic token) or *Administration: Read and write* (fine-grained token). |
| `Backup gagal` (backup failed) | Make sure `git` is installed and on your PATH. |
| Organization repos are missing | The script only lists repos **you own** (`affiliation=owner`). |

---

## 🙈 Recommended `.gitignore`

```gitignore
backup_repos/
github_cleanup_log.txt
```

---

## ⚠️ Disclaimer

Deleting a repository is **permanent**. Use `--dry-run` and `--backup` first. You are fully responsible for any repositories you delete with this script.
