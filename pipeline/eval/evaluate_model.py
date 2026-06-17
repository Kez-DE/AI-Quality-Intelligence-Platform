import os
import json
import sys

# Thêm đường dẫn thư mục gốc vào sys.path để import từ pipeline
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from classifier import predict_feedback

def evaluate_model(dataset_path: str):
    print(f"Loading dataset from {dataset_path}...")
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    total = len(dataset)
    if total == 0:
        print("Dataset is empty.")
        return

    metrics = {
        "topic": {"correct": 0, "total": total},
        "sentiment": {"correct": 0, "total": total},
        "severity": {"correct": 0, "total": total},
    }

    print("Running predictions...")
    for item in dataset:
        text = item["text"]
        expected = item["expected"]
        
        # Gọi mô hình để phân loại
        prediction = predict_feedback(text)
        
        # Đánh giá độ chính xác
        if prediction["topic"] == expected["topic"]:
            metrics["topic"]["correct"] += 1
        if prediction["sentiment"] == expected["sentiment"]:
            metrics["sentiment"]["correct"] += 1
            
        # So sánh severity, chú ý convert về P-level chuẩn
        sev = prediction["severity"]
        sev_value = sev if isinstance(sev, str) and sev.upper().startswith("P") else f"P{int(sev)}"
        if sev_value == expected["severity"]:
            metrics["severity"]["correct"] += 1

    print("\n" + "="*30)
    print("EVALUATION RESULTS")
    print("="*30)
    print(f"Total samples: {total}")
    
    for key, val in metrics.items():
        correct = val["correct"]
        accuracy = (correct / total) * 100
        print(f"Accuracy - {key.capitalize()}: {accuracy:.1f}% ({correct}/{total})")

if __name__ == "__main__":
    dataset_file = os.path.join(os.path.dirname(__file__), "gold_dataset.json")
    evaluate_model(dataset_file)
