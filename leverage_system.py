import sys
import yfinance as yf
import pandas as pd


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def get_sigma_events(ticker: str = "TQQQ", period: str = "1y"):
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
    returns = close.pct_change().dropna()

    mean_return = returns.mean()
    std_return = returns.std()

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

    df["z_score"] = (df["return"] - mean_return) / std_return
    df["below_ma120"] = df["close"] < df["ma120"]
    df["rsi30_or_less"] = df["rsi14"] <= 30

    latest_date = close.index[-1]
    latest_close = float(close.iloc[-1])

    return {
        "ticker": ticker,
        "data_start": data.index.min(),
        "data_end": data.index.max(),
        "data_count": len(data),
        "mean_return": float(mean_return),
        "std_return": float(std_return),
        "minus_2sigma": float(minus_2sigma),
        "minus_3sigma": float(minus_3sigma),
        "latest_date": latest_date,
        "latest_close": latest_close,
        "events": df
    }


def print_buy_target(ticker: str = "TQQQ", period: str = "1y"):
    result = get_sigma_events(ticker, period=period)
    df = result["events"]

    both_df = df[
        (df["below_ma120"]) &
        (df["return"] <= result["minus_2sigma"]) &
        (df["rsi14"] <= 30)
    ].copy()

    buy_df = df[
        (df["below_ma120"]) &
        (df["return"] <= result["minus_2sigma"]) &
        (df["rsi14"] > 30)
    ].copy()

    rsi_df = df[
        (df["rsi14"] <= 30) &
        ~(
            (df["below_ma120"]) &
            (df["return"] <= result["minus_2sigma"])
        )
    ].copy()

    print(f"[{ticker}] event")
    print(f"데이터 시작일 : {result['data_start'].date()}")
    print(f"데이터 종료일 : {result['data_end'].date()}")
    print(f"데이터 개수   : {result['data_count']}")
    print(f"종가          : ${result['latest_close']:.2f}")
    print(f"평균 수익률   : {result['mean_return'] * 100:.2f}%")
    print(f"표준편차      : {result['std_return'] * 100:.2f}%")
    print(f"-2σ 기준선    : {result['minus_2sigma'] * 100:.2f}%")
    print(f"-3σ 기준선    : {result['minus_3sigma'] * 100:.2f}%")
    print()

    print("[120일선 아래 & -2σ 이하]")
    if buy_df.empty:
        print("없음")
    else:
        for date, row in buy_df.iterrows():
            print(
                f"{date.date()} | "
                f"종가: ${row['close']:>6.2f} | "
                f"등락률: {row['return'] * 100:+7.2f}% | "
                f"z-score: {row['z_score']:+6.2f} | "
                f"120일선: ${row['ma120']:>6.2f} | "
                f"RSI: {row['rsi14']:>5.2f}"
            )

    print()
    print("[RSI 30 이하]")
    if rsi_df.empty:
        print("없음")
    else:
        for date, row in rsi_df.iterrows():
            print(
                f"{date.date()} | "
                f"종가: ${row['close']:>6.2f} | "
                f"등락률: {row['return'] * 100:+7.2f}% | "
                f"z-score: {row['z_score']:+6.2f} | "
                f"120일선: ${row['ma120']:>6.2f} | "
                f"RSI: {row['rsi14']:>5.2f}"
            )

    print()
    print("[120일선 아래 & -2σ 이하 & RSI 30 이하]")
    if both_df.empty:
        print("없음")
    else:
        for date, row in both_df.iterrows():
            print(
                f"{date.date()} | "
                f"종가: ${row['close']:>6.2f} | "
                f"등락률: {row['return'] * 100:+7.2f}% | "
                f"z-score: {row['z_score']:+6.2f} | "
                f"120일선: ${row['ma120']:>6.2f} | "
                f"RSI: {row['rsi14']:>5.2f}"
            )


if __name__ == "__main__":
    ticker = "TQQQ"
    period = "1y"

    if len(sys.argv) >= 2:
        ticker = sys.argv[1].upper()

    if len(sys.argv) >= 3:
        period = f"{sys.argv[2]}y"

    print_buy_target(ticker, period)
    print()
