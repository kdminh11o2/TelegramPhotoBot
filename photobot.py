import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from PIL import Image, ImageOps
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

# Cấu hình
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
LOGO_PATH = 'logo.png'
OUTPUT_SIZE = (1300, 1300)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gửi thông báo khi người dùng bắt đầu"""
    await update.message.reply_text(
        'Xin chào! Gửi cho tôi một bức ảnh và tôi sẽ xử lý nó:\n'
        '1. Crop thành tỉ lệ 1:1\n'
        '2. Điều chỉnh kích thước 1300x1300px\n'
        '3. Đóng logo\n'
        '4. Gửi lại ảnh đã xử lý'
    )

def process_image(photo_path: str) -> str:
    """Xử lý ảnh và trả về đường dẫn file output"""
    # Mở ảnh gốc
    original_img = Image.open(photo_path)
    
    # Crop ảnh thành hình vuông (tỉ lệ 1:1)
    width, height = original_img.size
    size = min(width, height)
    left = (width - size) / 2
    top = (height - size) / 2
    right = (width + size) / 2
    bottom = (height + size) / 2
    cropped_img = original_img.crop((left, top, right, bottom))
    
    # Resize về 1300x1300
    resized_img = cropped_img.resize(OUTPUT_SIZE, Image.LANCZOS)
    
    # Đóng logo (nếu có)
    if os.path.exists(LOGO_PATH):
        logo = Image.open(LOGO_PATH)
        # Đảm bảo logo có cùng kích thước
        logo = logo.resize(OUTPUT_SIZE, Image.LANCZOS)
        # Kết hợp ảnh và logo (giả sử logo có alpha channel)
        final_img = Image.alpha_composite(
            resized_img.convert('RGBA'),
            logo.convert('RGBA')
        )
    else:
        final_img = resized_img
    
    # Lưu ảnh đã xử lý
    output_path = 'processed_' + os.path.basename(photo_path)
    final_img.save(output_path, quality=95)
    
    return output_path

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý khi nhận được ảnh"""
    # Thông báo đang xử lý
    message = await update.message.reply_text('Đang xử lý ảnh...')
    
    # Tải ảnh về
    photo_file = await context.bot.get_file(update.message.photo[-1].file_id)
    input_path = photo_file.file_id + '.jpg'
    await photo_file.download_to_drive(input_path)
    
    try:
        # Xử lý ảnh
        output_path = process_image(input_path)
        
        # Gửi ảnh đã xử lý
        with open(output_path, 'rb') as photo:
            await update.message.reply_photo(photo, caption='Ảnh đã xử lý xong!')
        
        # Xóa file tạm
        os.remove(input_path)
        os.remove(output_path)
        
        # Cập nhật trạng thái
        await context.bot.edit_message_text(
            chat_id=message.chat_id,
            message_id=message.message_id,
            text='Xử lý ảnh hoàn tất!'
        )
    except Exception as e:
        # Báo lỗi nếu có
        await context.bot.edit_message_text(
            chat_id=message.chat_id,
            message_id=message.message_id,
            text=f'Có lỗi xảy ra: {str(e)}'
        )
        if os.path.exists(input_path):
            os.remove(input_path)

def main() -> None:
    """Khởi chạy bot"""
    # Tạo Application
    application = Application.builder().token(TOKEN).build()
    
    # Đăng ký các command và message handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Bắt đầu bot
    print('Bot đang chạy...')
    application.run_polling()

if __name__ == '__main__':
    main()