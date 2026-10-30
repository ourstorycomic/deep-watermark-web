# -*- coding: utf-8 -*-
# blockchain_mock.py
import json
import os
import hashlib
from datetime import datetime

# Đường dẫn file ledger trong thư mục dự án
DEFAULT_LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ledger.json")
LEDGER_FILE = os.environ.get("LEDGER_FILE", DEFAULT_LEDGER)

def sha256_bytes(data: bytes) -> str:
    """Tính mã băm SHA256 của chuỗi bytes"""
    return hashlib.sha256(data).hexdigest()

def _normalize_record(record: dict) -> dict:
    """Chuẩn hóa dữ liệu bản ghi để luôn có đầy đủ trường (tương thích các bản ghi cũ)"""
    if not isinstance(record, dict):
        return record

    im_h = record.get("image_hash", "")
    wm_h = record.get("watermark_hash", "")

    # Đảm bảo luôn có tx_hash
    if "tx_hash" not in record or not record["tx_hash"]:
        record["tx_hash"] = sha256_bytes((im_h + wm_h).encode("utf-8"))

    # Đảm bảo luôn có stego_params
    if "stego_params" not in record or not isinstance(record["stego_params"], dict):
        record["stego_params"] = {
            "channel": "G",
            "bit_depth": 1,
            "psnr": 70.0,
            "ssim": 0.9999
        }

    # Đảm bảo luôn có author dict
    if "author" not in record or not isinstance(record["author"], dict):
        record["author"] = {"name": "", "email": "", "link": ""}

    return record

def _load_ledger():
    """Đọc ledger từ file JSON và chuẩn hóa bản ghi"""
    if not os.path.exists(LEDGER_FILE):
        return {}
    try:
        with open(LEDGER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            normalized = {}
            for k, v in data.items():
                normalized[k] = _normalize_record(v)
            return normalized
        return {}
    except (json.JSONDecodeError, IOError):
        return {}

def _save_ledger(data):
    """Lưu ledger vào file JSON"""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(LEDGER_FILE)), exist_ok=True)
        with open(LEDGER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving ledger: {e}")
        return False

def register_image(
    image_bytes: bytes,
    watermark_text: str,
    author_info: dict,
    bits_len: int,
    stego_params: dict = None
):
    """
    Ghi nhận giao dịch lên Blockchain:
    - Tính hash SHA256 của ảnh đã nhúng watermark
    - Tính hash SHA256 của nội dung watermark
    - Lưu bản ghi kèm thông tin tác giả, tham số kỹ thuật
    - Trả về mã tx_hash và bản ghi record
    """
    ledger = _load_ledger()

    image_hash = sha256_bytes(image_bytes)
    wm_hash = sha256_bytes(watermark_text.encode("utf-8"))
    tx_hash = sha256_bytes((image_hash + wm_hash).encode("utf-8"))

    record = {
        "tx_hash": tx_hash,
        "image_hash": image_hash,
        "watermark_hash": wm_hash,
        "author": author_info or {"name": "", "email": "", "link": ""},
        "bits_length": bits_len,
        "stego_params": stego_params or {"channel": "G", "bit_depth": 1},
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    record = _normalize_record(record)
    ledger[image_hash] = record

    if not _save_ledger(ledger):
        raise Exception("Không thể lưu ledger")

    return tx_hash, record

def verify_image(image_bytes: bytes):
    """
    Xác thực ảnh:
    - Tính hash SHA256 của ảnh tải lên
    - Đối soát tìm kiếm trong ledger
    """
    ledger = _load_ledger()
    image_hash = sha256_bytes(image_bytes)
    record = ledger.get(image_hash)
    if record:
        record = _normalize_record(record)
    return image_hash, record

def get_all_records():
    """Lấy toàn bộ bản ghi trong sổ cái"""
    return _load_ledger()

def get_recent_records():
    """Lấy danh sách bản ghi sắp xếp mới nhất lên đầu"""
    ledger = _load_ledger()
    items = [_normalize_record(v) for v in ledger.values()]
    items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return items

def search_records(query: str):
    """Tìm kiếm bản ghi theo tên tác giả, email, tx_hash, hoặc image_hash"""
    q = (query or "").strip().lower()
    records = get_recent_records()
    if not q:
        return records

    matched = []
    for r in records:
        author = r.get("author", {}) or {}
        name = (author.get("name") or "").lower()
        email = (author.get("email") or "").lower()
        tx = (r.get("tx_hash") or "").lower()
        im = (r.get("image_hash") or "").lower()
        if q in name or q in email or q in tx or q in im:
            matched.append(r)
    return matched

def clear_ledger():
    """Xóa sổ cái (dùng cho testing)"""
    if os.path.exists(LEDGER_FILE):
        os.remove(LEDGER_FILE)
    return {}

def get_stats():
    """Thống kê chi tiết sổ cái phục vụ báo cáo khảo sát"""
    ledger = _load_ledger()
    records = list(ledger.values())
    total_records = len(records)
    total_bits = sum(r.get("bits_length", 0) for r in records)
    avg_bits = round(total_bits / total_records, 1) if total_records > 0 else 0

    return {
        "total_records": total_records,
        "total_bits_embedded": total_bits,
        "avg_bits_length": avg_bits,
        "ledger_file": LEDGER_FILE,
        "file_exists": os.path.exists(LEDGER_FILE)
    }
