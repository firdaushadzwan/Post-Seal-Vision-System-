import cv2
import numpy as np

REQUIRED_INSPECTIONS = [
    "upper sealing",
    "offset sealing",
]

def adaptive_binary(gray: np.ndarray) -> np.ndarray:
    if gray.size == 0:
        return gray
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary

def count_alignment_holes(gray_roi: np.ndarray) -> int:
    if gray_roi.size == 0:
        return 0
    binary_roi = adaptive_binary(gray_roi)
    inverted = cv2.bitwise_not(binary_roi)
    contours, _ = cv2.findContours(inverted, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = max(30, int(gray_roi.size * 0.0005))
    max_area = max(200, int(gray_roi.size * 0.05))
    valid_holes = 0
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        ratio = w / float(h + 1)
        if 0.3 <= ratio <= 3.0:
            valid_holes += 1
    return valid_holes

# def inspect_unit_alignment(gray_roi: np.ndarray, state: dict) -> dict:
#     hole_count = count_alignment_holes(gray_roi)
#     if hole_count >= 4:
#         if not state.get("has_full_group", False):
#             state["count"] = state.get("count", 0) + 1
#             state["has_full_group"] = True
#     else:
#         state["has_full_group"] = False

#     return {
#         "name": "unit alignment",
#         "passed": True,
#         "count": state.get("count", 0),
#         "hole_count": hole_count,
#         "message": f"Count {state.get('count', 0)} | Holes {hole_count}",
#     }

def inspect_upper_sealing(binary_roi: np.ndarray) -> dict:
    if binary_roi.size == 0:
        return {
            "name": "upper sealing",
            "passed": False,
            "ratio": 0.0,
            "message": "Upper sealing ROI is empty",
        }
    white_ratio = float(np.mean(binary_roi == 255))
    passed = white_ratio <= 0.15
    return {
        "name": "upper sealing",
        "passed": passed,
        "ratio": white_ratio,
        "message": "OK" if passed else "UPPER SEALING BROKEN",
    }

def inspect_offset_sealing(binary_roi: np.ndarray) -> dict:
    if binary_roi.size == 0:
        return {
            "name": "offset sealing",
            "passed": False,
            "ratio": 0.0,
            "message": "Offset sealing ROI is empty",
        }
    # Compute white pixel ratio in the binary ROI (white pixels are 255)
    white_ratio = float(np.mean(binary_roi == 255))
    # PASS if white percentage is less than 15%
    passed = white_ratio < 0.15
    message = "OK" if passed else "OFFSET SEALING"
    return {
        "name": "offset sealing",
        "passed": passed,
        "ratio": white_ratio,
        "message": message,
    }


def build_summary(results: list[dict]) -> dict:
    if not results:
        return {
            "status": "FAIL",
            "summary": "No inspection results",
            "details": "",
            "count_text": "Inspections: 0/0",
            "passed": False,
        }

    failed_items = [r["message"] for r in results if not r.get("passed", False)]
    passed_count = sum(1 for r in results if r.get("passed", False))
    total = len(results)

    if passed_count == total:
        status = "PASS"
        summary = "OK"
        passed = True
    else:
        status = "FAIL"
        summary = " / ".join(failed_items) if failed_items else "FAIL"
        passed = False

    return {
        "status": status,
        "summary": summary,
        "details": " / ".join(failed_items) if failed_items else "OK",
        "count_text": f"Inspections: {passed_count}/{total}",
        "passed": passed,
    }
