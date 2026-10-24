# HUSTLE

Turn your hustle into opportunity.

HUSTLE is a prototype for recording cash sales and creating a
QR-linked business passport for informal businesses.

## Run locally

python -m pip install -r requirements.txt
python app.py

## Deployment

Build command:
pip install -r requirements.txt

Start command:
gunicorn app:app

## Current limitations

Sales are seller-recorded and are not independently verified.
The current demo uses SQLite and a shared demo business profile.
