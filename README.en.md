# QRush: Temporary File Hosting

<img width="1034" height="583" alt="Qrush_demo" src="https://github.com/user-attachments/assets/37a75462-7bf5-4ecf-83c8-c7c62b4c105d" />

[Описание на русском языке](README.md)

**QRush** is a simple temporary file storage service. Upload one or multiple files (up to 1 GB), choose how long to keep them — and get a download link and QR code. Files are automatically deleted after the storage period expires.

---

## Features

- Upload one or multiple files (total size up to **1 GB** — configurable via `config.py`)
- Automatic archiving of multiple files into `.zip`
- Storage duration from **1 to 24 hours**
- Download link and QR code generation
- Fast and simple upload — no registration required
- Files are stored in the `uploads/` directory and automatically removed by a timer

---

## Tech Stack

### Backend:
- [FastAPI](https://fastapi.tiangolo.com/) — Web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) — ORM for SQLite
- [SQLite](https://www.sqlite.org/) — Database
- [QRCode](https://pypi.org/project/qrcode/) — QR code generation
- [Pillow](https://pillow.readthedocs.io/) — QR code image styling

### Frontend:
- HTML5 + CSS3 + Vanilla JS

---

## Installation & Setup

1. Clone the repository
```
git clone https://github.com/Twydir1762/QRush.git
cd QRush
```

2. Install dependencies
```
pip install -r requirements.txt
```

3. Run the application (via uvicorn)
```
uvicorn app.main:app
```

---

## Testing

Run automated tests with coverage report:
```bash
python -m pytest --cov
```

---

## Notes

This project was built for home deployment on a simple server using a Raspberry Pi, as a hands-on exercise to gain experience with technologies such as:

- **FastAPI**
- **SQLite** and **SQLAlchemy (ORM)**
- **REST API design principles**
- Client-server architecture

The use of a database and ORM in such a straightforward project is intentional — the goal was to practice designing and implementing a backend from scratch.
