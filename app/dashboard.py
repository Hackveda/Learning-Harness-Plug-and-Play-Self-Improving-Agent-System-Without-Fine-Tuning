from __future__ import annotations

import os
import pandas as pd
import requests
import streamlit as st

API = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Learning Harness", page_icon="🧠", layout="wide")
st.title("Learning Harness")
st.caption("Self-improving agent strategies without fine-tuning model weights")

def api_get(path: str):
    response = requests.get(f"{API}{path}", timeout=20)
    response.raise_for_status()
    return response.json()

def api_post(path: str, params=None, json=None):
    response = requests.post(f"{API}{path}", params=params, json=json, timeout=60)
    response.raise_for_status()
    return response.json()

try:
    champion = api_get("/playbook/champion")
except Exception as exc:
    st.error(f"API unavailable: {exc}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Champion version", champion["version"])
c2.metric("Champion score", f'{champion["champion_score"]:.1%}')
c3.metric("Proven rules", len(champion["proven_rules"]))
c4.metric("Trial rules", len(champion["trial_rules"]))

tabs = st.tabs(["Run Episode", "Simulate", "Review", "Rules", "Performance", "Audit"])

with tabs[0]:
    st.subheader("Run one support-routing episode")
    subject = st.text_input("Subject", "Invoice API access request")
    description = st.text_area("Description", "Need an invoice for API usage")
    expected = st.selectbox("Expected queue", ["billing", "technical", "account", "general"])
    if st.button("Run Episode", type="primary"):
        result = api_post(
            "/episodes",
            json={
                "agent_id": "support-routing-agent",
                "input_context": {
                    "subject": subject,
                    "description": description,
                    "expected_queue": expected,
                },
            },
        )
        st.success(f'Outcome: {result["final_outcome"]} · Reward: {result["reward_score"]}')
        st.json(result)

with tabs[1]:
    st.subheader("Generate synthetic episodes")
    count = st.slider("Episodes", 10, 500, 50, 10)
    bias = st.slider("Expected data quality", 0.0, 1.0, 0.9, 0.05)
    if st.button("Run Simulation"):
        result = api_post("/simulate", params={"count": count, "success_bias": bias})
        st.success(f'Created {result["created"]} episodes; average reward {result["average_reward"]:.1%}')

with tabs[2]:
    st.subheader("Evaluate trials and compare challenger against champion")
    improvement = st.number_input("Minimum relative improvement", 0.0, 1.0, 0.02, 0.01)
    min_samples = st.number_input("Minimum sample size", 1, 1000, 10)
    if st.button("Run Reviewer", type="primary"):
        result = api_post(
            "/review",
            params={
                "min_relative_improvement": improvement,
                "min_sample_size": min_samples,
            },
        )
        if result["promoted_to_champion"]:
            st.success(f'New champion: {result["playbook_after"]}')
        else:
            st.warning("Challenger rejected; champion preserved.")
        st.json(result)

with tabs[3]:
    st.subheader("Current strategy playbook")
    st.markdown("#### Fixed reference data")
    st.dataframe(pd.DataFrame(champion["fixed_reference_data"]), use_container_width=True)
    st.markdown("#### Proven rules")
    st.dataframe(pd.DataFrame(champion["proven_rules"]), use_container_width=True)
    st.markdown("#### Trial rules")
    st.dataframe(pd.DataFrame(champion["trial_rules"]), use_container_width=True)

    st.markdown("#### Add trial rule")
    with st.form("new_rule"):
        text = st.text_input("Rule")
        success = st.text_input("Success condition", "Routing matches expected_queue.")
        failure = st.text_input("Failure condition", "Routing differs from expected_queue.")
        window = st.number_input("Evaluation window", 1, 10000, 20)
        min_rate = st.slider("Minimum success rate", 0.0, 1.0, 0.8)
        fail_rate = st.slider("Failure threshold", 0.0, 1.0, 0.2)
        submitted = st.form_submit_button("Create Trial")
        if submitted:
            try:
                result = api_post(
                    "/rules/trial",
                    json={
                        "rule_text": text,
                        "success_condition": success,
                        "failure_condition": failure,
                        "evaluation_window": window,
                        "min_success_rate": min_rate,
                        "max_failure_rate": fail_rate,
                        "high_risk": False,
                        "created_by": "dashboard",
                    },
                )
                st.success(f'Created {result["rule_id"]}')
            except Exception as exc:
                st.error(str(exc))

with tabs[4]:
    episodes = api_get("/episodes?limit=1000")
    if episodes:
        df = pd.DataFrame(episodes)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")
        df["rolling_reward"] = df["reward_score"].rolling(20, min_periods=1).mean()
        st.line_chart(df.set_index("timestamp")[["rolling_reward"]])
        st.dataframe(
            df[["timestamp", "strategy_version", "final_outcome", "reward_score", "latency_ms", "cost"]],
            use_container_width=True,
        )
    else:
        st.info("No episodes yet.")

with tabs[5]:
    audits = api_get("/audits?limit=200")
    st.dataframe(pd.DataFrame(audits), use_container_width=True)
