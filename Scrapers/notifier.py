import os
import requests
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication 
from datetime import datetime
from fpdf import FPDF 

logger = logging.getLogger(__name__)

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.set_text_color(16, 185, 129) 
        self.cell(0, 10, 'Warsaw AI PropTech - Market Insights', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f'Report Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1, 'C')
        self.ln(10)

    def add_opportunity_table(self, data_rows):
        self.set_font('Arial', 'B', 10)
        self.set_fill_color(0, 51, 102) # Koyu Lacivert Başlıklar
        self.set_text_color(255, 255, 255)
        cols = ['District', 'Price (PLN)', 'Size (m2)', 'Est. ROI / Margin']
        widths = [45, 45, 30, 50]

        for i, col in enumerate(cols):
            self.cell(widths[i], 10, col, 1, 0, 'C', 1)
        self.ln()

        self.set_font('Arial', '', 10)
        self.set_text_color(0, 0, 0)
        for row in data_rows:
            self.cell(widths[0], 10, str(row[0]), 1)
            self.cell(widths[1], 10, f"{row[1]:,}", 1, 0, 'R')
            self.cell(widths[2], 10, str(row[2]), 1, 0, 'C')
            self.cell(widths[3], 10, str(row[3]), 1, 0, 'C')
            self.ln()

class TelegramBot:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def send_message(self, message, parse_mode="HTML"):
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode
        }
        try:
            response = requests.post(self.api_url, json=payload, timeout=10)
            if response.status_code != 200:
                logger.error(f"❌ TELEGRAM API ERROR: {response.text}")
        except Exception as e:
            logger.error(f"❌ Telegram Network Failed: {e}")

    def send_daily_report(self, stats):
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
        return False
    text = f"🚨 <b>NEW VIP INVESTMENT LEAD!</b>\n\n📌 <b>Target:</b> {deal_type}\n👤 <b>Name:</b> {name}\n📧 <b>Email:</b> {email}\n📞 <b>Phone:</b> {phone}\n💬 <b>Message:</b> {message}"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        response = requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json=payload, timeout=10)
        return response.status_code == 200
    except:
        return False

class EmailManager:
    def __init__(self):
        self.sender_email = os.getenv("SENDER_EMAIL")
        self.sender_password = os.getenv("SENDER_PASSWORD")

    def send_user_email(self, to_email, subject, body_html):
        if not self.sender_email or not self.sender_password:
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
            return True
        except Exception as e:
            logger.error(f"❌ Email Failed: {e}")
            return False

    def send_email_with_pdf(self, to_email, subject, body_html, pdf_path):
        if not self.sender_email or not self.sender_password:
            return False

        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body_html, 'html'))

        try:
            with open(pdf_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(pdf_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(pdf_path)}"'
            msg.attach(part)

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            logger.error(f"❌ PDF Email Failed: {e}")
            return False

    def create_html_template(self, title, content_lines, property_url):
        content_html = "".join(f"<p style='margin: 10px 0;'>{line}</p>" for line in content_lines)
        html = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                <div style="background: linear-gradient(135deg, #10B981 0%, #059669 100%); padding: 25px 20px; text-align: center;">
                    <h2 style="color: #ffffff; margin: 0; font-size: 24px;">{title}</h2>
                </div>
                <div style="padding: 30px 25px; color: #334155; font-size: 16px; line-height: 1.6;">
                    {content_html}
                    <div style="text-align: center; margin-top: 35px;">
                        <a href="{property_url}" style="background-color: #10B981; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold;">View Details</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        return html