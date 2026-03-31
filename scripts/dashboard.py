#!/usr/bin/env python3
"""
Beyond Recognition — Study Results Dashboard

Run:  python scripts/dashboard.py
Open: http://localhost:8050
"""

import json
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, html, dcc

# ─── Supabase fetch ──────────────────────────────────────────────

SUPABASE_URL = "https://utvncqkgaersidrtquif.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV0dm5jcWtnYWVyc2lkcnRxdWlmIiwi"
    "cm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NDQ1NjkzNSwiZXhwIjoyMDkw"
    "MDMyOTM1fQ.7YOabQCYg7ohJRxSWrbSjScDGkcKwoxQkfLYZ0AerQ4"
)


def fetch(table):
    headers = {"Authorization": f"Bearer {SUPABASE_KEY}", "apikey": SUPABASE_KEY}
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{table}?select=*&order=created_at.asc",
        headers=headers,
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


line_data = fetch("attempt_logs")
image_data = fetch("image_attempt_logs")
quest_data = fetch("questionnaire_responses")

# ─── Derived data ────────────────────────────────────────────────

line_sessions = defaultdict(list)
for a in line_data:
    line_sessions[a["session_id"]].append(a)

quest_by_session = {q["session_id"]: q for q in quest_data}

total_participants = len(line_sessions)
completed_participants = len(quest_data)

line_pass_rate = (
    sum(1 for a in line_data if a["outcome_reason"] == "success") / max(len(line_data), 1) * 100
)
image_pass_rate = (
    sum(1 for a in image_data if a["passed"] == 1) / max(len(image_data), 1) * 100
)

# ─── Figures ─────────────────────────────────────────────────────


def make_overview_cards():
    fig = go.Figure()
    fig.add_trace(go.Indicator(
        mode="number", value=total_participants,
        title={"text": "Sessions"},
        domain={"row": 0, "column": 0},
    ))
    fig.add_trace(go.Indicator(
        mode="number", value=completed_participants,
        title={"text": "Completed"},
        domain={"row": 0, "column": 1},
    ))
    fig.add_trace(go.Indicator(
        mode="number+delta", value=line_pass_rate,
        title={"text": "Line Pass %"},
        number={"suffix": "%"},
        domain={"row": 0, "column": 2},
    ))
    fig.add_trace(go.Indicator(
        mode="number+delta", value=image_pass_rate,
        title={"text": "Image Pass %"},
        number={"suffix": "%"},
        domain={"row": 0, "column": 3},
    ))
    fig.update_layout(
        grid={"rows": 1, "columns": 4, "pattern": "independent"},
        height=180, margin=dict(t=50, b=10, l=10, r=10),
        paper_bgcolor="#111827", font_color="white",
    )
    return fig


def make_line_outcomes():
    reasons = Counter(a["outcome_reason"] for a in line_data)
    labels = list(reasons.keys())
    values = list(reasons.values())
    colors = ["#22c55e" if l == "success" else "#ef4444" for l in labels]
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=colors))
    fig.update_layout(
        title="Line CAPTCHA Outcomes",
        xaxis_title="Reason", yaxis_title="Count",
        height=350, paper_bgcolor="#111827", plot_bgcolor="#1f2937",
        font_color="white",
    )
    return fig


def make_image_outcomes():
    reasons = Counter(a["reason"] for a in image_data)
    labels = list(reasons.keys())
    values = list(reasons.values())
    colors = ["#22c55e" if "clicked" in l else "#ef4444" for l in labels]
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=colors))
    fig.update_layout(
        title="Image CAPTCHA Outcomes",
        xaxis_title="Reason", yaxis_title="Count",
        height=350, paper_bgcolor="#111827", plot_bgcolor="#1f2937",
        font_color="white",
    )
    return fig


def make_per_session_pass_rates():
    sessions = []
    line_rates = []
    image_rates = []
    for sid, attempts in sorted(line_sessions.items(), key=lambda x: x[1][0]["created_at"]):
        short = sid[:8]
        lp = sum(1 for a in attempts if a["outcome_reason"] == "success")
        sessions.append(short)
        line_rates.append(lp / len(attempts) * 100)

    # Image doesn't have session_id — approximate by matching timestamps
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=sessions, y=line_rates,
        name="Line Pass %", marker_color="#818cf8",
    ))
    fig.update_layout(
        title="Line CAPTCHA Pass Rate Per Session",
        xaxis_title="Session", yaxis_title="Pass Rate (%)",
        yaxis_range=[0, 100],
        height=350, paper_bgcolor="#111827", plot_bgcolor="#1f2937",
        font_color="white",
    )
    return fig


def make_solve_times():
    line_success = [a["duration_ms"] for a in line_data if a["outcome_reason"] == "success"]
    line_fail = [a["duration_ms"] for a in line_data if a["outcome_reason"] != "success"]
    img_success = [a["solve_time_ms"] for a in image_data if a["passed"] == 1]
    img_fail = [a["solve_time_ms"] for a in image_data if a["passed"] != 1]

    fig = make_subplots(rows=1, cols=2, subplot_titles=("Line CAPTCHA", "Image CAPTCHA"))
    if line_success:
        fig.add_trace(go.Box(y=line_success, name="Pass", marker_color="#22c55e"), row=1, col=1)
    if line_fail:
        fig.add_trace(go.Box(y=line_fail, name="Fail", marker_color="#ef4444"), row=1, col=1)
    if img_success:
        fig.add_trace(go.Box(y=img_success, name="Pass", marker_color="#22c55e"), row=1, col=2)
    if img_fail:
        fig.add_trace(go.Box(y=img_fail, name="Fail", marker_color="#ef4444"), row=1, col=2)

    fig.update_yaxes(title_text="Duration (ms)")
    fig.update_layout(
        title="Solve Times",
        height=400, paper_bgcolor="#111827", plot_bgcolor="#1f2937",
        font_color="white", showlegend=False,
    )
    return fig


def make_coverage_distribution():
    coverages = [a["coverage_ratio"] for a in line_data if a["coverage_ratio"] is not None]
    outcomes = [a["outcome_reason"] for a in line_data if a["coverage_ratio"] is not None]
    colors = ["#22c55e" if o == "success" else "#ef4444" for o in outcomes]

    fig = go.Figure(go.Histogram(
        x=coverages, nbinsx=20,
        marker_color="#818cf8",
    ))
    fig.add_vline(x=0.75, line_dash="dash", line_color="#facc15",
                  annotation_text="75% threshold", annotation_position="top left")
    fig.update_layout(
        title="Line CAPTCHA Coverage Distribution",
        xaxis_title="Coverage Ratio", yaxis_title="Count",
        height=350, paper_bgcolor="#111827", plot_bgcolor="#1f2937",
        font_color="white",
    )
    return fig


def make_pointer_comparison():
    mouse_line = [a for a in line_data if a["pointer_type"] == "mouse"]
    touch_line = [a for a in line_data if a["pointer_type"] == "touch"]
    mouse_pass = sum(1 for a in mouse_line if a["outcome_reason"] == "success")
    touch_pass = sum(1 for a in touch_line if a["outcome_reason"] == "success")

    mouse_img = [a for a in image_data if a.get("pointer_type") == "mouse"]
    touch_img = [a for a in image_data if a.get("pointer_type") == "touch"]
    mouse_img_pass = sum(1 for a in mouse_img if a["passed"] == 1)
    touch_img_pass = sum(1 for a in touch_img if a["passed"] == 1)

    fig = make_subplots(rows=1, cols=2, subplot_titles=("Line CAPTCHA", "Image CAPTCHA"))

    categories = ["Mouse", "Touch"]
    line_rates = [
        mouse_pass / max(len(mouse_line), 1) * 100,
        touch_pass / max(len(touch_line), 1) * 100,
    ]
    img_rates = [
        mouse_img_pass / max(len(mouse_img), 1) * 100,
        touch_img_pass / max(len(touch_img), 1) * 100,
    ]

    fig.add_trace(go.Bar(
        x=categories, y=line_rates,
        text=[f"{r:.0f}%<br>(n={n})" for r, n in zip(line_rates, [len(mouse_line), len(touch_line)])],
        textposition="auto",
        marker_color=["#818cf8", "#f472b6"],
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=categories, y=img_rates,
        text=[f"{r:.0f}%<br>(n={n})" for r, n in zip(img_rates, [len(mouse_img), len(touch_img)])],
        textposition="auto",
        marker_color=["#818cf8", "#f472b6"],
    ), row=1, col=2)

    fig.update_yaxes(title_text="Pass Rate (%)", range=[0, 100])
    fig.update_layout(
        title="Mouse vs Touch Pass Rates",
        height=400, paper_bgcolor="#111827", plot_bgcolor="#1f2937",
        font_color="white", showlegend=False,
    )
    return fig


def make_questionnaire_charts():
    if not quest_data:
        return go.Figure().update_layout(
            title="No questionnaire data yet",
            height=200, paper_bgcolor="#111827", font_color="white",
        )

    metrics = {
        "Line Difficulty": [q["captcha1_difficulty"] for q in quest_data if q.get("captcha1_difficulty")],
        "Line Frustration": [q["captcha1_frustration"] for q in quest_data if q.get("captcha1_frustration")],
        "Image Difficulty": [q["captcha2_difficulty"] for q in quest_data if q.get("captcha2_difficulty")],
        "Image Frustration": [q["captcha2_frustration"] for q in quest_data if q.get("captcha2_frustration")],
    }

    fig = go.Figure()
    colors = ["#818cf8", "#f472b6", "#34d399", "#fbbf24"]
    for i, (name, vals) in enumerate(metrics.items()):
        if vals:
            avg = sum(vals) / len(vals)
            fig.add_trace(go.Bar(
                x=[name], y=[avg],
                text=[f"{avg:.1f}"],
                textposition="auto",
                marker_color=colors[i],
                name=name,
            ))

    fig.update_layout(
        title="Questionnaire Averages (1-5 Likert)",
        yaxis_title="Average Rating", yaxis_range=[0, 5.5],
        height=400, paper_bgcolor="#111827", plot_bgcolor="#1f2937",
        font_color="white", showlegend=False,
    )
    return fig


def make_comments_section():
    comments = []
    for q in quest_data:
        if q.get("comments"):
            device = q.get("device_type", "?")
            age = q.get("age_range", "?")
            comments.append(
                html.Div([
                    html.P(
                        f"\"{q['comments']}\"",
                        style={"fontStyle": "italic", "marginBottom": "4px"},
                    ),
                    html.P(
                        f"— {device}, {age}, tech comfort {q.get('tech_comfort', '?')}/5",
                        style={"fontSize": "12px", "color": "#9ca3af"},
                    ),
                ], style={
                    "borderLeft": "3px solid #818cf8",
                    "paddingLeft": "12px",
                    "marginBottom": "16px",
                })
            )
    if not comments:
        comments = [html.P("No comments yet.", style={"color": "#9ca3af"})]
    return comments


def make_timeline():
    timestamps = []
    labels = []
    colors = []
    for a in line_data:
        ts = datetime.fromtimestamp(a["created_at"])
        timestamps.append(ts)
        labels.append(f"Line: {a['outcome_reason']}")
        colors.append("#22c55e" if a["outcome_reason"] == "success" else "#ef4444")
    for a in image_data:
        ts = datetime.fromtimestamp(a["created_at"])
        timestamps.append(ts)
        labels.append(f"Image: {a['reason'][:20]}")
        colors.append("#22c55e" if a["passed"] == 1 else "#ef4444")

    fig = go.Figure(go.Scatter(
        x=timestamps, y=[1] * len(timestamps),
        mode="markers",
        marker=dict(size=10, color=colors),
        text=labels, hoverinfo="text+x",
    ))
    fig.update_layout(
        title="Attempt Timeline",
        xaxis_title="Time", yaxis_visible=False,
        height=200, paper_bgcolor="#111827", plot_bgcolor="#1f2937",
        font_color="white",
    )
    return fig


# ─── Dash app ────────────────────────────────────────────────────

app = Dash(__name__)

app.layout = html.Div(
    style={
        "backgroundColor": "#111827",
        "minHeight": "100vh",
        "padding": "24px",
        "fontFamily": "system-ui, sans-serif",
        "color": "white",
    },
    children=[
        html.H1(
            "Beyond Recognition — Study Dashboard",
            style={"textAlign": "center", "marginBottom": "8px", "color": "#818cf8"},
        ),
        html.P(
            f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
            f"{len(line_data)} line attempts | {len(image_data)} image attempts | "
            f"{len(quest_data)} questionnaires",
            style={"textAlign": "center", "color": "#9ca3af", "marginBottom": "24px"},
        ),

        dcc.Graph(figure=make_overview_cards()),

        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px"}, children=[
            dcc.Graph(figure=make_line_outcomes()),
            dcc.Graph(figure=make_image_outcomes()),
        ]),

        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px"}, children=[
            dcc.Graph(figure=make_pointer_comparison()),
            dcc.Graph(figure=make_solve_times()),
        ]),

        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px"}, children=[
            dcc.Graph(figure=make_coverage_distribution()),
            dcc.Graph(figure=make_per_session_pass_rates()),
        ]),

        dcc.Graph(figure=make_questionnaire_charts()),

        dcc.Graph(figure=make_timeline()),

        html.Div(
            style={
                "maxWidth": "600px",
                "margin": "24px auto",
                "padding": "16px",
                "backgroundColor": "#1f2937",
                "borderRadius": "8px",
            },
            children=[
                html.H3("Participant Comments", style={"marginBottom": "16px"}),
                *make_comments_section(),
            ],
        ),
    ],
)

if __name__ == "__main__":
    print("Dashboard: http://localhost:8050")
    app.run(debug=True, port=8050)
