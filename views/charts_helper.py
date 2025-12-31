"""
SuperPoll Charts Helper
Plotly chart generators for analytics
"""
import plotly.graph_objects as go
import plotly.express as px

# Color palette
COLORS = {
    'primary': '#3b82f6',
    'secondary': '#6366f1',
    'success': '#22c55e',
    'warning': '#f59e0b',
    'danger': '#ef4444',
    'gray': '#6b7280',
}

CHART_COLORS = [
    '#3b82f6', '#22c55e', '#f59e0b', '#ef4444', 
    '#8b5cf6', '#ec4899', '#14b8a6', '#f97316'
]

def create_bar_chart(question_text: str, options_data: list) -> go.Figure:
    """Create horizontal bar chart for vote results"""
    labels = [opt['option_text'] for opt in options_data]
    values = [opt['vote_count'] for opt in options_data]
    percentages = [opt.get('percentage', 0) for opt in options_data]
    
    # Create custom text
    text = [f"{v} ({p:.1f}%)" for v, p in zip(values, percentages)]
    
    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation='h',
        marker_color=CHART_COLORS[:len(labels)],
        text=text,
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>คะแนน: %{x}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(
            text=question_text,
            font=dict(size=16, color='#1f2937')
        ),
        xaxis_title='จำนวนคะแนน',
        yaxis_title='',
        height=max(300, len(labels) * 60),
        margin=dict(l=20, r=20, t=60, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Sarabun, Noto Sans Thai, sans-serif'),
        xaxis=dict(gridcolor='#e2e8f0'),
        yaxis=dict(autorange='reversed')
    )
    
    return fig

def create_pie_chart(question_text: str, options_data: list) -> go.Figure:
    """Create pie chart for vote distribution"""
    labels = [opt['option_text'] for opt in options_data]
    values = [opt['vote_count'] for opt in options_data]
    
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        marker=dict(colors=CHART_COLORS[:len(labels)]),
        hole=0.4,
        textinfo='percent+label',
        textposition='outside',
        hovertemplate='<b>%{label}</b><br>คะแนน: %{value}<br>สัดส่วน: %{percent}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(
            text=question_text,
            font=dict(size=16, color='#1f2937')
        ),
        height=400,
        margin=dict(l=20, r=20, t=60, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Sarabun, Noto Sans Thai, sans-serif'),
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.2,
            xanchor='center',
            x=0.5
        )
    )
    
    return fig

def create_gauge_chart(label: str, current: int, target: int) -> go.Figure:
    """Create gauge chart for quota tracking"""
    percentage = (current / target * 100) if target > 0 else 0
    
    # Determine color based on progress
    if percentage >= 100:
        color = COLORS['success']
    elif percentage >= 75:
        color = COLORS['primary']
    elif percentage >= 50:
        color = COLORS['warning']
    else:
        color = COLORS['danger']
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=current,
        number={'suffix': f" / {target}", 'font': {'size': 24}},
        delta={'reference': target, 'relative': False, 'position': 'bottom'},
        title={'text': label, 'font': {'size': 16}},
        gauge={
            'axis': {'range': [0, target], 'tickwidth': 1},
            'bar': {'color': color},
            'bgcolor': 'white',
            'borderwidth': 2,
            'bordercolor': '#e2e8f0',
            'steps': [
                {'range': [0, target * 0.5], 'color': '#fee2e2'},
                {'range': [target * 0.5, target * 0.75], 'color': '#fef3c7'},
                {'range': [target * 0.75, target], 'color': '#dcfce7'},
            ],
            'threshold': {
                'line': {'color': '#1f2937', 'width': 2},
                'thickness': 0.75,
                'value': target
            }
        }
    ))
    
    fig.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Sarabun, Noto Sans Thai, sans-serif')
    )
    
    return fig

def create_demographic_bar_chart(demographic_label: str, data: list) -> go.Figure:
    """Create bar chart for demographic breakdown"""
    labels = [d['value'] for d in data]
    values = [d['count'] for d in data]
    
    # Calculate percentages
    total = sum(values)
    percentages = [(v / total * 100) if total > 0 else 0 for v in values]
    text = [f"{v} ({p:.1f}%)" for v, p in zip(values, percentages)]
    
    fig = go.Figure(go.Bar(
        x=labels,
        y=values,
        marker_color=CHART_COLORS[:len(labels)],
        text=text,
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>จำนวน: %{y}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(
            text=f"แยกตาม{demographic_label}",
            font=dict(size=16, color='#1f2937')
        ),
        xaxis_title='',
        yaxis_title='จำนวน',
        height=350,
        margin=dict(l=20, r=20, t=60, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Sarabun, Noto Sans Thai, sans-serif'),
        yaxis=dict(gridcolor='#e2e8f0')
    )
    
    return fig

def create_stacked_bar_chart(title: str, categories: list, series_data: dict) -> go.Figure:
    """Create stacked bar chart for cross-tabulation"""
    fig = go.Figure()
    
    for i, (series_name, values) in enumerate(series_data.items()):
        fig.add_trace(go.Bar(
            name=series_name,
            x=categories,
            y=values,
            marker_color=CHART_COLORS[i % len(CHART_COLORS)]
        ))
    
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=16, color='#1f2937')
        ),
        barmode='stack',
        height=400,
        margin=dict(l=20, r=20, t=60, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Sarabun, Noto Sans Thai, sans-serif'),
        yaxis=dict(gridcolor='#e2e8f0'),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.2,
            xanchor='center',
            x=0.5
        )
    )
    
    return fig
