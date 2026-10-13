"""Streamlit interface for the offline policy assistant."""
from datetime import date

import streamlit as st

from policy_assistant import DEFAULT_AS_OF, ask


st.set_page_config(
    page_title="Policy Assistant",
    page_icon="📘",
    layout="centered",
)

st.title("Merchant Policy Assistant")
st.caption("Ask questions about settlement, MDR, refunds, limits, and account closure.")

with st.sidebar:
    st.header("Answer context")
    as_of = st.date_input(
        "Policy date",
        value=DEFAULT_AS_OF,
        min_value=date(2026, 1, 1),
        help="Amendments are applied according to this date.",
    )
    st.divider()
    st.subheader("Try an example")
    examples = [
        "When does a small merchant receive UPI money?",
        "A large merchant receives a Rs.4,000 UPI payment. What MDR and GST do they pay?",
        "A merchant refunds a customer 3 hours after the sale. Do they get the MDR back?",
        "Can a customer pay Rs.1,00,000 twice in one day to a merchant?",
    ]
    selected_example = st.selectbox("Example question", ["Choose one..."] + examples)

default_question = "" if selected_example == "Choose one..." else selected_example
question = st.text_area(
    "Your question",
    value=default_question,
    height=110,
    placeholder="For example: Does the policy allow me to settle card payments same day?",
)

if st.button("Ask policy assistant", type="primary", use_container_width=True):
    if not question.strip():
        st.warning("Enter a question first.")
    else:
        result = ask(question.strip(), as_of.isoformat())
        status = result["status"]
        status_colors = {
            "ANSWERED": "green",
            "CONFLICT_RESOLVED": "orange",
            "CANNOT_ANSWER": "red",
        }
        color = status_colors.get(status, "gray")
        st.markdown(f":{color}[**{status}**]")
        st.subheader("Answer")
        st.write(result["answer"])

        if result.get("resolution"):
            with st.expander("How the conflict was resolved"):
                st.write(result["resolution"])

        if result.get("citations"):
            with st.expander("Sources"):
                for citation in result["citations"]:
                    st.write(f"- {citation}")