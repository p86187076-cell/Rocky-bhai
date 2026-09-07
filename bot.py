import logging
import requests
import json
import threading
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import os

# Configuration
BOT_TOKEN = "8806980379:AAHQ8FFAMYWF5fS6ELxEMt39VH_rdBDHeHs"
CHAT_ID = "8063643675"
API_URL = "https://ansh-apis.is-dev.org/api/creta"

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store user sessions
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when /start is issued."""
    user = update.effective_user
    welcome_message = (
        f"👋 Hello {user.first_name}!\n\n"
        "I can fetch data from the Creta API.\n"
        "Use /fetch followed by a number to get data.\n\n"
        "Example: /fetch 12345\n\n"
        "Or use the buttons below:"
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 Fetch Data", callback_data="fetch")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")],
        [InlineKeyboardButton("📊 My Stats", callback_data="stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message."""
    help_text = (
        "ℹ️ **Help**\n\n"
        "**Commands:**\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/fetch [number] - Fetch data from API\n"
        "/stats - Show bot statistics\n"
        "/test - Test API connection\n\n"
        "**How to use:**\n"
        "1. Send /fetch followed by a number\n"
        "2. Or use the inline buttons\n\n"
        "**Example:**\n"
        "/fetch 12345"
    )
    await update.message.reply_text(help_text)

async def fetch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch data from API with the provided number."""
    user_id = update.effective_user.id
    
    # Check if number is provided
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a number!\n"
            "Example: /fetch 12345"
        )
        return
    
    number = context.args[0]
    
    # Validate number (simple check)
    if not number.isdigit():
        await update.message.reply_text(
            "❌ Please provide a valid number (digits only)!"
        )
        return
    
    # Send initial message
    status_message = await update.message.reply_text(
        f"⏳ Fetching data for number: {number}..."
    )
    
    # Fetch data from API
    try:
        result = await fetch_from_api(number)
        
        if result.get("success"):
            # Format and send the data
            data = result.get("data", {})
            await status_message.edit_text(
                format_api_response(data, number)
            )
            # Log successful fetch
            log_fetch(user_id, number, success=True)
        else:
            error_msg = result.get("error", "Unknown error")
            await status_message.edit_text(
                f"❌ Failed to fetch data:\n{error_msg}"
            )
            log_fetch(user_id, number, success=False, error=error_msg)
            
    except Exception as e:
        logger.error(f"Error in fetch_command: {e}")
        await status_message.edit_text(
            f"❌ An error occurred:\n{str(e)}"
        )

async def fetch_from_api(number: str) -> dict:
    """Fetch data from the API."""
    try:
        # Build the API URL with parameters
        url = f"{API_URL}?key=ansh&num={number}"
        
        # Add headers if needed
        headers = {
            "User-Agent": "TelegramBot/1.0",
            "Accept": "application/json"
        }
        
        logger.info(f"Fetching URL: {url}")
        
        # Make the request
        response = requests.get(url, headers=headers, timeout=10)
        
        # Log response status
        logger.info(f"Response status: {response.status_code}")
        
        # Check status code
        if response.status_code == 200:
            try:
                data = response.json()
                return {
                    "success": True,
                    "data": data
                }
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Invalid JSON response from API"
                }
        elif response.status_code == 422:
            return {
                "success": False,
                "error": "API Error 422: Unprocessable Entity. The request may be missing required parameters."
            }
        elif response.status_code == 404:
            return {
                "success": False,
                "error": "API not found. Please check the URL."
            }
        elif response.status_code == 403:
            return {
                "success": False,
                "error": "Access denied. Invalid API key."
            }
        else:
            return {
                "success": False,
                "error": f"API Error {response.status_code}: {response.text[:100]}"
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timeout. Please try again later."
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Cannot connect to the API server."
        }
    except Exception as e:
        logger.error(f"API fetch error: {e}")
        return {
            "success": False,
            "error": f"Error: {str(e)}"
        }

def format_api_response(data: dict, number: str) -> str:
    """Format the API response for display."""
    formatted = f"📊 **Data for number: {number}**\n\n"
    
    if isinstance(data, dict):
        # Check if data has specific fields
        if "name" in data:
            formatted += f"👤 Name: {data.get('name', 'N/A')}\n"
        if "phone" in data:
            formatted += f"📱 Phone: {data.get('phone', 'N/A')}\n"
        if "email" in data:
            formatted += f"📧 Email: {data.get('email', 'N/A')}\n"
        if "address" in data:
            formatted += f"📍 Address: {data.get('address', 'N/A')}\n"
        if "status" in data:
            formatted += f"📊 Status: {data.get('status', 'N/A')}\n"
        
        # If there are other fields, display them
        other_fields = []
        for key, value in data.items():
            if key not in ["name", "phone", "email", "address", "status"]:
                other_fields.append(f"🔹 {key}: {value}")
        
        if other_fields:
            formatted += "\n**Additional Data:**\n"
            formatted += "\n".join(other_fields)
        
        return formatted
    else:
        return f"📊 **Data for number: {number}**\n\n```\n{json.dumps(data, indent=2)}\n```"

def log_fetch(user_id: int, number: str, success: bool, error: str = None):
    """Log API fetch attempts."""
    if user_id not in user_sessions:
        user_sessions[user_id] = {"fetches": 0, "success": 0, "errors": 0}
    
    user_sessions[user_id]["fetches"] += 1
    if success:
        user_sessions[user_id]["success"] += 1
    else:
        user_sessions[user_id]["errors"] += 1

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bot statistics."""
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        await update.message.reply_text(
            "📊 You haven't made any API requests yet!\n\n"
            "Try: /fetch 12345"
        )
        return
    
    stats = user_sessions[user_id]
    stats_text = (
        f"📊 **Your Statistics**\n\n"
        f"Total requests: {stats['fetches']}\n"
        f"✅ Successful: {stats['success']}\n"
        f"❌ Failed: {stats['errors']}\n"
        f"📈 Success rate: {calculate_success_rate(stats)}%"
    )
    
    await update.message.reply_text(stats_text)

def calculate_success_rate(stats: dict) -> int:
    """Calculate success rate percentage."""
    if stats["fetches"] == 0:
        return 0
    return int((stats["success"] / stats["fetches"]) * 100)

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test the API connection."""
    await update.message.reply_text("🔍 Testing API connection...")
    
    try:
        # Test with a sample number
        result = await fetch_from_api("12345")
        
        if result.get("success"):
            await update.message.reply_text(
                "✅ API is working!\n\n"
                f"Response: {json.dumps(result.get('data', {}), indent=2)[:500]}"
            )
        else:
            await update.message.reply_text(
                f"❌ API test failed:\n{result.get('error', 'Unknown error')}"
            )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Test failed: {str(e)}"
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "fetch":
        await query.edit_message_text(
            "📝 Please send a number after /fetch command.\n"
            "Example: /fetch 12345"
        )
    elif query.data == "help":
        await query.edit_message_text(
            "ℹ️ **Help**\n\n"
            "Send /fetch followed by a number to get data.\n"
            "Example: /fetch 12345\n\n"
            "You can also use /stats to see your usage statistics."
        )
    elif query.data == "stats":
        # Show stats for the user
        user_id = query.from_user.id
        if user_id not in user_sessions:
            await query.edit_message_text(
                "📊 You haven't made any API requests yet!"
            )
        else:
            stats = user_sessions[user_id]
            stats_text = (
                f"📊 **Your Statistics**\n\n"
                f"Total requests: {stats['fetches']}\n"
                f"✅ Successful: {stats['success']}\n"
                f"❌ Failed: {stats['errors']}\n"
                f"📈 Success rate: {calculate_success_rate(stats)}%"
            )
            await query.edit_message_text(stats_text)

def keep_alive():
    """Keep the bot alive."""
    while True:
        time.sleep(60 * 10)  # Every 10 minutes
        logger.info("🔄 Bot is still running...")

def main():
    """Start the bot."""
    # Validate bot token
    if BOT_TOKEN == "8806980379:AAHQ8FFAMYWF5fS6ELxEMt39VH_rdBDHeHs":
        logger.info("✅ Using provided bot token")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("fetch", fetch_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("test", test_command))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start keep-alive thread
    threading.Thread(target=keep_alive, daemon=True).start()
    
    # Start the bot
    logger.info("🤖 Bot started! Press Ctrl+C to stop.")
    logger.info(f"📱 Bot username: @{application.bot.username if hasattr(application.bot, 'username') else 'unknown'}")
    logger.info(f"🔗 Test your bot: https://t.me/{application.bot.username if hasattr(application.bot, 'username') else 'your_bot'}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()