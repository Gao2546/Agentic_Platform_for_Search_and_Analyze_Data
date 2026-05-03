# UDTP Data Library v2.0 Standard

มาตรฐานการจัดการข้อมูลสำหรับ Agentic Platform โดยเน้นความละเอียดของ Metadata และความยืดหยุ่นในการสืบค้น

## 1. Metadata Schema
ข้อมูลทุกอย่างที่บันทึกผ่าน Library จะมีโครงสร้าง Metadata ใน PostgreSQL (คอลัมน์ `attributes`) ดังนี้:
- `asset_id`: SHA-256 Hash (Deterministic)
- `size_byte`: ขนาดไฟล์
- `mime_type`: ประเภทไฟล์มาตรฐาน
- `custom_metadata`: ข้อมูลเชิงลึกตามประเภทไฟล์
    - **Tabular (CSV/Parquet):** `columns` (List), `row_count`, `column_count`
    - **Image:** `width`, `height`, `channels`, `aspect_ratio`
    - **Video:** `width`, `height`, `fps`, `frame_count`
    - **Text:** `line_count`, `word_count`, `encoding`

## 2. การบันทึกข้อมูล (Save)
Library จะวิเคราะห์เนื้อหาไฟล์โดยอัตโนมัติ Tool ไม่ต้องส่ง Metadata ไปเอง

```python
path = manager.save_data(
    data=df, 
    stage="2_ETL", 
    scope_id=SCOPE_ID, 
    schedule_id=SCH_ID, 
    task_id=TASK_ID,
    file_extension="parquet"
)