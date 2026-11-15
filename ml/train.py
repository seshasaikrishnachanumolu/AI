"""Train the CNN waste classifier.

Two architectures (both are convolutional neural networks built with TensorFlow/Keras):
  --arch mobilenet  MobileNetV2 transfer learning (ImageNet weights) + new classification head. Default.
  --arch custom     Small CNN trained from scratch (used as the baseline).

Usage:
    python ml/train.py --data data/dataset --arch mobilenet
Outputs (ml/model/): waste_cnn.keras, class_names.json, training_curves.png, training_log.json
Models take raw 0-255 RGB pixels: normalisation is part of the model (see app/services/classifier.py).
"""
import argparse
import json
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

OUT_DIR = Path(__file__).resolve().parent / "model"


def augmentation():
    return keras.Sequential(
        [layers.RandomFlip("horizontal"), layers.RandomRotation(0.1), layers.RandomZoom(0.15),
         layers.RandomContrast(0.15)],
        name="augment",
    )


def build_custom(size, num_classes):
    return keras.Sequential(
        [
            layers.Input((size, size, 3)),
            layers.Rescaling(1.0 / 255),
            augmentation(),
            layers.Conv2D(32, 3, padding="same", activation="relu"), layers.BatchNormalization(), layers.MaxPooling2D(),
            layers.Conv2D(64, 3, padding="same", activation="relu"), layers.BatchNormalization(), layers.MaxPooling2D(),
            layers.Conv2D(128, 3, padding="same", activation="relu"), layers.BatchNormalization(), layers.MaxPooling2D(),
            layers.Conv2D(256, 3, padding="same", activation="relu"), layers.BatchNormalization(), layers.MaxPooling2D(),
            layers.GlobalAveragePooling2D(), layers.Dropout(0.4),
            layers.Dense(128, activation="relu"), layers.Dropout(0.3),
            layers.Dense(num_classes, activation="softmax"),
        ],
        name="waste_cnn",
    ), None


def build_mobilenet(size, num_classes):
    base = keras.applications.MobileNetV2(input_shape=(size, size, 3), include_top=False, weights="imagenet")
    base.trainable = False
    inputs = keras.Input((size, size, 3))
    x = layers.Rescaling(1.0 / 127.5, offset=-1)(inputs)  # MobileNetV2 expects [-1, 1]
    x = augmentation()(x)
    x = base(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.3)(x)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)
    return keras.Model(inputs, outputs, name="waste_mobilenetv2"), base


def class_weights(train_dir, class_names):
    counts = np.array([len(list((Path(train_dir) / c).glob("*"))) for c in class_names], dtype=float)
    w = counts.sum() / (len(counts) * counts)  # inverse frequency
    return {i: float(v) for i, v in enumerate(w)}


def compile_model(model, lr):
    model.compile(optimizer=keras.optimizers.Adam(lr), loss="sparse_categorical_crossentropy", metrics=["accuracy"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/dataset")
    ap.add_argument("--arch", choices=["mobilenet", "custom"], default="mobilenet")
    ap.add_argument("--size", type=int, default=128)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--epochs", type=int, default=30, help="custom: max epochs. mobilenet: head epochs")
    ap.add_argument("--finetune-epochs", type=int, default=12)
    ap.add_argument("--out", default="waste_cnn.keras")
    args = ap.parse_args()

    data = Path(args.data)
    common = dict(image_size=(args.size, args.size), batch_size=args.batch, label_mode="int")
    train = keras.utils.image_dataset_from_directory(data / "train", shuffle=True, seed=42, **common)
    val = keras.utils.image_dataset_from_directory(data / "val", shuffle=False, **common)
    class_names = train.class_names
    print("Classes:", class_names)
    weights = class_weights(data / "train", class_names)
    print("Class weights:", {class_names[k]: round(v, 2) for k, v in weights.items()})
    train, val = train.prefetch(tf.data.AUTOTUNE), val.prefetch(tf.data.AUTOTUNE)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / args.out
    ckpt = keras.callbacks.ModelCheckpoint(out_path, monitor="val_accuracy", save_best_only=True)
    plateau = keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2)
    hist = {"accuracy": [], "val_accuracy": [], "loss": [], "val_loss": []}

    def run(epochs, extra=()):
        h = model.fit(train, validation_data=val, epochs=epochs, class_weight=weights,
                      callbacks=[ckpt, plateau, keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=6, restore_best_weights=True), *extra])
        for k in hist:
            hist[k] += [float(v) for v in h.history[k]]

    if args.arch == "custom":
        model, _ = build_custom(args.size, len(class_names))
        compile_model(model, 1e-3)
        run(args.epochs)
    else:
        model, base = build_mobilenet(args.size, len(class_names))
        compile_model(model, 1e-3)
        print("== Phase 1: train the new head (base frozen)")
        run(args.epochs)
        print("== Phase 2: fine-tune the top of the base network")
        base.trainable = True
        for layer in base.layers[:-40]:
            layer.trainable = False
        for layer in base.layers:  # keep BatchNorm statistics frozen
            if isinstance(layer, layers.BatchNormalization):
                layer.trainable = False
        compile_model(model, 1e-5)
        run(args.finetune_epochs)

    best = keras.models.load_model(out_path)  # best checkpoint by val accuracy
    val_loss, val_acc = best.evaluate(val, verbose=0)
    print(f"Best validation accuracy: {val_acc:.4f}")
    (OUT_DIR / "class_names.json").write_text(json.dumps(class_names), encoding="utf-8")
    (OUT_DIR / "training_log.json").write_text(json.dumps({"arch": args.arch, "size": args.size, "best_val_accuracy": float(val_acc), "history": hist}), encoding="utf-8")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(1, 2, figsize=(11, 4))
        for a, key, title in ((ax[0], "accuracy", "Accuracy"), (ax[1], "loss", "Loss")):
            a.plot(hist[key], label="train"); a.plot(hist["val_" + key], label="validation"); a.set_title(title); a.set_xlabel("epoch"); a.legend()
        fig.savefig(OUT_DIR / "training_curves.png", dpi=120, bbox_inches="tight")
    except Exception as e:
        print("Could not save training curves:", e)
    print(f"Saved {out_path}. Now run: python ml/evaluate.py")


if __name__ == "__main__":
    main()
