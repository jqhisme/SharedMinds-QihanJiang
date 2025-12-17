import os
import time
import torch
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS

from univtg.run_on_video import clip, vid2clip, txt2clip
from univtg.utils.basic_utils import l2_normalize_np_array
from univtg.main.config import TestOptions, setup_model
import torch.backends.cudnn as cudnn
import logging
import sys

EMB_DIR = "./embeddings"

# check the ./univtg/ckpts directory
# if model_raw.ckpt exist use it
# otherwise use the first ckpt found
# if no ckpt found, raise error

MODEL_CKPT = None
ckpt_dir = "./univtg/ckpts"
if os.path.exists(ckpt_dir):
    ckpt_files = [f for f in os.listdir(ckpt_dir) if f.endswith('.ckpt')]
    if "model_raw.ckpt" in ckpt_files:
        MODEL_CKPT = os.path.join(ckpt_dir, "model_raw.ckpt")
    elif len(ckpt_files) > 0:
        MODEL_CKPT = os.path.join(ckpt_dir, ckpt_files[0])
if MODEL_CKPT is None:
    raise FileNotFoundError(f"No checkpoint found in {ckpt_dir}")
GPU_ID = 0
VIDEO_DIR = "./footages"

os.environ["CUDA_VISIBLE_DEVICES"] = str(GPU_ID)

model_version = "ViT-B/32"
clip_len = 2

clip_model, _ = clip.load(model_version, device=GPU_ID, jit=False)


def load_vtg_model(
    resume_path=MODEL_CKPT,
    save_dir=EMB_DIR,
    gpu_id=0
):
    """
    Safe loader for VTG inside a Jupyter notebook.
    Avoids argparse picking up Jupyter kernel arguments.
    """
    
    # ---- 1. Backup sys.argv to avoid argparse conflicts ----
    argv_backup = sys.argv.copy()
    
    # ---- 2. Replace sys.argv so parser gets a clean list ----
    sys.argv = [
        "notebook",
        "--resume", resume_path,
        #"--save_dir", save_dir,
        "--gpu_id", str(gpu_id)
    ]

    # ---- 3. Parse options ----
    opt = TestOptions().parse()

    # ---- Restore sys.argv back so Jupyter works normally ----
    sys.argv = argv_backup

    # ---- 4. Setup model ----
    cudnn.benchmark = True
    cudnn.deterministic = False

    # LR warmup setup (copied from your code)
    if opt.lr_warmup > 0:
        total_steps = opt.n_epoch
        warmup_steps = (
            opt.lr_warmup if opt.lr_warmup > 1 
            else int(opt.lr_warmup * total_steps)
        )
        opt.lr_warmup = [warmup_steps, total_steps]

    # ---- 5. Build model ----
    model, criterion, _, _ = setup_model(opt)

    return model, opt

def convert_to_hms(seconds):
    return time.strftime('%H:%M:%S', time.gmtime(seconds))

def load_data(save_dir):
    vid = np.load(os.path.join(save_dir, 'vid.npz'))['features'].astype(np.float32)
    txt = np.load(os.path.join(save_dir, 'txt.npz'))['features'].astype(np.float32)

    vid = torch.from_numpy(l2_normalize_np_array(vid))
    txt = torch.from_numpy(l2_normalize_np_array(txt))

    ctx_len = vid.shape[0]

    timestamp = ((torch.arange(ctx_len) + clip_len/2) / ctx_len).unsqueeze(1).repeat(1, 2)

    # Add temporal extent feature (TEF)
    tef_st = torch.arange(ctx_len) / ctx_len
    tef_ed = tef_st + 1 / ctx_len
    tef = torch.stack([tef_st, tef_ed], dim=1)

    vid = torch.cat([vid, tef], dim=1)

    src_vid = vid.unsqueeze(0).cuda()
    src_txt = txt.unsqueeze(0).cuda()
    m_vid  = torch.ones(src_vid.shape[:2]).cuda()
    m_txt  = torch.ones(src_txt.shape[:2]).cuda()

    return src_vid, src_txt, m_vid, m_txt, timestamp, ctx_len

def extract_video(video_path):
    print("Extracting video features...")
    vid2clip(clip_model, video_path,EMB_DIR)
    print("Done.")

def embed_text(query):
    txt2clip(clip_model, query,EMB_DIR)

def forward(model, save_dir, query):
    src_vid, src_txt, m_vid, m_txt, timestamp, ctx_l = load_data(save_dir)
    src_vid = src_vid.cuda(GPU_ID)
    src_txt = src_txt.cuda(GPU_ID)
    m_vid = m_vid.cuda(GPU_ID)
    m_txt = m_txt.cuda(GPU_ID)

    model.eval()
    with torch.no_grad():
        output = model(src_vid=src_vid, src_txt=src_txt, src_vid_mask=m_vid, src_txt_mask=m_txt)
    
    # prepare the model prediction
    pred_logits = output['pred_logits'][0].cpu()
    pred_spans = output['pred_spans'][0].cpu()
    pred_saliency = output['saliency_scores'].cpu()

    # prepare the model prediction
    pred_windows = (pred_spans + timestamp) * ctx_l * clip_len
    pred_confidence = pred_logits
    
    # grounding - get top-1 interval
    top1_idx = torch.argmax(pred_confidence)
    top1_window = pred_windows[top1_idx].tolist()
    top1_interval = " - ".join([convert_to_hms(int(i)) for i in top1_window])
    
    # highlight - get top-1 highlight
    hl_idx = torch.argmax(pred_saliency)
    hl_time = convert_to_hms(int(hl_idx * clip_len))
    
    return {
        "query": query,
        "interval": top1_interval,
        "highlight": hl_time
    }

if __name__ == "__main__":
    # Initialize models
    clip_model, _ = clip.load(model_version, device=GPU_ID, jit=False)
    vtg_model, vtg_opt = load_vtg_model()
    
    # Create Flask app
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        return response
    
    @app.route('/api/query', methods=['POST'])
    def query_endpoint():
        """
        Endpoint to process text queries on loaded video.
        Expected JSON: {"query": "query1; query2; query3"}
        Returns: [{"query": "...", "interval": "HH:MM:SS - HH:MM:SS", "highlight": "HH:MM:SS"}, ...]
        """
        try:
            data = request.get_json()
            if not data or 'query' not in data:
                return jsonify({"error": "Missing 'query' field in request"}), 400
            
            query_text = data['query']
            
            # Split the query string by semicolons
            queries = [q.strip() for q in query_text.split(';') if q.strip()]
            
            if not queries:
                return jsonify({"error": "No valid queries provided"}), 400
            
            # Process each query and collect results
            results = []
            for query in queries:
                # Embed the text query
                embed_text(query)
                
                # Run inference
                result = forward(vtg_model, EMB_DIR, query)
                results.append(result)
            print(results)
            
            return jsonify(results), 200
        
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/extract-video', methods=['POST'])
    def extract_video_endpoint():
        """
        Endpoint to extract video features from uploaded file.
        Expected: form-data with 'video' file
        Returns: {"status": "success", "message": "Video features extracted"}
        """
        try:
            if 'video' not in request.files:
                return jsonify({"error": "No video file provided"}), 400
            
            video_file = request.files['video']
            if video_file.filename == '':
                return jsonify({"error": "No selected file"}), 400
            
            # Save uploaded video temporarily
            video_path = os.path.join(EMB_DIR, 'temp_video.mp4')
            video_file.save(video_path)
            
            # Extract features
            extract_video(video_path)
            
            return jsonify({"status": "success", "message": "Video features extracted"}), 200
        
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({"status": "ok"}), 200
    
    # Run the Flask server
    print("Starting Flask server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)