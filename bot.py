import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
import re
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- কনফিগারেশন ---
# আপনার বট টোকেন এখানে দিন (সরাসরি কোডের ভিতরে)
BOT_TOKEN = '8707267313:AAFzqkne7yUZjeNnXza6KbhHIIJMuq1v_zI'  # <-- এখানে আপনার টোকেন দিন

API_URL = 'https://nhbdprank.ct.ws/api.php'

# বট ইন্সট্যান্স তৈরি
bot = telebot.TeleBot(BOT_TOKEN)

# ইউজারের ডেটা সংরক্ষণের জন্য টেম্পোরারি ডিকশনারি
user_data = {}

# প্র্যাঙ্ক আইডি ও টাইটেলের লিস্ট
PRANK_OPTIONS = [
    {"id": "8810", "title": "📱 আপনি আমার গার্লফ্রেন্ডকে কল করেন কেন?"},
    {"id": "8805", "title": "💨 গাজার মতো দুর্গন্ধ!"},
    {"id": "8808", "title": "📶 আপনি আমার ওয়াই-ফাই চুরি করছেন!"},
    {"id": "8809", "title": "🤔 আপনি কেন আমাকে কল করেন?"},
    {"id": "8803", "title": "🍕 পিজ্জা ডেলিভারি"},
    {"id": "8804", "title": "🚕 আপনার ট্যাক্সি আপনার জন্য অপেক্ষা করছে"},
    {"id": "8806", "title": "🔊 আপনার কামরার হৈচৈ আওয়াজ"},
    {"id": "8807", "title": "🐕 আপনার কুকুরটি খুবই ক্লান্তিকর!"}
]

# --- সেশন তৈরি করা (রিট্রাই মেকানিজম সহ) ---
def create_session():
    """রিট্রাই মেকানিজম সহ HTTP সেশন তৈরি করে"""
    session = requests.Session()
    retry = Retry(
        total=3,
        read=3,
        connect=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# সেশন তৈরি
session = create_session()

# --- হেল্পার ফাংশন ---
def is_valid_bangladesh_number(number):
    """বাংলাদেশের মোবাইল নম্বর ফরম্যাট চেক করে"""
    pattern = r'^01[3-9]\d{8}$'
    return re.match(pattern, number) is not None

def send_prank_call(phone_number, prank_id):
    """API-তে রিকোয়েস্ট পাঠিয়ে প্র্যাঙ্ক কল ট্রিগার করে"""
    params = {
        'number': phone_number,
        'prank': prank_id
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Connection': 'keep-alive'
    }
    
    try:
        response = session.get(
            API_URL, 
            params=params, 
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        
        if response.text.strip():
            return response.json()
        else:
            return {'success': False, 'error': 'API থেকে খালি রেসপন্স পাওয়া গেছে'}
            
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'API সার্ভার সময়সীমা অতিক্রম করেছে'}
    except requests.exceptions.ConnectionError:
        return {'success': False, 'error': 'API সার্ভারের সাথে সংযোগ স্থাপন করা যায়নি'}
    except requests.exceptions.HTTPError as e:
        return {'success': False, 'error': f'HTTP এরর: {str(e)}'}
    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': f'নেটওয়ার্ক সমস্যা: {str(e)}'}
    except json.JSONDecodeError:
        return {'success': False, 'error': 'API থেকে ভুল ফরম্যাটের রেসপন্স'}

def test_api_connection():
    """API সংযোগ পরীক্ষা করার ফাংশন"""
    try:
        response = session.get(API_URL, timeout=10)
        return response.status_code == 200
    except:
        return False

# --- বোতাম তৈরি ---
def get_main_keyboard():
    """মূল মেনুর জন্য ইনলাইন কীবোর্ড তৈরি করে"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    btn_prank = InlineKeyboardButton("📞 নতুন প্র্যাঙ্ক কল", callback_data="new_prank")
    btn_test = InlineKeyboardButton("🔍 API সংযোগ পরীক্ষা", callback_data="test_api")
    btn_help = InlineKeyboardButton("❓ সাহায্য", callback_data="help")
    btn_about = InlineKeyboardButton("ℹ️ সম্পর্কে", callback_data="about")
    keyboard.add(btn_prank, btn_test, btn_help, btn_about)
    return keyboard

def get_prank_selection_keyboard():
    """প্র্যাঙ্ক আইডি সিলেক্ট করার জন্য কীবোর্ড"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    for prank in PRANK_OPTIONS:
        button = InlineKeyboardButton(
            prank['title'], 
            callback_data=f"prank_{prank['id']}"
        )
        keyboard.add(button)
    
    keyboard.add(InlineKeyboardButton("🔙 পেছনে", callback_data="back_to_menu"))
    return keyboard

# --- বট কমান্ড ও কলব্যাক হ্যান্ডলার ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """স্বাগতম বার্তা"""
    api_status = "🟢 সংযুক্ত" if test_api_connection() else "🔴 সংযোগ নেই"
    
    welcome_text = (
        f"👋 স্বাগতম! এই বটটি ব্যবহার করে আপনি সহজেই প্র্যাঙ্ক কল পাঠাতে পারবেন।\n\n"
        f"📡 API স্ট্যাটাস: {api_status}\n\n"
        f"📌 নিচের বোতামে ক্লিক করুন এবং নির্দেশনা অনুসরণ করুন।"
    )
    bot.reply_to(message, welcome_text, reply_markup=get_main_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """সব ইনলাইন বোতামের ক্লিক হ্যান্ডেল করে"""
    user_id = call.from_user.id
    data = call.data

    if data == "new_prank":
        bot.answer_callback_query(call.id, "📱 এখন আপনার ফোন নম্বর পাঠান")
        bot.send_message(
            call.message.chat.id, 
            "📱 দয়া করে আপনার 11 ডিজিটের মোবাইল নম্বরটি পাঠান (যেমন: 018XXXXXXXX):\n\n"
            "⚠️ শুধুমাত্র বাংলাদেশি নম্বর গ্রহণযোগ্য।"
        )
        user_data[user_id] = {'state': 'awaiting_number'}

    elif data == "test_api":
        bot.answer_callback_query(call.id, "⏳ API সংযোগ পরীক্ষা করা হচ্ছে...")
        status = test_api_connection()
        if status:
            bot.send_message(
                call.message.chat.id,
                "✅ API সার্ভার সংযুক্ত আছে!\n\n"
                "এখন আপনি প্র্যাঙ্ক কল পাঠাতে পারেন।"
            )
        else:
            bot.send_message(
                call.message.chat.id,
                "❌ API সার্ভারে সংযোগ করা যাচ্ছে না!\n\n"
                "সম্ভাব্য কারণ:\n"
                "• ইন্টারনেট সংযোগ চেক করুন\n"
                "• API সার্ভার ডাউন থাকতে পারে\n"
                "• কিছুক্ষণ পর আবার চেষ্টা করুন"
            )
        bot.answer_callback_query(call.id)

    elif data == "help":
        help_text = (
            "📖 *কীভাবে ব্যবহার করবেন:*\n\n"
            "1. '📞 নতুন প্র্যাঙ্ক কল' বোতামে ক্লিক করুন\n"
            "2. আপনার 11 ডিজিটের মোবাইল নম্বর পাঠান\n"
            "3. উপলব্ধ প্র্যাঙ্ক টাইটেল থেকে একটি সিলেক্ট করুন\n"
            "4. বট স্বয়ংক্রিয়ভাবে কল পাঠিয়ে দেবে\n\n"
            "⚠️ *সতর্কতা:* শুধুমাত্র বিনোদনের জন্য ব্যবহার করুন\n"
            "📞 কোনো সমস্যায় যোগাযোগ করুন: @nobxvau"
        )
        bot.send_message(call.message.chat.id, help_text, parse_mode='Markdown')
        bot.answer_callback_query(call.id)

    elif data == "about":
        about_text = (
            "🤖 *প্র্যাঙ্ক কল বট*\n\n"
            "এটি একটি মজার প্র্যাঙ্ক কল বট যা 'NHB Prank' API ব্যবহার করে।\n\n"
            "📌 *উপলব্ধ প্র্যাঙ্ক টাইটেল:*\n" +
            "\n".join([f"• {p['title']}" for p in PRANK_OPTIONS]) +
            "\n\n👤 তৈরি করেছেন: @nobxvau\n"
            "🔗 API: https://nhbdprank.ct.ws/api.php"
        )
        bot.send_message(call.message.chat.id, about_text, parse_mode='Markdown')
        bot.answer_callback_query(call.id)

    elif data == "back_to_menu":
        bot.edit_message_text(
            "👋 মূল মেনুতে ফিরে এসেছেন।",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=get_main_keyboard()
        )
        bot.answer_callback_query(call.id)

    elif data.startswith("prank_"):
        prank_id = data.split("_")[1]
        user_id = call.from_user.id
        prank_title = next((p['title'] for p in PRANK_OPTIONS if p['id'] == prank_id), f"ID: {prank_id}")

        if user_id in user_data and 'number' in user_data[user_id]:
            phone_number = user_data[user_id]['number']
            
            bot.answer_callback_query(call.id, "⏳ প্র্যাঙ্ক কল পাঠানো হচ্ছে...")
            
            processing_msg = bot.send_message(
                call.message.chat.id, 
                f"⏳ *'{prank_title}'* টাইটেল দিয়ে {phone_number} নম্বরে কল পাঠানো হচ্ছে...\n\n"
                f"🔄 দয়া করে অপেক্ষা করুন (সর্বোচ্চ ৩০ সেকেন্ড)",
                parse_mode='Markdown'
            )

            result = send_prank_call(phone_number, prank_id)

            bot.delete_message(call.message.chat.id, processing_msg.message_id)

            if result.get('success'):
                response_msg = (
                    f"✅ *প্র্যাঙ্ক কল সফলভাবে পাঠানো হয়েছে!*\n\n"
                    f"📞 টার্গেট: {result.get('data', {}).get('target', phone_number)}\n"
                    f"🎭 প্র্যাঙ্ক: {prank_title}\n"
                    f"🆔 আইডি: {result.get('data', {}).get('prank_id', prank_id)}\n"
                    f"⚙️ টাস্ক: `{result.get('data', {}).get('task_id', 'N/A')}`\n"
                    f"💳 ক্রেডিট: {result.get('data', {}).get('credit_used', 1)}\n"
                    f"👤 মালিক: {result.get('owner', 'N/A')}"
                )
                bot.send_message(call.message.chat.id, response_msg, parse_mode='Markdown')
            else:
                error_msg = result.get('error', 'অজানা ত্রুটি ঘটেছে।')
                error_response = (
                    f"❌ *প্র্যাঙ্ক কল ব্যর্থ হয়েছে!*\n\n"
                    f"🔴 কারণ: {error_msg}\n\n"
                    f"💡 *সমাধান:*\n"
                    f"• '🔍 API সংযোগ পরীক্ষা' বোতাম ব্যবহার করুন\n"
                    f"• কিছুক্ষণ পর আবার চেষ্টা করুন"
                )
                bot.send_message(call.message.chat.id, error_response, parse_mode='Markdown')

            if user_id in user_data:
                del user_data[user_id]
        else:
            bot.send_message(
                call.message.chat.id, 
                "⚠️ আগে একটি বৈধ নম্বর দিন। /start দিয়ে আবার চেষ্টা করুন।"
            )

        bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """ইউজারের পাঠানো সাধারণ মেসেজ হ্যান্ডেল করে"""
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id in user_data and user_data[user_id].get('state') == 'awaiting_number':
        if is_valid_bangladesh_number(text):
            user_data[user_id]['number'] = text
            user_data[user_id]['state'] = 'awaiting_prank'
            
            prank_list_text = "✅ নম্বর গ্রহণ করা হয়েছে। এখন আপনার পছন্দের প্র্যাঙ্ক টাইটেল সিলেক্ট করুন:\n\n"
            bot.reply_to(
                message,
                prank_list_text,
                reply_markup=get_prank_selection_keyboard()
            )
        else:
            bot.reply_to(
                message,
                "❌ নম্বরটি বৈধ নয়। দয়া করে একটি সঠিক 11 ডিজিটের বাংলাদেশি মোবাইল নম্বর দিন (যেমন: 018XXXXXXXX)।"
            )
    else:
        bot.reply_to(
            message,
            "👋 সহায়তার জন্য /start বা /help কমান্ড ব্যবহার করুন।",
            reply_markup=get_main_keyboard()
        )

# --- বট চালু করুন ---
if __name__ == "__main__":
    print("🤖 প্র্যাঙ্ক কল বট চালু হচ্ছে...")
    print(f"📋 মোট {len(PRANK_OPTIONS)} টি প্র্যাঙ্ক টাইটেল লোড করা হয়েছে.")
    
    # টোকেন চেক
    if BOT_TOKEN == 'YOUR_BOT_API_TOKEN_HERE':
        print("⚠️ সতর্কতা: আপনি বট টোকেন পরিবর্তন করেননি! দয়া করে আপনার টোকেন দিন।")
    
    if test_api_connection():
        print("✅ API সার্ভার সংযুক্ত আছে!")
    else:
        print("⚠️ API সার্ভারে সংযোগ করা যাচ্ছে না!")
    
    print("🚀 বট রানিং...")
    bot.infinity_polling()
