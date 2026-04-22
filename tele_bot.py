import html
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
        "parse_mode": "HTML"
    }

    response = requests.post(url, data=payload, timeout=15)
    response.raise_for_status()


def build_section(result: SignalResult) -> str:
    lines = [
        f"[{html.escape(result.ticker)}]",
        f"• 현재가(등락률) : ${result.close:.2f}({result.daily_return_pct:+.2f}%)",
        f"• 120일선(-2σ) : ${result.ma120:.2f}({result.minus_2sigma_pct:+.2f}%)",
        f"• RSI : {result.rsi14:.1f}",
        "--------------------------------------------------",
    ]

    if result.signal_type == "BOTH":
        lines.append("&gt;&gt; 120일선, -2σ, RSI 조건 충족")
        lines.append(f"&gt;&gt; {html.escape(result.action_text)}")

    elif result.signal_type == "SIGMA":
        lines.append("&gt;&gt; 120일선, -2σ 조건 충족")
        lines.append(f"&gt;&gt; {html.escape(result.action_text)}")

    elif result.signal_type == "RSI":
        lines.append("&gt;&gt; RSI 조건 충족")
        lines.append(f"&gt;&gt; {html.escape(result.action_text)}")

    elif result.signal_type == "RSI70":
        lines.append("&gt;&gt; RSI 70 이상")
        lines.append(f"&gt;&gt; {html.escape(result.action_text)}")

    else:
        lines.append("&gt;&gt; 조건 미충족")
        lines.append("&gt;&gt; 대기")

    return "\n".join(lines)


def build_message(results: list[SignalResult]) -> str:
    base_date = results[0].latest_date if results else "-"
    sections = [build_section(result) for result in results]

    return (
        f"<b>레버리지 핀트</b>\n"
        f"{html.escape(base_date)}\n\n"
        + "\n\n".join(sections)
    )


def has_any_signal(results: list[SignalResult]) -> bool:
    return any(r.signal_type != "NONE" for r in results)


def main():
    results = analyze_portfolio(period="1y")

    # 신호가 있을 때만 보내고 싶으면 이 줄 유지
    if not has_any_signal(results):
        print("조건 미충족: 텔레그램 알림 미전송")
        return

    message = build_message(results)
    send_telegram(message)
    print("텔레그램 알림 전송 완료")


if __name__ == "__main__":
    main()
