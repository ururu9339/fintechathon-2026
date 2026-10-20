Then rebuild the Docker image:
    docker compose build --no-cache
    docker compose up

Change the requirements.txt when adding new modules

Approved requests:
curl -i -X POST http://localhost:8000/api/payments \
  -H "Content-Type: application/json" \
  -d '{
    "supplier": "Acme Supplies",
    "amount": 100,
    "purpose": "supplier invoice",
    "invoice_id": "invoice-001",
    "mandate_id": "mandate-demo"
  }'

to run the API:
./.venv/bin/python -m uvicorn backend.app.main:app --reload

The Quick One-Liner (Kill whatever is on port 8000)

    kill -9 $(lsof -t -i :8000)

*DB
simple table from payment_request:
sqlite3 -header -column backend/data/amanahpay.db \
  'SELECT * FROM payment_requests;'

to run webpage:
    cd frontend
    npm run web

Start the database in the background:
Open your terminal and run:
docker compose up db -d
(The -d means "detached". The database will run silently in the background, keeping your terminal free.)

Run your app on your Mac:
Run your usual command:
./.venv/bin/python -m uvicorn backend.app.main:app --reload

Code normally!
Every time you save a file, uvicorn will instantly reload your app. Your app will talk to localhost:5432, which Docker automatically routes directly into your Postgres