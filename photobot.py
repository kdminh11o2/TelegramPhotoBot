import os
import logging
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image
import tempfile
import pillow_heif

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def process_image(input_path, logo_path, output_path):
    try:
        logger.info(f"Processing image: input={input_path}, logo={logo_path}, output={output_path}")
        
        if input_path.lower().endswith('.heic'):
            logger.info("Detected HEIC file, converting to RGBA")
            heif_file = pillow_heif.read_heif(input_path)
            img = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data).convert('RGBA')
        else:
            img = Image.open(input_path).convert('RGBA')
        
        img = img.resize((1500, 1500), Image.LANCZOS)
        
        width, height = img.size
        new_size = min(width, height)
        left = (width - new_size) // 2
        top = (height - new_size) // 2
        img = img.crop((left, top, left + new_size, top + new_size))
        
        img = img.resize((1300, 1300), Image.LANCZOS)
        
        logo = Image.open(logo_path).convert('RGBA')
        img.paste(logo, (0, 0), logo)
        
        img = img.convert('RGB')
        
        logger.info(f"Saving output as JPG to {output_path}")
        img.save(output_path, 'JPEG', quality=95)
        return True
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Chào bạn! Tôi là bot xử lý ảnh. Hãy gửi hoặc forward ảnh để tôi xử lý:\n"
        "- Crop tỉ lệ 1:1\n"
        "- Resize thành 1300x1300 pixel\n"
        "- Thêm logo\n"
        "Hỗ trợ mọi định dạng ảnh phổ biến, bao gồm HEIC!"
    )

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    message = update.message
    file = None
    base_name = "photo"
    file_name = "input"

    if message.photo:
        photo = message.photo[-1]
        file = await photo.get_file()
        file_name = "photo.jpg"
    elif message.document and message.document.mime_type and message.document.mime_type.startswith('image/'):
        file = await message.document.get_file()
        file_name = message.document.file_name or "document"
        base_name = os.path.splitext(message.document.file_name)[0] if message.document.file_name else "document"
    elif message.forward_from or message.forward_from_chat:
        if message.media_group_id:
            await message.reply_text("Vui lòng gửi từng ảnh riêng lẻ, không hỗ trợ media group!")
            return
        if message.photo:
            photo = message.photo[-1]
            file = await photo.get_file()
            file_name = "photo.jpg"
        elif message.document and message.document.mime_type and message.document.mime_type.startswith('image/'):
            file = await message.document.get_file()
            file_name = message.document.file_name or "document"
            base_name = os.path.splitext(message.document.file_name)[0] if message.document.file_name else "document"

    if not file:
        await message.reply_text("Vui lòng gửi hoặc forward file ảnh!")
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, file_name)
        output_filename = f"{base_name}_edit.jpg"
        output_path = os.path.join(temp_dir, output_filename)
        
        logger.info(f"Downloading file to {input_path}")
        download_start = time.time()
        await file.download_to_drive(input_path)
        logger.info(f"Download took {time.time() - download_start:.2f} seconds")
        
        logo_path = "logo.png"
        
        process_start = time.time()
        if process_image(input_path, logo_path, output_path):
            logger.info(f"Processing took {time.time() - process_start:.2f} seconds")
            send_start = time.time()
            with open(output_path, 'rb') as output_file:
                await message.reply_document(document=output_file, filename=output_filename)
            logger.info(f"Sending took {time.time() - send_start:.2f} seconds")
            context.user_data['processed'] = True
        else:
            await message.reply_text("Có lỗi khi xử lý ảnh. File có thể không phải định dạng ảnh hợp lệ.")
            context.user_data['processed'] = False
        
        logger.info(f"Total time: {time.time() - start_time:.2f} seconds")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.message and not context.user_data.get('processed', False):
        await update.message.reply_text("Có lỗi xảy ra. Vui lòng thử lại sau!")

def main():
    application = Application.builder().token("7686014862:AAG9ML33YBkjkbDNc0ZbYE8I0SW6OQxV4ag").read_timeout(60).write_timeout(60).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_media))
    
    application.add_error_handler(error_handler)
    
    application.run_polling()

if __name__ == '__main__':
    main()
