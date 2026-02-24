"""Streamlit UI application for TinyBrain."""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional

import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_agraph import agraph, Config, Edge, Node

from tinybrain.database import Database, SQLiteBackend
from tinybrain.models.memory import MemoryCreateRequest
from tinybrain.models.session import SessionCreateRequest
from tinybrain.models.relationship import RelationshipCreateRequest, RelationshipType


# Initialize database connection
@st.cache_resource
def get_database():
    """Get database connection."""
    db_path = os.getenv("TINYBRAIN_DB_PATH", str(Path.home() / ".tinybrain" / "data.db"))
    backend = SQLiteBackend(db_path)
    db = Database(backend)
    
    # Initialize in a thread-safe way
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(db.initialize())
    
    return db


def run_async(coro):
    """Run an async function in the current event loop."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# Page configuration
st.set_page_config(
    page_title="TinyBrain",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Title
st.title("🧠 TinyBrain - Security Memory Storage")

# Sidebar
st.sidebar.title("Navigation")
page = st.sidebar.selectbox(
    "Choose a page",
    ["Dashboard", "Sessions", "Memories", "Relationships", "Graph Visualization", "Data Import"],
)

db = get_database()

# Dashboard page
if page == "Dashboard":
    st.header("Dashboard")
    
    # Get statistics
    stats = run_async(db.get_stats())
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Sessions", stats.get("sessions_count", 0))
    with col2:
        st.metric("Memory Entries", stats.get("memory_entries_count", 0))
    with col3:
        st.metric("Relationships", stats.get("relationships_count", 0))
    with col4:
        db_size_mb = stats.get("database_size_bytes", 0) / 1024 / 1024
        st.metric("Database Size", f"{db_size_mb:.2f} MB")
    
    # Top accessed entries
    top_accessed = stats.get("top_accessed_entries", [])
    if top_accessed:
        st.subheader("Top Accessed Entries")
        df = pd.DataFrame(top_accessed)
        st.dataframe(df, use_container_width=True)

# Sessions page
elif page == "Sessions":
    st.header("Sessions")
    
    # Create new session
    with st.expander("Create New Session"):
        with st.form("create_session"):
            session_name = st.text_input("Session Name")
            task_type = st.selectbox(
                "Task Type",
                ["security_review", "penetration_test", "exploit_dev", "vulnerability_analysis", "threat_modeling", "incident_response", "general"],
            )
            description = st.text_area("Description")
            
            if st.form_submit_button("Create Session"):
                try:
                    request = SessionCreateRequest(
                        name=session_name,
                        task_type=task_type,
                        description=description if description else None,
                    )
                    session = run_async(db.create_session(request))
                    st.success(f"Session created: {session.id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating session: {e}")
    
    # List sessions
    sessions = run_async(db.list_sessions(limit=100))
    
    if sessions:
        st.subheader("All Sessions")
        for session in sessions:
            with st.expander(f"{session.name} ({session.task_type})"):
                st.write(f"**ID:** {session.id}")
                st.write(f"**Status:** {session.status}")
                st.write(f"**Description:** {session.description or 'N/A'}")
                st.write(f"**Created:** {session.created_at}")

# Memories page
elif page == "Memories":
    st.header("Memories")
    
    # Create new memory
    with st.expander("Create New Memory"):
        with st.form("create_memory"):
            sessions = run_async(db.list_sessions(limit=100))
            session_options = {s.name: s.id for s in sessions}
            
            if session_options:
                session_name = st.selectbox("Session", list(session_options.keys()))
                session_id = session_options[session_name]
            else:
                st.warning("No sessions available. Create a session first.")
                session_id = None
            
            title = st.text_input("Title")
            content = st.text_area("Content")
            category = st.selectbox(
                "Category",
                ["finding", "vulnerability", "exploit", "payload", "technique", "tool", "reference", "context", "hypothesis", "evidence", "recommendation", "note"],
            )
            priority = st.slider("Priority", 0, 10, 5)
            confidence = st.slider("Confidence", 0.0, 1.0, 0.5)
            tags = st.text_input("Tags (comma-separated)")
            source = st.text_input("Source")
            
            if st.form_submit_button("Create Memory") and session_id:
                try:
                    tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
                    request = MemoryCreateRequest(
                        session_id=session_id,
                        title=title,
                        content=content,
                        category=category,
                        priority=priority,
                        confidence=confidence,
                        tags=tags_list,
                        source=source if source else None,
                    )
                    memory = run_async(db.create_memory(request))
                    st.success(f"Memory created: {memory.id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating memory: {e}")
    
    # Search memories
    st.subheader("Search Memories")
    search_query = st.text_input("Search Query")
    search_category = st.selectbox(
        "Category Filter",
        [None, "finding", "vulnerability", "exploit", "payload", "technique", "tool", "reference", "context", "hypothesis", "evidence", "recommendation", "note"],
    )
    
    if st.button("Search"):
        try:
            memories = run_async(
                db.search_memories(
                    query=search_query if search_query else None,
                    category=search_category,
                    limit=50,
                )
            )
            
            if memories:
                st.write(f"Found {len(memories)} memories")
                for memory in memories:
                    with st.expander(f"{memory.title} ({memory.category})"):
                        st.write(f"**ID:** {memory.id}")
                        st.write(f"**Priority:** {memory.priority} | **Confidence:** {memory.confidence}")
                        st.write(f"**Content:** {memory.content[:500]}...")
                        if memory.tags:
                            st.write(f"**Tags:** {', '.join(memory.tags)}")
            else:
                st.info("No memories found")
        except Exception as e:
            st.error(f"Error searching memories: {e}")

# Relationships page
elif page == "Relationships":
    st.header("Relationships")
    
    # Create new relationship
    with st.expander("Create New Relationship"):
        with st.form("create_relationship"):
            memories = run_async(db.search_memories(limit=100))
            memory_options = {f"{m.title} ({m.id[:8]})": m.id for m in memories}
            
            if len(memory_options) >= 2:
                source_memory = st.selectbox("Source Memory", list(memory_options.keys()))
                target_memory = st.selectbox("Target Memory", list(memory_options.keys()))
                relationship_type = st.selectbox(
                    "Relationship Type",
                    [rt.value for rt in RelationshipType],
                )
                strength = st.slider("Strength", 0.0, 1.0, 0.5)
                description = st.text_area("Description")
                
                if st.form_submit_button("Create Relationship"):
                    try:
                        request = RelationshipCreateRequest(
                            source_id=memory_options[source_memory],
                            target_id=memory_options[target_memory],
                            type=RelationshipType(relationship_type),
                            strength=strength,
                            description=description if description else None,
                        )
                        relationship = run_async(db.create_relationship(request))
                        st.success(f"Relationship created: {relationship.id}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating relationship: {e}")
            else:
                st.warning("Need at least 2 memories to create a relationship")

# Graph Visualization page
elif page == "Graph Visualization":
    st.header("Graph Visualization")
    
    # Build NetworkX graph
    try:
        memories = run_async(db.search_memories(limit=100))
        relationships = []
        
        # Get relationships for each memory
        for memory in memories:
            related = run_async(db.get_related_memories(memory.id, limit=10))
            for rel_memory in related:
                relationships.append((memory.id, rel_memory.id))
        
        # Create graph
        G = nx.Graph()
        
        # Add nodes
        for memory in memories:
            G.add_node(
                memory.id,
                label=memory.title[:30],
                category=memory.category,
                priority=memory.priority,
            )
        
        # Add edges
        for source, target in relationships:
            if source in G and target in G:
                G.add_edge(source, target)
        
        if len(G.nodes) > 0:
            # NetworkX visualization
            st.subheader("NetworkX Graph")
            
            # Calculate layout
            pos = nx.spring_layout(G, k=1, iterations=50)
            
            # Create Plotly figure
            edge_x = []
            edge_y = []
            for edge in G.edges():
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])
            
            edge_trace = go.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=0.5, color="#888"),
                hoverinfo="none",
                mode="lines",
            )
            
            node_x = []
            node_y = []
            node_text = []
            node_color = []
            for node in G.nodes():
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)
                node_info = G.nodes[node]
                node_text.append(node_info.get("label", node[:8]))
                # Color by category
                category = node_info.get("category", "note")
                colors = {
                    "vulnerability": "#ff0000",
                    "exploit": "#ff8800",
                    "finding": "#0088ff",
                    "note": "#888888",
                }
                node_color.append(colors.get(category, "#888888"))
            
            node_trace = go.Scatter(
                x=node_x, y=node_y,
                mode="markers+text",
                hoverinfo="text",
                text=node_text,
                textposition="middle center",
                marker=dict(
                    size=10,
                    color=node_color,
                    line=dict(width=2, color="#fff"),
                ),
            )
            
            fig = go.Figure(
                data=[edge_trace, node_trace],
                layout=go.Layout(
                    title="Memory Relationship Graph",
                    showlegend=False,
                    hovermode="closest",
                    margin=dict(b=20, l=5, r=5, t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                ),
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Graph statistics
            st.subheader("Graph Statistics")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Nodes", len(G.nodes()))
            with col2:
                st.metric("Edges", len(G.edges()))
            with col3:
                if len(G.nodes()) > 0:
                    density = len(G.edges()) / (len(G.nodes()) * (len(G.nodes()) - 1) / 2) if len(G.nodes()) > 1 else 0
                    st.metric("Density", f"{density:.3f}")
        else:
            st.info("No memories or relationships to visualize")
    except Exception as e:
        st.error(f"Error building graph: {e}")

# Data Import page
elif page == "Data Import":
    st.header("Data Import")
    
    st.subheader("Import JSON Data")
    uploaded_file = st.file_uploader("Choose a JSON file", type=["json"])
    
    if uploaded_file:
        try:
            data = json.load(uploaded_file)
            st.success("File loaded successfully")
            
            if st.button("Import Data"):
                # This would need to be implemented based on the JSON structure
                st.info("Import functionality to be implemented")
        except Exception as e:
            st.error(f"Error loading file: {e}")

