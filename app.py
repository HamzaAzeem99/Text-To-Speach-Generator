import os
import asyncio
import tempfile
import base64
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
        
        # Create a temporary file to save the audio
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # آڈیو فائل جنریٹ کریں
            asyncio.run(generate_voice_file(text, edge_voice, temp_path, is_news))
            
            # Read and encode the file to Base64
            with open(temp_path, 'rb') as f:
                audio_bytes = f.read()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        finally:
            # Clean up the temporary file immediately
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
        
        return jsonify({
            "success": True,
            "audio_base64": f"data:audio/mp3;base64,{audio_base64}",
            "verified_voice_id": voice_id
        })
        
    except Exception as e:
        return jsonify({"error": f"Server Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(port=5001)
app = app    