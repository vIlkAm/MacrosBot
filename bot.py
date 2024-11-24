import os
import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image
import openai

# Set your environment variables (use Railway or other hosting platforms)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Set OpenAI API Key
openai.api_key = OPENAI_API_KEY

# Desired Image Size for GPT-4 Mini
DESIRED_SIZE = (512, 512)

# Default prompt for analyzing food images
DEFAULT_PROMPT = """
You are an expert in food recognition and macronutrient analysis. Analyze the given image of food and provide the following details:
1. Detected food items.
2. Estimated macronutrients (calories, protein, carbs, and fats) for each item.
3. Ensure the response is concise and formatted as follows:
   Food: [Name of food]
   Calories: [calories] kcal
   Protein: [protein] g
   Carbs: [carbs] g
   Fats: [fats] g
"""

# Initialize SQLite database
DB_FILE = "user_history.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Create a table for user history if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            user_id INTEGER,
            response TEXT
        )
    """)
    conn.commit()
    conn.close()

# Save history to the database
def save_to_history(user_id, response):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO history (user_id, response) VALUES (?, ?)", (user_id, response))
    conn.commit()
    conn.close()

# Retrieve history from the database
def get_history(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT response FROM history WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

# Clear user history from the database
def clear_history_db(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# Handle photo input from Telegram
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id  # Get the user's Telegram ID
    photo = update.message.photo[-1]  # Get the highest resolution image
    file = await photo.get_file()

    # Save the photo locally
    file_path = "photo.jpg"
    await file.download_to_drive(file_path)

    # Resize the photo for efficiency and cost management
    resized_path = "resized_photo.jpg"
    with Image.open(file_path) as img:
        img = img.convert("RGB")  # Ensure the image is in RGB format
        img = img.resize(DESIRED_SIZE, Image.ANTIALIAS)  # Resize to 512x512
        img.save(resized_path)

    # Send the resized image to GPT-4.0 Mini for analysis
    try:
        with open(resized_path, "rb") as image_file:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",  # Use GPT-4.0 Mini
                messages=[
                    {"role": "system", "content": "You are an AI that processes images and provides detailed analyses."},
                    {"role": "user", "content": DEFAULT_PROMPT},
                ],
                files={"image": image_file},
            )

        # Extract GPT-4's response
        gpt_output = response["choices"][0]["message"]["content"]

        # Save the response to the database
        save_to_history(user_id, gpt_output)

        # Send the response back to the user
        await update.message.reply_text(f"Here's what I found:\n{gpt_output}")

    except Exception as e:
        # Handle errors gracefully
        await update.message.reply_text("Sorry, I couldn't process the image. Please try again later.")
        print(f"Error: {e}")

# Command to view history
async def view_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id  # Get the user's Telegram ID

    # Retrieve history from the database
    history = get_history(user_id)
    if history:
        formatted_history = "\n\n".join([f"Entry {i+1}:\n{entry}" for i, entry in enumerate(history)])
        await update.message.reply_text(f"Your history:\n\n{formatted_history}")
    else:
        await update.message.reply_text("You don't have any history yet. Send me a food image to start tracking!")

# Command to clear history
async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id  # Get the user's Telegram ID

    # Clear the user's history in the database
    clear_history_db(user_id)
    await update.message.reply_text("Your history has been cleared!")

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Send me a photo of your food, and I'll analyze it for macros! You can also use these commands:\n"
        "/history - View your food analysis history\n"
        "/clear - Clear your history"
    )

# Main function to run the bot
def main():
    # Initialize the database
    init_db()

    # Initialize the bot application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("history", view_history))
    application.add_handler(CommandHandler("clear", clear_history))

    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()

