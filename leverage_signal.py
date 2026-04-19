import sys
from dataclasses import dataclass
from typing import Dict, List

import pandas as pd
import yfinance as yf


@dataclass
class SignalResult:
    ticker: str
    latest_date: str
    close: float
    daily_return_pct: float
    ma120: float
    rsi14: float
    minus_2sigma_pct: float
    minus_3sigma_pct: float
    below_ma120: bool
    below_minus_2sigma: bool
    rsi30_or_less: bool
    rsi70_or_more: bool
    signal_type: str
    action_text: str


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def get_signal_data(ticker: str = "TQQQ", period: str = "1y") -> SignalResult:
    data = yf.download(
        ticker,
        period=period,
        interval="1d",
        auto_adjust=False,
        progress=False
    )

    if data.empty or len(data) < 120:
        raise ValueError(f"{ticker} 데이터가 부족합니다.")

    close = data["Close"].squeeze()
    returns = close.pct_change()

    mean_return = returns.dropna().mean()
    std_return = returns.dropna().std()

    minus_2sigma = mean_return - 2 * std_return
    minus_3sigma = mean_return - 3 * std_return

    ma120 = close.rolling(window=120).mean()
    rsi14 = calculate_rsi(close, period=14)

    df = pd.DataFrame({
        "close": close,
        "return": returns,
        "ma120": ma120,
        "rsi14": rsi14
    }).dropna()

    if df.empty:
        raise ValueError(f"{ticker} 계산 가능한 데이터가 부족합니다.")

    latest = df.iloc[-1]
    latest_date = df.index[-1].date().isoformat()

    below_ma120 = bool(latest["close"] < latest["ma120"])
    below_minus_2sigma = bool(latest["return"] <= minus_2sigma)
    rsi30_or_less = bool(latest["rsi14"] <= 30)
    rsi70_or_more = bool(latest["rsi14"] >= 70)

    signal_type = "NONE"
    action_text = "대기"

    if below_ma120 and below_minus_2sigma and rsi30_or_less:
        signal_type = "BOTH"
        action_text = "15주 매수"
    elif below_ma120 and below_minus_2sigma:
        signal_type = "SIGMA"
        action_text = "5주 매수"
    elif rsi30_or_less:
        signal_type = "RSI"
        action_text = "5주 매수"
    elif ticker.upper() == "TQQQ" and rsi70_or_more:
        signal_type = "RSI70"
        action_text = "단계별 비중조절"
    else:
        signal_type = "NONE"
        action_text = "대기"

    return SignalResult(
        ticker=ticker.upper(),
        latest_date=latest_date,
        close=float(latest["close"]),
        daily_return_pct=float(latest["return"] * 100),
        ma120=float(latest["ma120"]),
        rsi14=float(latest["rsi14"]),
        minus_2sigma_pct=float(minus_2sigma * 100),
        minus_3sigma_pct=float(minus_3sigma * 100),
        below_ma120=below_ma120,
        below_minus_2sigma=below_minus_2sigma,
        rsi30_or_less=rsi30_or_less,
        rsi70_or_more=rsi70_or_more,
        signal_type=signal_type,
        action_text=action_text
    )


def analyze_portfolio(period: str = "1y") -> List[SignalResult]:
    tickers = ["TQQQ", "QLD"]
    results = []

    for ticker in tickers:
        results.append(get_signal_data(ticker, period=period))

    return results


def print_signal(result: SignalResult):
    print(f"[{result.ticker}]")
    print(f"날짜: {result.latest_date}")
    print(f"현재가(등락률): ${result.close:.2f} ({result.daily_return_pct:+.2f}%)")
    print(f"120일선(-2σ): ${result.ma120:.2f} ({result.minus_2sigma_pct:+.2f}%)")
    print(f"RSI: {result.rsi14:.1f}")
    print("-" * 36)

    if result.signal_type == "BOTH":
        print(">>> 120일선, -2σ, RSI 조건 충족")
        print(f">>> {result.action_text}")
    elif result.signal_type == "SIGMA":
        print(">>> 120일선, -2σ 조건 충족")
        print(f">>> {result.action_text}")
    elif result.signal_type == "RSI":
        print(">>> RSI 조건 충족")
        print(f">>> {result.action_text}")
    elif result.signal_type == "RSI70":
        print(">>> RSI 70 이상")
        print(f">>> {result.action_text}")
    else:
        print(">>> 조건 미충족")
        print(">>> 대기")
    print()


if __name__ == "__main__":
    period = "1y"

    if len(sys.argv) >= 2:
        raw_period = sys.argv[1].lower()
        if raw_period.endswith("y"):
            period = raw_period
        else:
            period = f"{raw_period}y"

    results = analyze_portfolio(period=period)
    for item in results:
        print_signal(item)
