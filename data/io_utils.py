from docx import Document
import fitz
import json
import os
from typing import Any
import streamlit_authenticator as stauth
import mysql.connector

def read_docx(file):
    doc = Document(file)
    text = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(text)

def read_pdf(file):
    pdf = fitz.open(stream=file.read(), filetype="pdf")
    text = []
    for page in pdf:
        page_text = page.get_text()
        if page_text.strip():
            text.append(page_text)
    return "\n\n".join(text)

def load_json(path: str) -> Any:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

def save_json(path: str, data: Any):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",         
        password="nuocmat1", 
        database="teaching_assistant"
    )

def load_questions_db(username=None, role=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if role == 'admin':
            cursor.execute("SELECT * FROM question_bank ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM question_bank WHERE username = %s ORDER BY created_at DESC", (username,))
            
        rows = cursor.fetchall()
        
        bank = []
        for row in rows:
            q = {
                "id": row["id"],
                "type": row["q_type"],
                "question": row["question_text"],
                "answer": row["answer"],
                "justification": row["justification"],
                "created_at": str(row["created_at"]) if row["created_at"] else None,
                "username": row.get("username", "unknown"),
                "difficulty": row.get("difficulty", "Medium"),
                "subject": row.get("subject", "General")      
            }
            if row["options"]:
                q["options"] = json.loads(row["options"])
            bank.append(q)
            
        return bank
    except Exception as e:
        print(f"Database error: {e}")
        return []
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def save_questions_db(bank):
    if not bank:
        return
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = """
            INSERT INTO question_bank 
            (id, q_type, question_text, answer, options, justification, created_at, username, difficulty, subject)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                question_text=VALUES(question_text),
                answer=VALUES(answer),
                options=VALUES(options),
                justification=VALUES(justification),
                username=VALUES(username),
                difficulty=VALUES(difficulty),
                subject=VALUES(subject);
        """
        
        for q in bank:
            options_json = json.dumps(q["options"]) if q.get("options") else None
            
            created_at = q.get("created_at")
            if created_at and "T" in created_at:
                created_at = created_at.replace("T", " ")[:19]
                
            val = (
                q.get("id"),
                q.get("type"),
                q.get("question"),
                q.get("answer"),
                options_json,
                q.get("justification"),
                created_at,
                q.get("username", "admin"),
                q.get("difficulty", "Medium"),
                q.get("subject", "General")   
            )
            cursor.execute(sql, val)
            
        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def delete_questions_db(ids):
    if not ids:
        return
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        format_strings = ','.join(['%s'] * len(ids))
        cursor.execute(f"DELETE FROM question_bank WHERE id IN ({format_strings})", tuple(ids))
        conn.commit()
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def clear_all_questions_db(username=None, role=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if role == 'admin':
            cursor.execute("TRUNCATE TABLE question_bank")
        else:
            cursor.execute("DELETE FROM question_bank WHERE username = %s", (username,))
            
        conn.commit()
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            
def register_user_db(username, password):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return False, "Username already exists."
            
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        assigned_role = 'admin' if user_count == 0 else 'user'
            
        hashed_password = stauth.Hasher.hash(password)
        sql = "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)"
        cursor.execute(sql, (username, hashed_password, assigned_role))
        conn.commit()
        
        return True, f"Registration successful! You were registered as an {assigned_role.upper()}."
    except Exception as e:
        print(f"Database error: {e}")
        return False, f"An error occurred: {e}"
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def get_credentials_from_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT username, password, role FROM users")
        rows = cursor.fetchall()
        
        credentials = {"usernames": {}}
        for row in rows:
            credentials["usernames"][row["username"]] = {
                "name": row["username"], 
                "password": row["password"], 
                "role": row["role"] 
            }
            
        return credentials
    except Exception as e:
        print(f"Database error: {e}")
        return {"usernames": {}}
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def load_all_subjects_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM subjects ORDER BY name")
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"Database error: {e}")
        return ["General"]
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def add_subject_db(name):
    if not name or name.strip() == "": 
        return
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT IGNORE INTO subjects (name) VALUES (%s)", (name.strip(),))
        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def delete_subject_db(name):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subjects WHERE name = %s", (name,))
        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            
def get_all_users_info():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT username, role FROM users ORDER BY username")
        return cursor.fetchall()
    except Exception as e:
        print(f"Database error: {e}")
        return []
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def update_user_role_db(username, new_role):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = %s WHERE username = %s", (new_role, username))
        conn.commit()
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def delete_user_db(username):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = %s", (username,))
        conn.commit()
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            
def save_test_db(username, test_name, variants):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        variants_json = json.dumps(variants)
        cursor.execute(
            "INSERT INTO tests_bank (username, test_name, variants_data) VALUES (%s, %s, %s)",
            (username, test_name, variants_json)
        )
        conn.commit()
    except Exception as e:
        print(f"Database error saving test: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def load_tests_db(username=None, role=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if role == 'admin':
            cursor.execute("SELECT * FROM tests_bank ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM tests_bank WHERE username = %s ORDER BY created_at DESC", (username,))
        
        tests = cursor.fetchall()
        for t in tests:
            t['variants'] = json.loads(t['variants_data'])
        return tests
    except Exception as e:
        print(f"Database error loading tests: {e}")
        return []
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def delete_test_db(test_id, username, role):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if role == 'admin':
            cursor.execute("DELETE FROM tests_bank WHERE id = %s", (test_id,))
        else:
            cursor.execute("DELETE FROM tests_bank WHERE id = %s AND username = %s", (test_id, username))
        conn.commit()
    except Exception as e:
        print(f"Database error deleting test: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            
def save_lesson_db(username, lesson_name, lesson_type, lesson_data):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        lesson_json = json.dumps(lesson_data)
        cursor.execute(
            "INSERT INTO lesson_bank (username, lesson_name, lesson_type, lesson_data) VALUES (%s, %s, %s, %s)",
            (username, lesson_name, lesson_type, lesson_json)
        )
        conn.commit()
    except Exception as e:
        print(f"Database error saving lesson: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def load_lessons_db(username=None, role=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if role == 'admin':
            cursor.execute("SELECT * FROM lesson_bank ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM lesson_bank WHERE username = %s ORDER BY created_at DESC", (username,))
        
        lessons = cursor.fetchall()
        for l in lessons:
            l['lesson_data'] = json.loads(l['lesson_data'])
        return lessons
    except Exception as e:
        print(f"Database error loading lessons: {e}")
        return []
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def delete_lesson_db(lesson_id, username, role):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if role == 'admin':
            cursor.execute("DELETE FROM lesson_bank WHERE id = %s", (lesson_id,))
        else:
            cursor.execute("DELETE FROM lesson_bank WHERE id = %s AND username = %s", (lesson_id, username))
        conn.commit()
    except Exception as e:
        print(f"Database error deleting lesson: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()