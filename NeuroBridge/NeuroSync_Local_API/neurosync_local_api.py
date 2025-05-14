# This software is licensed under a **dual-license model**
# For individuals and businesses earning **under $1M per year**, this software is licensed under the **MIT License**
# Businesses or organizations with **annual revenue of $1,000,000 or more** must obtain permission to use this software commercially.

import torch
import os
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS

# Assuming your model and utilities are structured as shown
from utils.model.model import load_model
from utils.generate_face_shapes import generate_facial_data_from_bytes
from utils.config import config as config_data

app = Flask(__name__)
CORS(app)

# Load configuration and model
config = config_data
# Force CPU usage
# device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
device = torch.device('cpu')
blendshape_model = load_model(config["model_path"], config, device)

print(f" * Using device: {device}")  # Log the device being used

@app.route('/audio_to_blendshapes', methods=['POST'])
def audio_to_blendshapes_route():
    # if 'audio' not in request.files:
    #     return jsonify({"error": "No audio file part"}), 400
    # audio_bytes = request.files['audio'].read()
    audio_bytes = request.data # Use request.data again
    generated_facial_data = generate_facial_data_from_bytes(audio_bytes, blendshape_model, device, config)
    generated_facial_data_list = generated_facial_data.tolist() if isinstance(generated_facial_data, np.ndarray) else generated_facial_data
    return jsonify({'blendshapes': generated_facial_data_list})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
