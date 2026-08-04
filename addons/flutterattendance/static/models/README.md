# Face recognition models

Vendored so the Odoo server needs zero internet access at runtime to verify a
check-in selfie against an employee's registered face.

## Files

- **`det_500m.onnx`** — SCRFD-500M face detector. Input: `[1, 3, H, W]`
  float32 (dynamic H/W). Outputs 9 tensors (scores/bbox-deltas/landmark-deltas
  at 3 feature-map strides: 8, 16, 32) that `face_engine.py` decodes into
  bounding boxes + 5-point landmarks, then runs NMS on.
- **`w600k_mbf.onnx`** — MobileFaceNet embedder. Input: `[N, 3, 112, 112]`
  float32, RGB, `(pixel - 127.5) / 127.5` normalized, face aligned by its 5
  landmarks to the standard ArcFace template. Output: `[N, 512]` — a 512-d
  embedding per face, L2-normalize before comparing.

## Source

Both files are the unmodified `buffalo_sc` model pack from the
[InsightFace](https://github.com/deepinsight/insightface) project (the
smallest/fastest of their official packs — chosen over `buffalo_l`/
`antelopev2` for CPU-only inference on a standard Odoo server):

```
https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_sc.zip
```

Released under InsightFace's non-commercial research license — see the
[InsightFace repo](https://github.com/deepinsight/insightface) for full
license terms before any commercial deployment; swap in a differently
licensed ArcFace/MobileFaceNet ONNX export if that matters for this
deployment.

## Compatibility

Both the HR-registration reference embedding (`hr.employee.face_embedding`)
and every live check-in/check-out selfie are embedded through this exact
same `w600k_mbf.onnx`, so cosine similarity between them is meaningful. If
these files are ever swapped for a different model, **every existing
`face_embedding` must be regenerated** (they live in a different vector
space) — see `face_engine.py`'s module docstring.
