import os
import uuid
import asyncio
from flask import Flask, render_template, request, jsonify, send_file
import edge_tts

app = Flask(__name__)

AUDIO_DIR = os.path.join('static', 'audio')
os.makedirs(AUDIO_DIR, exist_ok=True)

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    try:
        data = request.get_json() or {}
        text = data.get('text', '').strip()
        voice_id = data.get('voice_id', '').strip()
        
        if not text:
            return jsonify({"error": "متن یا ٹیکسٹ لکھنا لازمی ہے"}), 400
            
        if voice_id not in VOICE_MAPPING:
            voice_id = "en_voice_1"
            
        edge_voice = VOICE_MAPPING[voice_id]
        is_news = (voice_id == "ur_voice_5")
        
        # پرانی فائلیں ڈیلیٹ کریں
        for f in os.listdir(AUDIO_DIR):
            try:
                os.remove(os.path.join(AUDIO_DIR, f))
            except Exception:
                pass

        filename = f"{voice_id}_{uuid.uuid4().hex}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)
        
        # آڈیو فائل جنریٹ کریں
        asyncio.run(generate_voice_file(text, edge_voice, filepath, is_news))
        
        return jsonify({
            "success": True,
            "audio_url": f"/static/audio/{filename}",
            "filename": filename,
            "verified_voice_id": voice_id
        })
        
    except Exception as e:
        return jsonify({"error": f"Server Error: {str(e)}"}), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_audio(filename):
    filepath = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name="synthesized_speech.mp3")
    return jsonify({"error": "Audio file not found"}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)