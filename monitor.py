"""Monitora a página do Recital de Encerramento de Semestre (Osesp, 04/12/2026)
e avisa quando o botão "Ingresso em breve" mudar (reservas liberadas).

Canais de aviso (cada um só é usado se os Secrets existirem):
- WhatsApp via CallMeBot: WHATSAPP_PHONE + CALLMEBOT_APIKEY
- Telegram: TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
- GitHub issue (chega por e-mail): sempre, via GITHUB_TOKEN no workflow

Uso: python monitor.py check | heartbeat | test
Saída: escreve "released=true|false" em $GITHUB_OUTPUT.
"""
import gzip
import html
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

PAGE_URL = "https://osesp.art.br/osesp/pt/concerto/2029?date=2026-12-04T22:30:00.000Z"
GENERIC_HREF = "https://tickets.oneboxtds.com/osesp/events"
BRT = timezone(timedelta(hours=-3))


def fetch_page():
    req = urllib.request.Request(PAGE_URL, headers={"User-Agent": "Mozilla/5.0 (osesp-monitor)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    if raw[:2] == b"\x1f\x8b":  # o servidor manda gzip mesmo sem pedir
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", errors="replace")


def read_button(page):
    """Devolve (texto, href) do botão de ingresso, ou None se não achar."""
    section = re.search(r'<section class="article-details".*?</section>', page, re.S)
    if not section:
        return None
    btn = re.search(r'<a href="([^"]*)"[^>]*class="btn primary[^"]*"[^>]*>(.*?)</a>', section.group(0), re.S)
    if not btn:
        return None
    text = re.sub(r"<[^>]+>", " ", btn.group(2))
    text = " ".join(html.unescape(text).split())
    return text, html.unescape(btn.group(1))


def status():
    """Retorna (estado, detalhe). estado: em_breve | liberado | mudou | erro."""
    try:
        page = fetch_page()
    except Exception as e:  # rede fora, 5xx etc.: tenta de novo na próxima rodada
        return "erro", f"falha ao acessar a página: {e}"
    button = read_button(page)
    if button is None:
        return "mudou", "o botão de ingresso não foi encontrado (a página mudou de formato)"
    text, href = button
    if "em breve" in text.lower() and href.rstrip("/") == GENERIC_HREF:
        return "em_breve", f'botão "{text}"'
    return "liberado", f'botão "{text}" apontando para {href}'


def send_whatsapp(msg, silent=False):
    phone, key = os.getenv("WHATSAPP_PHONE"), os.getenv("CALLMEBOT_APIKEY")
    if not (phone and key):
        return
    url = "https://api.callmebot.com/whatsapp.php?" + urllib.parse.urlencode(
        {"phone": phone, "text": msg, "apikey": key})
    urllib.request.urlopen(url, timeout=30).read()
    print("WhatsApp enviado")


def send_telegram(msg, silent=False):
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat):
        return
    params = {"chat_id": chat, "text": msg}
    if silent:  # chega no chat sem tocar nem vibrar
        params["disable_notification"] = "true"
    data = urllib.parse.urlencode(params).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=30).read()
    print("Telegram enviado")


def notify(msg, silent=False):
    for sender in (send_whatsapp, send_telegram):
        try:
            sender(msg, silent)
        except Exception as e:
            print(f"{sender.__name__} falhou: {e}")


def set_output(released):
    out = os.getenv("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"released={'true' if released else 'false'}\n")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    state, detail = status()
    now = datetime.now(BRT).strftime("%d/%m %H:%M")
    print(f"[{now}] {state}: {detail}")

    if state in ("liberado", "mudou"):
        notify("🎻 OSESP: a página do Recital de 04/12 mudou! "
               f"Provavelmente as reservas abriram ({detail}). Reserve já: {PAGE_URL}")
        set_output(True)
        return
    set_output(False)

    if mode == "heartbeat":
        notify(f"✅ Monitor Osesp ativo ({now}). Status: {detail}. Sigo vigiando a cada 5 min.", silent=True)
    elif mode == "test":
        notify(f"🧪 Teste do monitor Osesp ({now}). Status atual: {detail}.")


if __name__ == "__main__":
    main()
