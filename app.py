import os
import asyncio
import tempfile
import base64
import traceback
from flask import Flask, render_template, request, jsonify
import edge_tts

app = Flask(__name__)

# دونوں زبانوں کی 5+5 بالکل الگ اور مستقل نیورل آوازیں
VOICE_MAPPING = {
    # English Voices
    "en_voice_1": "en-US-AvaNeural",
    "en_voice_2": "en-US-AndrewNeural",
    "en_voice_3": "en-GB-SoniaNeural",
    "en_voice_4": "en-GB-RyanNeural",
    "en_voice_5": "en-AU-NatashaNeural",

    # Urdu Voices
    "ur_voice_1": "ur-PK-UzmaNeural",
    "ur_voice_2": "ur-PK-AsadNeural",
    "ur_voice_3": "ur-IN-GulNeural",
    "ur_voice_4": "ur-IN-SalmanNeural",
    "ur_voice_5": "ur-PK-UzmaNeural"  # اسپیڈ ویریئنٹ کے ساتھ چلائی جائے گی
}


async def generate_voice_file(text, voice_name, filepath, is_news=False):
    rate = "+10%" if is_news else "+0%"
    communicate = edge_tts.Communicate(text, voice_name, rate=rate)
    await communicate.save(filepath)


def run_async(coro):
    """
    Always create a brand-new event loop for this call and tear it down
    afterwards. This is the safe pattern for serverless platforms
    (Vercel/Lambda) where reusing get_event_loop() across invocations
    can hand back a closed/stale loop from a previous frozen container.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    temp_path = None
    try:
        data = request.get_json(silent=True) or {}
        text = (data.get('text') or '').strip()
        voice_id = (data.get('voice_id') or '').strip()

        if not text:
            return jsonify({"success": False, "error": "متن یا ٹیکسٹ لکھنا لازمی ہے"}), 400

        if voice_id not in VOICE_MAPPING:
            voice_id = "en_voice_1"

        edge_voice = VOICE_MAPPING[voice_id]
        is_news = (voice_id == "ur_voice_5")

        # Force temp file into /tmp explicitly — the only writable dir
        # on Vercel's serverless filesystem.
        tmp_dir = "/tmp" if os.path.isdir("/tmp") else tempfile.gettempdir()
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir=tmp_dir) as temp_file:
            temp_path = temp_file.name

        # Generate the audio file
        run_async(generate_voice_file(text, edge_voice, temp_path, is_news))

        if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            raise RuntimeError("Audio file was not generated (empty or missing). "
                                "This usually means the TTS engine could not reach "
                                "Microsoft's speech servers from this environment.")

        with open(temp_path, 'rb') as f:
            audio_bytes = f.read()
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        return jsonify({
            "success": True,
            "audio_base64": f"data:audio/mp3;base64,{audio_base64}",
            "verified_voice_id": voice_id
        })

    except Exception as e:
        tb = traceback.format_exc()
        print(tb)  # shows up in Vercel function logs
        return jsonify({
            "success": False,
            "error": f"Server Error: {str(e)}",
        }), 500

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@app.route('/api/debug-tts')
def debug_tts():
    """Temporary diagnostic route — hit this directly in the browser to
    see whether edge_tts can actually reach Microsoft's servers from
    Vercel. Remove this route once things are working."""
    try:
        tmp_dir = "/tmp" if os.path.isdir("/tmp") else tempfile.gettempdir()
        test_path = os.path.join(tmp_dir, "debug_test.mp3")
        run_async(generate_voice_file("This is a test", "en-US-AvaNeural", test_path))
        size = os.path.getsize(test_path)
        os.remove(test_path)
        return jsonify({"ok": True, "size_bytes": size})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "trace": traceback.format_exc()})


# Vercel's Python runtime looks for a WSGI-compatible `app` object
app = app

if __name__ == '__main__':
    app.run(port=5001, debug=False)