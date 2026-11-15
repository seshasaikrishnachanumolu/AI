"""Evaluate the trained model on the held-out test split.

Usage:  python ml/evaluate.py --data data/dataset --size 128
Writes ml/model/evaluation.txt and confusion_matrix.png.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import classification_report, confusion_matrix
from tensorflow import keras

OUT_DIR = Path(__file__).resolve().parent / "model"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/dataset")
    ap.add_argument("--size", type=int, default=128)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--model", default="waste_cnn.keras")
    ap.add_argument("--tag", default="", help="suffix for output files, e.g. _candidate")
    args = ap.parse_args()

    class_names = json.loads((OUT_DIR / "class_names.json").read_text(encoding="utf-8"))
    model = keras.models.load_model(OUT_DIR / args.model)
    test = keras.utils.image_dataset_from_directory(
        Path(args.data) / "test",
        image_size=(args.size, args.size),
        batch_size=args.batch,
        shuffle=False,
        label_mode="int",
        class_names=class_names,  # keep label order identical to training
    )

    y_true = np.concatenate([y.numpy() for _, y in test])
    y_pred = np.argmax(model.predict(test, verbose=0), axis=1)
    acc = float((y_true == y_pred).mean())
    report = classification_report(y_true, y_pred, target_names=class_names, digits=3)
    cm = confusion_matrix(y_true, y_pred)

    text = f"Test accuracy: {acc:.4f} ({len(y_true)} images)\n\n{report}\nConfusion matrix:\n{cm}\n"
    print(text)
    (OUT_DIR / f"evaluation{args.tag}.txt").write_text(text, encoding="utf-8")

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(5.5, 5))
        ax.imshow(cm, cmap="Greens")
        ax.set_xticks(range(len(class_names)), class_names, rotation=45)
        ax.set_yticks(range(len(class_names)), class_names)
        for i in range(len(class_names)):
            for j in range(len(class_names)):
                ax.text(j, i, cm[i, j], ha="center", va="center")
        ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
        fig.savefig(OUT_DIR / f"confusion_matrix{args.tag}.png", dpi=120, bbox_inches="tight")
    except Exception as e:
        print("Could not save confusion matrix:", e)


if __name__ == "__main__":
    main()
