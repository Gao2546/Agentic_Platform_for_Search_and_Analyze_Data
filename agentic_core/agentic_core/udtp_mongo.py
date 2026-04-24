def build_mongo_udtp_query(stage: str, scope_ids: list = None, schedule_ids: list = None, tags: list = None) -> dict:
    """
    สร้าง Query Document สำหรับ MongoDB ตามสถาปัตยกรรม UDTP
    Logic: (Scope AND Schedule) OR Tags
    """
    query = {"udtp.stage": stage}
    
    or_conditions = []
    
    # 1. เงื่อนไข Intersection (AND) ของ Scope และ Schedule
    and_conditions = []
    if scope_ids:
        and_conditions.append({"udtp.scope_ids": {"$in": scope_ids}})
    if schedule_ids:
        and_conditions.append({"udtp.schedule_ids": {"$in": schedule_ids}})
        
    if and_conditions:
        or_conditions.append({"$and": and_conditions})
            
    # 2. เงื่อนไข Union (OR) กับ Tags
    if tags:
        or_conditions.append({"udtp.tags": {"$in": tags}})
        
    # รวมเงื่อนไข
    if or_conditions:
        query["$or"] = or_conditions
        
    return query