import json
import requests
import logging
from datetime import datetime
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

# دیکشنری ارزها و رمز ارزهای موجود
CURRENCIES = {
    # ارزهای معروف
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

    # طلا و سکه
    'sekkeh': 'سکه امامی',
    'bahar': 'سکه بهار آزادی',
    'nim': 'سکه نیم',
    'rob': 'سکه ربع',
    'gerami': 'سکه گرمی',
    'abshodeh': 'مثقال طلای آبشده',
    '18ayar': 'گرم طلای ۱۸ عیار',
    'xau': 'اونس طلا',

    # رمز ارزها
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
        """دریافت آخرین قیمت‌ها از API نوسان"""
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
                # به‌روزرسانی نرخ‌های تبدیل
                self.update_conversion_rates(data)
                return data
            else:
                logger.error(f"خطا در دریافت قیمت: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"خطا در اتصال به API: {e}")
            return None

    def update_conversion_rates(self, data):
        """به‌روزرسانی نرخ‌های تبدیل برای ماشین حساب"""
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
        """تولید متن قیمت برای یک ارز"""
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
        """تبدیل ارز با استفاده از نرخ‌های ذخیره شده"""
        try:
            amount = float(amount)

            # اگر از ریال به ارز دیگر
            if from_currency == 'rial':
                if to_currency in self.conversion_rates:
                    rate = self.conversion_rates[to_currency]
                    result = amount / rate
                    return f"{amount:,.0f} ریال = {result:,.2f} {CURRENCIES.get(to_currency, to_currency)}"
                else:
                    return f"❌ نرخ {CURRENCIES.get(to_currency, to_currency)} در دسترس نیست"

            # اگر از ارز به ریال
            elif to_currency == 'rial':
                if from_currency in self.conversion_rates:
                    rate = self.conversion_rates[from_currency]
                    result = amount * rate
                    return f"{amount:,.2f} {CURRENCIES.get(from_currency, from_currency)} = {result:,.0f} ریال"
                else:
                    return f"❌ نرخ {CURRENCIES.get(from_currency, from_currency)} در دسترس نیست"

            # تبدیل دو ارز به یکدیگر
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


# ایجاد نمونه از ربات
bot = CurrencyBot()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع"""
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

📌 برای شروع روی دکمه‌های زیر کلیک کنید:
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
    """دستور راهنما"""
    help_text = """
📖 *راهنمای کامل ربات*

🔹 *دستورات اصلی:*
/prices - نمایش قیمت‌های محبوب
/allprices - نمایش همه قیمت‌ها  
/convert - تبدیل ارز
/help - این راهنما

🔹 *نحوه استفاده از ماشین حساب تبدیل:*
پس از انتخاب گزینه تبدیل، می‌توانید:
• از ریال به ارز تبدیل کنید: `1000000 rial usd`
• از ارز به ریال تبدیل کنید: `100 usd rial`
• از ارزی به ارز دیگر: `100 usd eur`

🔹 *ارزهای پشتیبانی شده:*
• ارزها: دلار، یورو، پوند، لیر، درهم، ین، یوان و...
• طلا و سکه: سکه امامی، بهار آزادی، نیم، ربع، گرمی، مثقال، اونس
• رمز ارزها: بیت‌کوین، اتریوم، تتر، سولانا و...

📌 *نکته:* تمام قیمت‌ها به‌روز و از وب‌سرویس نوسان دریافت می‌شوند.
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def prices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش قیمت‌های محبوب"""
    await show_popular_prices(update, context)


async def all_prices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش همه قیمت‌ها به صورت دسته‌بندی شده"""
    await show_all_prices(update, context)


async def show_popular_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش قیمت‌های محبوب"""
    # ارزهای محبوب
    popular_items = ['usd_sell', 'eur', 'gbp', 'try', 'aed_sell', 'sekkeh', 'bahar', 'btc', 'eth', 'usdt']

    data = bot.get_latest_prices(popular_items)

    if not data:
        await update.message.reply_text("❌ خطا در دریافت قیمت‌ها. لطفاً دوباره تلاش کنید.")
        return

    # ارسال قیمت‌ها به صورت دسته‌بندی
    response = "📊 *قیمت‌های لحظه‌ای:*\n\n"

    # ارزها
    response += "💰 *ارزها:*\n"
    for item in ['usd_sell', 'eur', 'gbp', 'try', 'aed_sell']:
        if item in data:
            response += bot.get_price_text(item, CURRENCIES.get(item, item), data) + "\n"

    # طلا و سکه
    response += "🥇 *طلا و سکه:*\n"
    for item in ['sekkeh', 'bahar', 'abshodeh', '18ayar', 'xau']:
        if item in data:
            response += bot.get_price_text(item, CURRENCIES.get(item, item), data) + "\n"

    # رمز ارزها
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
    """نمایش همه قیمت‌ها به صورت دسته‌بندی شده"""
    # دریافت همه قیمت‌ها (حداکثر ۲۰ آیتم در هر درخواست)
    all_items = list(CURRENCIES.keys())

    # تقسیم به دسته‌های کوچکتر
    chunks = [all_items[i:i + 15] for i in range(0, len(all_items), 15)]

    data = {}
    for chunk in chunks:
        chunk_data = bot.get_latest_prices(chunk)
        if chunk_data:
            data.update(chunk_data)

    if not data:
        await update.message.reply_text("❌ خطا در دریافت قیمت‌ها. لطفاً دوباره تلاش کنید.")
        return

    response = "📊 *همه قیمت‌های لحظه‌ای:*\n\n"

    # ارزها
    response += "💰 *ارزها:*\n"
    currency_items = ['usd_sell', 'usd_buy', 'eur', 'gbp', 'try', 'aed_sell', 'cad', 'aud', 'jpy', 'cny']
    for item in currency_items:
        if item in data:
            response += bot.get_price_text(item, CURRENCIES.get(item, item), data) + "\n"

    # طلا و سکه
    response += "🥇 *طلا و سکه:*\n"
    gold_items = ['sekkeh', 'bahar', 'nim', 'rob', 'gerami', 'abshodeh', '18ayar', 'xau']
    for item in gold_items:
        if item in data:
            response += bot.get_price_text(item, CURRENCIES.get(item, item), data) + "\n"

    # رمز ارزها
    response += "🪙 *رمز ارزها:*\n"
    crypto_items = ['btc', 'eth', 'usdt', 'bnb', 'xrp', 'sol', 'doge', 'ada', 'matic', 'dot', 'shib', 'avax', 'ltc',
                    'bch', 'link', 'xlm', 'trx', 'uni', 'etc', 'ton']
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
    """دستور تبدیل ارز"""
    # ابتدا دریافت قیمت‌ها برای به‌روزرسانی نرخ‌ها
    bot.get_latest_prices()

    convert_text = """
🔄 *ماشین حساب تبدیل ارز*

برای تبدیل ارز، از دستور زیر استفاده کنید:

مثال‌ها:
• `convert 1000000 rial usd` - تبدیل یک میلیون ریال به دلار
• `convert 100 usd rial` - تبدیل ۱۰۰ دلار به ریال
• `convert 100 usd eur` - تبدیل ۱۰۰ دلار به یورو

📌 *ارزهای قابل تبدیل:*
• `rial` - ریال ایران
• `usd` - دلار آمریکا
• `eur` - یورو
• `gbp` - پوند انگلیس
• `try` - لیر ترکیه
• `aed_sell` - درهم دبی
• `sekkeh` - سکه امامی
• `btc` - بیت‌کوین
• `eth` - اتریوم
• `usdt` - تتر

و سایر ارزهای موجود در لیست.

💡 *نکته:* برای دیدن همه ارزها از دستور /allprices استفاده کنید.
"""

    keyboard = [
        [InlineKeyboardButton("💰 قیمت‌های محبوب", callback_data="popular")],
        [InlineKeyboardButton("📊 همه قیمت‌ها", callback_data="all")],
        [InlineKeyboardButton("🔄 بروزرسانی نرخ‌ها", callback_data="update_rates")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(convert_text, reply_markup=reply_markup, parse_mode='Markdown')


async def handle_convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش دستور تبدیل"""
    text = update.message.text.strip()
    parts = text.split()

    if len(parts) != 4 or parts[0].lower() != 'convert':
        await update.message.reply_text(
            "❌ فرمت صحیح: `convert [مقدار] [از] [به]`\n"
            "مثال: `convert 1000000 rial usd`",
            parse_mode='Markdown'
        )
        return

    try:
        amount = parts[1]
        from_curr = parts[2].lower()
        to_curr = parts[3].lower()

        # به‌روزرسانی نرخ‌ها
        bot.get_latest_prices()

        # بررسی وجود ارزها
        if from_curr not in bot.conversion_rates and from_curr != 'rial':
            await update.message.reply_text(
                f"❌ ارز '{from_curr}' در دسترس نیست. از /allprices برای دیدن ارزهای موجود استفاده کنید.")
            return

        if to_curr not in bot.conversion_rates and to_curr != 'rial':
            await update.message.reply_text(
                f"❌ ارز '{to_curr}' در دسترس نیست. از /allprices برای دیدن ارزهای موجود استفاده کنید.")
            return

        # تبدیل
        result = bot.convert_currency(amount, from_curr, to_curr)
        await update.message.reply_text(f"🔄 *نتیجه تبدیل:*\n{result}", parse_mode='Markdown')

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در تبدیل: {e}")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش دکمه‌ها"""
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
    """نمایش قیمت‌های محبوب (برای کالبک)"""
    query = update.callback_query

    popular_items = ['usd_sell', 'eur', 'gbp', 'try', 'aed_sell', 'sekkeh', 'bahar', 'btc', 'eth', 'usdt']

    data = bot.get_latest_prices(popular_items)

    if not data:
        await query.edit_message_text("❌ خطا در دریافت قیمت‌ها. لطفاً دوباره تلاش کنید.")
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
    """نمایش همه قیمت‌ها (برای کالبک)"""
    query = update.callback_query

    all_items = list(CURRENCIES.keys())
    chunks = [all_items[i:i + 15] for i in range(0, len(all_items), 15)]

    data = {}
    for chunk in chunks:
        chunk_data = bot.get_latest_prices(chunk)
        if chunk_data:
            data.update(chunk_data)

    if not data:
        await query.edit_message_text("❌ خطا در دریافت قیمت‌ها. لطفاً دوباره تلاش کنید.")
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
    """نمایش ماشین حساب تبدیل (برای کالبک)"""
    query = update.callback_query

    bot.get_latest_prices()

    convert_text = """
🔄 *ماشین حساب تبدیل ارز*

برای تبدیل ارز، از دستور زیر استفاده کنید:

مثال‌ها:
• `convert 1000000 rial usd` - تبدیل یک میلیون ریال به دلار
• `convert 100 usd rial` - تبدیل ۱۰۰ دلار به ریال
• `convert 100 usd eur` - تبدیل ۱۰۰ دلار به یورو

📌 *ارزهای قابل تبدیل:*
• `rial` - ریال ایران
• `usd` - دلار آمریکا
• `eur` - یورو
• `gbp` - پوند انگلیس
• `try` - لیر ترکیه
• `aed_sell` - درهم دبی
• `sekkeh` - سکه امامی
• `btc` - بیت‌کوین
• `eth` - اتریوم
• `usdt` - تتر

و سایر ارزهای موجود در لیست.
"""

    keyboard = [
        [InlineKeyboardButton("💰 قیمت‌های محبوب", callback_data="popular")],
        [InlineKeyboardButton("📊 همه قیمت‌ها", callback_data="all")],
        [InlineKeyboardButton("🔄 بروزرسانی نرخ‌ها", callback_data="update_rates")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(convert_text, reply_markup=reply_markup, parse_mode='Markdown')


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش راهنما (برای کالبک)"""
    query = update.callback_query

    help_text = """
📖 *راهنمای کامل ربات*

🔹 *دستورات اصلی:*
/prices - نمایش قیمت‌های محبوب
/allprices - نمایش همه قیمت‌ها  
/convert - تبدیل ارز
/help - این راهنما

🔹 *نحوه استفاده از ماشین حساب تبدیل:*
پس از انتخاب گزینه تبدیل، می‌توانید:
• از ریال به ارز تبدیل کنید: `convert 1000000 rial usd`
• از ارز به ریال تبدیل کنید: `convert 100 usd rial`
• از ارزی به ارز دیگر: `convert 100 usd eur`

🔹 *ارزهای پشتیبانی شده:*
• ارزها: دلار، یورو، پوند، لیر، درهم، ین، یوان و...
• طلا و سکه: سکه امامی، بهار آزادی، نیم، ربع، گرمی، مثقال، اونس
• رمز ارزها: بیت‌کوین، اتریوم، تتر، سولانا و...

📌 *نکته:* تمام قیمت‌ها به‌روز و از وب‌سرویس نوسان دریافت می‌شوند.
"""

    keyboard = [
        [InlineKeyboardButton("💰 قیمت‌های محبوب", callback_data="popular")],
        [InlineKeyboardButton("🔄 تبدیل ارز", callback_data="convert")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')


async def update_rates_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بروزرسانی نرخ‌های تبدیل"""
    query = update.callback_query

    await query.edit_message_text("🔄 در حال بروزرسانی نرخ‌ها...")

    data = bot.get_latest_prices()

    if data:
        await query.edit_message_text(
            "✅ نرخ‌ها با موفقیت بروزرسانی شدند!\n\n"
            "اکنون می‌توانید از ماشین حساب تبدیل استفاده کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تبدیل ارز", callback_data="convert")],
                [InlineKeyboardButton("💰 قیمت‌های محبوب", callback_data="popular")]
            ])
        )
    else:
        await query.edit_message_text("❌ خطا در بروزرسانی نرخ‌ها. لطفاً دوباره تلاش کنید.")


def main():
    """تابع اصلی اجرای ربات - نسخه نهایی"""
    print("🤖 در حال راه‌اندازی ربات نوسان...")

    # ایجاد برنامه
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # ثبت دستورات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("prices", prices_command))
    application.add_handler(CommandHandler("allprices", all_prices_command))
    application.add_handler(CommandHandler("convert", convert_command))

    # ثبت هندلر برای دستور تبدیل (با فرمت خاص)
    application.add_handler(MessageHandler(filters.Regex(r'^convert\s+'), handle_convert))

    # ثبت هندلر دکمه‌ها
    application.add_handler(CallbackQueryHandler(button_callback))

    print("✅ ربات با موفقیت راه‌اندازی شد!")
    print("🔄 ربات در حال اجرا است... (برای متوقف کردن Ctrl+C بزنید)")

    # اجرای ربات به روش استاندارد
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
