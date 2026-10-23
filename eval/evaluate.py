
"""Evaluate the gym chatbot's language understanding (Track B).

Run from the project root:
    python eval/evaluate.py eval/validation.csv
    python eval/evaluate.py eval/test.csv

The threshold sweep is performed only on validation data.
"""

import argparse
import ast
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

# Ensure imports work when running: python eval/evaluate.py ...
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import src.recognizer as recognizer_module
from src.recognizer import recognize


OUT_OF_SCOPE_LABELS = {"None", "Fallback"}


def parse_slots(value):
    """Parse a CSV cell containing a JSON/Python dictionary of expected slots."""
    if pd.isna(value) or not str(value).strip():
        return {}

    text = str(value).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Allows simple Python-dict syntax as a fallback.
        parsed = ast.literal_eval(text)

    if not isinstance(parsed, dict):
        raise ValueError(f"Expected a dictionary of slots, got: {value!r}")
    return parsed


def load_dataset(csv_path):
    """Load and validate the evaluation CSV."""
    data = pd.read_csv(csv_path)

    required_columns = {"text", "expected_intent", "expected_slots"}
    missing = required_columns - set(data.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

    data["text"] = data["text"].fillna("").astype(str)
    data["expected_intent"] = data["expected_intent"].fillna("None").astype(str)
    data["expected_slots_parsed"] = data["expected_slots"].apply(parse_slots)

    return data


def run_understanding(data, today=None):
    """Call only recognize(), returning predicted intents and resolved slots."""
    predictions = []

    for _, row in data.iterrows():
        if today is None:
            result = recognize(row["text"])
        else:
            result = recognize(row["text"], today=today)

        # Support the RecognizerResult.get(slot_name) API.
        slots = {}
        for slot_name in ("class_type", "date", "time"):
            value = result.get(slot_name)
            if value is not None:
                slots[slot_name] = value

        predictions.append({
            "intent": result.intent,
            "slots": slots,
        })

    return predictions


def slot_metrics(expected_slots, predicted_slots):
    """Micro-averaged exact-match precision, recall, and F1 for slot values."""
    true_positive = 0
    predicted_total = 0
    expected_total = 0

    for expected, predicted in zip(expected_slots, predicted_slots):
        expected = expected or {}
        predicted = predicted or {}

        expected_total += len(expected)
        predicted_total += len(predicted)

        for name, expected_value in expected.items():
            if name in predicted and predicted[name] == expected_value:
                true_positive += 1

    precision = (
        true_positive / predicted_total if predicted_total else 0.0
    )
    recall = true_positive / expected_total if expected_total else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0.0
    )

    return precision, recall, f1


def out_of_scope_recall(expected_intents, predicted_intents):
    """Percentage of labeled out-of-scope utterances predicted as None/Fallback."""
    indices = [
        i for i, intent in enumerate(expected_intents)
        if intent in OUT_OF_SCOPE_LABELS
    ]

    if not indices:
        return None

    correct = sum(
        predicted_intents[i] in OUT_OF_SCOPE_LABELS for i in indices
    )
    return correct / len(indices)


def report_metrics(data, predictions, title="Evaluation"):
    expected_intents = data["expected_intent"].tolist()
    predicted_intents = [p["intent"] for p in predictions]

    expected_slots = data["expected_slots_parsed"].tolist()
    predicted_slots = [p["slots"] for p in predictions]

    labels = sorted(set(expected_intents) | set(predicted_intents))

    accuracy = accuracy_score(expected_intents, predicted_intents)
    macro_f1 = f1_score(
        expected_intents,
        predicted_intents,
        labels=labels,
        average="macro",
        zero_division=0,
    )
    precision, recall, slot_f1 = slot_metrics(expected_slots, predicted_slots)
    oos_recall = out_of_scope_recall(expected_intents, predicted_intents)

    print(f"\n=== {title} ===")
    print(f"Utterances: {len(data)}")
    print(f"Intent accuracy: {accuracy:.3f}")
    print(f"Intent macro-F1: {macro_f1:.3f}")
    print(f"Slot micro-precision: {precision:.3f}")
    print(f"Slot micro-recall: {recall:.3f}")
    print(f"Slot micro-F1: {slot_f1:.3f}")

    if oos_recall is None:
        print("Out-of-scope recall: N/A (no out-of-scope examples)")
    else:
        print(f"Out-of-scope recall: {oos_recall:.3f}")

    matrix = confusion_matrix(
        expected_intents,
        predicted_intents,
        labels=labels,
    )
    print("\nConfusion matrix (rows = expected, columns = predicted)")
    print("Labels:", labels)
    print(matrix)

    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "slot_precision": precision,
        "slot_recall": recall,
        "slot_f1": slot_f1,
        "oos_recall": oos_recall,
    }


def threshold_sweep(data):
    """Sweep INTENT_THRESHOLD on validation data only."""
    original_threshold = recognizer_module.INTENT_THRESHOLD
    thresholds = [round(x / 10, 1) for x in range(2, 9)]
    expected_intents = data["expected_intent"].tolist()
    rows = []

    try:
        for threshold in thresholds:
            recognizer_module.INTENT_THRESHOLD = threshold
            predictions = run_understanding(data)
            predicted_intents = [p["intent"] for p in predictions]

            accuracy = accuracy_score(expected_intents, predicted_intents)
            oos_recall = out_of_scope_recall(
                expected_intents, predicted_intents
            )

            rows.append({
                "threshold": threshold,
                "accuracy": accuracy,
                "out_of_scope_recall": (
                    oos_recall if oos_recall is not None else 0.0
                ),
            })
    finally:
        recognizer_module.INTENT_THRESHOLD = original_threshold

    results = pd.DataFrame(rows)
    print("\n=== Validation threshold sweep ===")
    print(results.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    ax = results.plot(
        x="threshold",
        y=["accuracy", "out_of_scope_recall"],
        marker="o",
    )
    ax.set_title("Validation performance by intent threshold")
    ax.set_xlabel("INTENT_THRESHOLD")
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1.05)
    ax.grid(True)
    plt.tight_layout()

    output_path = PROJECT_ROOT / "eval" / "threshold_sweep.png"
    plt.savefig(output_path, dpi=150)
    print(f"Threshold plot saved to: {output_path}")
    plt.show()

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate the gym chatbot recognizer."
    )
    parser.add_argument(
        "csv_path",
        help="Path to eval/validation.csv or eval/test.csv",
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="Run the threshold sweep (use validation data only).",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    if not csv_path.is_absolute():
        csv_path = PROJECT_ROOT / csv_path

    data = load_dataset(csv_path)
    predictions = run_understanding(data)
    report_metrics(data, predictions, title=csv_path.name)

    if args.sweep:
        if "validation" not in csv_path.name.lower():
            parser.error("--sweep may only be used with validation.csv")
        threshold_sweep(data)


if __name__ == "__main__":
    main()
