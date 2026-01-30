# Test do Monkey Patch
import asyncio
import logging
from telegram import Bot

# ==================== EMOJI FIX BY ENZITO 🚀 ====================
EMOJI_MAP = {
    "[ROCKET]": "🚀", "[PACOTE]": "📦"
}

def replace_tags(text: str) -> str:
    if not isinstance(text, str): return text
    for tag, emoji in EMOJI_MAP.items():
        text = text.replace(tag, emoji)
    return text

# Mocks
class MockBot:
    async def send_message(self, chat_id, text, *args, **kwargs):
        print(f"ORIGINAL send_message called with: {text}")
        return text

# Apply Patch
_original_send_message = MockBot.send_message

async def _patched_send_message(self, chat_id, text, *args, **kwargs):
    print("PATCHED send_message CALLED!")
    try:
        # Handle positional vs keyword 'text'
        if kwargs.get('text'): kwargs['text'] = replace_tags(kwargs['text'])
        else: text = replace_tags(text)
    except Exception as e:
        print(f"Error in patch: {e}")
    return await _original_send_message(self, chat_id, text, *args, **kwargs)

MockBot.send_message = _patched_send_message
# ================================================================

async def main():
    bot = MockBot()
    print("--- Test 1: Positional argument ---")
    await bot.send_message(123, "[ROCKET] Decolando!")
    
    print("\n--- Test 2: Keyword argument ---")
    await bot.send_message(123, text="[PACOTE] Chegou!")

if __name__ == "__main__":
    asyncio.run(main())
