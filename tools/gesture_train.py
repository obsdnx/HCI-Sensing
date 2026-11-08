"""
Train a gesture classifier from recorded CSVs in data/gestures/.
Saves model to data/gesture_model.pkl

Usage:
    python tools/gesture_train.py
"""
import sys
from pathlib import Path

try:
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import LabelEncoder
    import joblib
except ImportError:
    sys.exit("pip install numpy pandas scikit-learn joblib")

GESTURE_DIR = Path("data/gestures")
MODEL_PATH  = Path("data/gesture_model.pkl")


def extract_features(df):
    """Statistical + frequency features per axis."""
    feats = []
    for col in ["ax", "ay", "az", "gx", "gy", "gz"]:
        x = df[col].values
        feats += [x.mean(), x.std(), x.min(), x.max(),
                  np.percentile(x, 25), np.percentile(x, 75)]
        # Top 3 FFT magnitudes
        fft = np.abs(np.fft.rfft(x))[:len(x)//2]
        feats += sorted(fft, reverse=True)[:3]
    return feats


def main():
    csvs = list(GESTURE_DIR.glob("*.csv"))
    if not csvs:
        sys.exit(f"No gesture CSVs found in {GESTURE_DIR}. Run gesture_record.py first.")

    X, y = [], []
    for path in csvs:
        label = "_".join(path.stem.split("_")[:-2])  # strip timestamp
        df = pd.read_csv(path)
        X.append(extract_features(df))
        y.append(label)

    labels = sorted(set(y))
    print(f"Classes ({len(labels)}): {labels}")
    print(f"Samples: {len(X)}")

    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    scores = cross_val_score(clf, X, y_enc, cv=min(5, len(X)), scoring="accuracy")
    print(f"CV accuracy: {scores.mean():.2%} ± {scores.std():.2%}")

    clf.fit(X, y_enc)
    joblib.dump({"model": clf, "encoder": le}, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")


if __name__ == "__main__":
    main()
