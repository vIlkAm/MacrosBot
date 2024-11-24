import os
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from PIL import Image
import openai

# Telegram Bot Token and OpenAI API Key (from Railway environment variables)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Set OpenAI API Key
openai.api_key = OPENAI_API_KEY

# Desired Image Size
DESIRED_SIZE = (512, 512)

# Function to handle photos sent to the bot
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get the photo file from the message
    photo = update.message.photo[-1]  # Get the highest resolution photo
    file = await photo.get_file()

    # Download the photo locally
    file_path = "photo.jpg"
    await file.download_to_drive(file_path)

    # Resize the photo to reduce API load
    resized_path = "resized_photo.jpg"
    with Image.open(file_path) as img:
        img = img.convert("RGB")  # Ensure it's in RGB format
        img = img.resize(DESIRED_SIZE, Image.ANTIALIAS)  # Resize with smoothing
        img.save(resized_path)

    # Send the resized photo to ChatGPT API
    try:
        # Open the image file
        with open(resized_path, "rb") as image_file:
            response = openai.Image.create_variation(
                image=image_file,
                prompt="Analyze this food image and provide its name along with macros (calories, protein, carbs, fats).",
                n=1,
                size="512x512"
            )

        # Parse GPT's response (replace this with how you interpret the response format)
        gpt_output = response["choices"][0]["message"]["content"]

        # Reply to the user with GPT's response
        await update.message.reply_text(f"Here's what I found:\n{gpt_output}")

    except Exception as e:
        # Handle API errors
        await update.message.reply_text("Sorry, I couldn't process the image. Please try again later.")
        print(f"Error: {e}")

# Command to start the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Send me a food image, and I'll analyze it for you!")

# Main function to run the bot
def main():
    # Create the bot application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.COMMAND & filters.regex("/start"), start))

    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()

