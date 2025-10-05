# app/web/alerts.py

import streamlit as st
from .supabase_client import supabase
from ..stocks import get_current_price
import math

ALERTS_CSS = """
<style>
.alert-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
  box-shadow: 0 6px 18px rgba(12, 14, 20, 0.04);
  margin-bottom: 10px;
  border: 1px solid rgba(255,255,255,0.03);
  font-family: "Inter", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
}
.alert-left {
  flex: 1;
  min-width: 180px;
}
.alert-ticker {
  font-weight: 700;
  font-size: 16px;
  margin-bottom: 4px;
}
.alert-sub {
  font-size: 13px;
  color: #9aa3b2;
  margin-bottom: 6px;
}
.alert-center {
  width: 80px;
  display:flex;
  align-items:center;
  justify-content:center;
}
.range-rail {
  width: 12px;
  height: 84px;
  background: linear-gradient(180deg, rgba(0,0,0,0.06), rgba(0,0,0,0.02));
  border-radius: 10px;
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(0,0,0,0.06);
}
.range-fill {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: 10px;
  transition: height 0.35s ease, background 0.35s ease;
}
.range-labels {
  font-size: 12px;
  margin-left: 10px;
  display:flex;
  flex-direction:column;
  justify-content:space-between;
  height:84px;
}
.alert-right {
  width: 160px;
  display:flex;
  align-items:center;
  justify-content:flex-end;
  gap:8px;
}
.badge {
  display:inline-flex;
  align-items:center;
  gap:8px;
  font-weight:600;
  padding:6px 10px;
  border-radius:999px;
  font-size:13px;
}
.badge.up { background: rgba(16,185,129,0.12); color: #059669; border:1px solid rgba(16,185,129,0.12); }
.badge.down { background: rgba(220,53,69,0.09); color: #b91c1c; border:1px solid rgba(220,53,69,0.06); }
.badge.neutral { background: rgba(99,102,241,0.06); color: #4f46e5; border:1px solid rgba(99,102,241,0.04); }
.ticker-small { color:#94a3b8; font-size:12px; margin-left:6px; }
.small-btn { padding:6px 8px; border-radius:8px; font-size:13px; }
</style>
"""


def get_alerts(user_id: str):
    """Pobiera wszystkie alerty dla danego użytkownika."""
    try:
        res = supabase.table("alerts").select("*").eq("user_id", user_id).order("ticker").execute()
        return res.data or []
    except Exception as e:
        st.error(f"Błąd podczas ładowania alertów: {e}")
        return []


def add_alert(user_id, ticker, high, low):
    """Dodaje nowy alert cenowy."""
    try:
        supabase.table("alerts").insert({
            "user_id": user_id,
            "ticker": ticker.upper(),
            "threshold_high": high if high > 0 else None,
            "threshold_low": low if low > 0 else None
        }).execute()
        st.success(f"🔔 Ustawiono alert dla {ticker}!")
    except Exception as e:
        st.error(f"Błąd podczas dodawania alertu: {e}")


def remove_alert(alert_id: int):
    """Usuwa alert na podstawie jego ID."""
    try:
        supabase.table("alerts").delete().eq("id", alert_id).execute()
        st.toast("🗑️ Usunięto alert.")
    except Exception as e:
        st.error(f"Błąd podczas usuwania alertu: {e}")


def check_price(ticker: str):
    """Pobiera aktualne ceny dla podanego ticker'a."""
    try:
        price = get_current_price(ticker)
        return price
    except Exception as e:
        st.error(f"Błąd podczas pobierania ceny: {ticker} {e} alerts.py")
        return None


def render_styled_alert_card(alert):
    """
    Zwraca HTML dla karty alertu (używane w pętli).
    """
    ticker = alert.get('ticker', '---')
    low = alert.get('threshold_low')
    high = alert.get('threshold_high')
    current = None
    try:
        current = check_price(ticker)
    except Exception:
        current = None

    status = "neutral"
    arrow = "●"
    fill_pct = 50
    fill_color = "linear-gradient(180deg, rgba(99,102,241,0.9), rgba(79,70,229,0.8))"
    status = "neutral"
    arrow = "●"

    if current is not None:
        if low is not None and high is not None:
            if high > low:
                raw = (current - low) / (high - low)
                fill_pct = max(0, min(1, raw)) * 100
                if current >= high:
                    status = "up";
                    arrow = "▲"
                elif current <= low:
                    status = "down";
                    arrow = "▼"
                else:
                    status = "neutral";
                    arrow = "●"
        elif high is not None:  # tylko próg górny
            fill_pct = min(current / high, 1) * 100
            if current >= high:
                status = "up";
                arrow = "▲"
            else:
                status = "neutral";
                arrow = "●"
        elif low is not None:
            max_val = max(current, low * 2)
            fill_pct = (current / max_val) * 100
            if current <= low:
                status = "down";
                arrow = "▼"
            else:
                status = "neutral";
                arrow = "●"

    fill_pct = 0
    fill_color = "linear-gradient(180deg, rgba(34,197,94,0.95), rgba(6,95,70,0.9))"  # domyślnie zielony
    if low is not None and high is not None and isinstance(low, (int,float)) and isinstance(high, (int,float)) and high > low:
        if current is not None:
            try:
                raw = (current - low) / (high - low)
                fill_pct = max(0, min(1, raw)) * 100
            except Exception:
                fill_pct = 0
        else:
            fill_pct = 50

        if status == "up":
            fill_color = "linear-gradient(180deg, rgba(16,185,129,0.95), rgba(6,95,70,0.9))"
        elif status == "down":
            fill_color = "linear-gradient(180deg, rgba(220,53,69,0.95), rgba(127,29,29,0.9))"
        else:
            fill_color = "linear-gradient(180deg, rgba(99,102,241,0.9), rgba(79,70,229,0.8))"
    else:
        # jeśli nie ma obu progów -> użyj neutralnego wyglądu i małego filla
        fill_pct = 70 if status == "up" else (30 if status == "down" else 50)
        if status == "up":
            fill_color = "linear-gradient(180deg, rgba(16,185,129,0.95), rgba(6,95,70,0.9))"
        elif status == "down":
            fill_color = "linear-gradient(180deg, rgba(220,53,69,0.95), rgba(127,29,29,0.9))"
        else:
            fill_color = "linear-gradient(180deg, rgba(99,102,241,0.9), rgba(79,70,229,0.8))"

    low_label = f"${low:.2f}" if isinstance(low, (int,float)) else "Brak"
    high_label = f"${high:.2f}" if isinstance(high, (int,float)) else "Brak"
    current_label = f"${current:.2f}" if isinstance(current, (int,float)) else "---"

    # HTML karty
    html = f"""
    <div class="alert-card">
      <div class="alert-left">
        <div style="display:flex; align-items:center; gap:8px;">
          <div class="alert-ticker">{ticker}</div>
          <div class="ticker-small">{current_label}</div>
        </div>
        <div class="alert-sub">Poniżej: <strong style="color:#dc3545;">{low_label}</strong>  —  Powyżej: <strong style="color:#059669;">{high_label}</strong></div>
      </div>

      <div class="alert-center">
        <div style="display:flex; align-items:center;">
          <div class="range-rail" aria-hidden="true">
            <div class="range-fill" style="height:{fill_pct}%; background:{fill_color};"></div>
          </div>
          <div class="range-labels">
            <div style="text-align:left;">{high_label}</div>
            <div style="text-align:left;">{low_label}</div>
          </div>
        </div>
      </div>

      <div class="alert-right">
        <div class="badge {status}">{arrow} {status.capitalize()}</div>
      </div>
    </div>
    """
    return html