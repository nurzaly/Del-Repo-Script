# 🧹 GitHub Cleanup

Skrip Python untuk membersihkan repo GitHub lama yang tidak digunakan lagi. Anda boleh **padam** atau **archive** repo secara pukal, tetapi setiap tindakan perlu **pengesahan anda dahulu**.

Ia hanya guna library standard Python, jadi tiada `pip install` diperlukan.

---

## ✨ Ciri-ciri

- 📋 Senarai semua repo milik anda (public & private), repo paling lama di atas
- 🔍 Tapis ikut tempoh tiada aktiviti, fork sahaja, atau sembunyikan repo yang sudah di-archive
- ✅ **3 lapis pengesahan** sebelum apa-apa diubah
- 📦 Pilihan **archive** (read-only, boleh dibuka semula) selain padam
- 💾 Pilihan **backup** (`git clone --mirror`) sebelum repo dipadam
- 🧪 Mod **dry-run** untuk simulasi tanpa sebarang perubahan
- 📝 Log setiap tindakan ke `github_cleanup_log.txt`
- 🔁 Console kekal terbuka selepas selesai, dengan pilihan untuk ulang semula

---

## 📦 Keperluan

- Python 3.8 atau lebih baharu
- `git` (hanya jika guna `--backup`)
- GitHub Personal Access Token

### Membuat token

Pergi ke **GitHub → Settings → Developer settings → Personal access tokens**.

| Jenis token | Kebenaran diperlukan |
|---|---|
| Classic | `repo` dan `delete_repo` |
| Fine-grained | Repository access: *All repositories*<br>Permission: **Administration → Read and write** |

> ⚠️ Simpan token dengan selamat. Jangan commit token ke dalam repo.

---

## 🚀 Cara guna

### 1. Set token (pilihan)

Jika `GITHUB_TOKEN` tidak di-set, skrip akan minta token semasa dijalankan (input tersembunyi).

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

### 2. Jalankan

```bash
python github_cleanup.py
```

Atau double-click `github_cleanup.py` di Windows. Console tidak akan tertutup sendiri.

### Pilihan (flags)

| Flag | Fungsi |
|---|---|
| `--older-than N` | Hanya repo yang tiada push melebihi **N bulan** |
| `--forks-only` | Hanya repo fork |
| `--hide-archived` | Sembunyikan repo yang sudah di-archive |
| `--backup` | `git clone --mirror` ke folder `backup_repos/` sebelum padam |
| `--dry-run` | Simulasi sahaja, tiada repo diubah |
| `-h`, `--help` | Papar bantuan |

### Contoh

```bash
# Cuba dulu, tiada apa dipadam
python github_cleanup.py --dry-run --older-than 12

# Repo tiada aktiviti lebih 2 tahun, backup dulu sebelum padam
python github_cleanup.py --older-than 24 --backup

# Bersihkan repo fork sahaja
python github_cleanup.py --forks-only --hide-archived
```

---

## 🔐 Aliran pengesahan

```
Senarai repo
   │
   ▼
[1] Pilih nombor repo      →  1,3,5-9  |  semua  |  (kosong = batal)
   │
   ▼
[2] Sahkan setiap repo     →  p = padam   a = archive   l = langkau   q = berhenti
   │
   ▼
[3] Ringkasan + taip "SAH <jumlah>"   (cth: SAH 7)
   │
   ▼
Laksana → log → "Ulang lagi? [y/N]"
```

Jika teks pengesahan di langkah 3 tidak sepadan, **semua dibatalkan** dan tiada apa-apa diubah.

### Contoh paparan

```
 No  Nama repo                                Jenis    Push terakhir   ★     Saiz  Nota
-----------------------------------------------------------------------------------------------
  1  test-laravel-2019                        public   2019-04-12      0    1.2MB
  2  bootstrap-fork                           public   2020-01-03      0    8.4MB  fork
  3  old-portfolio                            private  2021-07-21      1    3.0MB  archived

Jumlah: 3 repo
```

---

## 💾 Backup & pemulihan

- Dengan `--backup`, setiap repo di-clone sebagai mirror penuh (semua branch & tag) ke `backup_repos/<nama>.git` **sebelum** dipadam. Jika backup gagal, repo itu **tidak** dipadam.
- Untuk pulihkan dari backup:
  ```bash
  cd backup_repos/nama-repo.git
  git push --mirror https://github.com/USERNAME/nama-repo.git
  ```
  (Cipta repo kosong di GitHub dahulu.)
- GitHub juga membenarkan pemulihan repo yang dipadam dalam tempoh **90 hari** melalui **Settings → Repositories → Deleted repositories**, tetapi tidak semua repo layak dipulihkan (contohnya repo fork).

> 💡 **Tip:** Jika tidak pasti, pilih **archive**. Repo jadi read-only tetapi masih ada dan boleh di-unarchive bila-bila masa.

---

## 🛠️ Masalah biasa

| Mesej | Penyelesaian |
|---|---|
| `Token tidak sah (401)` | Token salah atau sudah tamat tempoh. Jana token baharu. |
| `Tiada kebenaran padam ... delete_repo` | Tambah scope `delete_repo` (classic) atau *Administration: Read and write* (fine-grained). |
| `Backup gagal` | Pastikan `git` dipasang dan ada dalam PATH. |
| Repo organisasi tidak tersenarai | Skrip hanya menyenaraikan repo **milik anda sendiri** (`affiliation=owner`). |

---

## ⚠️ Penafian

Pemadaman repo adalah **kekal**. Gunakan `--dry-run` dan `--backup` terlebih dahulu. Pengguna bertanggungjawab sepenuhnya ke atas repo yang dipadam menggunakan skrip ini.
