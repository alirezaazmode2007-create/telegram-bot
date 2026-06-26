import json
import requests
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

with open('token.json', 'r') as f:
    token = json.load(f)

# تنظیمات
TELEGRAM_TOKEN = token['TELEGRAM_TOKEN']
NAVASAN_API_KEY = token['NAVASAN_API_KEY']
NAVASAN_BASE_URL = token['NAVASAN_BASE_URL']

# تنظیم لاگینگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ایجاد اپ Flask
app = Flask(__name__)

# دیکشنری ارزها و رمز ارزهای موجود
CURRENCIES = {
    'usd_sell': 'دلار تهران (فروش)',
    'usd_buy': 'دلار تهران (خرید)',
    'harat_naghdi_sell': 'دلار هرات نقدی (فروش)',
    'harat_naghdi_buy': 'دلار هرات نقدی (خرید)',
    'eur': 'یورو',
    'gbp': 'پوند انگلیس',
    'try': 'لیر ترکیه',
    'aed_sell': 'درهم دبی (فروش)',
    'cad': 'دلار کانادا',
    'aud': 'دلار استرالیا',
    'jpy': 'ین ژاپن',
    'cny': 'یوان چین',
    'usd_farda_buy': 'دلار فردایی (خرید)',
    'usd_farda_sell': 'دلار فردایی (فروش)',
    'usd_sherkat': 'دلار شرکت (حواله)',
    'usd_shakhs': 'دلار شخص (حواله)',
    'sekkeh': 'سکه امامی',
    'bahar': 'سکه بهار آزادی',
    'nim': 'سکه نیم',
    'rob': 'سکه ربع',
    'gerami': 'سکه گرمی',
    'abshodeh': 'مثقال طلای آبشده',
    '18ayar': 'گرم طلای ۱۸ عیار',
    'xau': 'اونس طلا',
    'btc': 'بیت‌کوین',
    'eth': 'اتریوم',
    'usdt': 'تتر',
    'bnb': 'بایننس',
    'xrp': 'ریپل',
    'sol': 'سولانا',
    'doge': 'دوج‌کوین',
    'ada': 'کاردانو',
    'matic': 'متیک',
    'dot': 'پولکادات',
    'shib': 'شیبا اینو',
    'avax': 'آوالانچ',
    'ltc': 'لایت‌کوین',
    'bch': 'بیت‌کوین کش',
    'link': 'چین لینک',
    'xlm': 'استلار',
    'trx': 'ترون',
    'uni': 'یونی‌سواپ',
    'etc': 'اتریوم کلاسیک',
    'ton': 'تون‌کوین',
}

class CurrencyBot:
    def __init__(self):
        self.conversion_rates = {}
        self.last_update = None
        
    def get_latest_prices(self, items=None):
        try:
            url = f"{NAVASAN_BASE_URL}/latest/"
            params = {'api_key': NAVASAN_API_KEY}
            if items:
                if isinstance(items, list):
                    params['item'] = ','.join(items)
                else:
                    params['item'] = items
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.update_conversion_rates(data)
                return data
            else:
                logger.error(f"خطا در دریافت قیمت: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"خطا در اتصال به API: {e}")
            return None
    
    def update_conversion_rates(self, data):
        for key, value in data.items():
            if key not in ['dollar_rate', 'dirham_rate', 'dollar_rate_time', 'dollar_rate_24h_change', 
                          'dollar_rate_24h_vol', 'dirham_rate_time', 'dirham_rate_24h_change', 
                          'dirham_rate_24h_vol']:
                if isinstance(value, dict) and 'value' in value:
                    try:
                        self.conversion_rates[key] = float(value['value'])
                    except:
                        pass
        self.last_update = datetime.now()
    
    def get_price_text(self, item_key, item_name, data):
        if item_key in data and isinstance(data[item_key], dict):
            item_data = data[item_key]
            value = item_data.get('value', 'نامشخص')
            change = item_data.get('change', 0)
            date = item_data.get('date', 'نامشخص')
            change_emoji = "📈" if change > 0 else "📉" if change < 0 else "➖"
            change_text = f"{change_emoji} {change:+,}" if change != 0 else "➖ بدون تغییر"
            return f"""
🏷️ *{item_name}*
💰 قیمت: `{value}`
📊 تغییر: {change_text}
🕐 زمان: {date}
"""
        return f"❌ قیمت {item_name} در دسترس نیست"
    
    def convert_currency(self, amount, from_currency, to_currency):
        try:
            amount = float(amount)
            if from_currency == 'rial':
                if to_currency in self.conversion_rates:
                    rate = self.conversion_rates[to_currency]
                    result = amount / rate
                    return f"{amount:,.0f} ریال = {result:,.2f} {CURRENCIES.get(to_currency, to_currency)}"
                else:
                    return f"❌ نرخ {CURRENCIES.get(to_currency, to_currency)} در دسترس نیست"
            elif to_currency == 'rial':
                if from_currency in self.conversion_rates:
                    rate = self.conversion_rates[from_currency]
                    result = amount * rate
                    return f"{amount:,.2f} {CURRENCIES.get(from_currency, from_currency)} = {result:,.0f} ریال"
                else:
                    return f"❌ نرخ {CURRENCIES.get(from_currency, from_currency)} در دسترس نیست"
            else:
                if from_currency in self.conversion_rates and to_currency in self.conversion_rates:
                    rate_from = self.conversion_rates[from_currency]
                    rate_to = self.conversion_rates[to_currency]
                    result = (amount * rate_from) / rate_to
                    return f"{amount:,.2f} {CURRENCIES.get(from_currency, from_currency)} = {result:,.2f} {CURRENCIES.get(to_currency, to_currency)}"
                else:
                    return f"❌ نرخ یکی از ارزها در دسترس نیست"
        except ValueError:
            return "❌ لطفاً عدد معتبر وارد کنید"
        except Exception as e:
            return f"❌ خطا در تبدیل: {e}"

bot = CurrencyBot()

# ============ توابع ربات تلگرام ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = f"""
🌟 سلام {user.first_name} عزیز! 🌟

به ربات قیمت‌های نوسان خوش آمدید!

📊 *قابلیت‌های ربات:*
• دریافت قیمت لحظه‌ای ارزها، طلا، سکه و رمز ارزها
• مشاهده قیمت‌های محبوب
• ماشین حساب تبدیل ارز

🔹 *دستورات:*
/prices - نمایش قیمت‌های محبوب
/allprices - نمایش همه قیمت‌ها
/convert - تبدیل ارز
/help - راهنمای کامل
"""
    keyboard = [
        [InlineKeyboardButton("💰 قیمت‌های محبوب", callback_data="popular")],
        [InlineKeyboardButton("🔄 ماشین حساب تبدیل", callback_data="convert")],
        [InlineKeyboardButton("📊 همه قیمت‌ها", callback_data="all")],
        [InlineKeyboardButton("❓ راهنما", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📖 *راهنمای کامل ربات*

🔹 *دستورات اصلی:*
/prices - نمایش قیمت‌های محبوب
/allprices - نمایش همه قیمت‌ها  
/convert - تبدیل ارز
/help - این راهنما

🔹 *نحوه استفاده از ماشین حساب تبدیل:*
• از ریال به ارز: `convert 1000000 rial usd`
• از ارز به ریال: `convert 100 usd rial`
• از ارزی به ارز دیگر: `convert 100 usd eur`
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def prices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_popular_prices(update, context)

async def all_prices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_all_prices(update, context)

async def show_popular_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    popular_items = ['usd_sell', 'eur', 'gbp', 'try', 'aed_sell', 'sekkeh', 'bahar', 'btc', 'eth', 'usdt']
    data = bot.get_latest_prices(popular_items)
    if not data:
        await update.message.reply_text("❌ خطا در دریافت قیمت‌ها. لطفاً دوباره تلاش کنید.")
        return
    response = "📊 *قیمت‌های لحظه‌ای:*\n\n"
    response += "💰 *ارزها:*\n"
    for item in ['usd_sell', 'eur', 'gbp', 'try', 'aed_sell']:
        if item in data:
            response += bot.get_price_text(item, CURRENCIES.get(item, item), data) + "\n"
    response += "🥇 *طلا و سکه:*\n"
    for item in ['sekkeh', 'bahar', 'abshodeh', '18ayar', 'xau']:
        if item in data:
            response += bot.get_price_text(item, CURRENCIES.get(item, item), data) + "\n"
    response += "🪙 *رمز ارزها:*\n"
    for item in ['btc', 'eth', 'usdt', 'bnb']:
        if item in data:
            response += bot.get_price_text(item, CURRENCIES.get(item, item), data) + "\n"
    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data="popular")],
        [InlineKeyboardButton("📊 همه قیمت‌ها", callback_data="all")],
        [InlineKeyboardButton("🔄 تبدیل ارز", callback_data="convert")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(response, reply_markup=reply_markup, parse_mode='Markdown')

async def show_all_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_items = list(CURRENCIES.keys())
    chunks = [all_items[i:i+15] for i in range(0, len(all_items), 15)]
    data = {}
    for chunk in chunks:
        chunk_data = bot.get_latest_prices(chunk)
        if chunk_data:
            data.update(chunk_data)
    if not data:
        await update.message.reply_text("❌ خطا در دریافت قیمت‌ها. لطفاً دوباره تلاش کنید.")
        return
    response = "📊 *همه قیمت‌های لحظه‌ای:*\n\n"
    response += "💰 *ارزها:*\n"
    currency_items = ['usd_sell', 'usd_buy', 'eur', 'gbp', 'try', 'aed_sell', 'cad', 'aud', 'jpy', 'cny']
    for item in currency_items:
        if item in data:
            response += bot.get_price_text(item, CURRENCIES.get(item, item), data) + "\n"
    response += "🥇 *طلا و سکه:*\n"
    gold_items = ['sekkeh', 'bahar', 'nim', 'rob', 'gerami', 'abshodeh', '18ayar', 'xau']
    for item in gold_items:
        if item in data:
            response += bot.get_price_text(item, CURRENCIES.get(item, item), data) + "\n"
    response += "🪙 *رمز ارزها:*\n"
    crypto_items = ['btc', 'eth', 'usdt', 'bnb', 'xrp', 'sol', 'doge', 'ada', 'matic', 'dot', 'shib', 'avax', 'ltc', 'bch', 'link', 'xlm', 'trx', 'uni', 'etc', 'ton']
    for item in crypto_items:
        if item in data:
            response += bot.get_price_text(item, CURRENCIES.get(item, item), data) + "\n"
    keyboard = [
        [InlineKeyboardButton("💰 قیمت‌های محبوب", callback_data="popular")],
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data="all")],
        [InlineKeyboardButton("🔄 تبدیل ارز", callback_data="convert")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(response, reply_markup=reply_markup, parse_mode='Markdown')

async def convert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot.get_latest_prices()
    convert_text = """
🔄 *ماشین حساب تبدیل ارز*

مثال‌ها:
• `convert 1000000 rial usd` - تبدیل یک میلیون ریال به دلار
• `convert 100 usd rial` - تبدیل ۱۰۰ دلار به ریال
• `convert 100 usd eur` - تبدیل ۱۰۰ دلار به یورو
"""
    keyboard = [
        [InlineKeyboardButton("💰 قیمت‌های محبوب", callback_data="popular")],
        [InlineKeyboardButton("📊 همه قیمت‌ها", callback_data="all")],
        [InlineKeyboardButton("🔄 بروزرسانی نرخ‌ها", callback_data="update_rates")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(convert_text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    parts = text.split()
    if len(parts) != 4 or parts[0].lower() != 'convert':
        await update.message.reply_text("❌ فرمت صحیح: `convert [مقدار] [از] [به]`", parse_mode='Markdown')
        return
    try:
        amount = parts[1]
        from_curr = parts[2].lower()
        to_curr = parts[3].lower()
        bot.get_latest_prices()
        if from_curr not in bot.conversion_rates and from_curr != 'rial':
            await update.message.reply_text(f"❌ ارز '{from_curr}' در دسترس نیست.")
            return
        if to_curr not in bot.conversion_rates and to_curr != 'rial':
            await update.message.reply_text(f"❌ ارز '{to_curr}' در دسترس نیست.")
            return
        result = bot.convert_currency(amount, from_curr, to_curr)
        await update.message.reply_text(f"🔄 *نتیجه تبدیل:*\n{result}", parse_mode='Markdown')
    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در تبدیل: {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "popular":
        await show_popular_prices_callback(update, context)
    elif query.data == "all":
        await show_all_prices_callback(update, context)
    elif query.data == "convert":
        await convert_callback(update, context)
    elif query.data == "help":
        await help_callback(update, context)
    elif query.data == "update_rates":
        await update_rates_callback(update, context)

async def show_popular_prices_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    popular_items = ['usd_sell', 'eur', 'gbp', 'try', 'aed_sell', 'sekkeh', 'bahar', 'btc', 'eth', 'usdt']
    data = bot.get_latest_prices(popular_items)
    if not data:
        await query.edit_message_text("❌ خطا در دریافت قیمت‌ها.")
        return
    response = "📊 *قیمت‌های لحظه‌ای:*\n\n"
    response += "💰 *ارزها:*\n"
    for item in ['usd_sell', 'eur', 'gbp', 'try', 'aed_sell']:
        if item in data:
            response += bot.get_price_text(item, CURRENCIES.get(item, item), data) + "\n"
    response += "🥇 *طلا و سکه:*\n"
    for item in ['sekkeh', 'bahar', 'abshodeh', '18ayar', 'xau']:
        if item in data:
            response += bot.get_price_text(item, CURRENCIES.get(item, item), data) + "\n"
    response += "🪙 *رمز ارزها:*\n"
    for item in ['btc', 'eth', 'usdt', 'bnb']:
        if item in data:
            response += bot.get_price_text(item, CURRENCIES.get(item, item), data) + "\n"
    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data="popular")],
        [InlineKeyboardButton("📊 همه قیمت‌ها", callback_data="all")],
        [InlineKeyboardButton("🔄 تبدیل ارز", callback_data="convert")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(response, reply_markup=reply_markup, parse_mode='Markdown')

async def show_all_prices_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    all_items = list(CURRENCIES.keys())
    chunks = [all_items[i:i+15] for i in range(0, len(all_items), 15)]
    data = {}
    for chunk in chunks:
        chunk_data = bot.get_latest_prices(chunk)
        if chunk_data:
            data.update(chunk_data)
    if not data:
        await query.edit_message_text("❌ خطا در دریافت قیمت‌ها.")
        return
    response = "📊 *همه قیمت‌های لحظه‌ای:*\n\n"
    response += "💰 *ارزها:*\n"
    currency_items = ['usd_sell', 'usd_buy', 'eur', 'gbp', 'try', 'aed_sell', 'cad', 'aud', 'jpy', 'cny']
    for item in currency_items:
        if item in data:
            response += bot.get_price_text(item, CURRENCIES.get(item, item), data) + "\n"
    response += "🥇 *طلا و سکه:*\n"
    gold_items = ['sekkeh', 'bahar', 'nim', 'rob', 'gerami', 'abshodeh', '18ayar', 'xau']
    for item in gold_items:
        if item in data:
            response += bot.get_price_text(item, CURRENCIES.get(item, item), data) + "\n"
    response += "🪙 *رمز ارزها:*\n"
    crypto_items = ['btc', 'eth', 'usdt', 'bnb', 'xrp', 'sol', 'doge', 'ada', 'matic', 'dot', 'shib', 'avax']
    for item in crypto_items:
        if item in data:
            response += bot.get_price_text(item, CURRENCIES.get(item, item), data) + "\n"
    keyboard = [
        [InlineKeyboardButton("💰 قیمت‌های محبوب", callback_data="popular")],
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data="all")],
        [InlineKeyboardButton("🔄 تبدیل ارز", callback_data="convert")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(response, reply_markup=reply_markup, parse_mode='Markdown')

async def convert_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot.get_latest_prices()
    convert_text = """
🔄 *ماشین حساب تبدیل ارز*

مثال‌ها:
• `convert 1000000 rial usd`
• `convert 100 usd rial`
• `convert 100 usd eur`
"""
    keyboard = [
        [InlineKeyboardButton("💰 قیمت‌های محبوب", callback_data="popular")],
        [InlineKeyboardButton("📊 همه قیمت‌ها", callback_data="all")],
        [InlineKeyboardButton("🔄 بروزرسانی نرخ‌ها", callback_data="update_rates")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(convert_text, reply_markup=reply_markup, parse_mode='Markdown')

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    help_text = """
📖 *راهنمای کامل ربات*

🔹 *دستورات اصلی:*
/prices - نمایش قیمت‌های محبوب
/allprices - نمایش همه قیمت‌ها  
/convert - تبدیل ارز
/help - این راهنما
"""
    keyboard = [
        [InlineKeyboardButton("💰 قیمت‌های محبوب", callback_data="popular")],
        [InlineKeyboardButton("🔄 تبدیل ارز", callback_data="convert")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

async def update_rates_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("🔄 در حال بروزرسانی نرخ‌ها...")
    data = bot.get_latest_prices()
    if data:
        await query.edit_message_text(
            "✅ نرخ‌ها با موفقیت بروزرسانی شدند!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تبدیل ارز", callback_data="convert")],
                [InlineKeyboardButton("💰 قیمت‌های محبوب", callback_data="popular")]
            ])
        )
    else:
        await query.edit_message_text("❌ خطا در بروزرسانی نرخ‌ها.")

# ============ راه‌اندازی ربات ============
def run_bot():
    """راه‌اندازی ربات تلگرام"""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("prices", prices_command))
    application.add_handler(CommandHandler("allprices", all_prices_command))
    application.add_handler(CommandHandler("convert", convert_command))
    application.add_handler(MessageHandler(filters.Regex(r'^convert\s+'), handle_convert))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("✅ ربات تلگرام راه‌اندازی شد!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

# ============ مسیرهای Flask برای Render ============
@app.route('/')
def home():
    return "🤖 ربات نوسان در حال اجراست!", 200

@app.route('/health')
def health():
    """مسیر سلامت برای بررسی وضعیت ربات"""
    return "✅ ربات سالم است!", 200

@app.route('/start_bot')
def start_bot_route():
    """مسیر برای شروع ربات - اینجا ربات را در پس‌زمینه اجرا می‌کنیم"""
    import threading
    thread = threading.Thread(target=run_bot)
    thread.daemon = True
    thread.start()
    return "✅ ربات در حال راه‌اندازی است!", 200

# ============ نقطه شروع برنامه ============
if __name__ == '__main__':
    import threading
    # شروع ربات در یک ترد جداگانه
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # اجرای سرور Flask
    app.run(host='0.0.0.0', port=10000)
