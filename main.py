import asyncio
import os
import re
import requests
import time
from urllib.parse import quote
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from groq import Groq
import edge_tts

BOT_TOKEN = "8899500242:AAEeCZ7eRV8vLvm4CWuNoMoEIXQblSe5Qv0"
GROQ_API_KEY = "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"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)

def generate_script(user_prompt):
    prompt_instruction = f"""
    You are a professional YouTube scriptwriter for American channels (like What If style).
    Write a detailed, fast-paced video script in English on the topic: '{user_prompt}'.
    Make sure the script is engaging, informative, and has a clear beginning, middle, and end.
    """

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt_instruction}]
    )
    return response.choices[0].message.content

def clean_text_for_speech(text):
    text = re.sub(r'[\*\_~`#]', '', text)
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text, flags=re.UNICODE)
    return text.strip()

async def async_text_to_speech(text, filename="script_audio.mp3"):
    VOICE_NAME = "en-US-GuyNeural"
    communicate = edge_tts.Communicate(text, VOICE_NAME)
    await communicate.save(filename)
    return filename

# Bir dona rasmni yuklab olish funksiyasi
def download_single_image(prompt_text, idx):
    clean_p = re.sub(r'[\*\_~`#"]', '', prompt_text)
    final_prompt = f"{clean_p[:150]}, cinematic, highly detailed, 8k"
    encoded_prompt = quote(final_prompt)
    
    img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=576&nologo=true"
    
    for attempt in range(1, 4):
        try:
            print(f"🖼 Rasm {idx} yuklanmoqda... (Urinish: {attempt})")
            res = requests.get(img_url, timeout=60)
            if res.status_code == 200:
                filename = f"image_{idx}.jpg"
                with open(filename, 'wb') as f:
                    f.write(res.content)
                return filename
        except Exception as e:
            print(f"⚠️ Rasm {idx} xatosi: {e}")
            time.sleep(2)
            
    return None

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "Menga videoyingiz mavzusini yozib yuboring, men sizga:\n"
        "1. 📜 Ssenariy\n"
        "2. 🎙 Ovoz (Voiceover)\n"
        "3. 🎨 **20 ta tayyor HD rasm**ni birma-bir yuboraman!"
    )

@dp.message(F.text)
async def generate_content(message: types.Message):
    user_topic = message.text
    status_msg = await message.answer("⏳ *1/3: Ssenariy yozilmoqda...*")

    try:
        loop = asyncio.get_event_loop()
        
        # 1. Ssenariy yaratish
        script_text = await loop.run_in_executor(None, generate_script, user_topic)

        if len(script_text) > 4000:
            for i in range(0, len(script_text), 4000):
                await message.answer(script_text[i:i+4000])
        else:
            await message.answer(script_text)

        # 2. Ovoz yaratish
        await status_msg.edit_text("🎙 *2/3: Audio ovoz yozilmoqda...*")
        cleaned_text = clean_text_for_speech(script_text)
        audio_file = await async_text_to_speech(cleaned_text)

        voice_input = FSInputFile(audio_file)
        await message.answer_voice(voice_input, caption="🎧 YouTube uchun tayyor ovozli xabar!")
        
        if os.path.exists(audio_file):
            os.remove(audio_file)

        # 3. 20 ta rasmni birma-bir yaratib va yuborish
        await status_msg.edit_text("🎨 *3/3: 20 ta rasm birma-bir chizilib yuborilmoqda...*")

        sentences = [s.strip() for s in re.split(r'\. |\? |! |\n', script_text) if len(s.strip()) > 15]
        
        # 20 ta qismga bo'lamiz
        step = max(1, len(sentences) // 20)
        prompts = [sentences[i] for i in range(0, len(sentences), step)][:20]

        # Agar jumlalar yetmasa 20 taga to'ldiramiz
        while len(prompts) < 20:
            prompts.append(f"{user_topic} cinematic visual scene {len(prompts)+1}")

        for idx, prompt in enumerate(prompts, start=1):
            img_file = await loop.run_in_executor(None, download_single_image, prompt, idx)
            if img_file and os.path.exists(img_file):
                photo_input = FSInputFile(img_file)
                await message.answer_photo(photo_input, caption=f"🖼 Rasm {idx}/20")
                os.remove(img_file)
            else:
                await message.answer(f"⚠️ Rasm {idx}/20 server javob bermagani uchun o'tkazib yuborildi.")

        await status_msg.delete()

    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")

async def main():
    print("🚀 Bot ishga tushdi va tayyor!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
