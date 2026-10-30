# -*- coding: utf-8 -*-
# app.py
import os
import sys
import time
from io import BytesIO
from flask import Flask, render_template, request, send_file, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import watermark as wm
import blockchain_mock as bc
import metrics as mt

# Cấu hình thư mục lưu ảnh (tương thích Vercel Serverless Read-Only Filesystem)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IS_VERCEL = bool(os.environ.get("VERCEL"))

if IS_VERCEL:
    UPLOAD_FOLDER = "/tmp/uploads"
else:
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(BASE_DIR, "static", "uploads"))

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = "super-secret-key-deep-watermark"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024  # Tối đa 30MB
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

def get_available_samples():
    """Lấy danh sách các tệp ảnh mẫu có trong thư mục uploads kèm thông tin tác giả nếu có"""
    samples = []
    # Tìm kiếm cả trong uploads tạm và uploads của repo
    search_dirs = [app.config["UPLOAD_FOLDER"], os.path.join(BASE_DIR, "static", "uploads")]
    seen = set()
    ledger = bc.get_all_records()

    for sdir in search_dirs:
        if os.path.exists(sdir):
            for fname in os.listdir(sdir):
                if fname.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")) and fname not in seen:
                    seen.add(fname)
                    fpath = os.path.join(sdir, fname)
                    author_name = "Chưa rõ"
                    try:
                        with open(fpath, "rb") as f:
                            img_h = bc.sha256_bytes(f.read())
                        if img_h in ledger:
                            author_name = ledger[img_h].get("author", {}).get("name", "Đã lưu sổ cái")
                    except Exception:
                        pass

                    samples.append({
                        "filename": fname,
                        "author": author_name
                    })
    return samples

@app.route("/")
def index():
    stats = bc.get_stats()
    return render_template("index.html", stats=stats)

@app.route("/embed", methods=["POST"])
def embed():
    try:
        if "image" not in request.files:
            flash("Vui lòng chọn file ảnh gốc", "error")
            return redirect(url_for("index"))

        file = request.files["image"]
        if not file or file.filename == "":
            flash("Vui lòng chọn ảnh hợp lệ", "error")
            return redirect(url_for("index"))

        # Kiểm tra dung lượng
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > app.config["MAX_CONTENT_LENGTH"]:
            flash("Kích thước ảnh vượt quá giới hạn (tối đa 30MB)", "error")
            return redirect(url_for("index"))

        watermark_text = request.form.get("watermark_text", "").strip()
        channel = request.form.get("channel", "G").strip().upper()
        bit_depth = int(request.form.get("bit_depth", 1))

        author_name = request.form.get("author_name", "").strip()
        author_email = request.form.get("author_email", "").strip()
        author_link = request.form.get("author_link", "").strip()

        if not watermark_text:
            flash("Vui lòng nhập nội dung watermark cần nhúng", "error")
            return redirect(url_for("index"))

        # Đọc dữ liệu ảnh gốc
        orig_bytes = file.read()

        # 1. Nhúng watermark (Spatial LSB)
        stego_bytes, bits_len = wm.embed_watermark_lsb(
            orig_bytes,
            watermark_text,
            channel=channel,
            bit_depth=bit_depth
        )

        # 2. Tính toán toàn bộ chỉ số chất lượng khoa học (PSNR, MSE, SSIM, BPP, Diff Map)
        quality_metrics = mt.calculate_quality_metrics(orig_bytes, stego_bytes, bits_len)

        # 3. Ghi nhận giao dịch lên Sổ cái Blockchain Mock
        author_info = {
            "name": author_name,
            "email": author_email,
            "link": author_link
        }
        stego_params = {
            "channel": channel,
            "bit_depth": bit_depth,
            "psnr": quality_metrics["psnr"],
            "ssim": quality_metrics["ssim"],
            "mse": quality_metrics["mse"]
        }
        tx_hash, record = bc.register_image(
            stego_bytes,
            watermark_text,
            author_info,
            bits_len,
            stego_params=stego_params
        )

        # 4. Lưu ảnh đã giấu tin
        filename = secure_filename(file.filename)
        base, _ = os.path.splitext(filename)
        base = "".join(c for c in base if c.isalnum() or c in "._-")
        if not base:
            base = "image"
        out_name = f"{base}_watermarked.png"
        out_path = os.path.join(app.config["UPLOAD_FOLDER"], out_name)

        with open(out_path, "wb") as f:
            f.write(stego_bytes)

        # URL hiển thị và download
        image_url = url_for("view_upload", filename=out_name)
        download_url = url_for("download_file", filename=out_name)

        flash("Nhúng watermark thành công và đã lưu bằng chứng lên Sổ cái!", "success")

        return render_template(
            "result_embed.html",
            image_url=image_url,
            download_url=download_url,
            tx_hash=tx_hash,
            record=record,
            metrics=quality_metrics,
            filename=out_name
        )

    except Exception as e:
        app.logger.error(f"Embed error: {str(e)}")
        flash(f"Lỗi: {str(e)}", "error")
        return redirect(url_for("index"))

@app.route("/verify", methods=["POST"])
def verify():
    try:
        if "image" not in request.files:
            flash("Vui lòng chọn ảnh cần xác minh", "error")
            return redirect(url_for("index"))

        file = request.files["image"]
        if not file or file.filename == "":
            flash("Vui lòng chọn ảnh hợp lệ", "error")
            return redirect(url_for("index"))

        image_bytes = file.read()
        if len(image_bytes) == 0:
            flash("File ảnh tải lên rỗng", "error")
            return redirect(url_for("index"))

        # 1. Tra cứu sổ cái theo mã băm SHA256 của toàn bộ ảnh
        image_hash, record = bc.verify_image(image_bytes)

        if record is None:
            return render_template(
                "result_verify.html",
                status="NOT_FOUND",
                image_hash=image_hash,
                message="Không tìm thấy bản ghi trên sổ cái. Ảnh này chưa từng được đăng ký, hoặc đã bị chỉnh sửa/nén lại làm thay đổi mã SHA-256."
            )

        # 2. Trích xuất watermark theo cấu hình lúc đăng ký
        bits_len = record.get("bits_length", 0)
        stego_params = record.get("stego_params") or {}
        channel = stego_params.get("channel", "G")
        bit_depth = stego_params.get("bit_depth", 1)

        extracted_text = wm.extract_watermark_lsb(
            image_bytes,
            bits_len,
            channel=channel,
            bit_depth=bit_depth
        )

        # 3. So khớp băm chữ ký watermark
        extracted_hash = bc.sha256_bytes(extracted_text.encode("utf-8"))
        is_valid = (extracted_hash == record.get("watermark_hash"))
        status = "VALID" if is_valid else "TAMPERED"

        if is_valid:
            message = "Xác thực thành công: Ảnh hợp lệ 100%, watermark trích xuất hoàn toàn trùng khớp với bản ghi bảo vệ trên sổ cái."
        else:
            message = "Cảnh báo: Ảnh có chứa dữ liệu giấu tin nhưng không khớp chữ ký gốc trên Blockchain. Dữ liệu ảnh đã bị chỉnh sửa hoặc sửa đổi."

        return render_template(
            "result_verify.html",
            status=status,
            image_hash=image_hash,
            record=record,
            extracted_text=extracted_text,
            extracted_hash=extracted_hash,
            message=message
        )

    except Exception as e:
        app.logger.error(f"Verify error: {str(e)}")
        flash(f"Lỗi: {str(e)}", "error")
        return redirect(url_for("index"))

@app.route("/benchmark", methods=["GET", "POST"])
def benchmark():
    """Phòng thí nghiệm khảo sát tính bền vững và khả năng chịu đựng tấn công"""
    available_samples = get_available_samples()
    attack_results = None
    selected_filename = request.args.get("filename", "")
    secret_text = request.form.get("secret_text", "")
    bits_len = int(request.form.get("bits_len", 160))

    if request.method == "POST":
        try:
            stego_bytes = None
            if "image" in request.files and request.files["image"].filename:
                file = request.files["image"]
                stego_bytes = file.read()
            elif request.form.get("sample_filename"):
                sample_name = secure_filename(request.form.get("sample_filename"))
                # Tìm trong uploads tạm hoặc repo uploads
                s_path = os.path.join(app.config["UPLOAD_FOLDER"], sample_name)
                if not os.path.exists(s_path):
                    s_path = os.path.join(BASE_DIR, "static", "uploads", sample_name)
                if os.path.exists(s_path):
                    with open(s_path, "rb") as f:
                        stego_bytes = f.read()
                    selected_filename = sample_name

            if not stego_bytes:
                flash("Vui lòng tải lên ảnh hoặc chọn một ảnh mẫu", "error")
                return redirect(url_for("benchmark"))

            if not secret_text:
                secret_text = "Watermark Test"
            calc_bits = len(secret_text.encode("utf-8")) * 8
            bits_len = max(bits_len, calc_bits)

            attack_results = mt.run_attack_benchmark(stego_bytes, secret_text, bits_len)
            flash("Đã hoàn thành 5 phép thử nghiệm tấn công khảo sát!", "success")

        except Exception as e:
            flash(f"Lỗi chạy thử nghiệm: {str(e)}", "error")

    elif selected_filename:
        target_path = os.path.join(app.config["UPLOAD_FOLDER"], selected_filename)
        if not os.path.exists(target_path):
            target_path = os.path.join(BASE_DIR, "static", "uploads", selected_filename)
        if os.path.exists(target_path):
            with open(target_path, "rb") as f:
                img_data = f.read()
            h, rec = bc.verify_image(img_data)
            if rec:
                bits_len = rec.get("bits_length", 160)
                params = rec.get("stego_params") or {}
                extracted = wm.extract_watermark_lsb(
                    img_data,
                    bits_len,
                    channel=params.get("channel", "G"),
                    bit_depth=params.get("bit_depth", 1)
                )
                secret_text = extracted

    return render_template(
        "benchmark.html",
        available_samples=available_samples,
        selected_filename=selected_filename,
        secret_text=secret_text,
        bits_len=bits_len,
        attack_results=attack_results
    )

@app.route("/ledger")
def ledger_view():
    """Khám phá Sổ cái Blockchain (Ledger Explorer)"""
    q = request.args.get("q", "").strip()
    records = bc.search_records(q)
    stats = bc.get_stats()
    return render_template("ledger.html", records=records, stats=stats, query=q)

@app.route("/theory")
def theory():
    """Báo cáo Cơ sở Lý thuyết phục vụ đề tài nghiên cứu"""
    return render_template("theory.html")

@app.route("/view-upload/<path:filename>")
def view_upload(filename):
    """Xem ảnh trực tiếp (tương thích cả /tmp/uploads trên Vercel và static/uploads)"""
    safe_name = os.path.basename(filename)
    path = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
    if not os.path.exists(path):
        repo_path = os.path.join(BASE_DIR, "static", "uploads", safe_name)
        if os.path.exists(repo_path):
            path = repo_path
        else:
            return "File not found", 404
    return send_file(path, mimetype="image/png")

@app.route("/download/<path:filename>")
def download_file(filename):
    """Tải tệp ảnh đã watermark về máy"""
    try:
        safe_name = os.path.basename(filename)
        path = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)

        if not os.path.exists(path):
            repo_path = os.path.join(BASE_DIR, "static", "uploads", safe_name)
            if os.path.exists(repo_path):
                path = repo_path
            else:
                flash("Tệp tin không tồn tại hoặc đã bị xóa", "error")
                return redirect(url_for("index"))

        return send_file(
            path,
            as_attachment=True,
            download_name=safe_name,
            mimetype="image/png"
        )
    except Exception as e:
        flash(f"Lỗi khi tải file: {str(e)}", "error")
        return redirect(url_for("index"))

@app.route("/api/records")
def api_records():
    return jsonify({
        "status": "success",
        "data": bc.get_all_records()
    })

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "is_vercel": IS_VERCEL,
        "upload_folder": app.config["UPLOAD_FOLDER"],
        "total_records": len(bc.get_all_records())
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Hệ thống Khảo sát Giấu tin đang chạy tại http://127.0.0.1:{port}")
    app.run(debug=True, host="127.0.0.1", port=port)
