# alerts.py — free tier via Gmail SMTP or WhatsApp Business API free tier
import smtplib
from email.mime.text import MIMEText

def send_price_alert(ticker, current_price, threshold, user_email):
    """Free via Gmail SMTP — 500 emails/day"""
    msg = MIMEText(
        f"🚨 JSE Alert: {ticker} has crossed R{threshold:.2f}\n"
        f"Current price: R{current_price:.2f}\n\n"
        f"View full analysis: https://your-app.streamlit.app"
    )
    msg["Subject"] = f"JSE Alert: {ticker} @ R{current_price:.2f}"
    msg["From"] = "alerts@yourdomain.com"
    msg["To"] = user_email
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login("your@gmail.com", "app_password")
        server.send_message(msg)