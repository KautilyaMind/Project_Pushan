"""API-driven operations and knowledge dashboard for Pushan V0.7."""

from typing import Any

import pandas as pd
import streamlit as st

from frontend.api_client import (
    PushanAPIError,
    ask_knowledge,
    run_agent,
    check_health,
    get_action_history,
    get_decision_history,
    get_fields,
    get_irrigation_recommendation,
    get_sensor_history,
    get_sensor_reading,
)


st.set_page_config(
    page_title="Pushan Agriculture Operations",
    page_icon="🌱",
    layout="wide",
)


def yes_or_no(value: bool) -> str:
    return "YES" if value else "NO"


def render_sensor_status(sensor: dict[str, Any]) -> None:
    """Render current sensor measurements without calculating domain logic."""
    st.subheader("Current Sensor Status")
    columns = st.columns(5)
    columns[0].metric("Soil Moisture", f"{sensor['soil_moisture']:g}%")
    columns[1].metric("Temperature", f"{sensor['temperature']:g} °C")
    columns[2].metric("Humidity", f"{sensor['humidity']:g}%")
    columns[3].metric("Rain Probability", f"{sensor['rain_probability']:g}%")
    columns[4].metric("Water Available", f"{sensor['water_available_litres']:g} L")

    status_columns = st.columns(2)
    status_columns[0].info(f"Pump status: **{sensor['pump_status']}**")
    status_columns[1].info(f"Sensor status: **{sensor['sensor_status']}**")


def render_assessment(assessment: dict[str, Any]) -> None:
    """Render a structured assessment returned by FastAPI."""
    rule = assessment["rule_based"]
    ml_result = assessment["ml"]
    comparison = assessment["comparison"]
    operational = assessment["operational"]

    st.divider()
    st.header("Irrigation Assessment")
    rule_column, ml_column, operation_column = st.columns(3)

    with rule_column:
        st.subheader("Rule-Based Recommendation")
        st.metric("Irrigation Required", yes_or_no(rule["irrigation_required"]))
        st.metric("Recommended Water", f"{rule['recommended_water_litres']:g} L")
        st.metric("Risk Level", rule["risk_level"])
        st.caption(rule["reason"])

    with ml_column:
        st.subheader("ML Advisory Prediction")
        st.metric(
            "Predicted Water",
            f"{ml_result['predicted_water_litres']:g} L",
        )
        st.metric(
            "Difference vs Rule",
            f"{comparison['absolute_difference_litres']:g} L",
        )
        st.metric("Difference", f"{comparison['difference_percentage']:g}%")
        st.caption("Advisory estimate only; it does not control irrigation.")

    with operation_column:
        st.subheader("Operational Decision")
        st.metric(
            "Execution Possible",
            yes_or_no(operational["execution_possible"]),
        )
        st.metric("Action Required", operational["action_required"])
        st.caption(operational["reason"])

    field_id = assessment["field_id"]
    if rule["irrigation_required"] and not operational["execution_possible"]:
        st.warning(
            f"{field_id} requires irrigation, but execution is blocked: "
            f"{operational['action_required']}."
        )
    elif rule["irrigation_required"]:
        st.success(f"{field_id} requires irrigation and execution can proceed.")
    else:
        st.success(f"{field_id} does not currently require irrigation.")


def render_history(
    sensor_records: list[dict[str, Any]],
    decision_records: list[dict[str, Any]],
    action_records: list[dict[str, Any]],
) -> None:
    """Render API histories as readable tables and one useful chart."""
    st.divider()
    st.header("Recent History")
    sensor_tab, decision_tab, action_tab = st.tabs(
        ["Sensor History", "Decision History", "Action History"]
    )

    with sensor_tab:
        if sensor_records:
            sensor_frame = pd.DataFrame(sensor_records)
            visible_columns = [
                "timestamp",
                "soil_moisture",
                "temperature",
                "humidity",
                "rain_probability",
                "pump_status",
                "sensor_status",
            ]
            st.dataframe(sensor_frame[visible_columns], width="stretch")
            chart_frame = sensor_frame[["timestamp", "soil_moisture"]].copy()
            chart_frame["timestamp"] = pd.to_datetime(chart_frame["timestamp"])
            chart_frame = chart_frame.sort_values("timestamp").set_index("timestamp")
            st.subheader("Soil Moisture Over Time")
            st.line_chart(chart_frame)
        else:
            st.info("No sensor history is available for this field yet.")

    with decision_tab:
        if decision_records:
            decision_frame = pd.DataFrame(decision_records)
            st.dataframe(
                decision_frame[
                    [
                        "timestamp",
                        "irrigation_required",
                        "recommended_water_litres",
                        "risk_level",
                    ]
                ],
                width="stretch",
            )
        else:
            st.info("No irrigation decision history is available yet.")

    with action_tab:
        if action_records:
            action_frame = pd.DataFrame(action_records)
            st.dataframe(
                action_frame[
                    ["timestamp", "execution_possible", "action_required", "reason"]
                ],
                width="stretch",
            )
        else:
            st.info("No operational action history is available yet.")


def render_knowledge_assistant() -> None:
    """Render an API-only interface to Pushan's grounded knowledge service."""
    st.divider()
    st.header("Knowledge Assistant")
    st.write("Ask Pushan about irrigation, crop water requirements, or operating procedures.")
    question = st.text_area(
        "Your agriculture question",
        placeholder="What should I check before starting drip irrigation?",
    )
    if st.button("Ask Pushan", type="primary"):
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            try:
                with st.spinner("Searching Pushan's knowledge base..."):
                    response = ask_knowledge(question.strip())
                st.subheader("Answer")
                st.write(response["answer"])
                st.subheader("Sources")
                for source in response.get("sources", []):
                    st.markdown(f"- `{source}`")
            except (PushanAPIError, KeyError, TypeError) as error:
                st.error(f"Knowledge request unavailable: {error}")


def render_pushan_agent() -> None:
    """Render controlled LangGraph orchestration through FastAPI."""
    st.divider()
    st.header("Pushan Agent")
    st.write("Coordinate field assessment and agriculture knowledge in one controlled workflow.")
    message = st.text_area(
        "Agent request",
        placeholder="Analyse FIELD_001 and explain whether irrigation should run.",
        key="agent_request",
    )
    if st.button("Run Agent", type="primary"):
        if not message.strip():
            st.warning("Please enter an agent request.")
            return
        try:
            with st.spinner("Running Pushan's controlled workflow..."):
                response = run_agent(message.strip())
            st.subheader("Final Answer")
            st.write(response["answer"])
            st.caption(f"Intent: {response['intent']}")
            with st.expander("Execution Trace"):
                for index, step in enumerate(response.get("execution_trace", []), 1):
                    st.write(f"{index}. {step}")
            if response.get("sources"):
                st.subheader("Sources")
                for source in response["sources"]:
                    st.markdown(f"- `{source}`")
            if response.get("errors"):
                st.warning("\n".join(response["errors"]))
        except (PushanAPIError, KeyError, TypeError) as error:
            st.error(f"Agent request unavailable: {error}")


def run_dashboard() -> None:
    """Load backend data and render the complete dashboard."""
    st.title("Pushan — The Next-Gen AI Agriculture Engine")
    st.caption("AI-enabled smart agriculture process intelligence dashboard")

    try:
        health = check_health()
    except PushanAPIError as error:
        st.sidebar.error("Pushan API: OFFLINE")
        st.error(str(error))
        st.info(
            "Start FastAPI with `python -m uvicorn app.main_api:app --reload`, "
            "then refresh this dashboard."
        )
        return

    st.sidebar.success(f"Pushan API: ONLINE (v{health.get('version', '?')})")

    try:
        fields = get_fields()
        if not fields:
            st.warning("No configured fields were returned by the backend.")
            return

        field_lookup = {field["field_id"]: field for field in fields}
        selected_field_id = st.sidebar.selectbox("Selected Field", field_lookup)
        history_limit = st.sidebar.slider("History Limit", 1, 50, 10)
        st.sidebar.button("Refresh Data", width="stretch")
        selected_field = field_lookup[selected_field_id]

        st.subheader(f"Field: {selected_field_id}")
        metadata_columns = st.columns(3)
        metadata_columns[0].metric("Crop", selected_field["crop"].title())
        metadata_columns[1].metric(
            "Crop Stage", selected_field["crop_stage"].title()
        )
        metadata_columns[2].metric(
            "Field Area", f"{selected_field['field_area_m2']:g} m²"
        )

        with st.spinner("Loading current field conditions..."):
            sensor = get_sensor_reading(selected_field_id)
        render_sensor_status(sensor)

        if st.button(
            "Run Irrigation Assessment",
            type="primary",
            width="stretch",
        ):
            with st.spinner("Running rule, ML, and operational assessment..."):
                st.session_state["latest_assessment"] = (
                    get_irrigation_recommendation(
                        selected_field_id,
                        selected_field["crop"],
                        selected_field["crop_stage"],
                        selected_field["field_area_m2"],
                    )
                )

        assessment = st.session_state.get("latest_assessment")
        if assessment and assessment.get("field_id") == selected_field_id:
            render_assessment(assessment)

        with st.spinner("Loading field history..."):
            sensor_records = get_sensor_history(selected_field_id, history_limit)
            decision_records = get_decision_history(selected_field_id, history_limit)
            action_records = get_action_history(selected_field_id, history_limit)
        render_history(sensor_records, decision_records, action_records)
        render_knowledge_assistant()
        render_pushan_agent()
    except (PushanAPIError, KeyError, TypeError, ValueError) as error:
        st.error(f"The dashboard could not load field data: {error}")
        st.info("Check the backend status and use Refresh Data to try again.")


run_dashboard()
