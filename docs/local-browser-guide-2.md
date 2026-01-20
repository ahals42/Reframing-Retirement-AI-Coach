# Local Browser Guide 2

Run the API and frontend locally using two terminals.

## Terminal 1: API
1) Install requirements
2) Activate the virtual environment
3) Start the FastAPI server

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./scripts/quickstart.sh api
```

## Terminal 2: Frontend (Caddy proxy)
```bash
cat <<'EOF' > /tmp/reframing-retirement.Caddyfile
:4173 {
  handle_path /api/* {
    reverse_proxy localhost:8000
  }
  root * /Users/aidanhalley/Documents/Reframing-Retirement/frontend
  file_server
}
EOF

~/bin/caddy run --config /tmp/reframing-retirement.Caddyfile
```

Then open `http://localhost:4173` in your browser.
