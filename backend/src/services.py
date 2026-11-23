from datetime import date, timedelta
from .db import query, one, execute
from .analysis import run_analysis

def audit(user, action, entity_type, entity_id, detail):
    execute("INSERT INTO audit_logs(actor_email,action,entity_type,entity_id,detail) VALUES(%s,%s,%s,%s,%s)", (user["email"], action, entity_type, entity_id, detail))

def survey_rows():
    return query("""
      SELECT s.*, t.full_name AS tenant_name, t.status AS tenant_status, t.property_id, t.lease_end_date,
             p.code AS property_code, p.name AS property_name, p.monthly_rent,
             p.property_age_years,
             COALESCE(AVG(se.resolution_days) FILTER (WHERE se.status='resolved'),0) AS service_resolution_days,
             CASE WHEN p.monthly_rent > 0 THEN p.monthly_rent/5000.0 ELSE 0 END AS rent_burden
      FROM renewal_surveys s
      JOIN tenants t ON t.id=s.tenant_id
      JOIN properties p ON p.id=t.property_id
      LEFT JOIN service_events se ON se.tenant_id=t.id
      GROUP BY s.id,t.id,p.id
      ORDER BY s.collected_at DESC
    """)

def build_followups(user):
    rows = survey_rows()
    created = []
    for s in rows:
        if s["tenant_status"] != "active":
            continue
        if s["renewal_intent"] >= 7 and s["service_score"] >= 4:
            continue
        exists = one("SELECT id FROM follow_up_tasks WHERE survey_id=%s", (s["id"],))
        if exists:
            continue
        priority = "high" if s["renewal_intent"] <= 4 or s["service_score"] <= 2 else "medium"
        reason = f"续租意愿 {s['renewal_intent']}/10，服务评分 {s['service_score']}/5"
        task = execute("""INSERT INTO follow_up_tasks(tenant_id,survey_id,task_type,priority,owner,due_date,reason,lease_end_snapshot)
          VALUES(%s,%s,'续租沟通',%s,'customer_manager',CURRENT_DATE + INTERVAL '5 days',%s,%s)
          RETURNING id""", (s["tenant_id"], s["id"], priority, reason, s["lease_end_date"]))
        audit(user, "create_follow_up", "follow_up_task", task["id"], reason)
        created.append(task["id"])
    return created

def get_analysis():
    rows = survey_rows()
    return run_analysis(rows)
