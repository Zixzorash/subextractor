import streamlit as st
import cv2
import easyocr
import tempfile
import os
import numpy as np

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="SubExtractor AI", page_icon="🎬")

st.title("🎬 SubExtractor: ดึงซับฝังจากวิดีโอ")
st.markdown("อัปโหลดวิดีโอ > เลือกตำแหน่งซับ > AI แกะข้อความ > ดาวน์โหลดไฟล์ .SRT")

# 1. ส่วนอัปโหลดไฟล์
uploaded_file = st.file_uploader("เลือกไฟล์วิดีโอ (MP4, MKV, AVI)", type=['mp4', 'mkv', 'avi', 'mov'])

# ฟังก์ชันแปลงวินาทีเป็นรูปแบบ SRT (00:00:00,000)
def format_timestamp(seconds):
    millisec = int((seconds - int(seconds)) * 1000)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millisec:03}"

if uploaded_file is not None:
    # บันทึกไฟล์ชั่วคราวเพื่อให้ OpenCV อ่านได้
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_file.read())
    video_path = tfile.name

    # เปิดวิดีโอเพื่อดูตัวอย่าง
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = total_frames / fps

    st.info(f"ความยาววิดีโอ: {duration:.2f} วินาที | FPS: {fps:.2f}")

    # 2. ตั้งค่าการอ่าน (Config)
    col1, col2 = st.columns(2)
    with col1:
        langs = st.multiselect("เลือกภาษาของซับไตเติล", ['en', 'th', 'ch_sim', 'ja'], default=['en', 'th'])
    with col2:
        # เลือกความถี่ในการสแกน (เพื่อความเร็ว)
        scan_interval = st.slider("ความละเอียด (สแกนทุกๆ กี่วินาที)", 0.5, 5.0, 1.0)

    # 3. เลือกพื้นที่ซับ (Crop Area) - เพื่อให้ AI ทำงานเร็วขึ้นและแม่นยำขึ้น
    st.write("---")
    st.subheader("✂️ ระบุตำแหน่งซับไตเติล (ช่วยให้ AI แม่นยำขึ้น)")
    
    # อ่านเฟรมตัวอย่างจากกลางเรื่องมาแสดง
    cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 2)
    ret, frame_sample = cap.read()
    if ret:
        frame_sample = cv2.cvtColor(frame_sample, cv2.COLOR_BGR2RGB)
        height, width, _ = frame_sample.shape
        
        # Slider เลือกพื้นที่แนวตั้ง (Y-axis)
        crop_range = st.slider("ปรับแถบนี้ให้ครอบคลุมแค่ส่วนที่เป็นซับไตเติล", 0, height, (int(height*0.75), height))
        
        # วาดเส้นสีแดงแสดงพื้นที่ที่เลือก
        preview_img = frame_sample.copy()
        cv2.rectangle(preview_img, (0, crop_range[0]), (width, crop_range[1]), (255, 0, 0), 2)
        st.image(preview_img, caption="พื้นที่ในกรอบสีแดงจะถูกส่งให้ AI อ่าน", use_container_width=True)

    # 4. ปุ่มเริ่มทำงาน
    if st.button("🚀 เริ่มดึงข้อความ (Start Extraction)"):
        reader = easyocr.Reader(langs) # โหลด AI
        srt_content = ""
        subtitle_index = 1
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # ลูปอ่านวิดีโอ
        current_sec = 0
        last_text = ""
        
        while current_sec < duration:
            # คำนวณเฟรมที่จะอ่าน
            frame_id = int(current_sec * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
            ret, frame = cap.read()
            
            if not ret:
                break

            # ตัดเฉพาะส่วนซับไตเติล
            cropped = frame[crop_range[0]:crop_range[1], :]
            
            # ให้ AI อ่าน (OCR)
            result = reader.readtext(cropped, detail=0)
            text = " ".join(result).strip()
            
            # ถ้ามีข้อความและไม่ซ้ำกับบรรทัดก่อนหน้า
            if text and text != last_text:
                start_time = format_timestamp(current_sec)
                end_time = format_timestamp(current_sec + scan_interval)
                
                srt_block = f"{subtitle_index}\n{start_time} --> {end_time}\n{text}\n\n"
                srt_content += srt_block
                
                # แสดงผลสดๆ
                status_text.code(f"[{start_time}] {text}")
                
                last_text = text
                subtitle_index += 1
            
            current_sec += scan_interval
            progress_bar.progress(min(current_sec / duration, 1.0))

        st.success("✅ เสร็จเรียบร้อย!")
        
        # 5. ปุ่มดาวน์โหลด
        st.download_button(
            label="⬇️ ดาวน์โหลดไฟล์ .SRT",
            data=srt_content,
            file_name="extracted_subtitles.srt",
            mime="text/plain"
        )
            
    cap.release()
    os.remove(video_path) # ลบไฟล์ temp
