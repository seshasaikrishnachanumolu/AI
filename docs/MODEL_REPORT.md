# AI Model Report

## Task
Classify a waste photo into five categories: **plastic, paper, metal, glass, organic**.

## Dataset
Hugging Face dataset *Garbage Classification with 12 classes* (`UdaraChamidu/Garbage-Classification-with-12-classes`,
a copy of the Kaggle "Garbage Classification" data). `ml/prepare_dataset.py` maps the original folders to the five
project categories and skips the rest:

| Project category | Source folders | Images |
|------------------|----------------|-------:|
| paper | paper, cardboard | 1,941 |
| glass | brown-glass, green-glass, white-glass | 2,016 |
| organic | biological | 985 |
| plastic | plastic | 865 |
| metal | metal | 769 |
| **Total** | | **6,576** |

Skipped classes: trash, battery, clothes, shoes. Images are resized to 128×128 and split 70 / 15 / 15
(seed 42): 4,608 train, 984 validation and 984 test images. Unreadable images skipped: 0.

**Known data limitations.** The classes are imbalanced (glass is 2.6× metal). The photos are mostly single
objects on plain backgrounds, so accuracy on cluttered real-world scenes will be lower. There is no "not waste /
unknown" class, so any image is forced into one of the five categories (a confidence threshold can be set with
`MIN_CONFIDENCE` in `config.py`).

## Models compared
| | Baseline CNN | MobileNetV2 transfer learning (deployed) |
|---|---|---|
| Architecture | 4 × (Conv + BatchNorm + MaxPool) + GAP + Dense | ImageNet-pretrained MobileNetV2 base + Dense head |
| Training | from scratch, 30 epochs max | phase 1: head with frozen base; phase 2: fine-tune top 40 layers at lr 1e-5 |
| Augmentation | flip, rotation, zoom | flip, rotation, zoom, contrast |
| Imbalance handling | none | inverse-frequency class weights |
| File size | 5.2 MB | 10.3 MB |
| **Test accuracy** | **74.3 %** | **87.2 %** |
| Macro F1 | 0.713 | 0.851 |

Both are convolutional neural networks built with TensorFlow/Keras. The test set (984 images) was never used
for training or checkpoint selection; the best checkpoint was chosen on validation accuracy (87.7 %).

## Deployed model: per-class results (test set)
| Class | Precision | Recall | F1 | Support |
|-------|----------:|-------:|---:|--------:|
| glass | 0.926 | 0.825 | 0.872 | 302 |
| metal | 0.714 | 0.826 | 0.766 | 115 |
| organic | 0.893 | 0.966 | 0.928 | 147 |
| paper | 0.955 | 0.938 | 0.946 | 291 |
| plastic | 0.723 | 0.767 | 0.744 | 129 |
| **Overall accuracy** | | | **0.872** | 984 |

Confusion matrix (rows = actual, columns = predicted; order glass, metal, organic, paper, plastic):

```
          glass metal organic paper plastic
glass      249    20     11     4     18
metal        3    95      1     1     15
organic      1     0    142     2      2
paper        2    10      3   273      3
plastic     14     8      2     6     99
```

Most remaining errors are glass ↔ plastic and metal ↔ plastic, which look alike under shiny reflections.
Baseline for comparison: metal recall improved from 0.50 to 0.83 with transfer learning.
Files: `ml/model/evaluation.txt`, `confusion_matrix.png`, `training_curves.png`, `training_log.json`
(baseline artefacts are kept as `*_baseline.*`).

## Reproduce
```powershell
python ml/prepare_dataset.py --raw data/raw --out data/dataset --size 128
python ml/train.py --data data/dataset --arch mobilenet --epochs 10 --finetune-epochs 12
python ml/evaluate.py --data data/dataset
```
(`--arch custom` retrains the baseline.) Training on a CPU takes about 12 minutes for the deployed model.
Results will differ slightly between runs because of random initialisation and augmentation.

## Ideas to improve further
Collect photos from the actual campus bins, add a "not waste / unknown" class, train at 160–224 px,
try EfficientNet-B0, and use test-time augmentation.
