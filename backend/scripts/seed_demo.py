from datetime import date, datetime, timezone
import hashlib
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.db import init_db, connect, execute

def ph(p): return hashlib.sha256(p.encode()).hexdigest()

def seed():
    init_db()
    with connect() as conn:
        cur = conn.cursor()
        users = [
          ("analyst@harborstay.local","林遥","analyst"),
          ("manager@harborstay.local","周岚","customer_manager"),
          ("service@harborstay.local","顾诚","service_coordinator")
        ]
        for email,name,role in users:
            cur.execute("INSERT INTO users(email,full_name,role,password_hash) VALUES(%s,%s,%s,%s) ON CONFLICT(email) DO NOTHING", (email,name,role,ph("rental123")))
        props = [
          ("HS-A-1203","海棠湾 A 座 1203","滨江北岸",5200,12,8.5),
          ("HS-B-0718","海棠湾 B 座 0718","滨江北岸",4600,7,3.0),
          ("HS-C-0206","海棠湾 C 座 0206","老城西区",3900,2,15.0),
          ("HS-D-1502","海棠湾 D 座 1502","新港片区",6100,15,1.5),
        ]
        for code,name,nb,rent,floor,age in props:
            cur.execute("""INSERT INTO properties(code,name,neighborhood,monthly_rent,floor,property_age_years)
              VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(code) DO NOTHING""", (code,name,nb,rent,floor,age))
        cur.execute("SELECT id,code FROM properties")
        pmap = {r['code']:r['id'] for r in cur.fetchall()}
        tenants = [
          ("沈宁","shen.ning@example.local", "HS-A-1203","2025-03-01","2027-02-28","active"),
          ("许川","xu.chuan@example.local", "HS-B-0718","2025-08-15","2027-08-14","active"),
          ("丁婉","ding.wan@example.local", "HS-C-0206","2024-05-01","2026-04-30","moved_out"),
          ("贺涛","he.tao@example.local", "HS-D-1502","2026-01-10","2027-01-09","active"),
          ("唐可","tang.ke@example.local", "HS-A-1203","2026-02-01","2027-01-31","active"),
          ("罗依","luo.yi@example.local", "HS-B-0718","2025-09-01","2027-08-31","active"),
        ]
        for name,email,code,mi,le,status in tenants:
            cur.execute("""INSERT INTO tenants(full_name,email,property_id,move_in_date,lease_end_date,status)
              VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(email) DO NOTHING""", (name,email,pmap[code],mi,le,status))
        cur.execute("SELECT id,email,property_id FROM tenants")
        tmap = {r['email']:(r['id'],r['property_id']) for r in cur.fetchall()}
        events = [
          ("shen.ning@example.local","漏水","urgent","2026-08-03T09:20:00+00:00","2026-08-05T14:20:00+00:00",2.2,3.0,"resolved","阳台窗框渗水，安排密封胶复修"),
          ("shen.ning@example.local","空调","routine","2026-09-11T10:00:00+00:00","2026-09-12T16:00:00+00:00",1.3,4.0,"resolved","滤网清洗并复测制冷"),
          ("xu.chuan@example.local","热水","emergency","2026-08-15T18:00:00+00:00","2026-08-16T10:00:00+00:00",0.7,4.0,"resolved","夜间热水器故障，值班维修"),
          ("ding.wan@example.local","门锁","urgent","2026-02-06T08:30:00+00:00","2026-02-08T09:10:00+00:00",2.0,2.0,"resolved","门锁电池与锁舌更换"),
          ("he.tao@example.local","网络","routine","2026-09-19T12:00:00+00:00",None,None,None,"open","公共区域网络信号弱，等待运营商排查"),
          ("tang.ke@example.local","电梯","urgent","2026-09-21T06:50:00+00:00","2026-09-21T13:00:00+00:00",0.3,4.5,"resolved","早高峰电梯误报，完成控制柜复位"),
          ("luo.yi@example.local","清洁","routine","2026-09-25T11:00:00+00:00","2026-09-26T15:00:00+00:00",1.2,3.5,"resolved","退租保洁后的公共走廊复检"),
        ]
        for email,cat,severity,opened,resolved,duration,score,status,summary in events:
            cur.execute("""INSERT INTO service_events(tenant_id,property_id,category,severity,opened_at,resolved_at,resolution_days,satisfaction_score,status,summary)
              SELECT %s,property_id,%s,%s,%s,%s,%s,%s,%s,%s FROM tenants WHERE id=%s
              AND NOT EXISTS (SELECT 1 FROM service_events WHERE tenant_id=%s AND summary=%s)""", (tmap[email][0],cat,severity,opened,resolved,duration,score,status,summary,tmap[email][0],tmap[email][0],summary))
        surveys = [
          ("shen.ning@example.local","2026-2027",3.8,3.2,3.4,4.1,5.0,"愿意续租，但希望维修进度更透明"),
          ("xu.chuan@example.local","2026-2027",4.4,4.2,3.8,4.0,8.0,"总体满意，愿意续租"),
          ("he.tao@example.local","2026-2027",4.2,3.8,3.2,3.9,6.0,"希望网络问题在续租前解决"),
          ("tang.ke@example.local","2026-2027",4.6,4.5,4.3,4.4,9.0,"体验很好"),
          ("luo.yi@example.local","2026-2027",3.6,3.4,3.2,3.5,4.0,"公共区域清洁频次需要提高"),
          ("shen.ning@example.local","2025-2026",3.7,2.8,3.5,3.9,5.0,"历史租期复盘样本"),
        ]
        for email,period,clean,service,value,community,intent,comment in surveys:
            cur.execute("""INSERT INTO renewal_surveys(tenant_id,lease_period,collected_at,cleanliness_score,service_score,value_score,community_score,renewal_intent,comments)
              SELECT %s,%s,NOW(),%s,%s,%s,%s,%s,%s WHERE NOT EXISTS (SELECT 1 FROM renewal_surveys WHERE tenant_id=%s AND lease_period=%s)""", (tmap[email][0],period,clean,service,value,community,intent,comment,tmap[email][0],period))
        conn.commit()
    print("seed ok")

if __name__ == '__main__': seed()
