"""
dashboard.py  —  A tiny live web dashboard for your AI-Trader account.

Plain English:
    Run this and open http://localhost:8080 in your browser to see, in one
    place and always up to date:
        * your account balance (equity, cash, buying power, today's P&L),
        * what you're holding right now (open positions + live profit/loss),
        * your full buy/sell history (every order, newest first).

    It's a small web server that runs on YOUR computer. When the page asks for
    data, the server fetches it fresh from Alpaca and hands it back. Your secret
    API keys stay on your machine and are NEVER sent to the browser — which is
    exactly why we use a little server instead of a plain HTML file.

    Uses only Python's standard library plus the Alpaca SDK you already have, so
    there's nothing new to install.

To run:
    python dashboard.py            (serves on http://localhost:8080)
    python dashboard.py 9000       (use a different port)
Stop it with Ctrl+C. It is READ-ONLY: it never places or cancels an order.
"""

from __future__ import annotations

import base64
import hmac
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import QueryOrderStatus
from alpaca.trading.requests import GetOrdersRequest

from config import load_config

cfg = load_config()
# One read-only trading client, reused for every request. paper vs live follows
# the same ALPACA_PAPER switch the bot uses, so the dashboard always shows the
# SAME account the bot is trading.
client = TradingClient(cfg.api_key, cfg.secret_key, paper=cfg.paper)

# Optional password protection. If DASHBOARD_PASSWORD is set in .env, every
# request must supply this username/password (HTTP Basic Auth). Leave the
# password blank for an open dashboard on localhost only. ALWAYS set a password
# before exposing the dashboard to the internet (e.g. via Tailscale Funnel).
DASH_USER = os.getenv("DASHBOARD_USER", "admin")
DASH_PASS = os.getenv("DASHBOARD_PASSWORD", "")


def _iso(dt) -> str | None:
    """Datetime -> ISO string (the browser turns it into your local time)."""
    return dt.isoformat() if dt is not None else None


def gather_data() -> dict:
    """Pull a fresh snapshot of the account, positions, and orders from Alpaca."""
    acct = client.get_account()
    equity = float(acct.equity)
    last_equity = float(acct.last_equity)
    today_pl = equity - last_equity
    today_pl_pct = (today_pl / last_equity * 100.0) if last_equity else 0.0

    account = {
        "paper": cfg.paper,
        "equity": equity,
        "cash": float(acct.cash),
        "buying_power": float(acct.buying_power),
        "portfolio_value": float(acct.portfolio_value),
        "today_pl": today_pl,
        "today_pl_pct": today_pl_pct,
    }

    positions = []
    for p in client.get_all_positions():
        positions.append({
            "symbol": p.symbol,
            "qty": float(p.qty),
            "avg_entry": float(p.avg_entry_price),
            "current_price": float(p.current_price),
            "market_value": abs(float(p.market_value)),
            "unrealized_pl": float(p.unrealized_pl),
            "unrealized_plpc": float(p.unrealized_plpc) * 100.0,
        })
    positions.sort(key=lambda x: x["market_value"], reverse=True)

    orders_raw = client.get_orders(
        filter=GetOrdersRequest(status=QueryOrderStatus.ALL, limit=200)
    )
    orders = []
    for o in orders_raw:
        filled_qty = float(o.filled_qty) if o.filled_qty is not None else 0.0
        qty = float(o.qty) if o.qty is not None else None
        orders.append({
            "symbol": o.symbol,
            "side": o.side.value,                       # "buy" / "sell"
            "qty": filled_qty or qty,
            "status": o.status.value,                   # "filled", "canceled", ...
            "fill_price": float(o.filled_avg_price) if o.filled_avg_price else None,
            "submitted_at": _iso(o.submitted_at),
            "filled_at": _iso(o.filled_at),
        })
    # Newest first: prefer fill time, fall back to submit time.
    orders.sort(key=lambda x: x["filled_at"] or x["submitted_at"] or "", reverse=True)

    return {"ok": True, "account": account, "positions": positions, "orders": orders}


PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI-Trader Dashboard</title>
<style>
  :root { --bg:#0f1419; --card:#1a2029; --line:#2a3340; --txt:#e6edf3;
          --muted:#8b98a5; --green:#2ea043; --red:#f85149; --accent:#388bfd; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--txt);
         font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }
  header { display:flex; align-items:center; gap:12px; flex-wrap:wrap;
           padding:18px 24px; border-bottom:1px solid var(--line); }
  h1 { font-size:18px; margin:0; font-weight:650; }
  .badge { font-size:11px; font-weight:700; padding:3px 8px; border-radius:99px; }
  .badge.paper { background:#1f6feb33; color:#79c0ff; border:1px solid #1f6feb66; }
  .badge.live  { background:#f8514933; color:#ff7b72; border:1px solid #f8514966; }
  .spacer { flex:1; }
  #updated { color:var(--muted); font-size:13px; }
  button { background:var(--accent); color:#fff; border:0; border-radius:7px;
           padding:8px 14px; font-size:14px; font-weight:600; cursor:pointer; }
  button:active { transform:translateY(1px); }
  main { padding:24px; max-width:1100px; margin:0 auto; }
  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
           gap:14px; margin-bottom:26px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px;
          padding:16px 18px; }
  .card .label { color:var(--muted); font-size:12px; text-transform:uppercase;
                 letter-spacing:.04em; }
  .card .value { font-size:24px; font-weight:700; margin-top:6px; }
  h2 { font-size:15px; color:var(--muted); margin:26px 0 10px;
       text-transform:uppercase; letter-spacing:.05em; }
  table { width:100%; border-collapse:collapse; background:var(--card);
          border:1px solid var(--line); border-radius:12px; overflow:hidden; }
  th,td { text-align:left; padding:10px 14px; font-size:14px;
          border-bottom:1px solid var(--line); white-space:nowrap; }
  th { color:var(--muted); font-weight:600; font-size:12px; text-transform:uppercase; }
  tr:last-child td { border-bottom:0; }
  td.num,th.num { text-align:right; font-variant-numeric:tabular-nums; }
  .pill { font-size:12px; font-weight:700; padding:2px 8px; border-radius:6px; }
  .buy  { background:#2ea04322; color:#3fb950; }
  .sell { background:#f8514922; color:#ff7b72; }
  .pos { color:var(--green); }
  .neg { color:var(--red); }
  .muted { color:var(--muted); }
  .empty { padding:18px 14px; color:var(--muted); font-size:14px; }
  #error { display:none; background:#f8514922; border:1px solid #f8514966;
           color:#ff7b72; padding:12px 16px; border-radius:10px; margin-bottom:18px; }
</style>
</head>
<body>
<header>
  <h1>AI-Trader Dashboard</h1>
  <span id="modeBadge" class="badge paper">PAPER</span>
  <div class="spacer"></div>
  <span id="updated">Loading…</span>
  <button onclick="load()">Refresh</button>
</header>
<main>
  <div id="error"></div>
  <div class="cards" id="cards"></div>

  <h2>Open Positions</h2>
  <div id="positions"></div>

  <h2>Buy / Sell History</h2>
  <div id="orders"></div>
</main>
<script>
const money = n => (n<0?"-$":"$") + Math.abs(n).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
const cls = n => n>=0 ? "pos" : "neg";
const when = iso => iso ? new Date(iso).toLocaleString() : "—";

function card(label, value, extra="") {
  return `<div class="card"><div class="label">${label}</div><div class="value">${value}${extra}</div></div>`;
}

function render(d) {
  // mode badge
  const badge = document.getElementById("modeBadge");
  badge.textContent = d.account.paper ? "PAPER" : "LIVE";
  badge.className = "badge " + (d.account.paper ? "paper" : "live");

  // balance cards
  const a = d.account;
  const plClass = cls(a.today_pl);
  document.getElementById("cards").innerHTML =
      card("Equity", money(a.equity))
    + card("Today's P/L", `<span class="${plClass}">${(a.today_pl>=0?"+":"")+money(a.today_pl)}</span>`,
           ` <span class="${plClass}" style="font-size:14px">(${a.today_pl_pct>=0?"+":""}${a.today_pl_pct.toFixed(2)}%)</span>`)
    + card("Cash", money(a.cash))
    + card("Buying Power", money(a.buying_power));

  // positions
  const pos = d.positions;
  if (!pos.length) {
    document.getElementById("positions").innerHTML = `<div class="card"><div class="empty">No open positions right now.</div></div>`;
  } else {
    let rows = pos.map(p => `<tr>
        <td><b>${p.symbol}</b></td>
        <td class="num">${p.qty}</td>
        <td class="num">${money(p.avg_entry)}</td>
        <td class="num">${money(p.current_price)}</td>
        <td class="num">${money(p.market_value)}</td>
        <td class="num ${cls(p.unrealized_pl)}">${(p.unrealized_pl>=0?"+":"")+money(p.unrealized_pl)}</td>
        <td class="num ${cls(p.unrealized_plpc)}">${(p.unrealized_plpc>=0?"+":"")}${p.unrealized_plpc.toFixed(2)}%</td>
      </tr>`).join("");
    document.getElementById("positions").innerHTML =
      `<table><thead><tr><th>Symbol</th><th class="num">Qty</th><th class="num">Avg Entry</th>
       <th class="num">Price</th><th class="num">Value</th><th class="num">Unrealized P/L</th>
       <th class="num">%</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  // orders
  const ords = d.orders;
  if (!ords.length) {
    document.getElementById("orders").innerHTML = `<div class="card"><div class="empty">No orders yet.</div></div>`;
  } else {
    let rows = ords.map(o => `<tr>
        <td><span class="pill ${o.side}">${o.side.toUpperCase()}</span></td>
        <td><b>${o.symbol}</b></td>
        <td class="num">${o.qty ?? "—"}</td>
        <td class="num">${o.fill_price!=null ? money(o.fill_price) : "—"}</td>
        <td class="${o.status==='filled'?'':'muted'}">${o.status}</td>
        <td class="muted">${when(o.filled_at || o.submitted_at)}</td>
      </tr>`).join("");
    document.getElementById("orders").innerHTML =
      `<table><thead><tr><th>Side</th><th>Symbol</th><th class="num">Qty</th>
       <th class="num">Fill Price</th><th>Status</th><th>Time</th></tr></thead>
       <tbody>${rows}</tbody></table>`;
  }

  document.getElementById("error").style.display = "none";
  document.getElementById("updated").textContent = "Updated " + new Date().toLocaleTimeString();
}

async function load() {
  try {
    const r = await fetch("/api/data", {cache:"no-store"});
    const d = await r.json();
    if (!d.ok) throw new Error(d.error || "Unknown error");
    render(d);
  } catch (e) {
    const box = document.getElementById("error");
    box.textContent = "Could not load data: " + e.message + "  (Is the bot's .env set up and Alpaca reachable?)";
    box.style.display = "block";
    document.getElementById("updated").textContent = "Update failed " + new Date().toLocaleTimeString();
  }
}

load();
setInterval(load, 15000);   // auto-refresh every 15 seconds
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, content_type: str):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        """True if no password is required, or the right one was supplied."""
        if not DASH_PASS:
            return True  # no password configured -> open (localhost use)
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return False
        try:
            user, _, pw = base64.b64decode(header[6:]).decode("utf-8").partition(":")
        except Exception:  # noqa: BLE001 - malformed header = not authorized
            return False
        # Constant-time compares so the password can't be guessed by timing.
        return (hmac.compare_digest(user, DASH_USER)
                and hmac.compare_digest(pw, DASH_PASS))

    def _ask_for_password(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="AI-Trader Dashboard"')
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):  # noqa: N802 (name fixed by BaseHTTPRequestHandler)
        if not self._authorized():
            self._ask_for_password()
            return
        if self.path.startswith("/api/data"):
            try:
                payload = gather_data()
            except Exception as exc:  # noqa: BLE001 - report errors to the page
                payload = {"ok": False, "error": str(exc)}
            self._send(200, json.dumps(payload).encode("utf-8"), "application/json")
        elif self.path in ("/", "/index.html"):
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        else:
            self._send(404, b"Not found", "text/plain")

    def log_message(self, *args):  # keep the console quiet
        pass


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    mode = "PAPER (fake money)" if cfg.paper else "LIVE (REAL money)"
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"AI-Trader dashboard [{mode}] running.")
    print(f"  Open your browser to:  http://localhost:{port}")
    if DASH_PASS:
        print(f"  Password protection: ON (user '{DASH_USER}').")
    else:
        print("  Password protection: OFF. Fine on localhost, but set "
              "DASHBOARD_PASSWORD in .env BEFORE exposing this to the internet.")
    print("  It refreshes every 15s; press the Refresh button any time. Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped. Goodbye.")
        server.server_close()


if __name__ == "__main__":
    main()
