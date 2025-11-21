# -*- coding: utf-8 -*-
"""
db_store.py - simple SQLite storage for uploads and analyses
schema (single file): analyses(id TEXT PRIMARY KEY, pdf_id, filename, path, result JSON, created_ts)
"""
import sqlite3, json, os, time
DB_PATH = os.path.join(os.getcwd(), "backend", "analyses.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def _conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS analyses(
        id TEXT PRIMARY KEY,
        pdf_id TEXT,
        filename TEXT,
        path TEXT,
        result TEXT,
        created_ts REAL
    )""")
    return conn

def save_analysis(id:str, pdf_id:str, filename:str, path:str, result:dict):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO analyses(id,pdf_id,filename,path,result,created_ts) VALUES(?,?,?,?,?,?)",
                (id,pdf_id,filename,path,json.dumps(result, ensure_ascii=False), time.time()))
    conn.commit()
    conn.close()

def list_analyses(limit=100):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT id,pdf_id,filename,created_ts FROM analyses ORDER BY created_ts DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [{"id":r[0],"pdf_id":r[1],"filename":r[2],"created_ts":r[3]} for r in rows]

def get_analysis(id:str):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT id,pdf_id,filename,path,result,created_ts FROM analyses WHERE id=?", (id,))
    r = cur.fetchone()
    conn.close()
    if not r:
        return None
    return {"id":r[0],"pdf_id":r[1],"filename":r[2],"path":r[3],"result": json.loads(r[4] or "{}"), "created_ts": r[5]}
