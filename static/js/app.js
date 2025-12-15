/**
 * Charlie Munger's Second Brain - 前端应用
 */

// ===== 全局变量 =====
let network = null;
let graphData = null;

// ===== 对话管理 =====
let conversations = {};  // 所有对话 {id: {title, messages, createdAt}}
let currentConversationId = null;

// ===== 初始化 =====
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    loadGraphData();
    loadSuggestions();
    loadConversations();  // 加载历史对话
    
    // 绑定示例问题点击
    document.querySelectorAll('.message.system li').forEach(li => {
        li.addEventListener('click', () => {
            document.getElementById('chat-input').value = li.textContent;
            sendQuestion();
        });
    });
});

// ===== 对话管理函数 =====
function loadConversations() {
    // 从 localStorage 加载对话
    const saved = localStorage.getItem('munger_conversations');
    if (saved) {
        conversations = JSON.parse(saved);
    }
    
    // 如果没有对话，创建一个新的
    if (Object.keys(conversations).length === 0) {
        createNewConversation();
    } else {
        // 加载最近的对话
        const sortedIds = Object.keys(conversations).sort((a, b) => 
            conversations[b].createdAt - conversations[a].createdAt
        );
        switchConversation(sortedIds[0]);
    }
    
    renderConversationList();
}

function saveConversations() {
    localStorage.setItem('munger_conversations', JSON.stringify(conversations));
}

function createNewConversation() {
    const id = 'conv_' + Date.now();
    conversations[id] = {
        title: '新对话',
        messages: [],
        createdAt: Date.now()
    };
    currentConversationId = id;
    saveConversations();
    renderConversationList();
    clearChatMessages();
    addSystemMessage();
}

function switchConversation(id) {
    if (!conversations[id]) return;
    
    currentConversationId = id;
    clearChatMessages();
    
    // 恢复消息
    const conv = conversations[id];
    if (conv.messages.length === 0) {
        addSystemMessage();
    } else {
        conv.messages.forEach(msg => {
            addMessageToDOM(msg.type, msg.content, false);
        });
    }
    
    renderConversationList();
}

function deleteConversation(id) {
    if (Object.keys(conversations).length <= 1) {
        alert('至少保留一个对话');
        return;
    }
    
    delete conversations[id];
    saveConversations();
    
    if (currentConversationId === id) {
        const remaining = Object.keys(conversations);
        switchConversation(remaining[0]);
    }
    
    renderConversationList();
}

function clearChatMessages() {
    const container = document.getElementById('chat-messages');
    container.innerHTML = '';
}

function addSystemMessage() {
    const content = `
        <p>👋 你好！我是芒格思想助手。</p>
        <p>试试问我这些问题：</p>
        <ul>
            <li onclick="askExample(this)">芒格对激励机制有什么看法？</li>
            <li onclick="askExample(this)">什么是铁锤人综合征？</li>
            <li onclick="askExample(this)">复利思维如何应用到投资中？</li>
        </ul>
    `;
    addMessageToDOM('system', content, false);
}

function askExample(el) {
    document.getElementById('chat-input').value = el.textContent;
    sendQuestion();
}

function renderConversationList() {
    const container = document.getElementById('conversation-list');
    if (!container) return;
    
    const sortedConvs = Object.entries(conversations)
        .sort((a, b) => b[1].createdAt - a[1].createdAt);
    
    container.innerHTML = sortedConvs.map(([id, conv]) => `
        <div class="conv-item ${id === currentConversationId ? 'active' : ''}" onclick="switchConversation('${id}')">
            <span class="conv-title">${conv.title}</span>
            <span class="conv-time">${formatTime(conv.createdAt)}</span>
            <button class="conv-delete" onclick="event.stopPropagation(); deleteConversation('${id}')" title="删除">×</button>
        </div>
    `).join('');
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
    if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前';
    return date.toLocaleDateString('zh-CN');
}

function updateConversationTitle(question) {
    if (!currentConversationId) return;
    const conv = conversations[currentConversationId];
    if (conv.title === '新对话' && question) {
        conv.title = question.substring(0, 20) + (question.length > 20 ? '...' : '');
        saveConversations();
        renderConversationList();
    }
}

// 获取当前对话历史（用于多轮对话上下文）
function getConversationHistory() {
    if (!currentConversationId || !conversations[currentConversationId]) {
        return [];
    }
    
    const messages = conversations[currentConversationId].messages;
    const history = [];
    
    // 转换为 API 需要的格式，只取最近6条消息（3轮对话）
    const recentMessages = messages.slice(-6);
    
    for (const msg of recentMessages) {
        if (msg.type === 'user') {
            history.push({
                role: 'user',
                content: msg.content
            });
        } else if (msg.type === 'assistant') {
            // 清理 HTML，只保留纯文本
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = msg.content;
            // 提取主要回答内容（去除引用部分）
            const answerBody = tempDiv.querySelector('.answer-body');
            const textContent = answerBody ? answerBody.textContent : tempDiv.textContent;
            
            history.push({
                role: 'assistant',
                content: textContent.substring(0, 500)  // 限制长度
            });
        }
    }
    
    return history;
}

// ===== Tab 切换 =====
function initTabs() {
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // 更新 tab 状态
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // 切换面板
            const targetId = tab.dataset.tab + '-panel';
            document.querySelectorAll('.panel').forEach(panel => {
                panel.classList.remove('active');
            });
            document.getElementById(targetId).classList.add('active');
        });
    });
}

// ===== 加载图谱数据 =====
async function loadGraphData() {
    try {
        const response = await fetch('/api/graph');
        
        if (!response.ok) {
            showEmptyState();
            return;
        }
        
        graphData = await response.json();
        
        if (!graphData.nodes || graphData.nodes.length === 0) {
            showEmptyState();
            return;
        }
        
        hideEmptyState();
        renderGraph(graphData);
        updateStats();
        
    } catch (error) {
        console.error('加载图谱失败:', error);
        showEmptyState();
    }
}

// ===== 节点类型配置 =====
const NODE_CONFIG = {
    "概念": { color: "#FF6B6B", icon: "💡", size: 45, priority: 1 },
    "思维模型": { color: "#4ECDC4", icon: "🧠", size: 40, priority: 2 },
    "原则": { color: "#45B7D1", icon: "📐", size: 35, priority: 3 },
    "人物": { color: "#96CEB4", icon: "👤", size: 38, priority: 4 },
    "公司": { color: "#FFEAA7", icon: "🏢", size: 32, priority: 5 },
    "案例": { color: "#DDA0DD", icon: "📋", size: 30, priority: 6 },
    "学科": { color: "#98D8C8", icon: "📚", size: 35, priority: 7 },
    "认知偏误": { color: "#F7DC6F", icon: "⚠️", size: 28, priority: 8 },
    "书籍": { color: "#BB8FCE", icon: "📖", size: 28, priority: 9 },
};

// 当前过滤器状态
let activeFilters = new Set(Object.keys(NODE_CONFIG));

// ===== 渲染图谱 =====
function renderGraph(data) {
    const container = document.getElementById('graph-canvas');
    
    // 计算节点连接数用于调整大小
    const connectionCount = {};
    data.edges.forEach(edge => {
        connectionCount[edge.source] = (connectionCount[edge.source] || 0) + 1;
        connectionCount[edge.target] = (connectionCount[edge.target] || 0) + 1;
    });
    
    // 准备节点数据
    const nodes = new vis.DataSet(data.nodes
        .filter(node => activeFilters.has(node.type))
        .map(node => {
            const config = NODE_CONFIG[node.type] || { color: "#95a5a6", size: 25 };
            const connections = connectionCount[node.id] || 0;
            // 根据连接数调整大小
            const sizeBonus = Math.min(connections * 3, 20);
            const finalSize = config.size + sizeBonus;
            
            return {
                id: node.id,
                label: node.label,
                title: `【${node.type}】${node.label}\n${node.description || ''}`,
                color: {
                    background: config.color,
                    border: darkenColor(config.color, 20),
                    highlight: {
                        background: lightenColor(config.color, 15),
                        border: config.color
                    },
                    hover: {
                        background: lightenColor(config.color, 10),
                        border: config.color
                    }
                },
                size: finalSize,
                font: {
                    color: '#ffffff',
                    size: Math.max(12, finalSize / 3),
                    face: 'Noto Serif SC, Microsoft YaHei, sans-serif',
                    strokeWidth: 3,
                    strokeColor: 'rgba(0,0,0,0.7)'
                },
                borderWidth: 3,
                shadow: {
                    enabled: true,
                    color: config.color + '40',
                    size: 15,
                    x: 0,
                    y: 0
                }
            };
        }));
    
    // 准备边数据
    const nodeIds = new Set(nodes.getIds());
    const edges = new vis.DataSet(data.edges
        .filter(edge => nodeIds.has(edge.source) && nodeIds.has(edge.target))
        .map((edge, index) => ({
            id: index,
            from: edge.source,
            to: edge.target,
            label: edge.label,
            title: `${edge.source} → ${edge.label} → ${edge.target}`,
            arrows: {
                to: {
                    enabled: true,
                    scaleFactor: 1.2,
                    type: 'arrow'
                }
            },
            color: {
                color: 'rgba(150, 150, 150, 0.6)',
                highlight: '#58a6ff',
                hover: '#ffffff'
            },
            font: {
                color: '#aaaaaa',
                size: 11,
                strokeWidth: 4,
                strokeColor: '#0d1117',
                face: 'Noto Serif SC, sans-serif',
                align: 'middle'
            },
            smooth: {
                enabled: true,
                type: 'curvedCW',
                roundness: 0.15
            },
            width: 2,
            hoverWidth: 3
        })));
    
    // 配置选项
    const options = {
        nodes: {
            shape: 'dot',
            scaling: {
                min: 20,
                max: 60
            }
        },
        edges: {
            selectionWidth: 2
        },
        physics: {
            enabled: true,
            barnesHut: {
                gravitationalConstant: -3000,
                centralGravity: 0.3,
                springLength: 150,
                springConstant: 0.04,
                damping: 0.09,
                avoidOverlap: 0.5
            },
            maxVelocity: 50,
            solver: 'barnesHut',
            timestep: 0.5,
            stabilization: {
                enabled: true,
                iterations: 200,
                updateInterval: 25
            }
        },
        interaction: {
            hover: true,
            tooltipDelay: 100,
            navigationButtons: true,
            keyboard: {
                enabled: true,
                speed: { x: 10, y: 10, zoom: 0.02 }
            },
            zoomView: true,
            dragView: true,
            multiselect: true
        },
        layout: {
            improvedLayout: true,
            randomSeed: 42
        }
    };
    
    // 创建网络图
    network = new vis.Network(container, { nodes, edges }, options);
    
    // 点击节点事件
    network.on('click', function(params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            showNodeDetail(nodeId);
            // 高亮相邻节点
            highlightConnected(nodeId);
        } else {
            closeNodeDetail();
            resetHighlight();
        }
    });
    
    // 双击节点探索
    network.on('doubleClick', function(params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            document.getElementById('explore-input').value = nodeId;
            document.querySelector('[data-tab="explore"]').click();
            exploreEntity();
        }
    });
    
    // 稳定后适应视图
    network.once('stabilizationIterationsDone', function() {
        network.fit({ animation: { duration: 500 } });
    });
}

// 高亮连接的节点
function highlightConnected(nodeId) {
    if (!network) return;
    
    const connectedNodes = network.getConnectedNodes(nodeId);
    const allNodes = network.body.data.nodes.getIds();
    
    const updates = allNodes.map(id => {
        if (id === nodeId || connectedNodes.includes(id)) {
            return { id, opacity: 1 };
        } else {
            return { id, opacity: 0.2 };
        }
    });
    
    network.body.data.nodes.update(updates);
}

// 重置高亮
function resetHighlight() {
    if (!network) return;
    
    const allNodes = network.body.data.nodes.getIds();
    const updates = allNodes.map(id => ({ id, opacity: 1 }));
    network.body.data.nodes.update(updates);
}

// 切换过滤器
function toggleFilter(type) {
    if (activeFilters.has(type)) {
        activeFilters.delete(type);
    } else {
        activeFilters.add(type);
    }
    updateFilterUI();
    if (graphData) {
        renderGraph(graphData);
    }
}

// 更新过滤器 UI
function updateFilterUI() {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        const type = btn.dataset.type;
        if (activeFilters.has(type)) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// 重置所有过滤器
function resetFilters() {
    activeFilters = new Set(Object.keys(NODE_CONFIG));
    updateFilterUI();
    if (graphData) {
        renderGraph(graphData);
    }
}

// 只显示核心概念
function showCoreOnly() {
    activeFilters = new Set(["概念", "思维模型", "原则", "人物"]);
    updateFilterUI();
    if (graphData) {
        renderGraph(graphData);
    }
}

// ===== 显示节点详情 =====
async function showNodeDetail(nodeId) {
    try {
        const response = await fetch(`/api/entity/${encodeURIComponent(nodeId)}`);
        if (!response.ok) return;
        
        const entity = await response.json();
        
        document.getElementById('detail-name').textContent = entity.name;
        document.getElementById('detail-type').textContent = entity.type;
        document.getElementById('detail-desc').textContent = entity.description || '暂无描述';
        
        // 显示关系
        const relationsDiv = document.getElementById('detail-relations');
        let html = '';
        
        if (entity.neighbors.in && entity.neighbors.in.length > 0) {
            html += '<h4>入边关系</h4>';
            entity.neighbors.in.forEach(rel => {
                html += `<div class="relation-item">
                    <span class="entity">${rel.entity}</span>
                    <span class="arrow">→</span>
                    <span class="relation-type">[${rel.relation}]</span>
                    <span class="arrow">→</span>
                    <span>${entity.name}</span>
                </div>`;
            });
        }
        
        if (entity.neighbors.out && entity.neighbors.out.length > 0) {
            html += '<h4>出边关系</h4>';
            entity.neighbors.out.forEach(rel => {
                html += `<div class="relation-item">
                    <span>${entity.name}</span>
                    <span class="arrow">→</span>
                    <span class="relation-type">[${rel.relation}]</span>
                    <span class="arrow">→</span>
                    <span class="entity">${rel.entity}</span>
                </div>`;
            });
        }
        
        relationsDiv.innerHTML = html || '<p style="color: var(--text-muted)">暂无关系</p>';
        
        document.getElementById('node-detail').classList.add('show');
        
    } catch (error) {
        console.error('获取节点详情失败:', error);
    }
}

function closeNodeDetail() {
    document.getElementById('node-detail').classList.remove('show');
}

// ===== 更新统计信息 =====
async function updateStats() {
    try {
        const response = await fetch('/api/stats');
        if (!response.ok) return;
        
        const stats = await response.json();
        document.getElementById('node-count').textContent = stats['节点数'] || 0;
        document.getElementById('edge-count').textContent = stats['边数'] || 0;
    } catch (error) {
        console.error('获取统计信息失败:', error);
    }
}

// ===== 空状态 =====
function showEmptyState() {
    document.getElementById('empty-state').style.display = 'block';
    document.querySelector('.graph-container').style.display = 'none';
}

function hideEmptyState() {
    document.getElementById('empty-state').style.display = 'none';
    document.querySelector('.graph-container').style.display = 'block';
}

// ===== 完整构建：知识图谱 + 向量索引 =====
async function buildFullSystem() {
    showLoading();
    
    try {
        // 步骤1：构建知识图谱
        document.querySelector('.loading-overlay p').textContent = '🧠 步骤1/2：提取知识图谱...\n（约需1分钟）';
        
        let response = await fetch('/api/build_with_llm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        let result = await response.json();
        
        if (!result.success) {
            hideLoading();
            alert('知识图谱提取失败: ' + (result.error || '未知错误'));
            return;
        }
        
        const graphStats = result.stats;
        
        // 步骤2：构建向量索引
        document.querySelector('.loading-overlay p').textContent = '📚 步骤2/2：构建向量索引...\n（约需1-2分钟，用于语义搜索）';
        
        response = await fetch('/api/build_vector_index', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        result = await response.json();
        
        if (!result.success) {
            hideLoading();
            alert('向量索引构建失败: ' + (result.error || '未知错误'));
            return;
        }
        
        await loadGraphData();
        hideLoading();
        
        alert(`🎉 完整系统构建完成！\n\n📊 知识图谱：\n- 节点数: ${graphStats['节点数']}\n- 关系数: ${graphStats['边数']}\n\n📚 向量索引：\n- 文本块: ${result.chunks}\n- 向量维度: ${result.dimension}\n\n✨ 现在支持语义搜索和原文引用！`);
        
    } catch (error) {
        hideLoading();
        alert('构建失败: ' + error.message);
    }
}

// ===== 使用 LLM 智能提取 =====
async function buildWithLLM() {
    showLoading();
    document.querySelector('.loading-overlay p').textContent = '🧠 使用通义千问智能分析书籍...\n（约需1-2分钟）';
    
    try {
        const response = await fetch('/api/build_with_llm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (result.success) {
            await loadGraphData();
            hideLoading();
            const stats = result.stats;
            alert(`🎉 LLM 智能提取完成！\n\n📊 统计：\n- 节点数: ${stats['节点数']}\n- 关系数: ${stats['边数']}\n\n✨ 使用通义千问从书中智能发现知识`);
        } else {
            hideLoading();
            alert('提取失败: ' + (result.error || '未知错误'));
        }
    } catch (error) {
        hideLoading();
        alert('提取失败: ' + error.message);
    }
}

// ===== 从书中提取知识（词典匹配）=====
async function buildFromBook() {
    showLoading();
    document.querySelector('.loading-overlay p').textContent = '正在从《穷查理宝典》提取知识...';
    
    try {
        const response = await fetch('/api/build_from_book', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (result.success) {
            await loadGraphData();
            hideLoading();
            const stats = result.stats;
            alert(`🎉 知识提取完成！\n\n📊 统计：\n- 节点数: ${stats['节点数']}\n- 关系数: ${stats['边数']}\n\n数据来源: 词典匹配模式`);
        } else {
            hideLoading();
            alert('提取失败: ' + (result.error || '未知错误'));
        }
    } catch (error) {
        hideLoading();
        alert('提取失败: ' + error.message);
    }
}

// ===== 构建演示图谱 =====
async function buildDemo() {
    showLoading();
    document.querySelector('.loading-overlay p').textContent = '正在构建演示图谱...';
    
    try {
        const response = await fetch('/api/build_demo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (result.success) {
            await loadGraphData();
            hideLoading();
            alert('🎉 演示图谱构建完成！');
        } else {
            hideLoading();
            alert('构建失败: ' + (result.error || '未知错误'));
        }
    } catch (error) {
        hideLoading();
        alert('构建失败: ' + error.message);
    }
}

// ===== 智能问答 =====
async function sendQuestion() {
    const input = document.getElementById('chat-input');
    const question = input.value.trim();
    
    if (!question) return;
    
    // 更新对话标题
    updateConversationTitle(question);
    
    // 添加用户消息
    addMessage('user', question);
    input.value = '';
    
    // 添加加载提示
    const loadingId = addMessageToDOM('assistant', '<div class="typing">🔍 正在从书籍和知识图谱中检索...</div>', false);
    
    try {
        // 获取对话历史（用于多轮对话）
        const history = getConversationHistory();
        
        // 优先尝试混合查询（向量检索 + 图谱 + LLM）
        let response = await fetch('/api/hybrid_query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, history })
        });
        
        let result = await response.json();
        
        // 如果混合查询失败（向量索引未构建），回退到普通查询
        if (result.error && result.error.includes('向量索引')) {
            console.log('向量索引未构建，使用图谱查询');
            response = await fetch('/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question, history })
            });
            result = await response.json();
        }
        
        // 移除加载提示
        document.getElementById(loadingId)?.remove();
        
        if (result.answer) {
            // 构建完整回答（包含可折叠引用）
            let fullContent = '';
            
            // 模式标识
            const modeIcon = result.mode === 'hybrid' ? '📚+🔗' : '🔗';
            fullContent += `<div class="answer-mode">${modeIcon} ${result.mode === 'hybrid' ? '向量检索 + 知识图谱' : '知识图谱'}</div>`;
            
            // 主要回答（Markdown 渲染）
            fullContent += `<div class="answer-body">${formatAnswer(result.answer)}</div>`;
            
            // 可折叠的引用来源
            if (result.citations && result.citations.length > 0) {
                const citationId = 'cite-' + Date.now();
                fullContent += `
                    <div class="citations-section">
                        <button class="citations-toggle" onclick="toggleCitations('${citationId}')">
                            <span class="toggle-icon">▶</span>
                            📖 查看引用来源 (${result.citations.length})
                        </button>
                        <div class="citations-list collapsed" id="${citationId}">
                `;
                result.citations.forEach(cite => {
                    fullContent += `
                        <div class="citation-item">
                            <span class="citation-num">[${cite.id}]</span>
                            <span class="citation-chapter">${cite.chapter}</span>
                            <span class="citation-score">相似度: ${(cite.score * 100).toFixed(1)}%</span>
                            <p class="citation-text">"${cite.text}"</p>
                        </div>
                    `;
                });
                fullContent += '</div></div>';
            }
            
            addMessage('assistant', fullContent);
        } else {
            addMessage('assistant', '抱歉，暂时无法回答这个问题。' + (result.error || ''));
        }
        
    } catch (error) {
        document.getElementById(loadingId)?.remove();
        addMessage('assistant', '请求失败: ' + error.message);
    }
}

// 折叠/展开引用
function toggleCitations(id) {
    const list = document.getElementById(id);
    const btn = list.previousElementSibling;
    const icon = btn.querySelector('.toggle-icon');
    
    if (list.classList.contains('collapsed')) {
        list.classList.remove('collapsed');
        icon.textContent = '▼';
        btn.querySelector('span:last-child') || (btn.innerHTML = btn.innerHTML.replace('查看引用来源', '收起引用来源'));
    } else {
        list.classList.add('collapsed');
        icon.textContent = '▶';
        btn.innerHTML = btn.innerHTML.replace('收起引用来源', '查看引用来源');
    }
}

// 添加消息（保存到对话历史）
function addMessage(type, content) {
    // 保存到当前对话
    if (currentConversationId && conversations[currentConversationId]) {
        conversations[currentConversationId].messages.push({ type, content });
        saveConversations();
    }
    
    return addMessageToDOM(type, content, true);
}

// 仅添加到 DOM（不保存）
function addMessageToDOM(type, content, scroll = true) {
    const container = document.getElementById('chat-messages');
    const id = 'msg-' + Date.now();
    
    const msgDiv = document.createElement('div');
    msgDiv.id = id;
    msgDiv.className = `message ${type}`;
    msgDiv.innerHTML = `<div class="message-content">${content}</div>`;
    
    container.appendChild(msgDiv);
    
    if (scroll) {
        container.scrollTop = container.scrollHeight;
    }
    
    return id;
}

function formatAnswer(text) {
    // 使用 marked.js 渲染 Markdown
    if (typeof marked !== 'undefined') {
        // 配置 marked
        marked.setOptions({
            breaks: true,  // 换行符转为 <br>
            gfm: true,     // GitHub 风格 Markdown
            sanitize: false
        });
        return marked.parse(text);
    }
    
    // 降级：简单的 markdown 格式化
    return text
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>');
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendQuestion();
    }
}

// ===== 概念探索 =====
async function loadSuggestions() {
    try {
        const response = await fetch('/api/entities');
        if (!response.ok) return;
        
        const entities = await response.json();
        const container = document.getElementById('suggestion-tags');
        
        // 选取部分实体作为建议
        const suggestions = entities
            .filter(e => ['概念', '思维模型', '认知偏误'].includes(e.type))
            .slice(0, 8);
        
        container.innerHTML = suggestions.map(e => 
            `<span class="suggestion-tag" onclick="exploreByName('${e.name}')">${e.name}</span>`
        ).join('');
        
    } catch (error) {
        console.error('加载建议失败:', error);
    }
}

function exploreByName(name) {
    document.getElementById('explore-input').value = name;
    exploreEntity();
}

async function exploreEntity() {
    const input = document.getElementById('explore-input');
    const entityName = input.value.trim();
    
    if (!entityName) return;
    
    const resultDiv = document.getElementById('explore-result');
    resultDiv.innerHTML = '<div class="explore-card"><p>正在探索...</p></div>';
    
    try {
        const response = await fetch(`/api/explore/${encodeURIComponent(entityName)}`);
        
        if (!response.ok) {
            const error = await response.json();
            resultDiv.innerHTML = `<div class="explore-card"><p style="color: var(--accent-red)">❌ ${error.error}</p></div>`;
            return;
        }
        
        const data = await response.json();
        
        let html = `
            <div class="explore-card">
                <h3>
                    <span style="font-size: 1.5em">📌</span>
                    ${data.center}
                </h3>
                <div class="relation-list">
        `;
        
        data.edges.forEach(edge => {
            const isOutgoing = edge.source === data.center;
            if (isOutgoing) {
                html += `
                    <div class="relation-row">
                        <span class="entity" onclick="exploreByName('${data.center}')">${data.center}</span>
                        <span class="rel-type">—[${edge.label}]→</span>
                        <span class="entity" onclick="exploreByName('${edge.target}')">${edge.target}</span>
                    </div>
                `;
            } else {
                html += `
                    <div class="relation-row">
                        <span class="entity" onclick="exploreByName('${edge.source}')">${edge.source}</span>
                        <span class="rel-type">—[${edge.label}]→</span>
                        <span class="entity" onclick="exploreByName('${data.center}')">${data.center}</span>
                    </div>
                `;
            }
        });
        
        if (data.edges.length === 0) {
            html += '<p style="color: var(--text-muted)">暂无关联关系</p>';
        }
        
        html += '</div></div>';
        resultDiv.innerHTML = html;
        
    } catch (error) {
        resultDiv.innerHTML = `<div class="explore-card"><p style="color: var(--accent-red)">请求失败: ${error.message}</p></div>`;
    }
}

function handleExploreKeyPress(event) {
    if (event.key === 'Enter') {
        exploreEntity();
    }
}

// ===== 工具函数 =====
function showLoading() {
    document.getElementById('loading-overlay').classList.add('show');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.remove('show');
}

function lightenColor(color, percent) {
    const num = parseInt(color.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = (num >> 16) + amt;
    const G = (num >> 8 & 0x00FF) + amt;
    const B = (num & 0x0000FF) + amt;
    return '#' + (
        0x1000000 +
        (R < 255 ? (R < 1 ? 0 : R) : 255) * 0x10000 +
        (G < 255 ? (G < 1 ? 0 : G) : 255) * 0x100 +
        (B < 255 ? (B < 1 ? 0 : B) : 255)
    ).toString(16).slice(1);
}

function darkenColor(color, percent) {
    const num = parseInt(color.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = (num >> 16) - amt;
    const G = (num >> 8 & 0x00FF) - amt;
    const B = (num & 0x0000FF) - amt;
    return '#' + (
        0x1000000 +
        (R > 0 ? R : 0) * 0x10000 +
        (G > 0 ? G : 0) * 0x100 +
        (B > 0 ? B : 0)
    ).toString(16).slice(1);
}

