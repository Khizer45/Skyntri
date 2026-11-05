"""Repair a Skyntri model file exported with ``build_model(weights=None)``.

Keras builds EfficientNetB0-B7 with ``weights="imagenet"`` with one extra
``Rescaling`` layer after the input normalisation. ``weights=None`` leaves it
out. The notebooks trained with ImageNet weights but exported with
``weights=None``, so the exported file lost that layer: the trained weights are
all there, but the model sees the image with the wrong contrast and its
predictions differ from the trained model.

This script rebuilds the backbone with the extra layer, copies every weight
across and saves a fixed copy. No training data and no GPU are needed (the
ImageNet weights are downloaded once, only to build the right architecture).

    python repair_efficientnet_export.py facial_concerns_efficientnet.keras \
        --metadata facial_concerns_metadata.json

The fixed model is written next to the input as ``*_fixed.keras``. With
``--metadata`` the ``sha256`` in the JSON is updated to the fixed file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import tensorflow as tf

BACKBONES = {f"efficientnetb{i}": f"EfficientNetB{i}" for i in range(8)}


def needs_repair(base: tf.keras.Model) -> bool:
    """True when the layer after the input Normalization is not a Rescaling layer."""
    layers = base.layers
    for i, layer in enumerate(layers[:-1]):
        if isinstance(layer, tf.keras.layers.Normalization):
            return not isinstance(layers[i + 1], tf.keras.layers.Rescaling)
    return False


def repair(src: tf.keras.Model) -> tf.keras.Model:
    tf.keras.mixed_precision.set_global_policy("float32")
    base_old = next(layer for layer in src.layers if isinstance(layer, tf.keras.Model))
    if base_old.name not in BACKBONES:
        raise SystemExit(f"backbone {base_old.name!r} is not an EfficientNetB0-B7: nothing to repair")
    if not needs_repair(base_old):
        raise SystemExit("this model already has the ImageNet rescaling layer: nothing to repair")
    shape = tuple(src.input_shape[1:])
    base_new = getattr(tf.keras.applications, BACKBONES[base_old.name])(
        include_top=False, weights="imagenet", input_shape=shape)
    base_new.set_weights(base_old.get_weights())
    base_new.trainable = base_old.trainable
    inputs = tf.keras.Input(shape, name=src.layers[0].name)
    x = base_new(inputs, training=False)
    for layer in src.layers[src.layers.index(base_old) + 1:]:
        x = layer(x)
    fixed = tf.keras.Model(inputs, x, name=src.name)
    if len(fixed.get_weights()) != len(src.get_weights()):
        raise SystemExit("weight count changed while rebuilding: not saving")
    return fixed


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model", type=Path)
    ap.add_argument("--metadata", type=Path, help="metadata JSON whose sha256 should point to the fixed file")
    ap.add_argument("--out", type=Path, help="output file (default: <model>_fixed.keras)")
    args = ap.parse_args()

    src = tf.keras.models.load_model(args.model, compile=False)
    fixed = repair(src)
    out = args.out or args.model.with_name(args.model.stem + "_fixed.keras")
    fixed.save(out)

    x = np.random.default_rng(0).uniform(0, 255, (4, *src.input_shape[1:])).astype("float32")
    reloaded = tf.keras.models.load_model(out, compile=False)
    print(f"saved {out}")
    print(f"old vs fixed: max prob difference {np.abs(src.predict_on_batch(x) - reloaded.predict_on_batch(x)).max():.4f}"
          " (a large value is expected: the old file was wrong)")

    if args.metadata:
        meta = json.loads(args.metadata.read_text())
        meta["sha256"] = hashlib.sha256(out.read_bytes()).hexdigest()
        args.metadata.write_text(json.dumps(meta, indent=2))
        print(f"updated sha256 in {args.metadata}")


if __name__ == "__main__":
    main()
