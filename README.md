Telegram Ferma Bot - tez boshlash
================================

Qisqacha: Bu kichik Telegram bot foydalanuvchini onboarding orqali fermani va hayvonlarni qo'shish, eslatma yaratish, ro'yxatni ko'rish va o'chirish imkonini beradi. Maqsad — MVP, keyin AI/LLM va RAG integratsiya qo'shiladi.

Talablar:
- Python 3.10+
- Bot token (BotFather orqali oling). Avval chatdagi oshkor bo'lgan tokenni bekor qiling va yangisini yarating.

Ishga tushirish:
1. Repo fayllarini saqlang.
2. .env fayl yarating va TELEGRAM_TOKEN ni qo'ying.
3. Virtualenv yaratib kutubxonalarni o'rnating:
   - python -m venv venv
   - source venv/bin/activate  (Windows: venv\\Scripts\\activate)
   - pip install -r requirements.txt
4. Botni ishga tushiring:
   - python bot.py
5. Telegramda botni topib /start bilan onboardingni boshlang.

Eslatma va xavfsizlik:
- Agar token chatda oshkor bo'lsa, BotFather orqali tokenni qayta tiklang (regen) va eski tokenni bekor qiling.
- .env faylni gitga push qilmang. Ishlatilsa .gitignore ga qo'shing.

Keyingi qadamlar (tavsiya):
- Reminder uchun takroriy qoidalar (repeat) qo'shish.
- User-friendly reminder yaratish (conversation, inline calendar).
- AI (OpenAI/HF) integratsiyasi: maslahatlar va RAG.
- Web dashboard yoki veb-form integratsiyasi.
