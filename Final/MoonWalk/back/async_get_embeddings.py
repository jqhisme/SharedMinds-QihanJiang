import os
import time
import torch
import numpy as np

from univtg.run_on_video.video_extractor import clip, vid2clip, txt2clip
from univtg.utils.basic_utils import l2_normalize_np_array
from univtg.main.config import TestOptions, setup_model
import torch.backends.cudnn as cudnn
import logging
import sys
from IPython import get_ipython
import argparse
import warnings

EMB_DIR = "./embeddings"
MODEL_CKPT = "./univtg/ckpts/model_raw.ckpt"
GPU_ID = 0
VIDEO_DIR = "./footages"

os.environ["CUDA_VISIBLE_DEVICES"] = str(GPU_ID)

model_version = "ViT-B/32"
clip_len = 2

clip_model, _ = clip.load(model_version, device=GPU_ID, jit=False)

def convert_to_hms(seconds):
    return time.strftime('%H:%M:%S', time.gmtime(seconds))

def extract_video(video_path):
    print("Extracting video features...")
    vid2clip(clip_model, video_path, EMB_DIR)
    print("Done.")


if __name__ == "__main__":
    # check if the directory is back or MoonWalk
    if os.path.basename(os.getcwd()) == "back":
        raise RuntimeError("Please run this script from the MoonWalk root directory, not from the back directory.")
    
    video_file = [os.path.join(VIDEO_DIR, f) for f in os.listdir(VIDEO_DIR) if f.endswith(('.mp4'))]
    if len(video_file) == 0:
        raise RuntimeError(f"No video files found in {VIDEO_DIR}. Please add .mp4 video files to the directory.")
    elif len(video_file) > 1:
        warnings.warn(f"Multiple video files found in {VIDEO_DIR}. Only the first one,{video_file[0]}, will be processed.\n Please concat all videos into one.")
    

    extract_video(video_file[0])
    print("Video feature extracted to ", EMB_DIR,"vid.npz")