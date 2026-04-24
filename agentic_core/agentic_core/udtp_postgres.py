def build_postgres_udtp_where_clause(stage: str, scope_ids: list = None, schedule_ids: list = None, tags: list = None):
    """
    สร้าง WHERE Clause สำหรับ PostgreSQL (ใช้ GIN Index && Operator)
    คืนค่ามาเป็น (SQL_String, Parameter_Dictionary) เพื่อความปลอดภัยจาก SQL Injection
    """
    # ใช้ Named Parameters (เช่น %(stage)s) เพื่อให้ใช้ร่วมกับ psycopg2 ได้ง่าย
    where_clause = "udtp_stage = %(stage)s"
    params = {"stage": stage}

    or_clauses = []

    # 1. เงื่อนไข Intersection (AND)
    and_clauses = []
    if scope_ids:
        and_clauses.append("udtp_scope_ids && %(scope_ids)s::uuid[]")
        params["scope_ids"] = scope_ids
    if schedule_ids:
        and_clauses.append("udtp_schedule_ids && %(schedule_ids)s::uuid[]")
        params["schedule_ids"] = schedule_ids

    if and_clauses:
        or_clauses.append(f"({' AND '.join(and_clauses)})")

    # 2. เงื่อนไข Union (OR)
    if tags:
        or_clauses.append("udtp_tags && %(tags)s::text[]")
        params["tags"] = tags

    # รวมเงื่อนไข
    if or_clauses:
        where_clause += f" AND ({' OR '.join(or_clauses)})"

    return where_clause, params