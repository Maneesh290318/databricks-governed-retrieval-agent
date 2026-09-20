import json
import os
import requests
import streamlit as st
from databricks import sql as dbsql
from databricks.sdk.core import Config

cfg = Config()
DATABRICKS_HOST = cfg.host.replace("https://", "").rstrip("/")
WAREHOUSE_ID = os.environ["DATABRICKS_WAREHOUSE_ID"]
CATALOG_SCHEMA = os.environ.get("CATALOG_SCHEMA", "corrections_health_demo.curated")
MODEL_NAME = os.environ.get("MODEL_NAME", "system.ai.meta-llama-3-3-70b-instruct")
CHAT_ENDPOINT = f"https://{DATABRICKS_HOST}/ai-gateway/mlflow/v1/chat/completions"

ROLE_CONFIG = {
    "Analyst": {
        "data_tool": "get_analyst_data",
        "data_tool_desc": "Look up operational encounter data. No demographic, identifier, or diagnosis-content fields.",
        "system_prompt": "You are an assistant for hospital operations staff. The user's role is Analyst. You may use operational encounter data and governed document search. Do not expose diagnoses, demographics, or identifiers.",
    },
    "Supervisor": {
        "data_tool": "get_supervisor_data",
        "data_tool_desc": "Look up pre-aggregated operational trends. Never row-level patient data.",
        "system_prompt": "You are an assistant for hospital operations leadership. The user's role is Supervisor. Structured data is pre-aggregated by design; never claim access to individual patient records.",
    },
    "Doctor": {
        "data_tool": "get_doctor_data",
        "data_tool_desc": "Look up clinical encounter data including diagnoses, demographics, labs, and medications.",
        "system_prompt": "You are an assistant for physicians. The user's role is Doctor and the governed Doctor tool exposes the project's full clinical encounter view.",
    },
    "Nurse": {
        "data_tool": "get_nurse_data",
        "data_tool_desc": "Look up medication and monitoring data. No diagnosis codes or demographics.",
        "system_prompt": "You are an assistant for nursing staff. The user's role is Nurse. Use medication and monitoring data; diagnoses and demographics are outside this role's scope.",
    },
}

SHARED_TOOL_INSTRUCTION = (
    "\n\nFor protocol, policy, or procedure questions, call search_policy_documents "
    "instead of answering from general knowledge."
)

def run_query(sql_text: str):
    with dbsql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
        credentials_provider=lambda: cfg.authenticate,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_text)
            columns = [c[0] for c in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

def esc(value: str) -> str:
    return value.replace("'", "''")

def execute_tool(tool_name: str, arguments: dict, role: str):
    role_lower = role.lower()
    data_tool_name = ROLE_CONFIG[role]["data_tool"]

    if tool_name == data_tool_name:
        if data_tool_name == "get_supervisor_data":
            value = arguments.get("admission_type_filter")
            arg_sql = f"admission_type_filter => '{esc(value)}'" if value else "admission_type_filter => NULL"
        else:
            value = arguments.get("encounter_id_filter")
            arg_sql = f"encounter_id_filter => {int(value)}" if value else "encounter_id_filter => NULL"
        return run_query(f"SELECT * FROM {CATALOG_SCHEMA}.{data_tool_name}({arg_sql}) LIMIT 20")

    if tool_name == "search_policy_documents":
        query_text = arguments.get("query_text", "")
        return run_query(
            f"SELECT * FROM {CATALOG_SCHEMA}.search_policy_documents("
            f"'{esc(query_text)}', '{esc(role_lower)}')"
        )
    return {"error": f"Unknown tool: {tool_name}"}

def build_tools(role: str):
    data_tool_name = ROLE_CONFIG[role]["data_tool"]
    if data_tool_name == "get_supervisor_data":
        params = {"type": "object", "properties": {"admission_type_filter": {"type": "string", "description": "Optional admission type filter."}}}
    else:
        params = {"type": "object", "properties": {"encounter_id_filter": {"type": "integer", "description": "Optional real encounter ID supplied by the user. Never invent one."}}}

    return [
        {"type": "function", "function": {"name": data_tool_name, "description": ROLE_CONFIG[role]["data_tool_desc"], "parameters": params}},
        {"type": "function", "function": {
            "name": "search_policy_documents",
            "description": "Search governed policy documents and case notes by meaning.",
            "parameters": {"type": "object", "properties": {"query_text": {"type": "string"}}, "required": ["query_text"]},
        }},
    ]

def call_model(messages, role):
    headers = cfg.authenticate()
    headers["Content-Type"] = "application/json"
    tools = build_tools(role)

    for _ in range(5):
        response = requests.post(
            CHAT_ENDPOINT,
            headers=headers,
            json={"model": MODEL_NAME, "max_tokens": 1024, "messages": messages, "tools": tools},
            timeout=60,
        )
        response.raise_for_status()
        choice = response.json()["choices"][0]["message"]
        messages.append(choice)
        tool_calls = choice.get("tool_calls")
        if not tool_calls:
            return choice.get("content", ""), messages

        for tool_call in tool_calls:
            try:
                args = json.loads(tool_call["function"]["arguments"])
            except json.JSONDecodeError:
                args = {}
            try:
                result = execute_tool(tool_call["function"]["name"], args, role)
            except Exception as exc:
                result = {"error": str(exc)}
            messages.append({"role": "tool", "tool_call_id": tool_call["id"], "content": json.dumps(result, default=str)})

    return "Sorry, I couldn't complete that request.", messages

st.set_page_config(page_title="Corrections Health Ops Assistant", layout="centered")
st.title("Corrections Health Operations Assistant")

st.session_state.setdefault("role", None)
st.session_state.setdefault("messages", [])

if st.session_state.role is None:
    st.subheader("Sign in as:")
    for col, role_name in zip(st.columns(4), ROLE_CONFIG):
        if col.button(role_name, use_container_width=True):
            st.session_state.role = role_name
            st.session_state.messages = [{"role": "system", "content": ROLE_CONFIG[role_name]["system_prompt"] + SHARED_TOOL_INSTRUCTION}]
            st.rerun()
else:
    st.caption(f"Signed in as: **{st.session_state.role}**")
    if st.button("Switch role"):
        st.session_state.role = None
        st.session_state.messages = []
        st.rerun()

    for message in st.session_state.messages:
        if message["role"] in ("user", "assistant") and message.get("content"):
            with st.chat_message(message["role"]):
                st.write(message["content"])

    if user_input := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)
        with st.spinner("Thinking..."):
            answer, updated = call_model(st.session_state.messages, st.session_state.role)
            st.session_state.messages = updated
        with st.chat_message("assistant"):
            st.write(answer)
