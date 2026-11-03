import os
import re
import json
import random
import time
from datetime import datetime
import streamlit as st
from lesson.lesson_planner import generate_lesson_plan, render_lesson_plan
from processing.embedding import embed_chunks_parallel
from lesson.section_detector import detect_sections
from lesson.chunker import chunk_sections
from lesson.vector_store import SimpleVectorStore
from utils.html_safe import safe_html
import time

from config import (
    QUESTION_TYPE_ORDER,
)

from io_utils import (
    read_docx, read_pdf, load_json, save_json, 
    load_questions_db, save_questions_db, delete_questions_db, clear_all_questions_db,
    register_user_db, get_credentials_from_db,
    load_all_subjects_db, add_subject_db, delete_subject_db,
    get_all_users_info, update_user_role_db, delete_user_db,
    save_test_db, load_tests_db, delete_test_db,
    save_lesson_db, load_lessons_db, delete_lesson_db
)

import streamlit_authenticator as stauth

from pipeline.generation import generate_questions_pipeline

from questions.normalize import (
    ensure_question_id,
    shuffle_mcq_options,
    get_mcq_answer_text,
)

from test_builder.sampler import pick
from test_builder.word_export import (
    save_lesson_plan_to_word,
    save_test_to_word,
    save_answer_key_to_word,
)

if "generated_questions" not in st.session_state:
    st.session_state.generated_questions = []

if "bank_selected_ids" not in st.session_state:
    st.session_state.bank_selected_ids = set()

if "use_selected_bank" not in st.session_state:
    st.session_state.use_selected_bank = False

if "selected_for_test" not in st.session_state:
    st.session_state.selected_for_test = []
    
if "confirm_reset_create_test" not in st.session_state:
    st.session_state.confirm_reset_create_test = False

def reset_create_test_state():
    st.session_state.pop("variants", None)
    st.session_state.use_selected_bank = False
    st.session_state.selected_for_test = []
    st.session_state.bank_selected_ids = set()
    st.rerun()

def sync_generated_questions():
    current_user = st.session_state.get("username", "unknown")
    current_role = st.session_state.get("role", "user")
    
    bank = load_questions_db(current_user, current_role)
    existing_ids = {q.get("id") for q in bank if "id" in q}
    new_additions = False
    
    curr_sub = st.session_state.get("current_subject", "General")
    
    for q in st.session_state.get("generated_questions", []):
        ensure_question_id(q)
        if q["id"] not in existing_ids:
            q["username"] = current_user
            q["subject"] = q.get("subject", curr_sub)        
            q["difficulty"] = q.get("difficulty", "Medium") 
            bank.append(q)
            existing_ids.add(q["id"])
            new_additions = True
            
    if new_additions:
        save_questions_db(bank)
        
    return bank

st.set_page_config(page_title="LLM-Based Teaching Assistant", page_icon="🎓", layout="wide")

credentials = get_credentials_from_db()

authenticator = stauth.Authenticate(
    credentials,
    cookie_name="teaching_assistant_cookie", 
    key="random_signature_key_123",
    cookie_expiry_days=30
)

try:
    authenticator.login()
except Exception as e:
    st.error(e)
    
if not st.session_state.get("authentication_status"):
    keys_to_wipe = [
        "variants", 
        "generated_questions", 
        "bank_selected_ids", 
        "use_selected_bank", 
        "selected_for_test", 
        "active_tab", 
        "role"
    ]
    for key in keys_to_wipe:
        st.session_state.pop(key, None)

auth_status = st.session_state.get("authentication_status")
if auth_status is False:
    st.error("Username/password is incorrect")

if auth_status is None or auth_status is False:
    with st.expander("📝 Don't have an account? Register here", expanded=True):
        with st.form("register_form"):
            reg_user = st.text_input("Choose a Username")
            reg_pass = st.text_input("Choose a Password", type="password")
            
            if st.form_submit_button("Register"):
                if not reg_user or not reg_pass:
                    st.warning("Please fill out both fields.")
                else:
                    success, message = register_user_db(reg_user, reg_pass)
                    if success:
                        st.success(message)
                        time.sleep(2)
                        st.rerun() 
                    else:
                        st.error(f"Registration Failed: {message}")
                        
    st.stop()

elif st.session_state["authentication_status"]:
    username = st.session_state["username"]
    st.session_state.role = credentials["usernames"][username]["role"]
    st.session_state.logged_in = True
    
    st.title("🎓 LLM-Based Teaching Assistant")

    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "Question Generator"

    with st.sidebar:
        st.write(f"👤 Logged in as: **{username.upper()} ({st.session_state.role.upper()})**")
        authenticator.logout("Logout", "sidebar") 
        st.divider()        

        if st.session_state.role == "admin":
            nav_options = {
                "⚙️ Admin Dashboard": "Admin Dashboard",
                "📝 Question Generator": "Question Generator",
                "🗄️ Question Bank": "Question Bank",
                "📄 Create Test": "Create Test",
                "📁 Test Bank": "Test Bank",
                "📅 Lesson Planner": "Lesson Planner",
                "📚 Lesson Bank": "Lesson Bank"
            }
        else: 
            nav_options = {
                "📝 Question Generator": "Question Generator",
                "🗄️ Question Bank": "Question Bank",
                "📄 Create Test": "Create Test",
                "📁 Test Bank": "Test Bank",
                "📅 Lesson Planner": "Lesson Planner",
                "📚 Lesson Bank": "Lesson Bank"
            }
        
        selected_nav = st.radio("Navigation", list(nav_options.keys()), label_visibility="collapsed")
        st.session_state.active_tab = nav_options[selected_nav]
        sync_generated_questions()
        

    if st.session_state.active_tab == "Admin Dashboard":
        st.subheader("⚙️ Admin Dashboard")
        if st.session_state.role != "admin":
            st.error("Unauthorized access. Admin privileges required.")
            st.stop()
            
        tab1, tab2, tab3, tab4 = st.tabs(["👥 Users", "📈 Analytics", "🔍 Backup", "📚 Subjects"])

        with tab1:
            st.markdown("#### User Management")
            
            st.session_state.setdefault("sort_col", "username")
            st.session_state.setdefault("sort_order", "asc")

            users = get_all_users_info()
            reverse_sort = st.session_state.sort_order == "desc"
            users = sorted(users, key=lambda x: x[st.session_state.sort_col], reverse=reverse_sort)
            
            user_arrow = " 🔼" if st.session_state.sort_col == "username" and st.session_state.sort_order == "asc" else (" 🔽" if st.session_state.sort_col == "username" else "")
            role_arrow = " 🔼" if st.session_state.sort_col == "role" and st.session_state.sort_order == "asc" else (" 🔽" if st.session_state.sort_col == "role" else "")

            col_u1, col_u2, col_u3 = st.columns([0.4, 0.3, 0.3])
            
            if col_u1.button(f"USERNAME{user_arrow}", key="sort_user_btn", use_container_width=True):
                if st.session_state.sort_col == "username":
                    st.session_state.sort_order = "desc" if st.session_state.sort_order == "asc" else "asc"
                else:
                    st.session_state.sort_col = "username"
                    st.session_state.sort_order = "asc"
                st.rerun()
                
            if col_u2.button(f"ROLE{role_arrow}", key="sort_role_btn", use_container_width=True):
                if st.session_state.sort_col == "role":
                    st.session_state.sort_order = "desc" if st.session_state.sort_order == "asc" else "asc"
                else:
                    st.session_state.sort_col = "role"
                    st.session_state.sort_order = "asc"
                st.rerun()
                
            col_u3.button("ACTIONS", disabled=True, use_container_width=True)

            for u in users:
                col1, col2, col3 = st.columns([0.4, 0.3, 0.3])
                
                is_superadmin = (u['username'] == 'admin')
                
                col1.markdown(f"<div style='padding-top:8px;'><b>{u['username']}</b></div>", unsafe_allow_html=True)
                
                with col2:
                    if is_superadmin:
                        st.markdown("<div style='padding-top:8px; color: #DC3545;'><b>admin 🔒</b></div>", unsafe_allow_html=True)
                    else:
                        new_role = st.selectbox(
                            "Role", 
                            ["user", "admin"], 
                            index=0 if u['role'] == 'user' else 1, 
                            key=f"role_{u['username']}",
                            label_visibility="collapsed"
                        )
                        if new_role != u['role']:
                            update_user_role_db(u['username'], new_role)
                            st.success(f"Updated {u['username']} to {new_role}")
                            import time
                            time.sleep(1)
                            st.rerun()
                        
                with col3:
                    if not is_superadmin and u['username'] != st.session_state.username: 
                        if st.button("🗑️ Delete", key=f"del_{u['username']}", use_container_width=True):
                            delete_user_db(u['username'])
                            st.rerun()
                            
        with tab2:
            st.markdown("#### System Analytics")
            
            all_questions = load_questions_db(role='admin') 
            all_tests = load_tests_db(role='admin')
            all_lessons = load_lessons_db(role='admin')
            
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("Total Questions", len(all_questions))
            col_m2.metric("Total Tests", len(all_tests))
            col_m3.metric("Total Lessons", len(all_lessons))
            col_m4.metric("Total Users", len(users))
            
            st.divider()
            
            col_r1_1, col_r1_2 = st.columns(2)
            
            with col_r1_1:
                st.markdown("**Questions by User**")
                if all_questions:
                    q_user_counts = {}
                    for q in all_questions:
                        u = q.get("username", "Unknown")
                        q_user_counts[u] = q_user_counts.get(u, 0) + 1
                    st.bar_chart(q_user_counts)
                else:
                    st.info("No questions data.")
                    
            with col_r1_2:
                st.markdown("**Questions by Type**")
                if all_questions:
                    type_counts = {"mcq": 0, "short_answer": 0, "fill_blank": 0}
                    for q in all_questions:
                        t = q.get("type", "unknown")
                        if t in type_counts:
                            type_counts[t] += 1
                        else:
                            type_counts[t] = 1 
                    st.bar_chart(type_counts)
                else:
                    st.info("No questions data.")

            st.markdown("<br>", unsafe_allow_html=True) 

            col_r2_1, col_r2_2 = st.columns(2)
            
            with col_r2_1:
                st.markdown("**Tests by User**")
                if all_tests:
                    test_counts = {}
                    for t in all_tests:
                        u = t.get("username", "Unknown")
                        test_counts[u] = test_counts.get(u, 0) + 1
                    st.bar_chart(test_counts)
                else:
                    st.info("No tests data.")

            st.markdown("<br>", unsafe_allow_html=True)

            col_r3_1, col_r3_2 = st.columns(2)
            
            with col_r3_1:
                st.markdown("**Lessons by User**")
                if all_lessons:
                    l_user_counts = {}
                    for l in all_lessons:
                        u = l.get("username", "Unknown")
                        l_user_counts[u] = l_user_counts.get(u, 0) + 1
                    st.bar_chart(l_user_counts)
                else:
                    st.info("No lessons data.")
                    
            with col_r3_2:
                st.markdown("**Lessons by Type**")
                if all_lessons:
                    lesson_counts = {}
                    for l in all_lessons:
                        lt = l.get("lesson_type", "Unknown")
                        lesson_counts[lt] = lesson_counts.get(lt, 0) + 1
                    st.bar_chart(lesson_counts)
                else:
                    st.info("No lessons data.")

        with tab3:
            st.markdown("#### Database Backup")
            st.write("Download complete JSON snapshots of your system databases.")
            
            import json
            current_date = datetime.now().strftime('%Y%m%d')
            
            col_b1, col_b2, col_b3 = st.columns(3)
            
            with col_b1:
                st.markdown("##### 🗄️ Question Bank")
                if all_questions:
                    json_q = json.dumps(all_questions, indent=2, default=str)
                    st.download_button(
                        label="📥 Download Questions",
                        data=json_q,
                        file_name=f"questions_backup_{current_date}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                else:
                    st.info("Database is empty.")

            with col_b2:
                st.markdown("##### 📁 Test Bank")
                if all_tests:
                    json_t = json.dumps(all_tests, indent=2, default=str)
                    st.download_button(
                        label="📥 Download Tests",
                        data=json_t,
                        file_name=f"tests_backup_{current_date}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                else:
                    st.info("Database is empty.")

            with col_b3:
                st.markdown("##### 📚 Lesson Bank")
                if all_lessons:
                    json_l = json.dumps(all_lessons, indent=2, default=str)
                    st.download_button(
                        label="📥 Download Lessons",
                        data=json_l,
                        file_name=f"lessons_backup_{current_date}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                else:
                    st.info("Database is empty.")
                    
        with tab4:
            st.markdown("#### Manage Global Subjects")
            st.write("Remove obsolete or misspelled subjects from the dropdown list.")
            
            col_sub1, col_sub2 = st.columns([0.5, 0.5])
            with col_sub1:
                all_subs = load_all_subjects_db()
                subj_to_del = st.selectbox("Select Subject to Delete", all_subs, key="del_subj_select")
                
                if st.button("🗑️ Delete Subject", use_container_width=True):
                    if subj_to_del:
                        if subj_to_del == "General":
                            st.error("Cannot delete the default 'General' subject.")
                        else:
                            delete_subject_db(subj_to_del)
                            st.success(f"Removed '{subj_to_del}' from the global dropdown.")
                            st.rerun()
    
    elif st.session_state.active_tab == "Question Generator":
        st.subheader("📝 Question Generator")
        
        existing_subjects = load_all_subjects_db()
        selected_subject = st.selectbox(
            "Subject Name", 
            options=["➕ Type a New Subject..."] + existing_subjects,
            index=1 if len(existing_subjects) > 0 else 0 
        )
        if selected_subject == "➕ Type a New Subject...":
            subject_input = st.text_input("Enter new subject name:", placeholder="e.g., Computer Science...")
        else:
            subject_input = selected_subject
            
        st.session_state.current_subject = subject_input if subject_input.strip() else "General"
        
        uploaded_file = st.file_uploader("Upload DOCX or PDF", type=["docx", "pdf"])

        num_questions = st.number_input("Number of Questions", min_value=1, max_value=50, value=10)

        question_types = st.multiselect("Question Types", ["MCQ", "Short Answer", "Fill in the Blank"], default=["MCQ"])

        st.markdown("##### Difficulty Distribution (%)")
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            diff_easy = st.slider("Easy (%)", min_value=0, max_value=100, value=40, step=5)
        with col_d2:
            diff_medium = st.slider("Medium (%)", min_value=0, max_value=100, value=30, step=5)
        with col_d3:
            diff_hard = st.slider("Hard (%)", min_value=0, max_value=100, value=30, step=5)
            
        total_diff = diff_easy + diff_medium + diff_hard
        if total_diff != 100:
            st.warning(f"Current total is {total_diff}%. The system will automatically normalize this to 100% during generation.")

        st.session_state.diff_distribution = {"Easy": diff_easy, "Medium": diff_medium, "Hard": diff_hard}
        
        col1, col2 = st.columns([0.5, 0.5])
        generate_clicked = col1.button(
            "Generate Questions",
            key="btn_generate_questions",
            use_container_width=True
        )

        reset_clicked = col2.button(
            "Reset",
            key="btn_reset_generator",
            use_container_width=True
        )

        if reset_clicked:
            st.session_state.generated_questions = []
            st.rerun()

        if uploaded_file and generate_clicked:
            add_subject_db(st.session_state.current_subject)
            with st.spinner("Extracting document text..."):
                if uploaded_file.type == "application/pdf":
                    text = read_pdf(uploaded_file)
                else:
                    text = read_docx(uploaded_file)

            if not text.strip():
                st.error("Document is empty.")
                st.stop()

            with st.spinner("Generating questions..."):
                start_time = time.time()
                questions, failures = generate_questions_pipeline(
                    text=text,
                    num_questions=num_questions,
                    selected_labels=question_types,
                    subject=st.session_state.current_subject,     
                    diff_distribution=st.session_state.diff_distribution
                )
                gen_time = time.time() - start_time

            st.session_state.generated_questions = questions
            sync_generated_questions()
                
            if len(questions) == num_questions:
                st.success(f"Generated {len(questions)} questions in {gen_time:.2f} seconds")
            elif len(questions) > 0:
                st.warning(f"Partially generated {len(questions)}/{num_questions} questions in {gen_time:.2f} seconds. The strict AI safety filter removed invalid/hallucinated options because the document context wasn't rich enough.")
                if failures:
                    with st.expander("View Filter Details"):
                        st.write("\n".join(f"- {f}" for f in sorted(set(failures))))
            else:
                st.error(f"Generation failed after {gen_time:.2f} seconds. The document might not contain extractable academic facts.")
                if failures:
                    st.error("\n".join(f"- {f}" for f in sorted(set(failures))))

        if st.session_state.generated_questions:
            st.subheader("Generated Questions")

            for i, q in enumerate(st.session_state.generated_questions, 1):
                q_type = q["type"]

                if q_type == "mcq":
                    answer = get_mcq_answer_text(q)
                    options = "<br>".join(q.get("options", []))
                else:
                    answer = q["answer"]
                    options = ""

                diff = q.get('difficulty', 'Medium')
                diff_color = "#28A745" if diff == "Easy" else ("#DC3545" if diff == "Hard" else "#FFC107")
                diff_badge = f" <span style='background:{diff_color};color:white;padding:2px 8px;border-radius:12px;font-size:12px;margin-left:8px;'>⚡ {diff}</span>"
                
                st.markdown(
                    f"""
                    <div style="border:1px solid #ccc;padding:15px;border-radius:10px;margin-bottom:12px;">
                        <b>Q{i} ({q_type.replace('_',' ').title()}):</b> {diff_badge}
                        <p>{safe_html(q['question'])}</p>
                        <p>{options}</p>
                        <b>Answer:</b> {answer}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    elif st.session_state.active_tab == "Question Bank":
        st.subheader("🗄️ Question Bank")
        bank = load_questions_db(st.session_state.username, st.session_state.role)
        
        all_subjects = sorted(list({q.get("subject", "General") for q in bank}))
        
        search_text = st.text_input("Search question", placeholder="Type keywords here...")
        
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            filter_type = st.selectbox("Filter by Type", ["All", "MCQ", "Short Answer", "Fill Blank"])
        with col_f2:
            filter_subject = st.selectbox("Filter by Subject", ["All"] + all_subjects)
        with col_f3:
            filter_diff = st.selectbox("Filter by Difficulty", ["All", "Easy", "Medium", "Hard"])
        with col_f4:
            time_filter = st.selectbox("Filter by Time", ["All Time", "Today", "Last 7 Days", "Last 30 Days"])
            
        
        filtered_bank = []
        for q in bank:
            if search_text and search_text.lower() not in q["question"].lower():
                continue
                
            type_map = {"MCQ": "mcq", "Short Answer": "short_answer", "Fill Blank": "fill_blank"}
            if filter_type != "All" and q["type"] != type_map.get(filter_type, ""):
                continue
                
            if filter_subject != "All" and q.get("subject", "General") != filter_subject:
                continue
                
            if filter_diff != "All" and q.get("difficulty", "Medium") != filter_diff:
                continue
                
            if time_filter != "All Time" and q.get("created_at"):
                try:
                    ts = q["created_at"]
                    dt = datetime.fromisoformat(ts) if "T" in ts else datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                    now = datetime.now()
                    
                    if time_filter == "Today" and dt.date() != now.date(): continue
                    elif time_filter == "Last 7 Days" and (now - dt).days > 7: continue
                    elif time_filter == "Last 30 Days" and (now - dt).days > 30: continue
                except ValueError:
                    pass 

            filtered_bank.append(q)

        def get_time(q):
            try:
                ts = q.get("created_at", "")
                return datetime.fromisoformat(ts) if "T" in ts else datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            except:
                return datetime.min

        filtered_bank.sort(key=get_time, reverse=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Delete Selected", key="btn_delete_selected", use_container_width=True):
                delete_questions_db(list(st.session_state.bank_selected_ids))
                st.session_state.bank_selected_ids.clear()
                st.success("Deleted selected questions")
                st.rerun()

        with col2:
            if st.button("Delete ALL", key="btn_delete_all", use_container_width=True):
                clear_all_questions_db(st.session_state.username, st.session_state.role)
                st.session_state.bank_selected_ids.clear()
                st.success("Question bank cleared")
                st.rerun()

        with col3:
            if st.button("Send selected to Create Test", key="btn_send_to_create_test", use_container_width=True):
                selected = [q for q in bank if q["id"] in st.session_state.bank_selected_ids]

                if not selected:
                    st.warning("No questions selected")
                else:
                    st.session_state["selected_for_test"] = selected
                    st.session_state["use_selected_bank"] = True
                    
                    st.session_state.active_tab = "Create Test" 
                    
                    st.success(f"Loaded {len(selected)} questions into Create Test")
                    st.rerun()

        st.markdown(f"**Showing {len(filtered_bank)} / {len(bank)} questions**")

        for idx, q in enumerate(filtered_bank, 1):
            qid = q["id"]

            checked = qid in st.session_state.bank_selected_ids

            col_chk, col_body = st.columns([0.05, 0.95])

            with col_chk:
                if st.checkbox(
                    "",
                    value=checked,
                    key=f"select_{qid}"
                ):
                    st.session_state.bank_selected_ids.add(qid)
                else:
                    st.session_state.bank_selected_ids.discard(qid)

            with col_body:
                if q["type"] == "mcq":
                    answer = get_mcq_answer_text(q)
                    options = "<br>".join(q.get("options", []))
                else:
                    answer = q["answer"]
                    options = ""

                owner_badge = f" <span style='background:#007BFF;color:white;padding:2px 8px;border-radius:12px;font-size:12px;margin-left:8px;'>👤 {q.get('username', 'unknown')}</span>" if st.session_state.role == "admin" else ""
                subject_badge = f" <span style='background:#6C757D;color:white;padding:2px 8px;border-radius:12px;font-size:12px;margin-left:8px;'>📚 {q.get('subject', 'General')}</span>"
                
                diff = q.get('difficulty', 'Medium')
                diff_color = "#28A745" if diff == "Easy" else ("#DC3545" if diff == "Hard" else "#FFC107")
                diff_badge = f" <span style='background:{diff_color};color:white;padding:2px 8px;border-radius:12px;font-size:12px;margin-left:8px;'>⚡ {diff}</span>"
                
                st.markdown(
                    f"""
                    <div style="border:1px solid #ddd;padding:12px;border-radius:8px;margin-bottom:10px;">
                        <b>{idx}. {safe_html(q['question'])}</b> 
                        <p>{options}</p>
                        <b>Answer:</b> {answer} <br>
                        <small>Created at: {q.get('created_at', 'Unknown')} </small> 
                        <br> {owner_badge} {subject_badge} {diff_badge}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    elif st.session_state.active_tab == "Create Test":
        st.subheader("📄 Create Test")
        use_selected = st.session_state.get("use_selected_bank", False)
        selected_bank_questions = st.session_state.get("selected_for_test", [])
        
        full_bank = load_questions_db(st.session_state.username, st.session_state.role)
        if not full_bank:
            st.info("Question bank is empty.")
            st.stop()

        if not use_selected:
            st.markdown("##### 1. Test Configuration")
            col_c1, col_c2 = st.columns(2)
            
            all_subjects = sorted(list({q.get("subject", "General") for q in full_bank}))
            
            with col_c1:
                selected_subject = st.selectbox("Select Subject", all_subjects)
                subject_bank = [q for q in full_bank if q.get("subject", "General") == selected_subject]
                st.caption(f"Questions in this subject: **{len(subject_bank)}**")
                
            with col_c2:
                question_types = st.multiselect(
                    "Question Types",
                    ["MCQ", "Short Answer", "Fill in the Blank"],
                    default=["MCQ"]
                )
                type_map = {"MCQ": "mcq", "Short Answer": "short_answer", "Fill in the Blank": "fill_blank"}
                valid_types = [type_map.get(t) for t in question_types]
                
                filtered_bank = [q for q in subject_bank if q.get("type") in valid_types]
                st.caption(f"Available after type filter: **{len(filtered_bank)}**")

            easy_avail = len([q for q in filtered_bank if q.get("difficulty", "Medium") == "Easy"])
            med_avail = len([q for q in filtered_bank if q.get("difficulty", "Medium") == "Medium"])
            hard_avail = len([q for q in filtered_bank if q.get("difficulty", "Medium") == "Hard"])

            st.markdown("##### 2. Difficulty Distribution (%)")
            st.caption(f"Current Pool: **{easy_avail}** Easy | **{med_avail}** Medium | **{hard_avail}** Hard")
            
            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1:
                diff_easy = st.slider("Easy (%)", 0, 100, 25, 5, key="test_easy")
            with col_d2:
                diff_medium = st.slider("Medium (%)", 0, 100, 50, 5, key="test_med")
            with col_d3:
                diff_hard = st.slider("Hard (%)", 0, 100, 25, 5, key="test_hard")

            diff_dist = {"Easy": diff_easy, "Medium": diff_medium, "Hard": diff_hard}
            if sum(diff_dist.values()) != 100:
                st.warning("Difficulty distribution does not equal 100%. The system will automatically normalize it.")
                
        else:
            filtered_bank = selected_bank_questions
            st.info(f"Using {len(filtered_bank)} manually selected questions from the Question Bank.")

        st.markdown("##### 3. Test Details")
        max_possible = len(filtered_bank)
        
        test_name = st.text_input("Test Name", value="")
        
        num_q = st.number_input(
            "Number of questions",
            min_value=1,
            max_value=max(1, max_possible), 
            value=min(10, max_possible) if not use_selected else max_possible,
            disabled=use_selected 
        )
        
        num_variants = st.number_input("Number of variants", 1, 10, 1)

        col_create, col_reset = st.columns([0.5, 0.5])
        with col_create:
            create_clicked = st.button("Create Test", key="btn_create_test", use_container_width=True)
        with col_reset:
            if st.button("Reset", key="btn_reset_create_test", use_container_width=True):
                st.session_state.use_selected_bank = False
                st.session_state.selected_for_test = []
                st.session_state.pop("variants", None)
                st.rerun()
                    
        if create_clicked:
            if not test_name.strip():
                st.error("Please provide a Test Name.")
                st.stop()
            if max_possible == 0:
                st.error("No questions available with the current filters!")
                st.stop()
                
            variants = []

            if use_selected:
                base_pool = selected_bank_questions
                for v in range(num_variants):
                    final = []
                    for q in base_pool:
                        q_copy = json.loads(json.dumps(q))
                        if q_copy["type"] == "mcq":
                            shuffle_mcq_options(q_copy)
                        final.append(q_copy)

                    variants.append({
                        "title": f"Custom Selected Test {v+1}",
                        "questions": final
                    })
                st.session_state.use_selected_bank = False  

            else:
                from questions.quota import compute_diff_quota
                
                for v in range(num_variants):
                    actual_num_q = min(num_q, max_possible)
                    targets = compute_diff_quota(actual_num_q, diff_dist)

                    pools = {
                        "Easy": [q for q in filtered_bank if q.get("difficulty", "Medium") == "Easy"],
                        "Medium": [q for q in filtered_bank if q.get("difficulty", "Medium") == "Medium"],
                        "Hard": [q for q in filtered_bank if q.get("difficulty", "Medium") == "Hard"]
                    }

                    for k in pools: random.shuffle(pools[k])

                    selected = []
                    shortfall = 0

                    for diff in ["Easy", "Medium", "Hard"]:
                        take = min(targets[diff], len(pools[diff]))
                        selected.extend(pools[diff][:take])
                        pools[diff] = pools[diff][take:] 
                        shortfall += (targets[diff] - take)

                    if shortfall > 0:
                        leftovers = pools["Easy"] + pools["Medium"] + pools["Hard"]
                        random.shuffle(leftovers)
                        selected.extend(leftovers[:shortfall])

                    final = []
                    for q in selected:
                        q_copy = json.loads(json.dumps(q))
                        if q_copy["type"] == "mcq":
                            shuffle_mcq_options(q_copy)
                        final.append(q_copy)

                    variants.append({
                        "title": f"Auto Test {v+1}",
                        "questions": final
                    })
            st.session_state["variants"] = variants
            
            save_test_db(st.session_state.username, test_name, variants)
            
            st.success(f"Test '{test_name}' created!")
            
            st.session_state.selected_for_test = []
            st.session_state.bank_selected_ids = set()

        if "variants" in st.session_state:
            for test in st.session_state["variants"]:
                col1, col2 = st.columns(2)

                with col1:
                    st.download_button(
                        "Download Test",
                        save_test_to_word(test, QUESTION_TYPE_ORDER),
                        file_name=f"{test['title']}.docx",
                        use_container_width=True
                    )

                with col2:
                    st.download_button(
                        "Answer Key",
                        save_answer_key_to_word(test),
                        file_name=f"{test['title']}_ANSWER_KEY.docx",
                        use_container_width=True
                    )

    elif st.session_state.active_tab == "Test Bank":
        st.subheader("📁 Test Bank")
        
        saved_tests = load_tests_db(st.session_state.username, st.session_state.role)
        
        if not saved_tests:
            st.info("You haven't generated any tests yet.")
        else:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                search_test = st.text_input("Search by Test Name", placeholder="Type keywords here...")
            with col_f2:
                time_filter_test = st.selectbox("Filter by Time", ["All Time", "Today", "Last 7 Days", "Last 30 Days"], key="time_test")

            filtered_tests = []
            for test in saved_tests:
                if search_test and search_test.lower() not in test['test_name'].lower():
                    continue

                if time_filter_test != "All Time" and test.get("created_at"):
                    try:
                        if isinstance(test["created_at"], datetime):
                            dt = test["created_at"]
                        else:
                            ts = str(test["created_at"])
                            dt = datetime.fromisoformat(ts) if "T" in ts else datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                        
                        now = datetime.now()
                        if time_filter_test == "Today" and dt.date() != now.date(): continue
                        elif time_filter_test == "Last 7 Days" and (now - dt).days > 7: continue
                        elif time_filter_test == "Last 30 Days" and (now - dt).days > 30: continue
                    except Exception:
                        pass
                        
                filtered_tests.append(test)
                
            st.markdown(f"**Showing {len(filtered_tests)} / {len(saved_tests)} tests**")
            
            for test in filtered_tests:
                admin_badge = f" <span style='background:#007BFF;color:white;padding:2px 8px;border-radius:12px;font-size:12px;margin-left:8px;'>👤 {test['username']}</span>" if st.session_state.role == "admin" else ""
                with st.container():
                    st.markdown(f"#### 📄 {test['test_name']}{admin_badge}", unsafe_allow_html=True)
                    st.caption(f"**Variants:** {len(test['variants'])} | **Created on:** {test['created_at']}")
                    
                    col_var, col1, col2, col3, col_spacer = st.columns([0.15, 0.2, 0.2, 0.2, 0.25])
                    
                    num_variants = len(test['variants'])
                    variant_options = [f"Variant {i+1}" for i in range(num_variants)]
                    
                    with col_var:
                        selected_variant_label = st.selectbox(
                            "Select Variant",
                            options=variant_options,
                            key=f"var_select_{test['id']}",
                            label_visibility="collapsed"
                        )
                    selected_idx = int(selected_variant_label.split(" ")[1]) - 1
                    selected_variant = test['variants'][selected_idx]
                    
                    with col1:
                        test_docx = save_test_to_word(selected_variant, QUESTION_TYPE_ORDER) 
                        st.download_button(
                            label="📄 Download Test",
                            data=test_docx,
                            file_name=f"{test['test_name'].replace(' ', '_')}_V{selected_idx+1}_Test.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"dl_test_{test['id']}_{selected_idx}",
                            use_container_width=True
                        )
                        
                    with col2:
                        ans_docx = save_answer_key_to_word(selected_variant)
                        st.download_button(
                            label="🔑 Download Key",
                            data=ans_docx,
                            file_name=f"{test['test_name'].replace(' ', '_')}_V{selected_idx+1}_Answers.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"dl_ans_{test['id']}_{selected_idx}",
                            use_container_width=True
                        )
                    
                    with col3:
                        if st.button("🗑️ Delete", key=f"del_test_{test['id']}", type="secondary", use_container_width=True):
                            delete_test_db(test['id'], st.session_state.username, st.session_state.role)
                            st.success("Test deleted!")
                            st.rerun()
                            
                    st.divider()
    
    elif st.session_state.active_tab == "Lesson Planner":
        st.subheader("📅 Lesson Planner Generator")

        uploaded_file = st.file_uploader(
            "Upload DOCX or PDF (optional)",
            type=["docx", "pdf"],
            key="lesson_file"
        )

        topic = st.text_input("Topic")
        chapter = st.text_input("Chapter / Section (optional)")
        duration = st.text_input("Duration", value="45 minutes")

        style = st.selectbox(
            "Teaching Style",
            ["theory", "practical"]
        )

        lesson_type = st.selectbox(
            "Lesson Type",
            ["lecture", "lab"]
        )

        notes = st.text_area("Additional Notes (e.g., 'first lecture introduction')")

        col_gen_lp, col_res_lp = st.columns([0.5, 0.5])
        with col_gen_lp:
            generate_clicked = st.button("Generate Lesson Plan", use_container_width=True)
        with col_res_lp:
            reset_clicked = st.button("Reset", key="btn_reset_lp", use_container_width=True)

        if reset_clicked:
            st.session_state.pop("lesson_plan", None)
            st.rerun()

        if generate_clicked:
            context = ""
            store = None
            
            final_topic = topic.strip()
            final_chapter = chapter.strip()

            if not final_topic and not final_chapter:
                st.error("Please provide either a Topic or a Chapter/Section.")
                st.stop()

            if uploaded_file:
                with st.spinner("Reading file..."):
                    if uploaded_file.type == "application/pdf":
                        text = read_pdf(uploaded_file)
                    else:
                        text = read_docx(uploaded_file)

                if text.strip():
                    sections = detect_sections(text)
    
                    if not final_topic and final_chapter:

                        query = final_chapter.lower()
                        prefix_pattern = r"^(chapter\s+|section\s+)?0*" + re.escape(query) + r"(\s+|:|\.|$)"
                        
                        for sec in sections:
                            if re.search(prefix_pattern, sec["title"].lower()):
                                final_topic = sec["title"]
                                break

                        if not final_topic and any(c.isalpha() for c in query):
                            for sec in sections:
                                if query in sec["title"].lower():
                                    final_topic = sec["title"]
                                    break
                                
                    if not final_topic:
                        final_topic = final_chapter

                    chunks = chunk_sections(sections, chunk_size=150)

                    def embed_fn(text):
                        return embed_chunks_parallel([text])[0]

                    store = SimpleVectorStore(embed_fn)

                    texts = [c["text"] for c in chunks]
                    vectors = [v.flatten() for v in embed_chunks_parallel(texts)]

                    store.data = []
                    for i, c in enumerate(chunks):
                        store.data.append({
                            "text": c["text"],
                            "source": c["source"],
                            "embedding": vectors[i]
                        })
            else:
                if not final_topic and final_chapter:
                    final_topic = final_chapter

            with st.spinner("Generating lesson plan..."):
                start_time = time.time()
                data = generate_lesson_plan(
                    topic=final_topic,       
                    chapter=final_chapter,      
                    duration=duration,
                    notes=notes,
                    vector_store=store,
                    style=style,
                    lesson_type=lesson_type 
                )
                gen_time = time.time() - start_time

            if "error" in data:
                st.error("Failed to parse lesson plan")
                st.text(data.get("raw", ""))
            else:
                st.markdown(render_lesson_plan(data))
                
                final_name = data.get("title", final_topic if final_topic else "Lesson Plan")
                
                save_lesson_db(
                    username=st.session_state.username, 
                    lesson_name=final_name, 
                    lesson_type=lesson_type.capitalize(), 
                    lesson_data=data
                )
                st.success(f"Lesson plan '{final_name}' created in {gen_time:.2f} seconds and saved to the Lesson Bank!")
        
            st.download_button(
                "Download Lesson Plan",
                save_lesson_plan_to_word(data),
                file_name="lesson_plan.docx"
            )
    
    elif st.session_state.active_tab == "Lesson Bank":
        st.subheader("📚 Lesson Bank")
        
        saved_lessons = load_lessons_db(st.session_state.username, st.session_state.role)
        
        if not saved_lessons:
            st.info("You haven't generated any lesson plans yet.")
        else:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                search_lesson = st.text_input("Search by Lesson Name", placeholder="Type keywords here...")
            with col_f2:
                time_filter_lesson = st.selectbox("Filter by Time", ["All Time", "Today", "Last 7 Days", "Last 30 Days"], key="time_lesson")

            filtered_lessons = []
            for lesson in saved_lessons:
                if search_lesson and search_lesson.lower() not in lesson['lesson_name'].lower():
                    continue

                if time_filter_lesson != "All Time" and lesson.get("created_at"):
                    try:
                        if isinstance(lesson["created_at"], datetime):
                            dt = lesson["created_at"]
                        else:
                            ts = str(lesson["created_at"])
                            dt = datetime.fromisoformat(ts) if "T" in ts else datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                        
                        now = datetime.now()
                        if time_filter_lesson == "Today" and dt.date() != now.date(): continue
                        elif time_filter_lesson == "Last 7 Days" and (now - dt).days > 7: continue
                        elif time_filter_lesson == "Last 30 Days" and (now - dt).days > 30: continue
                    except Exception:
                        pass
                        
                filtered_lessons.append(lesson)
                
            st.markdown(f"**Showing {len(filtered_lessons)} / {len(saved_lessons)} lessons**")
            
            for lesson in filtered_lessons:
                admin_badge = f" <span style='background:#007BFF;color:white;padding:2px 8px;border-radius:12px;font-size:12px;margin-left:8px;'>👤 {lesson['username']}</span>" if st.session_state.role == "admin" else ""
                type_color = "#B0B817" if lesson['lesson_type'].lower() == "lab" else "#FF0000"
                type_badge = f" <span style='background:{type_color};color:white;padding:2px 8px;border-radius:12px;font-size:12px;margin-left:8px;'>{lesson['lesson_type']}</span>"
                
                with st.container():
                    st.markdown(f"#### 📅 {lesson['lesson_name']}{type_badge}{admin_badge}", unsafe_allow_html=True)
                    st.caption(f"**Created on:** {lesson['created_at']}")
                    
                    col1, col2, col_spacer = st.columns([0.25, 0.25, 0.5])
                    
                    with col1:
                        lesson_docx = save_lesson_plan_to_word(lesson['lesson_data']) 
                        st.download_button(
                            label="📄 Download Plan",
                            data=lesson_docx,
                            file_name=f"{lesson['lesson_name'].replace(' ', '_')}_Plan.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"dl_lesson_{lesson['id']}",
                            use_container_width=True
                        )
                        
                    with col2:
                        if st.button("🗑️ Delete", key=f"del_lesson_{lesson['id']}", type="secondary", use_container_width=True):
                            delete_lesson_db(lesson['id'], st.session_state.username, st.session_state.role)
                            st.success("Lesson plan deleted!")
                            st.rerun()
                            
                    st.divider()
            