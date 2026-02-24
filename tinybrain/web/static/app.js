// TinyBrain Web UI
class TinyBrainApp {
    constructor() {
        this.currentSession = null;
        this.cy = null;
        this.tagsCy = null;
        this.init();
    }

    async init() {
        await this.loadDashboard();
    }

    showView(viewName) {
        // Update nav
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.view === viewName) {
                btn.classList.add('active');
            }
        });

        // Update views
        document.querySelectorAll('.view').forEach(view => {
            view.classList.remove('active');
        });
        document.getElementById(`${viewName}-view`).classList.add('active');

        // Load data for view
        if (viewName === 'dashboard') {
            this.loadDashboard();
        } else if (viewName === 'sessions') {
            this.loadSessions();
        } else if (viewName === 'graph') {
            this.loadGraphView();
        } else if (viewName === 'tags') {
            this.loadTagsGraph();
        }
    }

    async loadDashboard() {
        const stats = await fetch('/api/stats').then(r => r.json());
        
        // Update stats
        document.getElementById('stat-sessions').textContent = stats.sessions;
        document.getElementById('stat-memories').textContent = stats.memories;
        document.getElementById('stat-relationships').textContent = stats.relationships;
        document.getElementById('stat-tags').textContent = stats.unique_tags;

        // Category breakdown
        const categoryDiv = document.getElementById('category-breakdown');
        const maxCount = Math.max(...Object.values(stats.by_category));
        categoryDiv.innerHTML = Object.entries(stats.by_category)
            .sort((a, b) => b[1] - a[1])
            .map(([cat, count]) => {
                const width = (count / maxCount) * 100;
                return `
                    <div class="category-bar">
                        <div class="w-32 text-sm">${cat}</div>
                        <div class="flex-1">
                            <div class="category-bar-fill" style="width: ${width}%"></div>
                        </div>
                        <div class="text-sm text-slate-400">${count}</div>
                    </div>
                `;
            }).join('');

        // Recent sessions
        const sessions = await fetch('/api/sessions?limit=5').then(r => r.json());
        const sessionsDiv = document.getElementById('recent-sessions');
        sessionsDiv.innerHTML = sessions.map(s => `
            <div class="session-card" onclick="app.showSessionDetail('${s.id}')">
                <div class="font-semibold">${s.name}</div>
                <div class="text-sm text-slate-400">${s.task_type} • ${new Date(s.created_at).toLocaleDateString()}</div>
            </div>
        `).join('');
    }

    async loadSessions() {
        const sessions = await fetch('/api/sessions').then(r => r.json());
        const listDiv = document.getElementById('sessions-list');
        listDiv.innerHTML = sessions.map(s => `
            <div class="session-card" onclick="app.showSessionDetail('${s.id}')">
                <div class="flex justify-between items-start">
                    <div>
                        <div class="font-semibold text-lg">${s.name}</div>
                        <div class="text-sm text-slate-400 mt-1">${s.description || 'No description'}</div>
                    </div>
                    <div class="text-right">
                        <div class="text-sm font-medium">${s.task_type}</div>
                        <div class="text-xs text-slate-400">${new Date(s.created_at).toLocaleDateString()}</div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    async showSessionDetail(sessionId) {
        this.currentSession = sessionId;
        
        // Load session
        const session = await fetch(`/api/sessions/${sessionId}`).then(r => r.json());
        document.getElementById('session-name').textContent = session.name;
        document.getElementById('session-description').textContent = session.description || 'No description';

        // Load memories
        const memories = await fetch(`/api/sessions/${sessionId}/memories`).then(r => r.json());
        this.renderMemories(memories);

        // Show view
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.getElementById('session-detail-view').classList.add('active');
    }

    renderMemories(memories) {
        const listDiv = document.getElementById('memories-list');
        listDiv.innerHTML = memories.map(m => {
            const priorityClass = m.priority >= 8 ? 'priority-high' : m.priority >= 5 ? 'priority-medium' : 'priority-low';
            const tags = m.tags ? m.tags.map(t => `<span class="tag">${t}</span>`).join('') : '';
            
            return `
                <div class="memory-card ${priorityClass}">
                    <div class="flex justify-between items-start mb-2">
                        <div class="font-semibold">${m.title}</div>
                        <div class="text-sm text-slate-400">Priority: ${m.priority}</div>
                    </div>
                    <div class="text-sm text-slate-300 mb-2">${m.content.substring(0, 150)}${m.content.length > 150 ? '...' : ''}</div>
                    <div class="flex justify-between items-center">
                        <div class="text-xs">
                            <span class="tag">${m.category}</span>
                            ${tags}
                        </div>
                        <div class="text-xs text-slate-400">Confidence: ${(m.confidence * 100).toFixed(0)}%</div>
                    </div>
                </div>
            `;
        }).join('');
    }

    async searchMemories() {
        const query = document.getElementById('memory-search').value;
        if (!query || query.length < 2) {
            // Reload all memories
            const memories = await fetch(`/api/sessions/${this.currentSession}/memories`).then(r => r.json());
            this.renderMemories(memories);
            return;
        }

        const results = await fetch(`/api/search?q=${encodeURIComponent(query)}&session_id=${this.currentSession}`).then(r => r.json());
        this.renderMemories(results);
    }

    async loadGraphView() {
        // Load sessions for dropdown
        const sessions = await fetch('/api/sessions').then(r => r.json());
        const select = document.getElementById('graph-session-select');
        select.innerHTML = '<option value="">Select a session...</option>' + 
            sessions.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
    }

    async loadSessionGraph() {
        const sessionId = document.getElementById('graph-session-select').value;
        if (!sessionId) return;

        const data = await fetch(`/api/graph/session/${sessionId}`).then(r => r.json());
        
        if (this.cy) {
            this.cy.destroy();
        }

        const categoryColors = {
            vulnerability: '#ef4444',
            exploit: '#f59e0b',
            finding: '#3b82f6',
            technique: '#8b5cf6',
            tool: '#06b6d4',
            reference: '#6b7280',
            context: '#10b981',
            hypothesis: '#ec4899',
            evidence: '#14b8a6',
            recommendation: '#84cc16'
        };

        this.cy = cytoscape({
            container: document.getElementById('graph-container'),
            elements: [...data.nodes, ...data.edges],
            style: [
                {
                    selector: 'node',
                    style: {
                        'background-color': ele => categoryColors[ele.data('category')] || '#6b7280',
                        'label': 'data(label)',
                        'color': '#f1f5f9',
                        'text-outline-color': '#0f172a',
                        'text-outline-width': 2,
                        'font-size': '12px',
                        'width': ele => 20 + (ele.data('priority') * 3),
                        'height': ele => 20 + (ele.data('priority') * 3)
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': ele => 1 + (ele.data('strength') * 3),
                        'line-color': '#475569',
                        'target-arrow-color': '#475569',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'label': 'data(type)',
                        'font-size': '10px',
                        'color': '#cbd5e1',
                        'text-outline-color': '#0f172a',
                        'text-outline-width': 1
                    }
                }
            ],
            layout: {
                name: 'cose',
                animate: true,
                animationDuration: 500,
                nodeRepulsion: 8000,
                idealEdgeLength: 100
            }
        });

        // Click handler
        this.cy.on('tap', 'node', evt => {
            const node = evt.target;
            console.log('Clicked:', node.data());
        });
    }

    async loadTagsGraph() {
        const data = await fetch('/api/graph/tags').then(r => r.json());
        
        if (this.tagsCy) {
            this.tagsCy.destroy();
        }

        this.tagsCy = cytoscape({
            container: document.getElementById('tags-graph-container'),
            elements: [...data.nodes, ...data.edges],
            style: [
                {
                    selector: 'node',
                    style: {
                        'background-color': '#3b82f6',
                        'label': 'data(label)',
                        'color': '#f1f5f9',
                        'text-outline-color': '#0f172a',
                        'text-outline-width': 2,
                        'font-size': '14px',
                        'width': ele => 30 + (ele.data('count') * 2),
                        'height': ele => 30 + (ele.data('count') * 2)
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': ele => 1 + (ele.data('weight') * 0.5),
                        'line-color': '#475569',
                        'opacity': 0.6
                    }
                }
            ],
            layout: {
                name: 'cose',
                animate: true,
                animationDuration: 500,
                nodeRepulsion: 10000,
                idealEdgeLength: 150
            }
        });
    }

    async exportSession() {
        if (!this.currentSession) return;
        
        const data = await fetch(`/api/export/session/${this.currentSession}`).then(r => r.json());
        
        // Download as JSON
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `tinybrain-session-${this.currentSession}-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }
}

// Initialize app
const app = new TinyBrainApp();
