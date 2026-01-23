import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import pydeck as pdk
import streamlit as st

# How often to update the map and "global" state table. Frequent updates strongly impact performance.
MAP_UPDATE_INTERVAL_SECONDS = 0.5
# How often to update the knowledge consistency table
TABLE_UPDATE_INTERVAL_SECONDS = 0.2
AVOID_RADIUS = 300


def load_agent_states(state_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Load all agent states from JSON files"""
    states: Dict[str, Dict[str, Any]] = {}
    if not state_dir.exists():
        return states

    for state_file in state_dir.glob("*.json"):
        try:
            with open(state_file, "r") as f:
                cow_id = state_file.stem
                states[cow_id] = json.load(f)
        except (json.JSONDecodeError, IOError):
            continue

    return states


def get_actual_states(agent_states: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Extract the actual current state of each cow (their self-knowledge)"""
    actual_states = {}
    for cow_id, full_state in agent_states.items():
        if cow_id in full_state:
            actual_states[cow_id] = full_state[cow_id]
    return actual_states


def build_knowledge_consistency_data(agent_states: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
    """
    Build a dataframe showing what each cow knows about other cows
    and whether that information is up-to-date.
    """
    rows = []
    actual_states = get_actual_states(agent_states)

    for observer_id, observer_knowledge in agent_states.items():
        for cow_id in sorted(agent_states.keys()):
            if cow_id == observer_id:
                continue

            if cow_id not in observer_knowledge:
                status = "❌ Unknown"
                location = "N/A"
                health = "N/A"
                timestamp_diff = "N/A"
            elif cow_id not in actual_states:
                status = "⚠️ No Actual Data"
                location = str(observer_knowledge[cow_id].get("location", "N/A"))
                health = observer_knowledge[cow_id].get("health", "N/A")
                timestamp_diff = "N/A"
            else:
                observer_timestamp = observer_knowledge[cow_id].get("timestamp", 0)
                actual_timestamp = actual_states[cow_id].get("timestamp", 0)

                if abs(observer_timestamp - actual_timestamp) < 1:
                    status = "✅ Up-to-date"
                else:
                    status = "⏳ Outdated"

                location = str(observer_knowledge[cow_id].get("location", "N/A"))
                health = observer_knowledge[cow_id].get("health", "N/A")
                timestamp_diff = f"{actual_timestamp - observer_timestamp:.1f}s"

            rows.append(
                {
                    "Observer": observer_id,
                    "Target Cow": cow_id,
                    "Status": status,
                    "Known Location": location,
                    "Known Health": health,
                    "Time Diff": timestamp_diff,
                }
            )

    return pd.DataFrame(rows)


@st.fragment(run_every=MAP_UPDATE_INTERVAL_SECONDS)
def render_location_plot() -> None:
    """Render the location plot with auto-refresh"""
    state_dir = Path("state")
    agent_states = load_agent_states(state_dir)

    if not agent_states:
        st.warning("No agent data available. Make sure agents are running and dumping state to 'state/' directory.")
        return

    actual_states = get_actual_states(agent_states)

    infected_areas = []
    for cow_id, state in actual_states.items():
        if state.get("health") == "unhealthy":
            loc = state["location"]
            infected_areas.append(
                {
                    "lon": loc["longitude"],
                    "lat": loc["latitude"],
                    "radius": AVOID_RADIUS,
                }
            )

    boundary_layer = None

    if actual_states:
        any_cow = next(iter(actual_states.values()))
        bounds = any_cow.get("boundaries")

        if bounds:
            shapely_coords = [[lon, lat] for lat, lon in bounds]

            boundary_layer = pdk.Layer(
                "PolygonLayer",
                data=[{"polygon": shapely_coords}],
                get_polygon="polygon",
                get_fill_color=[255, 255, 255, 40],
                get_line_color=[255, 255, 255, 200],
                line_width_min_pixels=2,
                pickable=False,
            )

    locations_data = []
    for cow_id, state in actual_states.items():
        location = state.get("location", (0, 0))
        health = state.get("health", "unknown")
        locations_data.append(
            {"cow_id": cow_id, "latitude": location["latitude"], "longitude": location["longitude"], "health": health}
        )

    if locations_data:
        df = pd.DataFrame(locations_data)

        st.subheader("🐄 Cow locations")

        df["cow_number"] = df["cow_id"].str.extract(r"(\d+)")[0].astype(str)

        def get_color(health: str) -> list:
            if health == "healthy":
                return [0, 255, 0, 200]  # Green
            elif health == "unhealthy":
                return [255, 0, 0, 200]  # Red
            else:
                return [128, 128, 128, 200]  # Gray

        df["color"] = df["health"].apply(get_color)

        df = df.rename(columns={"latitude": "lat", "longitude": "lon"})

        peer_lines = []
        for cow_id, state in actual_states.items():
            peers = state.get("peers", [])
            cow_location = state.get("location", (0, 0))

            for peer_jid in peers:
                peer_num = peer_jid.split("@")[0].replace("cow", "")
                peer_cow_id = f"Cow-{peer_num}"

                if peer_cow_id in actual_states and cow_id < peer_cow_id:
                    peer_location = actual_states[peer_cow_id].get("location", (0, 0))
                    peer_lines.append(
                        {
                            "start": [cow_location["longitude"], cow_location["latitude"]],  # [lon, lat]
                            "end": [peer_location["longitude"], peer_location["latitude"]],  # [lon, lat]
                        }
                    )

        line_layer = pdk.Layer(
            "LineLayer",
            peer_lines,
            get_source_position="start",
            get_target_position="end",
            get_color=[100, 100, 255, 150],  # Blue with transparency
            get_width=2,
            pickable=False,
        )

        circle_layer = pdk.Layer(
            "ScatterplotLayer",
            df,
            get_position=["lon", "lat"],
            get_fill_color="color",
            get_radius=70,
            pickable=True,
            opacity=0.4,
            stroked=True,
            filled=True,
            line_width_min_pixels=1,
        )

        infected_layer = pdk.Layer(
            "ScatterplotLayer",
            infected_areas,
            get_position=["lon", "lat"],
            get_radius="radius",
            get_fill_color=[255, 0, 0, 80],
            pickable=False,
            stroked=False,
            filled=True,
        )

        text_layer = pdk.Layer(
            "TextLayer",
            df,
            get_position=["lon", "lat"],
            get_text="cow_number",
            get_color=[255, 255, 255, 255],  # White text
            get_size=20,
            get_alignment_baseline="'center'",
        )

        view_state = pdk.ViewState(
            latitude=52.1219914893008,
            longitude=20.47171532833653,
            zoom=13,
            pitch=0,
        )

        layers = []
        if boundary_layer:
            layers.append(boundary_layer)

        layers.extend([line_layer, circle_layer, infected_layer, text_layer])

        deck = pdk.Deck(
            layers=layers,
            initial_view_state=view_state,
        )

        st.pydeck_chart(deck, width="stretch")

        st.dataframe(
            df[["cow_id", "lat", "lon", "health"]],
            width="stretch",
            hide_index=True,
        )


@st.fragment(run_every=TABLE_UPDATE_INTERVAL_SECONDS)
def render_knowledge_table() -> None:
    """Render the knowledge consistency table with auto-refresh"""
    state_dir = Path("state")
    agent_states = load_agent_states(state_dir)

    if not agent_states:
        return

    st.subheader("🧠 Knowledge consistency")
    st.caption("Shows what each cow knows about others and whether that information is current")

    knowledge_df = build_knowledge_consistency_data(agent_states)

    if not knowledge_df.empty:
        for observer in sorted(agent_states.keys(), key=lambda x: int(x.split("-")[1])):
            observer_data = knowledge_df[knowledge_df["Observer"] == observer]
            if not observer_data.empty:
                with st.expander(f"📋 {observer}'s Knowledge", expanded=True):
                    st.dataframe(
                        observer_data[["Target Cow", "Status", "Known Location", "Known Health", "Time Diff"]],
                        width="stretch",
                        hide_index=True,
                    )


def main() -> None:
    st.set_page_config(
        page_title="Cow Herd Monitoring",
        page_icon="🐄",
        layout="wide",
    )

    st.title("🐄 Cow Herd Monitoring")
    st.markdown("Real-time monitoring of cow agent locations, health, and *cow2cow* knowledge propagation")

    col1, col2 = st.columns([1, 1])

    with col1:
        render_location_plot()

    with col2:
        render_knowledge_table()


if __name__ == "__main__":
    main()
