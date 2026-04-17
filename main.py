import os
from datetime import datetime

import pandas as pd
import requests
import yfinance as yf
import pandas_market_calendars as mcal


def send_telegram(message: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID가 설정되지 않았습니다.")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    response = requests.post(url, data=payload, timeout=15)
    response.raise_for_status()


def is_us_market_open_today() -> bool:
    """
    오늘(미국 동부시간 기준)이 NYSE 개장일인지 확인
    휴장일이면 False
    """
    nyse = mcal.get_calendar("NYSE")
    now_et = pd.Timestamp.now(tz="America/New_York")
    today_et = now_et.date()

    schedule = nyse.schedule(start_date=today_et, end_date=today_et)
    return not schedule.empty


def calculate_rsi(close_series: pd.Series, period: int = 14) -> pd.Series:
    """
    Wilder RSI 계산
    """
    delta = close_series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def get_price_and_change(ticker: str):
    data = yf.download(
        ticker,
        period="5d",
        interval="1d",
        auto_adjust=False,
        progress=False
    )

    if data.empty or len(data) < 2:
        raise ValueError(f"{ticker} 가격 데이터를 충분히 가져오지 못했습니다.")

    close_col = "Close"
    current_price = float(data[close_col].iloc[-1])
    prev_close = float(data[close_col].iloc[-2])
    change_pct = ((current_price - prev_close) / prev_close) * 100

    return current_price, change_pct


def get_qqq_rsi(period: int = 14):
    data = yf.download(
        "QQQ",
        period="3mo",
        interval="1d",
        auto_adjust=False,
        progress=False
    )

    if data.empty or len(data) < period + 1:
        raise ValueError("QQQ RSI 계산에 필요한 데이터가 부족합니다.")

    close_series = data["Close"]
    rsi_series = calculate_rsi(close_series, period=period)
    rsi_value = float(rsi_series.iloc[-1])

    return rsi_value


def build_message(rsi_value: float, status: str, strategy: str,
                  tqqq_price: float, tqqq_change: float,
                  qld_price: float, qld_change: float) -> str:
    return (
        f"*\\[QQQ RSI 알림\\]*\n\n"
        f"QQQ RSI(14): {rsi_value:.1f}\n"
        f"상태: {status}\n\n"
        f"TQQQ: ${tqqq_price:.2f} ({tqqq_change:+.1f}%)\n"
        f"QLD: ${qld_price:.2f} ({qld_change:+.1f}%)\n\n"
        f"전략 체크: {strategy}"
    )


def check_market():
    # 미국 휴장일이면 종료
    if not is_us_market_open_today():
        print("오늘은 미국 휴장일입니다. 알림을 보내지 않습니다.")
        return

    rsi_value = get_qqq_rsi(period=14)

    tqqq_price, tqqq_change = get_price_and_change("TQQQ")
    qld_price, qld_change = get_price_and_change("QLD")

    if rsi_value <= 30:
        status = "과매도"
        strategy = "TQQQ 1주 + QLD 1주 추가매수 고려 구간"
    elif rsi_value >= 70:
        status = "과매수"
        strategy = "반등장 비중조절 검토 구간"
    else:
        print(f"조건 미충족: RSI={rsi_value:.1f}")
        return

    message = build_message(
        rsi_value=rsi_value,
        status=status,
        strategy=strategy,
        tqqq_price=tqqq_price,
        tqqq_change=tqqq_change,
        qld_price=qld_price,
        qld_change=qld_change
    )

    send_telegram(message)
    print("텔레그램 알림 전송 완료")


if __name__ == "__main__":
    check_market()
