import os
import requests
import time
import asyncio
import traceback
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

print("=== START: bot.py (begin) ===")

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

def analizar_token(contrato):
    try:
        url = f"https://api.dexscreener.com/tokens/v1/solana/{contrato}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        pairs = data if isinstance(data, list) else data.get("pairs", [])
        if not pairs:
            return None
        pairs.sort(key=lambda x: float((x.get("liquidity") or {}).get("usd", 0)), reverse=True)
        p = pairs[0]
        nombre = (p.get("baseToken") or {}).get("name", "N/A")
        precio = float(p.get("priceUsd") or 0)
        liq = float((p.get("liquidity") or {}).get("usd", 0))
        vol = float((p.get("volume") or {}).get("h24", 0))
        cambio = float((p.get("priceChange") or {}).get("h24", 0))
        txns = (p.get("txns") or {}).get("h24", {})
        total_txns = (txns.get("buys") or 0) + (txns.get("sells") or 0)
        fdv = float(p.get("fdv") or 0)
        edad = 0
        if p.get("pairCreatedAt"):
            edad = (time.time() * 1000 - p["pairCreatedAt"]) / (1000 * 60 * 60)
        score = 0
        riesgo = 0
        if liq > 100000:
            score += 25
        elif liq > 20000:
            score += 15
        else:
            riesgo += 30
        if vol > 150000:
            score += 25
        elif vol < 5000:
            riesgo += 20
        if total_txns > 800:
            score += 15
        elif total_txns < 80:
            riesgo += 20
        if cambio > 10:
            score += 15
        elif cambio < -15:
            riesgo += 10
        if edad > 24:
            score += 10
        elif edad < 6:
            riesgo += 25
        if fdv > 0 and liq > 0:
            ratio = fdv / liq
            if ratio > 40:
                riesgo += 20
            elif ratio < 8:
                score += 10
        if vol > liq * 3:
            riesgo += 20
        if liq < 8000:
            riesgo += 30
        if score >= 75 and riesgo < 30:
            senal = "🔥 JOYA"
        elif score >= 60 and riesgo < 40:
            senal = "🟢 BUENO"
        elif score >= 40:
            senal = "🟡 OBSERVAR"
        else:
            senal = "🔴 SCAM/EVITAR"
        return {
            "nombre": nombre,
            "precio": precio,
            "liq": liq,
            "vol": vol,
            "cambio": cambio,
            "txns": total_txns,
            "edad": edad,
            "score": score,
            "riesgo": riesgo,
            "senal": senal,
            "contrato": contrato,
        }
    except Exception:
        return None

def formato_reporte(t):
    return (
        f"🦅 HAWKEYE REPORT\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 Token: {t['nombre']}\n"
        f"📍 Contrato: {t['contrato']}\n\n"
        f"💰 Precio: ${t['precio']:.8f}\n"
        f"💧 Liquidez: ${t['liq']:,.0f}\n"
        f"📊 Volumen 24h: ${t['vol']:,.0f}\n"
        f"📈 Cambio 24h: {t['cambio']:.2f}%\n"
        f"🔄 Transacciones: {t['txns']}\n"
        f"⏰ Edad: {t['edad']:.1f}h\n\n"
        f"🧠 Score IA: {t['score']}/100\n"
        f"⚠️ Riesgo: {t['riesgo']}/100\n\n"
        f"{t['senal']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💬 Esperando tu opinion..."
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🦅 HAWKEYE Analytics Bot\n\nComandos:\n/analisis CONTRATO\n/scan\n/stop (solo admin)\n/ayuda"
    )

async def analisis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /analisis CONTRATO")
        return
    contrato = context.args[0].strip()
    await update.message.reply_text("🔍 Analizando...")
    resultado = analizar_token(contrato)
    if not resultado:
        await update.message.reply_text("❌ Token no encontrado")
        return
    await update.message.reply_text(formato_reporte(resultado))

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Escaneando Solana...")
    try:
        url = "https://api.dexscreener.com/latest/dex/tokens/So11111111111111111111111111111111111111112"
        r = requests.get(url, timeout=15)
        pairs = r.json().get("pairs", [])
        joyas = []
        for p in pairs[:50]:
            liq = float((p.get("liquidity") or {}).get("usd", 0))
            vol = float((p.get("volume") or {}).get("h24", 0))
            cambio = float((p.get("priceChange") or {}).get("h24", 0))
            if liq > 20000 and vol > 50000 and cambio > 5:
                joyas.append(p)
        if not joyas:
            await update.message.reply_text("😔 Sin tokens destacados ahora. Intenta en 5 min.")
            return
        msg = "🦅 TOKENS DETECTADOS\n━━━━━━━━━━━━━━━━━━\n"
        for p in joyas[:5]:
            nombre = (p.get("baseToken") or {}).get("name", "N/A")
            contrato = (p.get("baseToken") or {}).get("address", "")
            liq = float((p.get("liquidity") or {}).get("usd", 0))
            vol = float((p.get("volume") or {}).get("h24", 0))
            cambio = float((p.get("priceChange") or {}).get("h24", 0))
            msg += f"\n🔸 {nombre}\n💧 ${liq:,.0f} | 📊 ${vol:,.0f} | 📈 {cambio:.1f}%\n{contrato}\n"
        msg += "\n_Usa /analisis CONTRATO para analisis completo_"
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🦅 HAWKEYE - Comandos\n\n"
        "/start - Iniciar\n"
        "/analisis CONTRATO - Analisis completo\n"
        "/scan - Scanner de tokens\n"
        "/stop - Apagar bot (solo admin)\n"
        "/ayuda - Esta ayuda"
    )

async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else None
    if user_id != ADMIN_ID:
        await update.message.reply_text("No autorizado.")
        return
    await update.message.reply_text("Apagando...")
    await context.application.stop()
    await context.application.shutdown()

async def main():
    print("main: starting application...")
    try:
        if not TOKEN:
            print("ERROR: BOT_TOKEN no está definido en variables de entorno.")
            return
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("analisis", analisis))
        app.add_handler(CommandHandler("scan", scan))
        app.add_handler(CommandHandler("ayuda", ayuda))
        app.add_handler(CommandHandler("stop", stop_cmd))
        print("🦅 HawkEye Bot iniciado... (about to run polling)")
        await app.run_polling(allowed_updates=None, close_loop=False)
        print("main: run_polling finished")
    except Exception:
        print("main: exception occurred:")
        traceback.print_exc()
        await asyncio.sleep(5)

final start
if name == "main":
    try:
        asyncio.run(main())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.create_task(main())

requirements.txt
python-telegram-bot[job-queue]==20.3
requests==2.31.0
httpx==0.24.1

Now what?
