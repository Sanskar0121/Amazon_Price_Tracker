import requests
from bs4 import BeautifulSoup
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fake_useragent import UserAgent 
import random
import json
import os 

# Configuration 
ua = UserAgent()
HEADERS = { 
    "User-Agent": ua.random,
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://www.google.com/"
} 

# Email configuration
EMAIL_SENDER = "xyz@gmail.com"
EMAIL_PASSWORD = "xyz" 
EMAIL_RECEIVER = "xyz@gmail.com" 
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Price history file
PRICE_HISTORY_FILE = "price_history.json"

# Products to track
PRODUCTS_TO_TRACK = [
    ("https://www.amazon.com/Apple-MacBook-13-inch-256GB-Storage/dp/B08N5KWB9H", 999.00, "MacBook Air M1"),
    ("https://www.amazon.com/Sony-WH-1000XM5-Canceling-Headphones-Hands-Free/dp/B09XS7JWHH", 299.00, "Sony WH-1000XM5 Headphones"),
    ("https://www.amazon.com/Apple-iPhone-14-Pro-128GB/dp/B0BN93V3TZ", 899.00, "iPhone 14 Pro"),
    ("https://www.amazon.com/Samsung-55-Inch-Class-QN90B-Neo-QLED/dp/B09V2RSZ74", 1499.00, "Samsung 55\" QN90B Neo QLED TV"),
    ("https://www.amazon.com/Instant-Pot-Duo-Evo-Plus/dp/B07W55DDFB", 99.00, "Instant Pot Duo Evo Plus"),
    ("https://www.amazon.com/Ninja-FD401-DualZone-Technology-Black/dp/B07FDJMC5Q", 199.00, "Ninja Foodi Air Fryer"),
    ("https://www.amazon.com/Atomic-Habits-Proven-Build-Break/dp/0735211299", 15.00, "Atomic Habits by James Clear"),
    ("https://www.amazon.com/PlayStation-5-Console/dp/B08FC5L3RG", 499.00, "PlayStation 5 Console"),
    ("https://www.amazon.com/Xbox-Series-X/dp/B08H75RTZ8", 449.00, "Xbox Series X"),
    ("https://www.amazon.com/Levis-Mens-501-Original-Fit/dp/B00N1YXQ9C", 40.00, "Levi's 501 Original Fit Jeans"),
]

def load_price_history():
    if os.path.exists(PRICE_HISTORY_FILE):
        with open(PRICE_HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_price_history(history):
    with open(PRICE_HISTORY_FILE, 'w') as f:
        json.dump(history, f)

def get_amazon_price(url):
    try:
        HEADERS["User-Agent"] = ua.random
        time.sleep(random.uniform(1, 5))

        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()

        if "api-services-support@amazon.com" in response.text:
            print("Amazon CAPTCHA triggered - try again later")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        price_selectors = [
            'span.a-price[data-a-size="xl"] span.a-offscreen',
            'span.aok-offscreen',
            'span.priceToPay span.a-offscreen',
            'span.a-price-whole',
            'span#priceblock_ourprice',
            'span#priceblock_dealprice',
            'span#priceblock_saleprice',
        ]

        for selector in price_selectors:
            price_element = soup.select_one(selector)
            if price_element:
                price_text = price_element.get_text()
                try:
                    price = float(price_text.replace('$', '').replace(',', '').strip())
                    return price
                except ValueError:
                    continue

        unavailable = soup.select_one('#availability span')
        if unavailable and 'currently unavailable' in unavailable.text.lower():
            print("Product is currently unavailable")
            return None

        return None

    except requests.exceptions.RequestException as e:
        print(f"Network error: {str(e)}")
        return None
    except Exception as e:
        print(f"Error scraping Amazon: {str(e)}")
        return None

def send_email_alert(product_name, current_price, threshold_price, product_url, price_history=None):
    try:
        message = MIMEMultipart()
        message['From'] = EMAIL_SENDER
        message['To'] = EMAIL_RECEIVER
        message['Subject'] = f"💰 Price Alert: {product_name} dropped to ${current_price:.2f}!"

        history_table = ""
        if price_history and len(price_history) > 1:
            history_rows = "\n".join(
                f"<tr><td>{date}</td><td>${price:.2f}</td></tr>"
                for date, price in sorted(price_history.items())
            )
            history_table = f"""
            <h3>Price History:</h3>
            <table border="1" cellpadding="5" cellspacing="0">
                <tr><th>Date</th><th>Price</th></tr>
                {history_rows}
            </table>
            """

        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <h2 style="color: #e63946;">🚨 Price Drop Alert!</h2>
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;">
                    <p><strong>📦 Product:</strong> {product_name}</p>
                    <p><strong>💰 Current Price:</strong> <span style="color: #2a9d8f; font-weight: bold;">${current_price:.2f}</span></p>
                    <p><strong>🎯 Your Threshold:</strong> ${threshold_price:.2f}</p>
                    <p><strong>💵 Savings:</strong> <span style="color: #e63946; font-weight: bold;">${threshold_price - current_price:.2f}</span> below your target!</p>
                    <p><a href="{product_url}" style="background-color: #457b9d; color: white; padding: 8px 12px; text-decoration: none; border-radius: 4px;">👉 View Product on Amazon</a></p>
                </div>
                {history_table}
                <p style="margin-top: 20px; font-size: 0.9em; color: #6c757d;">
                    This is an automated alert. You can modify your tracking list in the script.
                </p>
            </body>
        </html>
        """

        message.attach(MIMEText(body, 'html'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, message.as_string())

        print(f"Alert sent for {product_name}!")

    except Exception as e:
        print(f"Failed to send email alert: {e}")

def track_prices():
    print("Starting price tracker...")
    price_history = load_price_history()

    while True:
        for product_url, threshold_price, product_name in PRODUCTS_TO_TRACK:
            print(f"\nChecking price for {product_name}...")

            current_price = get_amazon_price(product_url)

            if current_price is None:
                print("Could not retrieve price. Trying again later...")
                continue

            current_time = time.strftime("%Y-%m-%d %H:%M")
            if product_name not in price_history:
                price_history[product_name] = {}
            price_history[product_name][current_time] = current_price
            save_price_history(price_history)

            print(f"Current price: ${current_price:.2f} | Your threshold: ${threshold_price:.2f}")

            if current_price <= threshold_price:
                print(f"ALERT: {product_name} is below your threshold price!")
                send_email_alert(
                    product_name,
                    current_price,
                    threshold_price,
                    product_url,
                    price_history.get(product_name)
                )
            else:
                price_history_for_product = price_history.get(product_name, {})
                if len(price_history_for_product) > 1:
                    previous_prices = list(price_history_for_product.values())
                    previous_low = min(previous_prices[:-1])
                    if current_price < previous_low * 0.9:
                        print(f"NOTICE: {product_name} had a significant price drop (${previous_low:.2f} → ${current_price:.2f})")
                        send_email_alert(
                            product_name,
                            current_price,
                            previous_low,
                            product_url,
                            price_history_for_product
                        )
                else:
                    print("Price is still above your threshold.")

        wait_time = random.randint(2*3600, 6*3600)
        wait_hours = wait_time // 3600
        wait_minutes = (wait_time % 3600) // 60
        print(f"\nWaiting for {wait_hours} hours and {wait_minutes} minutes before next check...")
        time.sleep(wait_time)

if __name__ == "__main__":
    try:
        track_prices()
    except KeyboardInterrupt:
        print("\nPrice tracker stopped by user.")
    except Exception as e:
        print(f"Unexpected error: {e}") 
