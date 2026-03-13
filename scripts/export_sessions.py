# DO NOT MODIFY THIS FILE

import sqlite3
import os
import json
import sys
import re
from datetime import datetime

DB_PATH = os.path.expanduser("~/.local/share/opencode/opencode.db")

def get_db_connection():
    if not os.path.exists(DB_PATH):
        print(f"Error: OpenCode database not found at {DB_PATH}")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_sessions(conn):
    query = """
        SELECT 
            s.id AS session_id, 
            s.title, 
            s.time_created,
            json_extract(m.data, '$.modelID') AS model
        FROM session s
        JOIN message m ON s.id = m.session_id
        WHERE json_extract(m.data, '$.modelID') IS NOT NULL
        GROUP BY s.id
        ORDER BY s.time_created DESC;
    """
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()

def fetch_parts(conn, message_id):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT data FROM part WHERE message_id = ? ORDER BY time_created ASC;",
        (message_id,)
    )
    parts = []
    for row in cursor.fetchall():
        try:
            parts.append(json.loads(row['data']))
        except json.JSONDecodeError:
            continue
    return parts


def fetch_trajectory(conn, session_id):
    query = "SELECT id, data FROM message WHERE session_id = ? ORDER BY time_created ASC;"
    cursor = conn.cursor()
    cursor.execute(query, (session_id,))

    trajectory = []
    for row in cursor.fetchall():
        try:
            msg = json.loads(row['data'])
            parts = fetch_parts(conn, row['id'])
            if parts:
                msg['parts'] = parts
            trajectory.append(msg)
        except json.JSONDecodeError:
            continue
    return trajectory


def sanitize_filename(title):
    safe_title = re.sub(r'[^a-zA-Z0-9]+', '-', title).strip('-').lower()
    return safe_title[:40] if len(safe_title) > 40 else safe_title


def _flatten_content(items):
    return "\n\n".join(str(s).strip() for s in items if s and str(s).strip())


def _extract_questions_from_tool(part):
    blocks = []
    try:
        inp = part.get("state", {}).get("input") or part.get("input", {})
        for q in inp.get("questions", []):
            qtext = q.get("question") or q.get("header", "")
            if not qtext:
                continue
            lines = [qtext]
            for opt in q.get("options", []):
                label = opt.get("label", "")
                desc = opt.get("description", "")
                if label:
                    lines.append(f"  - {label}" + (f" ({desc})" if desc else ""))
            blocks.append("\n".join(lines))
    except (TypeError, AttributeError):
        pass
    return blocks


def _extract_answers_from_tool(part):
    try:
        state = part.get("state", {})
        meta = state.get("metadata", {})
        answers = meta.get("answers", [])
        if answers:
            inp = state.get("input", {}) or {}
            qs = inp.get("questions", [])
            parts = []
            for i, q in enumerate(qs):
                qtext = q.get("question", "") or q.get("header", "")
                ans = answers[i] if i < len(answers) else []
                ans_str = ", ".join(ans) if isinstance(ans, list) else str(ans)
                if qtext and ans_str:
                    parts.append(f"{qtext}: {ans_str}")
            if parts:
                return "\n".join(parts)
        output = state.get("output", "")
        if output and "User has answered" in output:
            return output
    except (TypeError, AttributeError, IndexError):
        pass
    return ""


def _format_tool_call(part):
    tool = part.get("tool", "")
    if not tool or tool == "question":
        return None
    inp = part.get("state", {}).get("input") or part.get("input") or {}
    if not isinstance(inp, dict):
        return tool
    args = []
    for key in ("path", "file", "command", "paths"):
        val = inp.get(key)
        if val is not None and val != "":
            if isinstance(val, list):
                args.extend(str(v) for v in val)
            else:
                args.append(str(val))
    if "path" not in inp and "file" not in inp:
        for key, val in inp.items():
            if key in ("path", "file", "command", "paths"):
                continue
            if isinstance(val, str) and len(val) < 80:
                args.append(val)
            elif isinstance(val, str):
                args.append(val[:77] + "...")
    return f"{tool} {' '.join(args)}".strip() if args else tool


def simplify_rollout(raw_rollout):
    simplified = []
    turn = 1

    for msg in raw_rollout:
        role = msg.get("role", "")
        parts = msg.get("parts", [])

        if role == "user":
            texts = []
            for p in parts:
                if p.get("type") == "text" and p.get("text"):
                    texts.append(p["text"])
            content = _flatten_content(texts)
            if content:
                simplified.append({"turn": turn, "role": "user", "content": content})
                turn += 1

        elif role == "assistant":
            reasoning_parts = []
            text_parts = []
            question_texts = []
            answer_content = None
            tool_calls = []

            for p in parts:
                ptype = p.get("type", "")
                if ptype == "reasoning" and p.get("text"):
                    reasoning_parts.append(p["text"])
                elif ptype == "text" and p.get("text"):
                    text_parts.append(p["text"])
                elif ptype == "tool" and p.get("tool") == "question":
                    qs = _extract_questions_from_tool(p)
                    question_texts.extend(qs)
                    ans = _extract_answers_from_tool(p)
                    if ans:
                        answer_content = ans
                elif ptype == "tool":
                    tc = _format_tool_call(p)
                    if tc:
                        tool_calls.append(tc)

            content_parts = reasoning_parts + question_texts + text_parts
            content = _flatten_content(content_parts)

            if content:
                obj = {"turn": turn, "role": "assistant", "content": content}
                if tool_calls:
                    obj["tool_calls"] = tool_calls
                simplified.append(obj)
                turn += 1

            if answer_content:
                simplified.append({"turn": turn, "role": "user", "content": answer_content})
                turn += 1

    return simplified


def main():
    print("\nScanning OpenCode database for sessions...\n")
    conn = get_db_connection()
    sessions = fetch_sessions(conn)

    if not sessions:
        print("No sessions found with an associated model.")
        sys.exit(0)

    print(f"{'#':<4} | {'Date':<12} | {'Model':<20} | {'Task Title'}")
    print("-" * 80)
    
    for i, s in enumerate(sessions):
        dt = datetime.fromtimestamp(s['time_created'] / 1000).strftime('%Y-%m-%d')
        title = s['title'] if len(s['title']) < 40 else s['title'][:37] + "..."
        print(f"{i + 1:<4} | {dt:<12} | {s['model']:<20} | {title}")

    print("-" * 80)
    
    print("\nEnter the numbers of the sessions you want to export (comma-separated, e.g., '1, 3, 4')")
    print("Or type 'all' to export everything, or 'q' to quit.")
    
    choice = input("\nYour choice: ").strip().lower()
    
    if choice == 'q':
        print("Exiting.")
        sys.exit(0)

    selected_sessions = []
    if choice == 'all':
        selected_sessions = sessions
    else:
        try:
            indices = [int(x.strip()) - 1 for x in choice.split(',')]
            selected_sessions = [sessions[i] for i in indices if 0 <= i < len(sessions)]
        except ValueError:
            print("Invalid input. Please enter numbers separated by commas.")
            sys.exit(1)

    if not selected_sessions:
        print("No valid sessions selected. Exiting.")
        sys.exit(0)

    print(f"\nExtracting trajectories for {len(selected_sessions)} session(s)...\n")
    
    trajectories = []
    for s in selected_sessions:
        rollout = fetch_trajectory(conn, s['session_id'])
        trajectories.append({
            "model": s['model'],
            "rollout": simplify_rollout(rollout)
        })
        print(f"  Done: {s['model']}: {s['title'][:50]}{'...' if len(s['title']) > 50 else ''}")

    export_data = {"trajectories": trajectories}
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    output_dir = "trajectories"
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"trajectories-{timestamp}.json")

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2)

    print(f"\nSaved {len(trajectories)} trajectory(ies) to: {filename}")
    print("\nExport complete!\n")
    conn.close()

if __name__ == "__main__":
    main()
