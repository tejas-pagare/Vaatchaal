import time
import uuid

import streamlit as st
import streamlit.components.v1 as components
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from graph.graph import app
from utils.icons import get_svg_icon
from utils.map_service import generate_itinerary_map_html
from utils.pdf_generator import generate_itinerary_pdf

st.set_page_config(
    page_title="Travel Companion AI",
    page_icon=None,
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Agent display metadata using clean SVG vector icons (NO EMOJIS)
AGENT_META = {
    "supervisor": {
        "icon": get_svg_icon("brain", size=18, color="#10B981"),
        "label": "Supervisor",
        "description": "Validating request & orchestrating specialists",
    },
    "flight_agent": {
        "icon": get_svg_icon("plane", size=18, color="#3B82F6"),
        "label": "Flight Specialist",
        "description": "Searching flight routes via Aviationstack MCP",
    },
    "hotel_agent": {
        "icon": get_svg_icon("hotel", size=18, color="#8B5CF6"),
        "label": "Accommodation Specialist",
        "description": "Finding top hotels via Tavily MCP",
    },
    "weather_agent": {
        "icon": get_svg_icon("cloud-sun", size=18, color="#F59E0B"),
        "label": "Weather Specialist",
        "description": "Analyzing climate & forecast via OpenWeather MCP",
    },
    "budget_agent": {
        "icon": get_svg_icon("wallet", size=18, color="#10B981"),
        "label": "Budget Analyst",
        "description": "Evaluating cost breakdown & feasibility",
    },
    "itinerary_agent": {
        "icon": get_svg_icon("calendar", size=18, color="#6366F1"),
        "label": "Itinerary Builder",
        "description": "Structuring schedule & resolving landmark photos",
    },
    "human_approval": {
        "icon": get_svg_icon("user-check", size=18, color="#F59E0B"),
        "label": "Trip Customization",
        "description": "Awaiting your feedback & review",
    },
    "final_response": {
        "icon": get_svg_icon("sparkles", size=18, color="#10B981"),
        "label": "Final Response",
        "description": "Polishing personalized travel plan",
    },
    "output_guardrail": {
        "icon": get_svg_icon("shield-check", size=18, color="#10B981"),
        "label": "Quality & Pricing Guardrail",
        "description": "Verifying pricing integrity & recommendations",
    },
}

# Custom Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #F8F9FA;
        color: #111827;
    }

    .main .block-container {
        max-width: 680px;
        padding-top: 1.25rem;
        padding-bottom: 5rem;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* App Header Banner */
    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1.25rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid #E5E7EB;
    }
    
    .app-title {
        font-size: 1.35rem;
        font-weight: 800;
        color: #111827;
        letter-spacing: -0.02em;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .app-subtitle {
        font-size: 0.825rem;
        color: #6B7280;
        margin-top: 0.15rem;
    }

    /* AI Avatar Orb */
    .ai-orb {
        display: inline-block;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background: radial-gradient(circle at 30% 30%, #34D399, #059669 70%, #064E3B);
        box-shadow: 0 0 8px rgba(52, 211, 153, 0.6);
        vertical-align: middle;
    }

    /* Chat Messages */
    .stChatMessage {
        border-radius: 1.25rem !important;
        padding: 1rem 1.25rem !important;
        margin-bottom: 1rem !important;
        border: 1px solid #E5E7EB !important;
        background-color: #FFFFFF !important;
        box-shadow: 0 4px 16px -2px rgba(0, 0, 0, 0.04) !important;
    }

    /* Interactive Thinking Step Card with Accordion */
    .thinking-box {
        background: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 1rem;
        padding: 0.75rem;
        margin: 0.5rem 0 1rem 0;
    }

    details.thinking-step-details {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-left: 3.5px solid #10B981;
        border-radius: 0.5rem;
        padding: 0.55rem 0.85rem;
        margin-bottom: 0.4rem;
        font-size: 0.835rem;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    details.thinking-step-details[open] {
        border-color: #CBD5E1;
        border-left-color: #10B981;
        background: #FFFFFF;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }

    details.thinking-step-details.error {
        border-left-color: #EF4444;
        background: #FEF2F2;
    }

    summary.thinking-summary {
        font-weight: 700;
        color: #111827;
        list-style: none;
        display: flex;
        align-items: center;
        justify-content: space-between;
        user-select: none;
    }

    summary.thinking-summary::-webkit-details-marker {
        display: none;
    }

    .tools-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        background: #ECFDF5;
        color: #065F46;
        padding: 0.15rem 0.5rem;
        border-radius: 9999px;
        font-size: 0.7rem;
        font-weight: 600;
        margin-right: 0.35rem;
        margin-top: 0.35rem;
        border: 1px solid #A7F3D0;
    }

    .tools-count-pill {
        background: #F1F5F9;
        color: #475569;
        font-size: 0.7rem;
        font-weight: 600;
        padding: 0.15rem 0.45rem;
        border-radius: 9999px;
        margin-left: auto;
        margin-right: 0.5rem;
    }

    /* Itinerary Visual Timeline */
    .timeline-container {
        position: relative;
        padding-left: 2.25rem;
        margin-top: 1.25rem;
        margin-bottom: 1.75rem;
    }

    .timeline-container::before {
        content: '';
        position: absolute;
        top: 24px;
        bottom: 24px;
        left: 13px;
        width: 2px;
        background: #E5E7EB;
    }

    .timeline-node {
        position: relative;
        margin-bottom: 1.75rem;
    }

    .timeline-dot {
        position: absolute;
        left: -2.25rem;
        top: 4px;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: #111827;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        font-weight: 700;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15);
        z-index: 2;
    }

    .itinerary-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 1.25rem;
        padding: 1.15rem;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.06);
    }

    .itinerary-card-img {
        width: 100%;
        height: 190px;
        object-fit: cover;
        border-radius: 0.85rem;
        margin-bottom: 0.85rem;
        display: block;
    }

    .itinerary-card-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 0.35rem;
    }

    .tag-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        background: #F3F4F6;
        color: #374151;
        font-size: 0.725rem;
        font-weight: 600;
        padding: 0.2rem 0.55rem;
        border-radius: 9999px;
        margin-right: 0.35rem;
        margin-bottom: 0.5rem;
    }

    .itinerary-card-desc {
        font-size: 0.85rem;
        color: #4B5563;
        line-height: 1.5;
    }

    /* Hero Trip Banner */
    .hero-banner {
        position: relative;
        border-radius: 1.25rem;
        overflow: hidden;
        margin-bottom: 1.25rem;
        box-shadow: 0 6px 24px -4px rgba(0,0,0,0.1);
    }

    .hero-banner img {
        width: 100%;
        height: 220px;
        object-fit: cover;
        display: block;
    }

    .hero-banner-overlay {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        padding: 1.25rem;
        background: linear-gradient(180deg, transparent 0%, rgba(17, 24, 39, 0.88) 100%);
        color: #FFFFFF;
    }

    .hero-title {
        font-size: 1.35rem;
        font-weight: 800;
        margin-bottom: 0.25rem;
        color: #FFFFFF;
    }

    .hero-meta {
        font-size: 0.825rem;
        color: #E5E7EB;
        display: flex;
        gap: 0.85rem;
        align-items: center;
    }

    /* Smart AI Tip Pill */
    .ai-tip-pill {
        background: #F0FDF4;
        border: 1px solid #BBF7D0;
        border-radius: 9999px;
        padding: 0.65rem 1.15rem;
        margin: 1.15rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.825rem;
        color: #166534;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.08);
    }

    .section-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #111827;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": "Where would you like to travel next? Share your destination, preferences, or follow up with changes to your existing plan.",
    })

if "awaiting_approval" not in st.session_state:
    st.session_state.awaiting_approval = False
    st.session_state.pending_config = None
    st.session_state.pending_trace = []
    st.session_state.pending_days = []
    st.session_state.pending_hero_img = ""
    st.session_state.pending_query = ""


def _render_trace_html(trace_steps: list[dict]) -> str:
    """Build interactive HTML for agent execution trace with clickable tool accordions."""
    html_parts = ["<div class='thinking-box'>"]
    for step in trace_steps:
        meta = AGENT_META.get(step["agent"], {})
        icon = meta.get("icon", get_svg_icon("compass", size=16, color="#6B7280"))
        label = meta.get("label", step["agent"])
        tools = step.get("tools", [])
        summary = step.get("summary", "")
        elapsed = step.get("elapsed", "")
        is_error = step.get("error", False)

        if is_error:
            icon = get_svg_icon("alert-circle", size=16, color="#EF4444")

        css_class = "thinking-step-details error" if is_error else "thinking-step-details"
        badges = "".join(f'<span class="tools-badge">{get_svg_icon("compass", size=10, color="#065F46")} {t}</span>' for t in tools)
        timing_html = f'<span style="color:#9CA3AF; font-size:0.75rem;">{elapsed}</span>' if elapsed else ""
        tool_count_pill = f'<span class="tools-count-pill">{len(tools)} tool{"s" if len(tools) != 1 else ""}</span>' if tools else ""

        html_parts.append(
            f'<details class="{css_class}" open>'
            f'<summary class="thinking-summary">'
            f'<div style="display:flex; align-items:center; gap:6px;">{icon} <span>{label}</span></div>'
            f'<div style="display:flex; align-items:center;">{tool_count_pill}{timing_html}</div>'
            f'</summary>'
            f'<div style="padding-top:6px; color:#4B5563; font-size:0.8rem;">{summary}</div>'
            f'<div style="margin-top:4px;">{badges}</div>'
            f'</details>'
        )
    html_parts.append("</div>")
    return "".join(html_parts)


def _render_visual_itinerary(destination_image: str, days: list[dict], query: str = "", enable_actions: bool = True):
    """Render the rich photo-based timeline cards, interactive map, and PDF export."""
    if not days:
        return

    # Hero Banner
    dest_name = query.title() if query else "Your Tailored Itinerary"
    hero_img = destination_image or "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?auto=format&fit=crop&w=800&q=80"
    
    pin_icon = get_svg_icon("map-pin", size=14, color="#E5E7EB")
    cal_icon = get_svg_icon("calendar", size=14, color="#E5E7EB")
    sparkle_icon = get_svg_icon("sparkles", size=14, color="#E5E7EB")

    hero_html = (
        f'<div class="hero-banner">'
        f'<img src="{hero_img}" alt="{dest_name}" />'
        f'<div class="hero-banner-overlay">'
        f'<div class="hero-title">Full {len(days)}-Day Schedule</div>'
        f'<div class="hero-meta">'
        f'<span>{pin_icon} {dest_name}</span> &bull; '
        f'<span>{cal_icon} {len(days)} Day Highlights</span> &bull; '
        f'<span>{sparkle_icon} AI Curated</span>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(hero_html, unsafe_allow_html=True)

    # Smart AI Tip Pill
    tip_html = (
        f'<div class="ai-tip-pill">'
        f'<span class="ai-orb"></span>'
        f'<span><strong>Pro Tip:</strong> Start major sightseeing spots early in the morning to beat the crowds and enjoy ideal photo lighting!</span>'
        f'</div>'
    )
    st.markdown(tip_html, unsafe_allow_html=True)

    # 1. Interactive Route Map Section
    map_title_icon = get_svg_icon("map", size=18, color="#111827")
    st.markdown(f'<div class="section-title">{map_title_icon} Interactive Route Map</div>', unsafe_allow_html=True)
    
    map_html = generate_itinerary_map_html(dest_name, days)
    if map_html:
        components.html(map_html, height=280)

    # 2. Timeline Section
    list_title_icon = get_svg_icon("list-checks", size=18, color="#111827")
    st.markdown(f'<div class="section-title">{list_title_icon} Day-by-Day Schedule</div>', unsafe_allow_html=True)

    nodes_html = []
    tag_icon = get_svg_icon("tag", size=11, color="#6B7280")
    for idx, day_info in enumerate(days, start=1):
        day_num = day_info.get("day", idx)
        title = day_info.get("title", f"Day {day_num}")
        tags = day_info.get("tags", ["Sightseeing", "Culture"])
        desc = day_info.get("description", "")
        img_url = day_info.get("image_url") or "https://images.unsplash.com/photo-1542051841857-5f90071e7989?auto=format&fit=crop&w=800&q=80"

        tags_html = "".join(f'<span class="tag-pill">{tag_icon} {t}</span>' for t in tags)

        nodes_html.append(
            f'<div class="timeline-node">'
            f'<div class="timeline-dot">{day_num}</div>'
            f'<div class="itinerary-card">'
            f'<img src="{img_url}" class="itinerary-card-img" alt="{title}" />'
            f'<div class="itinerary-card-title">{title}</div>'
            f'<div>{tags_html}</div>'
            f'<div class="itinerary-card-desc">{desc}</div>'
            f'</div>'
            f'</div>'
        )

    all_timeline = f'<div class="timeline-container">{"".join(nodes_html)}</div>'
    st.markdown(all_timeline, unsafe_allow_html=True)

    # 3. PDF Download Action Button
    if enable_actions:
        pdf_bytes = generate_itinerary_pdf(
            destination=dest_name,
            days=days,
        )
        st.download_button(
            label="Download Schedule (PDF)",
            data=pdf_bytes,
            file_name=f"{dest_name.replace(' ', '_')}_Itinerary.pdf",
            mime="application/pdf",
            use_container_width=True,
            icon=":material/download:",
        )


def _stream_and_render(graph_input: dict, config: dict, status_container):
    """Stream LangGraph events in 'updates' mode with open live trace panel."""
    trace_steps = []
    final_response = ""
    hit_interrupt = False
    structured_days = []
    dest_image = ""

    for event in app.stream(graph_input, config, stream_mode="updates"):
        for node_name, node_output in event.items():
            if node_name == "__interrupt__":
                hit_interrupt = True
                continue

            start_time = time.time()
            meta = AGENT_META.get(node_name, {})
            label = meta.get("label", node_name)

            agent_traces = node_output.get("agent_trace", [])
            trace_entry = agent_traces[0] if agent_traces else {}

            tools = trace_entry.get("tools", [])
            summary = trace_entry.get("summary", meta.get("description", ""))
            is_error = trace_entry.get("error", False)

            elapsed = time.time() - start_time
            elapsed_str = f"{elapsed:.1f}s" if elapsed >= 0.1 else "<0.1s"

            step = {
                "agent": node_name,
                "tools": tools,
                "summary": summary,
                "elapsed": elapsed_str,
                "error": is_error,
            }
            trace_steps.append(step)

            status_container.update(
                label=f"Active: {label} — {summary}",
                state="running",
                expanded=True,
            )
            status_container.markdown(
                _render_trace_html(trace_steps),
                unsafe_allow_html=True,
            )

            if node_output.get("structured_itinerary"):
                structured_days = node_output["structured_itinerary"]
            if node_output.get("destination_image"):
                dest_image = node_output["destination_image"]

            if node_name in ("final_response", "output_guardrail") and node_output.get("final_response"):
                final_response = node_output.get("final_response", "")
            elif node_name == "supervisor" and node_output.get("final_response"):
                final_response = node_output.get("final_response", "")

    return trace_steps, final_response, hit_interrupt, structured_days, dest_image


def _handle_approval_flow(approved: bool, feedback: str):
    """Resume the graph after human review with streaming typing animation."""
    config = st.session_state.pending_config
    resume_input = Command(resume={"approved": approved, "feedback": feedback})

    with st.chat_message("assistant"):
        status = st.status("Finalizing itinerary...", expanded=True)
        trace_steps = list(st.session_state.pending_trace)
        final_response = ""
        structured_days = list(st.session_state.pending_days)
        dest_image = st.session_state.pending_hero_img
        dest_query = st.session_state.pending_query

        for event in app.stream(resume_input, config, stream_mode="updates"):
            for node_name, node_output in event.items():
                if node_name == "__interrupt__":
                    continue

                meta = AGENT_META.get(node_name, {})
                label = meta.get("label", node_name)

                agent_traces = node_output.get("agent_trace", [])
                trace_entry = agent_traces[0] if agent_traces else {}

                tools = trace_entry.get("tools", [])
                summary = trace_entry.get("summary", meta.get("description", ""))

                step = {
                    "agent": node_name,
                    "tools": tools,
                    "summary": summary,
                    "elapsed": "",
                    "error": trace_entry.get("error", False),
                }
                trace_steps.append(step)

                status.update(label=f"Active: {label} — {summary}", state="running", expanded=True)
                status.markdown(_render_trace_html(trace_steps), unsafe_allow_html=True)

                if node_output.get("structured_itinerary"):
                    structured_days = node_output["structured_itinerary"]
                if node_output.get("destination_image"):
                    dest_image = node_output["destination_image"]

                if node_name in ("final_response", "output_guardrail") and node_output.get("final_response"):
                    final_response = node_output.get("final_response", "")

        status.update(label="Plan finalized", state="complete", expanded=True)

        if structured_days:
            _render_visual_itinerary(dest_image, structured_days, dest_query, enable_actions=True)

        if final_response:
            # Stream text typing effect
            def _stream_text():
                for word in final_response.split(" "):
                    yield word + " "
                    time.sleep(0.015)
            
            st.write_stream(_stream_text)
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": final_response,
                "trace": trace_steps,
                "structured_days": structured_days,
                "dest_image": dest_image,
                "query": dest_query,
            })

    st.session_state.awaiting_approval = False
    st.session_state.pending_config = None
    st.session_state.pending_trace = []
    st.session_state.pending_days = []
    st.session_state.pending_hero_img = ""
    st.session_state.pending_query = ""


# Header with Reset Button
col_h1, col_h2 = st.columns([5, 1])
with col_h1:
    st.markdown("""
    <div class="app-header">
        <div>
            <div class="app-title"><span class="ai-orb"></span>Travel Companion AI</div>
            <div class="app-subtitle">Multi-agent intelligence with live landmark imagery, route mapping & PDF export</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_h2:
    if st.button("New", help="Start a new travel plan", icon=":material/refresh:"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = [{
            "role": "assistant",
            "content": "Where would you like to travel next? Share your destination, preferences, or follow up with changes to your existing plan.",
        }]
        st.session_state.awaiting_approval = False
        st.session_state.pending_days = []
        st.rerun()

# Render Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("structured_days"):
            _render_visual_itinerary(msg.get("dest_image", ""), msg.get("structured_days", []), msg.get("query", ""), enable_actions=True)
        st.markdown(msg["content"])

# Approval Form (if paused at interrupt)
if st.session_state.awaiting_approval:
    st.markdown("---")
    st.info("Review your draft schedule above. Approve to finalize or provide custom adjustments.")

    with st.form("approval_form"):
        approved = st.radio("Do you approve this draft?", ["Yes, looks fantastic!", "I have adjustments"], index=0)
        feedback = st.text_area("Feedback or customization (optional)", placeholder="e.g., Make it more budget friendly, add a food tour in Harajuku, switch to 4-star hotels...")
        submitted = st.form_submit_button("Submit & Finalize Trip", icon=":material/check:")

    if submitted:
        is_approved = approved == "Yes, looks fantastic!"
        user_msg = f"Approved with feedback: {feedback}" if (is_approved and feedback) else ("Approved" if is_approved else f"Revisions requested: {feedback}")
        st.session_state.messages.append({"role": "user", "content": user_msg})
        _handle_approval_flow(is_approved, feedback)
        st.rerun()

# User Input (Follow-up conversations & new queries)
if prompt := st.chat_input("Ask a question or refine your plan (e.g., 'Make it cheaper', 'Add a day in Kyoto')..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    graph_input = {
        "messages": [HumanMessage(content=prompt)],
        "user_query": prompt,
        "flight_results": "",
        "hotel_results": "",
        "weather_results": "",
        "budget_results": "",
        "itinerary": "",
        "llm_calls": 0,
        "agent_trace": [],
        "structured_itinerary": [],
        "destination_image": "",
    }

    with st.chat_message("assistant"):
        status = st.status("AI is processing...", expanded=True)
        trace_steps, final_response, hit_interrupt, structured_days, dest_image = _stream_and_render(
            graph_input, config, status
        )

        if hit_interrupt:
            status.update(label="Draft schedule ready", state="complete", expanded=True)
            current_state = app.get_state(config)
            draft_itinerary = current_state.values.get("itinerary", "")
            s_days = current_state.values.get("structured_itinerary") or structured_days
            d_img = current_state.values.get("destination_image") or dest_image

            if s_days:
                _render_visual_itinerary(d_img, s_days, prompt, enable_actions=False)

            if draft_itinerary:
                # Stream draft text typing effect
                def _stream_draft():
                    for word in draft_itinerary.split(" "):
                        yield word + " "
                        time.sleep(0.012)
                
                st.write_stream(_stream_draft)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": draft_itinerary,
                    "trace": trace_steps,
                    "structured_days": s_days,
                    "dest_image": d_img,
                    "query": prompt,
                })

            st.session_state.awaiting_approval = True
            st.session_state.pending_config = config
            st.session_state.pending_trace = trace_steps
            st.session_state.pending_days = s_days
            st.session_state.pending_hero_img = d_img
            st.session_state.pending_query = prompt
            st.rerun()
        else:
            is_guardrail_block = (len(trace_steps) == 1 and trace_steps[0].get("agent") == "supervisor")
            if is_guardrail_block:
                status.update(label="Request blocked by guardrail", state="complete", expanded=True)
            else:
                status.update(label="Plan ready", state="complete", expanded=True)

            if structured_days:
                _render_visual_itinerary(dest_image, structured_days, prompt, enable_actions=True)

            if final_response:
                # Stream typing effect
                def _stream_text():
                    for word in final_response.split(" "):
                        yield word + " "
                        time.sleep(0.015)
                
                st.write_stream(_stream_text)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": final_response,
                    "trace": trace_steps,
                    "structured_days": structured_days,
                    "dest_image": dest_image,
                    "query": prompt,
                })
