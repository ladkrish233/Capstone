import os
import tempfile
from pathlib import Path

import numpy as np
import onnxruntime as ort
from huggingface_hub import snapshot_download
from tokenizers import Tokenizer

MODEL_DIR = Path(os.environ.get("MODEL_DIR", Path(tempfile.gettempdir()) / "gemma"))

REPO = "onnx-community/embeddinggemma-300m-ONNX"
MODEL_DIR = Path(__file__).parent / "models" / "gemma"
MAX_LEN = 512  # lower to 256 if the Nano runs out of memory

PREFIX = {
    "query": "task: search result | query: ",
    "document": "title: none | text: ",
}


class LocalEmbeddings:
    def __init__(self):
        if not (MODEL_DIR / "onnx" / "model_q4.onnx").exists():
            snapshot_download(
                REPO,
                local_dir=str(MODEL_DIR),
                allow_patterns=["onnx/model_q4.onnx*", "tokenizer.json", "config.json"],
            )
        path = str(MODEL_DIR)
        self.tok = Tokenizer.from_file(f"{path}/tokenizer.json")
        self.tok.enable_padding()
        self.tok.enable_truncation(max_length=MAX_LEN)
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        opts.inter_op_num_threads = 1
        self.sess = ort.InferenceSession(
            f"{path}/onnx/model_q4.onnx", opts, providers=["CPUExecutionProvider"]
        )
        self.embed(["warm up"], "query")  # first run is slower, so do it now

    def embed(self, texts: list[str], kind: str = "document") -> list[list[float]]:
        enc = self.tok.encode_batch([PREFIX[kind] + t for t in texts])
        feed = {
            "input_ids": np.array([e.ids for e in enc], dtype=np.int64),
            "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64),
        }
        vec = self.sess.run(["sentence_embedding"], feed)[0]
        vec = vec / np.linalg.norm(vec, axis=1, keepdims=True)
        return vec.tolist()