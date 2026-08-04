"""Face detection + embedding, run entirely server-side against the ONNX
models vendored in static/models/ (see that folder's README for what they
are and why). Both the HR-registration reference photo and every live
check-in/check-out selfie go through get_embedding() from the exact same
w600k_mbf.onnx, so their embeddings share a vector space and cosine
similarity between them is meaningful — swapping either model requires
regenerating every stored hr.employee.face_embedding.

Detection follows the standard SCRFD decode (3 feature-map strides, anchor
centers repeated per-location, distance-based bbox/landmark regression) and
alignment follows the standard 5-point ArcFace template. Kept as plain
functions (not an Odoo model) so it can be unit tested without a DB.
"""
import logging
import os

import numpy as np

_logger = logging.getLogger(__name__)

try:
    import cv2
    import onnxruntime as ort
except ImportError:  # pragma: no cover - surfaced via manifest external_dependencies
    cv2 = None
    ort = None

_MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'models')
_DET_PATH = os.path.join(_MODELS_DIR, 'det_500m.onnx')
_EMB_PATH = os.path.join(_MODELS_DIR, 'w600k_mbf.onnx')

_DET_INPUT = 640
_SCORE_THRESH = 0.5
_NMS_THRESH = 0.4
_STRIDES = (8, 16, 32)
_NUM_ANCHORS = 2

# Standard ArcFace 112x112 alignment template (left eye, right eye, nose,
# left mouth corner, right mouth corner).
_REF_LANDMARKS = np.array([
    [38.2946, 51.6963],
    [73.5318, 51.5014],
    [56.0252, 71.7366],
    [41.5493, 92.3655],
    [70.7299, 92.2041],
], dtype=np.float32)

_det_session = None
_emb_session = None


def _get_det_session():
    global _det_session
    if _det_session is None:
        _det_session = ort.InferenceSession(_DET_PATH, providers=['CPUExecutionProvider'])
    return _det_session


def _get_emb_session():
    global _emb_session
    if _emb_session is None:
        _emb_session = ort.InferenceSession(_EMB_PATH, providers=['CPUExecutionProvider'])
    return _emb_session


def _letterbox(img, size):
    h, w = img.shape[:2]
    scale = size / max(h, w)
    nh, nw = int(round(h * scale)), int(round(w * scale))
    resized = cv2.resize(img, (nw, nh))
    canvas = np.zeros((size, size, 3), dtype=np.uint8)
    canvas[:nh, :nw] = resized
    return canvas, scale


def _detect_best_face(img):
    """Returns (box_xyxy, score, kps_5x2) for the highest-confidence face in
    img (BGR, any size), in img's own coordinate space, or None."""
    canvas, scale = _letterbox(img, _DET_INPUT)
    blob = (canvas.astype(np.float32) - 127.5) / 128.0
    blob = blob.transpose(2, 0, 1)[None]

    sess = _get_det_session()
    outs = sess.run(None, {sess.get_inputs()[0].name: blob})
    scores_list, bboxes_list, kpss_list = outs[0:3], outs[3:6], outs[6:9]

    all_boxes, all_scores, all_kpss = [], [], []
    for i, stride in enumerate(_STRIDES):
        scores = scores_list[i].reshape(-1)
        keep = scores > _SCORE_THRESH
        if not np.any(keep):
            continue

        bbox_preds = (bboxes_list[i].reshape(-1, 4) * stride)[keep]
        kps_preds = (kpss_list[i].reshape(-1, 10) * stride)[keep]
        sc = scores[keep]

        fh = fw = _DET_INPUT // stride
        ys, xs = np.meshgrid(np.arange(fh), np.arange(fw), indexing='ij')
        centers = np.stack([xs.ravel(), ys.ravel()], axis=1).astype(np.float32) * stride
        centers = np.repeat(centers, _NUM_ANCHORS, axis=0)[keep]

        x1 = centers[:, 0] - bbox_preds[:, 0]
        y1 = centers[:, 1] - bbox_preds[:, 1]
        x2 = centers[:, 0] + bbox_preds[:, 2]
        y2 = centers[:, 1] + bbox_preds[:, 3]
        all_boxes.append(np.stack([x1, y1, x2, y2], axis=1))
        all_scores.append(sc)
        all_kpss.append(centers[:, None, :] + kps_preds.reshape(-1, 5, 2))

    if not all_boxes:
        return None

    boxes = np.concatenate(all_boxes) / scale
    scores = np.concatenate(all_scores)
    kpss = np.concatenate(all_kpss) / scale

    idxs = cv2.dnn.NMSBoxes(boxes.tolist(), scores.tolist(), _SCORE_THRESH, _NMS_THRESH)
    if len(idxs) == 0:
        return None
    idxs = np.array(idxs).reshape(-1)
    best = idxs[np.argmax(scores[idxs])]
    return boxes[best], float(scores[best]), kpss[best]


def detect_and_align(image_bytes):
    """image_bytes: raw JPEG/PNG bytes. Returns a 112x112x3 BGR aligned face
    crop (np.ndarray), or None if no face was found or the image is
    unreadable."""
    if cv2 is None or ort is None:
        _logger.error("face_engine: opencv-python / onnxruntime not installed")
        return None
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return None

    detection = _detect_best_face(img)
    if detection is None:
        return None
    _box, _score, kps = detection

    matrix, _ = cv2.estimateAffinePartial2D(kps.astype(np.float32), _REF_LANDMARKS, method=cv2.LMEDS)
    if matrix is None:
        return None
    return cv2.warpAffine(img, matrix, (112, 112), borderValue=0)


def get_embedding(aligned_bgr):
    """aligned_bgr: 112x112x3 BGR array from detect_and_align(). Returns an
    L2-normalized 512-float list, or None."""
    if aligned_bgr is None or ort is None:
        return None
    rgb = cv2.cvtColor(aligned_bgr, cv2.COLOR_BGR2RGB)
    blob = (rgb.astype(np.float32) - 127.5) / 127.5
    blob = blob.transpose(2, 0, 1)[None]

    sess = _get_emb_session()
    out = sess.run(None, {sess.get_inputs()[0].name: blob})[0][0]
    norm = np.linalg.norm(out)
    if norm == 0:
        return None
    return (out / norm).tolist()


def embed_image_bytes(image_bytes):
    """Convenience wrapper: detect_and_align + get_embedding. Returns a
    512-float list, or None if no face was found."""
    aligned = detect_and_align(image_bytes)
    if aligned is None:
        return None
    return get_embedding(aligned)


def cosine_similarity(a, b):
    if not a or not b:
        return 0.0
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)
