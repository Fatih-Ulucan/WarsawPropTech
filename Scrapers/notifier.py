import os
import requests
import logging
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def send_message(self, message, parse_mode="HTML"):
        """Sends a text message to the specified Telegram chat. (Exact logic from main)"""

        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=10)
            if response.status_code != 200:
                logger.error(f"❌ TELEGRAM API ERROR: {response.text}")
            else:
                logger.info("✅ TELEGRAM MESSAGE SENT SUCCESSFULLY!")
        except Exception as e:
            logger.error(f"❌ Telegram Network Failed: {e}")

    def send_daily_report(self, stats):
        """Formats and sends the summary report at the end of a cycle. (Exact logic from main)"""
        uptime = datetime.now() - stats['start_time']

        report = f"📊 <b>WARSAW MARKET REPORT</b>\n" \
                 f"━━━━━━━━━━━━━━━━━━━━\n" \
                 f"⏱ <b>Uptime:</b> {str(uptime).split('.')[0]}\n" \
                 f"🧐 <b>Ads Scanned:</b> {stats['scanned']}\n" \
                 f"✅ <b>New Entries:</b> {stats['added']}\n" \
                 f"🔥 <b>AI Deals Found:</b> {stats['bargains']}\n" \
                 f"📉 <b>Price Drops Detected:</b> {stats['price_drops']}\n" \
                 f"━━━━━━━━━━━━━━━━━━━━"

        self.send_message(report)

    def create_price_drop_alert(self, drop_data):
        """Exact string format from check_and_update_price for price drops."""
        alert_template = f"🚨 <b>PRICE DROP ALERT!</b> 🚨\n" \
                         f"━━━━━━━━━━━━━━━━━━━━\n" \
                         f"🔻 <b>Discount:</b> -{drop_data['drop_amount']:,} PLN\n" \
                         f"📉 <b>Old Price:</b> {drop_data['db_price']:,} PLN\n" \
                         f"━━━━━━━━━━━━━━━━━━━━\n" \
                         f"📍 <b>District:</b> {drop_data['location']}\n" \
                         f"💰 <b>Total Price:</b> {drop_data['current_price']:,} PLN\n" \
                         f"📐 <b>Size:</b> {drop_data['sqm']} m² | 🚪 <b>Rooms:</b> {drop_data['rooms']}\n" \
                         f"📈 <b>Margin vs Avg:</b> %{drop_data['profit_margin']}\n" \
                         f"━━━━━━━━━━━━━━━━━━━━\n" \
                         f"🧠 <b>PROPTECH AI ANALYSIS:</b>\n" \
                         f"{{ai_report}}\n" \
                         f"━━━━━━━━━━━━━━━━━━━━\n" \
                         f"🔗 <a href='{drop_data['full_url']}'>View Listing</a>"
        return alert_template

    def create_deal_alert(self, deal_data):
        """Exact string format from test_scraper for new bargains."""
        alert_template = f"{deal_data['flip_flag_text']}" \
                         f"{deal_data['score_icon']} <b>INVESTMENT SCORE: {deal_data['deal_score']}/100</b>\n" \
                         f"━━━━━━━━━━━━━━━━━━━━\n" \
                         f"📍 <b>District:</b> {deal_data['location']}\n" \
                         f"🏢 <b>Category:</b> {deal_data['label']}\n" \
                         f"💰 <b>Total Price:</b> {deal_data['clean_price']:,} PLN\n" \
                         f"📐 <b>Size:</b> {deal_data['sqm']} m² | 🚪 <b>Rooms:</b> {deal_data['rooms']}\n" \
                         f"📈 <b>Market Avg:</b> {deal_data['avg_sqm_price']:,.0f} PLN\n" \
                         f"💎 <b>PROFIT MARGIN:</b> %{deal_data['profit_margin']}\n" \
                         f"━━━━━━━━━━━━━━━━━━━━\n"

        if deal_data.get('trans_id') == 1 and deal_data.get('true_profit', 0) > 0:
            alert_template += f"💸 <b>TRUE NET PROFIT:</b> ~{deal_data['true_profit']:,.0f} PLN (after reno)\n"

        if deal_data.get('roi_percent', 0) > 0:
            alert_template += f"🔮 <b>Est. ROI:</b> %{deal_data['roi_percent']} / Year\n"

        alert_template += f"━━━━━━━━━━━━━━━━━━━━\n" \
                          f"🧠 <b>PROPTECH AI ANALYSIS:</b>\n" \
                          f"{{ai_report}}\n" \
                          f"━━━━━━━━━━━━━━━━━━━━\n" \
                          f"🔗 <a href='{deal_data['full_url']}'>View Listing</a>"

        return alert_template

def send_telegram_lead(name, email, phone, message, deal_type):
    bot_token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        logger.error("❌ Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in environment variables.")
        return False

    text = f"🚨 <b>NEW VIP INVESTMENT LEAD!</b>\n\n" \
           f"📌 <b>Target:</b> {deal_type}\n" \
           f"👤 <b>Name:</b> {name}\n" \
           f"📧 <b>Email:</b> {email}\n" \
           f"📞 <b>Phone:</b> {phone}\n" \
           f"💬 <b>Message:</b> {message}"

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("✅ VIP LEAD NOTIFICATION SENT TO TELEGRAM!")
            return True
        else:
            logger.error(f"❌ VIP LEAD TELEGRAM ERROR: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ VIP Lead Telegram Network Failed: {e}")
        return False


class EmailManager:
    def __init__(self, sender_email, sender_password):
        self.sender_email = sender_email
        self.sender_password = sender_password

    def send_user_email(self, to_email, subject, body_html):
        """Sends an HTML email notification to a specific user."""
        if not self.sender_email or not self.sender_password:
            logger.error("❌ Email credentials missing. Cannot send email.")
            return False

        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body_html, 'html'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
            server.quit()
            logger.info(f"✅ EMAIL SENT SUCCESSFULLY TO: {to_email}")
            return True
        except Exception as e:
            logger.error(f"❌ Email Sending Failed for {to_email}: {e}")
            return False

    def create_html_template(self, title, content_lines, property_url):
        """Generates a professional, responsive HTML template for customer emails."""

        content_html = "".join(f"<p style='margin: 10px 0;'>{line}</p>" for line in content_lines)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                <div style="background: linear-gradient(135deg, #10B981 0%, #059669 100%); padding: 25px 20px; text-align: center;">
                    <h2 style="color: #ffffff; margin: 0; font-size: 24px; letter-spacing: 0.5px;">{title}</h2>
                </div>
                
                <div style="padding: 30px 25px; color: #334155; font-size: 16px; line-height: 1.6;">
                    {content_html}
                    
                    <div style="text-align: center; margin-top: 35px; margin-bottom: 15px;">
                        <a href="{property_url}" style="background-color: #10B981; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px; display: inline-block;">View Property Details</a>
                    </div>
                </div>
                
                <div style="background-color: #f8fafc; padding: 20px; text-align: center; font-size: 13px; color: #94a3b8; border-top: 1px solid #e2e8f0;">
                    <p style="margin: 0 0 10px 0;"><strong>Warsaw AI PropTech Engine</strong> &copy; {datetime.now().year}</p>
                    <p style="margin: 0;">You received this email because you are tracking this property or it matches your VIP alert criteria.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html