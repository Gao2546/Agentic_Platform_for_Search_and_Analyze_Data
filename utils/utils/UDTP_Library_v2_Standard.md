# UDTP Data Library v2.0 Standard

มาตรฐานการจัดการข้อมูลสำหรับ Agentic Platform โดยเน้นความละเอียดของ Metadata และความยืดหยุ่นในการสืบค้น[cite: 1]

## 1. Metadata Schema
ข้อมูลทุกอย่างที่บันทึกผ่าน Library จะมีโครงสร้าง Metadata ใน PostgreSQL (คอลัมน์ `attributes`) ดังนี้:[cite: 1]
- `asset_id`: รหัสประจำไฟล์ในรูปแบบ SHA-256 Hash (Deterministic)[cite: 1, 2]
- `size_byte`: ขนาดไฟล์เป็นไบต์[cite: 1, 2]
- `mime_type`: ประเภทไฟล์มาตรฐาน (เช่น `application/json`, `image/jpeg`, `video/mp4`)[cite: 1, 2]
- `custom_metadata`: ข้อมูลเชิงลึกตามประเภทไฟล์ ซึ่งจะถูกดึงออกมาโดยอัตโนมัติ[cite: 1, 2]
    - **Tabular (CSV/Parquet):** จะเก็บ `columns` (List), `row_count`, `column_count`[cite: 1, 2]
    - **Image (PNG/JPG/JPEG):** จะเก็บ `width`, `height`, `channels`, `aspect_ratio`[cite: 1, 2]
    - **Video (MP4/AVI/MOV):** จะเก็บ `width`, `height`, `fps`, `frame_count`[cite: 1, 2]
    - **Text (TXT):** จะเก็บ `line_count`, `word_count`, `encoding`[cite: 1, 2]

---

## 2. วิธีการใช้งาน Methods และ Arguments

Library จะทำการวิเคราะห์เนื้อหาไฟล์โดยอัตโนมัติ Tool ไม่ต้องส่ง Metadata ไปเอง[cite: 1] คลาสหลักที่ใช้ในการจัดการคือ `UDTPDataManager`[cite: 2]

### 2.1 การบันทึกข้อมูล (`save_data`)
เมธอดนี้ใช้สำหรับบันทึกข้อมูลลง MinIO (S3) และบันทึก Metadata ลง PostgreSQL พร้อมกัน[cite: 2] ข้อมูลที่บันทึกหากซ้ำกับ `asset_id` เดิม จะทำการอัปเดต Metadata ที่เกี่ยวข้องให้อัตโนมัติ (Upsert)[cite: 2]

**Arguments:**
- `data` *(Union[Dict, list, str, bytes])* **[Required]**: เนื้อหาข้อมูลที่ต้องการบันทึก[cite: 2] หากเป็น `dict` หรือ `list` ระบบจะทำความสะอาดและแปลงเป็น JSON ให้อัตโนมัติ[cite: 2]
- `stage` *(str)* **[Required]**: ขั้นตอนของข้อมูลตาม Data Stage Enum ซึ่งเลือกได้ 4 ค่าคือ `"1_RAW"`, `"2_ETL"`, `"3_ANALYZE"`, `"4_VISUALIZE"`[cite: 2, 3]
- `scope_id` *(str)* **[Required]**: รหัส UUID ของ Scope โปรเจกต์[cite: 2, 3]
- `schedule_id` *(str)* **[Required]**: รหัส UUID ของรอบการทำงาน (Schedule)[cite: 2, 3]
- `task_id` *(str)* **[Required]**: รหัส UUID ของงาน (Task)[cite: 2, 3]
- `tags` *(List[str])* **[Optional]**: ลิสต์ของ Tag ที่ต้องการแนบไปกับไฟล์ ค่าเริ่มต้นคือ `None`[cite: 2]
- `file_extension` *(str)* **[Optional]**: นามสกุลไฟล์ที่ต้องการบันทึก ค่าเริ่มต้นคือ `"json"`[cite: 2] ตัวเลือกที่ระบบรองรับในการแยก Metadata ได้แก่ `json`, `csv`, `parquet`, `png`, `jpg`, `jpeg`, `mp4`, `avi`, `mov`, `txt`, `pdf`[cite: 2]

**ตัวอย่างการใช้งาน:**
```python
manager = UDTPDataManager()
path = manager.save_data(
    data=df_bytes,              # หากเป็น DataFrame ควรแปลงเป็น Bytes ก่อน
    stage="2_ETL",              # เลือกจาก '1_RAW', '2_ETL', '3_ANALYZE', '4_VISUALIZE'
    scope_id="uuid-scope-123",  
    schedule_id="uuid-sch-456", 
    task_id="uuid-task-789",
    tags=["clean_data", "finance"], # Optional
    file_extension="parquet"        # Optional
)
```

### 2.2 การค้นหาข้อมูล (`search_data`)
เมธอดนี้ช่วยให้สามารถค้นหาข้อมูลที่บันทึกไว้ได้อย่างยืดหยุ่น โดยสามารถกรองจากคุณสมบัติ (Attributes/Metadata) เฉพาะตัวของไฟล์ หรือกรองตาม Stage และ ID ต่างๆ ได้[cite: 2]

**Arguments:**
- `expected_metadata` *(Dict[str, Any])* **[Optional]**: ระบุ Key-Value ของ Metadata ที่คาดหวังให้อยู่ในไฟล์ (ค้นหาได้ลึกถึง `custom_metadata`) ค่าเริ่มต้นคือ `None`[cite: 2] เช่น `{"row_count": 100}`, `{"aspect_ratio": 1.77}`, หรือ `{"encoding": "utf-8"}`[cite: 2]
- `**kwargs` **[Optional]**: สามารถใส่เงื่อนไขกรองเพิ่มเติมจากระบบ UDTP ได้แก่:[cite: 2]
    - `stage="1_RAW" | "2_ETL" | "3_ANALYZE" | "4_VISUALIZE"`[cite: 2, 3]
    - `scope_id="uuid..."`[cite: 2]
    - `schedule_id="uuid..."`[cite: 2]
    - `task_id="uuid..."`[cite: 2]

**ตัวอย่างการใช้งาน:**
```python
manager = UDTPDataManager()
results = manager.search_data(
    expected_metadata={"column_count": 15, "extension": "csv"}, # กรองด้วย Metadata เชิงลึก
    stage="1_RAW",                                              # กรองเฉพาะ Raw Data
    scope_id="uuid-scope-123"                                   # กรองเฉพาะ Scope นี้
)
```

### 2.3 การลบข้อมูล (`delete_data`)
เมธอดสำหรับลบข้อมูลออกแบบ Hierarchical (ลบแบบลดหลั่นตาม Path) ซึ่งจะลบไฟล์ที่ตรงกับเงื่อนไขออกจาก MinIO S3 และลบ Record ในฐานข้อมูล PostgreSQL พร้อมกัน[cite: 2]

**Arguments:**
- `stage` *(str)* **[Required]**: ระบุ Stage เริ่มต้นในการลบ (`"1_RAW"`, `"2_ETL"`, `"3_ANALYZE"`, `"4_VISUALIZE"`)[cite: 2, 3]
- `scope_id` *(str)* **[Optional]**: รหัส UUID ของ Scope[cite: 2]
- `schedule_id` *(str)* **[Optional]**: รหัส UUID ของ Schedule[cite: 2]
- `task_id` *(str)* **[Optional]**: รหัส UUID ของ Task[cite: 2]
- `asset_id` *(str)* **[Optional]**: ระบุเจาะจงรหัสไฟล์ SHA-256 หากต้องการลบแค่ไฟล์เดียว[cite: 2]

*หมายเหตุ: หากคุณระบุเพียงแค่ `stage` และ `scope_id` ระบบจะทำการลบไฟล์ทั้งหมดที่อยู่ภายใต้ Scope นั้นๆ ในรูปแบบ Wildcard[cite: 2]*

**ตัวอย่างการใช้งาน:**
```python
manager = UDTPDataManager()

# 1. ลบข้อมูลทั้งหมดภายใต้ Scope 
manager.delete_data(stage="2_ETL", scope_id="uuid-scope-123")

# 2. ลบเฉพาะไฟล์เดียวแบบเจาะจง
manager.delete_data(
    stage="2_ETL", 
    scope_id="uuid-scope-123", 
    schedule_id="uuid-sch-456", 
    task_id="uuid-task-789",
    asset_id="abc123hash..."
)
```