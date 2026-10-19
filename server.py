#!/usr/bin/env python3
"""FoodQ class demonstration: HTML frontend + standard-library Python REST API + SQLite.
Run `python3 server.py`, then visit http://127.0.0.1:8877.
Local demonstration only. Not secure for public internet deployment.
"""
from __future__ import annotations
import json
import os
import re
import sqlite3
import sys
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parent
DB_FILE = Path(os.environ.get('FOODQ_DB_PATH', str(BASE / 'foodq.sqlite3')))
HTML = BASE / 'index.html'
HOST = os.environ.get('FOODQ_HOST', '0.0.0.0' if os.environ.get('PORT') else '127.0.0.1')
PORT = int(os.environ.get('PORT', os.environ.get('FOODQ_PORT', '8877')))
CAPACITY = 10
SLOTS = [f'{hour:02d}:{minute:02d}' for hour in range(10,14) for minute in (0,15,30,45)]
# The menu IDs mirror those already defined in the original FoodQ HTML frontend.
STORES = [
    (1,'ร้านกะเพราพี่ต้น'), (2,'ร้านข้าวมันไก่'), (3,'ร้านก๋วยเตี๋ยวป้าน้อย'), (4,'ร้านน้ำและขนม')
]
MENUS = [
    (101,1,'ข้าวกะเพราหมูสับ',45),(102,1,'ข้าวกะเพราไก่',45),(103,1,'ไข่ดาว',10),
    (201,2,'ข้าวมันไก่ต้ม',50),(202,2,'ข้าวมันไก่ทอด',55),
    (301,3,'ก๋วยเตี๋ยวหมูน้ำใส',45),(302,3,'ก๋วยเตี๋ยวต้มยำ',50),
    (401,4,'ชาไทยเย็น',30),(402,4,'น้ำเปล่า',10),
]
STATES = {'pending':'accepted','accepted':'preparing','preparing':'ready','ready':'completed'}

class ApiError(Exception):
    def __init__(self, message: str, status: int = 400):
        self.status = status
        super().__init__(message)

def db_conn():
    con = sqlite3.connect(DB_FILE, timeout=10, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA busy_timeout=10000')
    con.execute('PRAGMA foreign_keys=ON')
    return con

def setup():
    with db_conn() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, is_open INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS menus (
            id INTEGER PRIMARY KEY, store_id INTEGER NOT NULL REFERENCES stores(id),
            name TEXT NOT NULL, price INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT NOT NULL, student TEXT NOT NULL,
            store_id INTEGER NOT NULL REFERENCES stores(id),
            pickup_date TEXT NOT NULL, pickup_time TEXT NOT NULL,
            status TEXT NOT NULL, total INTEGER NOT NULL,
            qty INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            UNIQUE(store_id,pickup_date,number)
        );
        CREATE TABLE IF NOT EXISTS order_items (
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            menu_id INTEGER NOT NULL REFERENCES menus(id),
            name TEXT NOT NULL, price INTEGER NOT NULL, qty INTEGER NOT NULL,
            PRIMARY KEY(order_id,menu_id)
        );
        CREATE TABLE IF NOT EXISTS counters (
            store_id INTEGER NOT NULL, pickup_date TEXT NOT NULL, last_seq INTEGER NOT NULL,
            PRIMARY KEY(store_id,pickup_date)
        );
        CREATE INDEX IF NOT EXISTS idx_order_capacity ON orders(store_id,pickup_date,pickup_time,status);
        ''')
        con.executemany('INSERT OR IGNORE INTO stores(id,name) VALUES(?,?)', STORES)
        con.executemany('INSERT OR IGNORE INTO menus(id,store_id,name,price) VALUES(?,?,?,?)', MENUS)

def now(): return datetime.now().isoformat(timespec='seconds')

def order_dict(con, row):
    items = [dict(r) for r in con.execute('SELECT menu_id AS id, name, price, qty FROM order_items WHERE order_id=? ORDER BY menu_id',(row['id'],))]
    return {
        'id':str(row['id']), 'number':row['number'], 'student':row['student'],
        'storeId':row['store_id'], 'date':row['pickup_date'], 'pickup':row['pickup_time'],
        'status':row['status'], 'total':row['total'], 'items':items,
        'createdAt':row['created_at'], 'updatedAt':row['updated_at'],
    }

def safe_int(value):
    if isinstance(value,bool): raise ValueError()
    if isinstance(value,float) and not value.is_integer(): raise ValueError()
    return int(value)

class Handler(BaseHTTPRequestHandler):
    server_version = 'FoodQDemo/1.0'
    def log_message(self, fmt, *args):
        print('[FoodQ]', fmt % args)
    def send_json(self, obj, code=200):
        raw = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Length',str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def body(self):
        try: size=int(self.headers.get('Content-Length','0'))
        except ValueError: raise ApiError('Content-Length ไม่ถูกต้อง')
        if size<=0 or size>30000: raise ApiError('ขนาดคำขอไม่ถูกต้อง',413)
        try: obj=json.loads(self.rfile.read(size).decode('utf-8'))
        except (ValueError,UnicodeDecodeError): raise ApiError('ข้อมูล JSON ไม่ถูกต้อง')
        if not isinstance(obj,dict): raise ApiError('ต้องส่งข้อมูลแบบ JSON object')
        return obj
    def dispatch(self, action):
        try: action()
        except ApiError as e: self.send_json({'error':str(e)},e.status)
        except (sqlite3.Error, OSError) as e:
            print('Backend error:',repr(e));self.send_json({'error':'เกิดข้อผิดพลาดในฐานข้อมูล'},500)
    def do_GET(self): self.dispatch(self.get)
    def do_POST(self): self.dispatch(self.post)
    def do_PATCH(self): self.dispatch(self.patch)
    def get(self):
        p=urlsplit(self.path).path
        if p in ('/','/index.html'):
            raw=HTML.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.end_headers();self.wfile.write(raw);return
        if p=='/api/health':
            with db_conn() as con: con.execute('SELECT 1').fetchone()
            return self.send_json({'ok':True,'backend':'Python standard library','database':'SQLite','port':PORT})
        if p=='/api/state':
            with db_conn() as con:
                orders=[order_dict(con,r) for r in con.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 500')]
            return self.send_json({'mode':'backend','publicDemo': bool(os.environ.get('PORT') or os.environ.get('FOODQ_PUBLIC') == '1'),'stores':[{'id':i,'name':n} for i,n in STORES], 'menus':[{'id':i,'storeId':sid,'name':n,'price':pr} for i,sid,n,pr in MENUS], 'orders':orders})
        if p=='/favicon.ico':
            self.send_response(204);self.end_headers();return
        self.send_json({'error':'ไม่พบ API นี้'},404)
    def post(self):
        p=urlsplit(self.path).path
        if p=='/api/orders': return self.create(self.body())
        if p=='/api/reset':
            # Public deployments are for classroom testing: do not allow unauthenticated deletion.
            if os.environ.get('PORT') or os.environ.get('FOODQ_PUBLIC') == '1':
                raise ApiError('ปิดการล้างข้อมูลบนเซิร์ฟเวอร์สาธารณะ', 403)
            with db_conn() as con:
                con.execute('BEGIN IMMEDIATE')
                con.execute('DELETE FROM order_items')
                con.execute('DELETE FROM orders')
                con.execute('DELETE FROM counters')
                con.commit()
            return self.send_json({'ok':True})
        raise ApiError('ไม่พบ API นี้',404)
    def create(self, body):
        student=str(body.get('student','')).strip()
        if not (2<=len(student)<=70):raise ApiError('กรุณากรอกชื่อนักศึกษาอย่างน้อย 2 ตัวอักษร')
        try: sid=safe_int(body.get('storeId'))
        except (TypeError,ValueError):raise ApiError('ร้านอาหารไม่ถูกต้อง')
        if sid not in {x[0] for x in STORES}:raise ApiError('ไม่พบร้านอาหาร')
        day=body.get('date'); pickup=body.get('pickup')
        try: dt=date.fromisoformat(day)
        except (ValueError,TypeError):raise ApiError('วันที่รับอาหารไม่ถูกต้อง')
        if dt not in {date.today()+timedelta(days=d) for d in range(3)}:raise ApiError('เลือกจองได้เฉพาะวันนี้และอีก 2 วัน')
        if pickup not in SLOTS:raise ApiError('ช่วงเวลารับอาหารไม่ถูกต้อง')
        items=body.get('items')
        if not isinstance(items,list) or not (1<=len(items)<=10):raise ApiError('กรุณาเลือกเมนู 1–10 รายการ')
        normalized={}
        for item in items:
            if not isinstance(item,dict):raise ApiError('รูปแบบเมนูอาหารไม่ถูกต้อง')
            try: mid=safe_int(item['id']);q=safe_int(item['qty'])
            except (KeyError,TypeError,ValueError):raise ApiError('รหัสเมนูหรือจำนวนไม่ถูกต้อง')
            if q<1 or q>10:raise ApiError('จำนวนอาหารต่อเมนูต้องอยู่ระหว่าง 1–10')
            normalized[mid]=normalized.get(mid,0)+q
        qty=sum(normalized.values())
        if qty>CAPACITY:raise ApiError('หนึ่งออร์เดอร์ต้องไม่เกิน 10 จาน')
        with db_conn() as con:
            try:
                con.execute('BEGIN IMMEDIATE')
                shop=con.execute('SELECT is_open FROM stores WHERE id=?',(sid,)).fetchone()
                if not shop or not shop['is_open']:raise ApiError('ร้านปิดรับจองในขณะนี้',409)
                mids=','.join('?' for _ in normalized)
                selected=list(con.execute(f'SELECT * FROM menus WHERE store_id=? AND id IN ({mids})',[sid,*normalized.keys()]))
                if len(selected)!=len(normalized):raise ApiError('มีเมนูอาหารที่ไม่ใช่ของร้านนี้')
                used=con.execute('SELECT COALESCE(SUM(qty),0) FROM orders WHERE store_id=? AND pickup_date=? AND pickup_time=? AND status != ?', (sid,day,pickup,'cancelled')).fetchone()[0]
                if used+qty>CAPACITY:raise ApiError('ช่วงเวลานี้เหลือคิวไม่เพียงพอ กรุณาเลือกเวลาใหม่',409)
                existing=con.execute('SELECT last_seq FROM counters WHERE store_id=? AND pickup_date=?',(sid,day)).fetchone()
                sequence=(existing['last_seq'] if existing else 0)+1
                con.execute('INSERT INTO counters(store_id,pickup_date,last_seq) VALUES(?,?,?) ON CONFLICT(store_id,pickup_date) DO UPDATE SET last_seq=excluded.last_seq',(sid,day,sequence))
                number=f'{chr(64+sid)}-{sequence:03d}'
                cost=sum(row['price']*normalized[row['id']] for row in selected)
                timestamp=now()
                cursor=con.execute('INSERT INTO orders(number,student,store_id,pickup_date,pickup_time,status,total,qty,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)', (number,student,sid,day,pickup,'pending',cost,qty,timestamp,timestamp))
                oid=cursor.lastrowid
                con.executemany('INSERT INTO order_items(order_id,menu_id,name,price,qty) VALUES(?,?,?,?,?)',[(oid,m['id'],m['name'],m['price'],normalized[m['id']]) for m in selected])
                obj=order_dict(con,con.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone())
                con.commit()
                return self.send_json({'order':obj},201)
            except Exception:
                if con.in_transaction:con.rollback()
                raise
    def patch(self):
        p=urlsplit(self.path).path
        m=re.fullmatch(r'/api/orders/(\d+)/status',p)
        if not m:raise ApiError('ไม่พบ API นี้',404)
        status=self.body().get('status')
        if status not in {*STATES.values(),'cancelled'}:raise ApiError('สถานะไม่ถูกต้อง')
        with db_conn() as con:
            try:
                con.execute('BEGIN IMMEDIATE')
                row=con.execute('SELECT * FROM orders WHERE id=?',(int(m[1]),)).fetchone()
                if not row:raise ApiError('ไม่พบหมายเลขคิว',404)
                prior=row['status']
                if not (STATES.get(prior)==status or (status=='cancelled' and prior in ('pending','accepted'))):
                    raise ApiError('เปลี่ยนสถานะไม่ถูกต้องตามลำดับกระบวนการ',409)
                con.execute('UPDATE orders SET status=?,updated_at=? WHERE id=?',(status,now(),int(m[1])))
                obj=order_dict(con,con.execute('SELECT * FROM orders WHERE id=?',(int(m[1]),)).fetchone())
                con.commit()
                return self.send_json({'order':obj})
            except Exception:
                if con.in_transaction:con.rollback()
                raise

if __name__=='__main__':
    setup()
    try:
        server=ThreadingHTTPServer((HOST,PORT), Handler)
    except OSError as e:
        print(f'ไม่สามารถเริ่ม FoodQ ที่พอร์ต {PORT}: {e}',file=sys.stderr)
        print('ลองปิดหน้าต่าง FoodQ ที่เปิดอยู่ แล้วรันใหม่ หรือใช้ FOODQ_PORT=8878 python3 server.py', file=sys.stderr)
        sys.exit(1)
    print('\nFoodQ เชื่อมต่อ Frontend + Backend + SQLite แล้ว')
    print(f'เปิดเว็บที่ http://{"127.0.0.1" if HOST == "0.0.0.0" else HOST}:{PORT}\n')
    try: server.serve_forever()
    except KeyboardInterrupt: print('\nปิด FoodQ แล้ว')
    finally: server.server_close()
