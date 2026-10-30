# -*- coding: utf-8 -*-
# watermark.py
import io
import time
import numpy as np
from PIL import Image

def text_to_bits(text: str) -> str:
    """Chuyển text (hỗ trợ UTF-8 / tiếng Việt có dấu) thành chuỗi bit '010101...'"""
    raw_bytes = text.encode("utf-8")
    return "".join(format(b, "08b") for b in raw_bytes)

def bits_to_text(bits: str) -> str:
    """Chuyển chuỗi bit thành chuỗi text UTF-8 hoàn chỉnh"""
    byte_list = bytearray()
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        if len(byte) < 8:
            break
        byte_list.append(int(byte, 2))
    return byte_list.decode("utf-8", errors="replace")

def _get_target_channels(channel: str):
    """Lấy danh sách chỉ số kênh màu cần nhúng"""
    ch_upper = channel.upper()
    if ch_upper == "RGB":
        return [0, 1, 2]
    elif ch_upper == "B":
        return [2]
    elif ch_upper == "R":
        return [0]
    else:  # Mặc định kênh G (Green)
        return [1]

def embed_watermark_lsb(
    image_bytes: bytes,
    watermark_text: str,
    channel: str = "G",
    bit_depth: int = 1,
    max_len: int = 50000
):
    """
    Nhúng watermark vào ảnh sử dụng phương pháp LSB (Least Significant Bit).
    - channel: "G" (Kênh xanh lá - chuẩn mắt người), "B" (Kênh xanh dương), "R" (Kênh đỏ), hoặc "RGB" (Tuần tự cả 3 kênh)
    - bit_depth: 1 (1-LSB: PSNR cực cao > 70dB), 2 (2-LSB: Dung lượng gấp đôi, PSNR ~ 50dB)
    - Hỗ trợ đầy đủ tiếng Việt UTF-8 và ký tự đặc biệt.
    """
    try:
        start_time = time.time()
        if not watermark_text:
            raise ValueError("Nội dung watermark không được để trống")

        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")

        img_array = np.array(img)
        h, w, c = img_array.shape

        bits = text_to_bits(watermark_text)
        if len(bits) > max_len:
            bits = bits[:max_len]

        pad_len = (8 - (len(bits) % 8)) % 8
        bits_padded = bits + ("0" * pad_len)

        flat = img_array.reshape(-1, 3)
        target_channels = _get_target_channels(channel)

        bit_depth = 2 if bit_depth == 2 else 1
        capacity = len(flat) * len(target_channels) * bit_depth

        if len(bits_padded) > capacity:
            raise ValueError(
                f"Watermark quá dài ({len(bits_padded)} bits). Sức chứa tối đa của ảnh theo cấu hình này là {capacity} bits."
            )

        bit_idx = 0
        total_bits = len(bits_padded)

        if bit_depth == 1:
            mask = 0xFE
            for i in range(len(flat)):
                for ch in target_channels:
                    if bit_idx >= total_bits:
                        break
                    b = int(bits_padded[bit_idx])
                    flat[i, ch] = (int(flat[i, ch]) & mask) | b
                    bit_idx += 1
                if bit_idx >= total_bits:
                    break
        elif bit_depth == 2:
            mask = 0xFC
            for i in range(len(flat)):
                for ch in target_channels:
                    if bit_idx >= total_bits:
                        break
                    chunk = bits_padded[bit_idx:bit_idx+2]
                    if len(chunk) < 2:
                        chunk = chunk.ljust(2, "0")
                    val = int(chunk, 2)
                    flat[i, ch] = (int(flat[i, ch]) & mask) | val
                    bit_idx += 2
                if bit_idx >= total_bits:
                    break

        stego_img = flat.reshape(h, w, 3)
        out_img = Image.fromarray(stego_img.astype("uint8"))

        buffer = io.BytesIO()
        out_img.save(buffer, format="PNG")
        buffer.seek(0)
        output_bytes = buffer.getvalue()

        elapsed_time = time.time() - start_time
        print(f"Embedding done in {elapsed_time:.3f}s | Bits: {len(bits_padded)} | Ch: {channel} | BitDepth: {bit_depth}")

        return output_bytes, len(bits_padded)

    except Exception as e:
        print(f"Error in embed_watermark_lsb: {str(e)}")
        raise Exception(f"Lỗi nhúng watermark: {str(e)}")

def extract_watermark_lsb(
    image_bytes: bytes,
    bits_length: int,
    channel: str = "G",
    bit_depth: int = 1
) -> str:
    """
    Trích xuất watermark từ ảnh stego dựa trên thông số đã lưu trên Blockchain
    """
    try:
        start_time = time.time()
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")

        img_array = np.array(img)
        flat = img_array.reshape(-1, 3)
        target_channels = _get_target_channels(channel)
        bit_depth = 2 if bit_depth == 2 else 1

        extracted_bits = []

        if bit_depth == 1:
            for i in range(len(flat)):
                for ch in target_channels:
                    if len(extracted_bits) >= bits_length:
                        break
                    extracted_bits.append(str(flat[i, ch] & 1))
                if len(extracted_bits) >= bits_length:
                    break
        elif bit_depth == 2:
            for i in range(len(flat)):
                for ch in target_channels:
                    if len(extracted_bits) >= bits_length:
                        break
                    val = int(flat[i, ch] & 3)
                    extracted_bits.append(format(val, "02b"))
                if len(extracted_bits) >= bits_length:
                    break
            extracted_bits = "".join(extracted_bits)[:bits_length]

        watermark_text = bits_to_text("".join(extracted_bits))
        elapsed_time = time.time() - start_time
        print(f"Extraction done in {elapsed_time:.3f}s | Bits: {bits_length}")

        return watermark_text if watermark_text else "Không tìm thấy watermark hợp lệ"

    except Exception as e:
        print(f"Error in extract_watermark_lsb: {str(e)}")
        raise Exception(f"Lỗi trích xuất watermark: {str(e)}")
