import os
import requests

from leverage_signal import analyze_portfolio, SignalResult


def send_telegram(message: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID가 설정되지 않았습니다.")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
    }

    response = requests.post(url, data=payload, timeout=15)
    response.raise_for_status()


def build_section(result: SignalResult) -> str:
    lines = [
        f"[{result.ticker}]",
        f"• 현재가(등락률) : ${result.close:.2f}({result.daily_return_pct:+.2f}%)",
        f"• 120일선(-2σ) : ${result.ma120:.2f}({result.minus_2sigma_pct:+.2f}%)",
        f"• RSI : {result.rsi14:.1f}",
        "--------------------------------------------------",
    ]

    if result.signal_type == "BOTH":
        lines.append(">> 120일선, -2σ, RSI 조건 충족")
        lines.append(f">> {result.action_text}")

    elif result.signal_type == "SIGMA":
        lines.append(">> 120일선, -2σ 조건 충족")
        lines.append(f">> {result.action_text}")

    elif result.signal_type == "RSI":
        lines.append(">> RSI 조건 충족")
        lines.append(f">> {result.action_text}")

    elif result.signal_type == "SELL80":
        lines.append(">> RSI 80 이상")
        lines.append(f">> {result.action_text}")

    elif result.signal_type == "SELL75":
        lines.append(">> RSI 75 이상")
        lines.append(f">> {result.action_text}")

    elif result.signal_type == "SELL70":
        lines.append(">> RSI 70 이상")
        lines.append(f">> {result.action_text}")

    else:
        if result.in_sell_zone_hold:
            lines.append(">> 기존 익절 구간 유지 중")
            lines.append(">> 추가 행동 없음")
        else:
            lines.append(">> 조건 미충족")
            lines.append(">> 대기")

    return "\n".join(lines)


def build_message(results: list[SignalResult]) -> str:
    base_date = results[0].latest_date if results else "-"
    sections = [build_section(result) for result in results]

    return (
        f"레버리지 핀트\n"
        f"{base_date}\n\n"
        + "\n\n".join(sections)
    )


def main():
    results = analyze_portfolio(period="1y")
    message = build_message(results)
    send_telegram(message)
    print("텔레그램 알림 전송 완료")


if __name__ == "__main__":
    main()
