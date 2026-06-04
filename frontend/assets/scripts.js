document.addEventListener('DOMContentLoaded', async () => {
    // --- STATE ---
    let authToken = localStorage.getItem('cc_token');
    let isRegister = false;
    let ws = null;
    let currentUserName = "User";
    let currentUserRole = null;

    // Default helper: if served from GitHub Pages, suggest the Vercel backend hostname.
    const defaultApiBase = window.location.hostname.endsWith('github.io')
        ? 'https://campus-connect-backend.vercel.app'
        : window.location.origin;

    const apiBaseAttr = (document.body.getAttribute('data-api-base') || '').replace(/\/$/, '');
    const fallbackAttr = (document.body.getAttribute('data-api-base-fallback') || '').replace(/\/$/, '');

    const probe = async (base) => {
        if(!base) return false;
        try {
            const controller = new AbortController();
            const id = setTimeout(() => controller.abort(), 2000);
            const res = await fetch(`${base.replace(/\/$/, '')}/api/v1/auth/ping`, { signal: controller.signal });
            clearTimeout(id);
            return res.ok;
        } catch (e) { return false; }
    };

    let apiBase = '';
    if(apiBaseAttr) {
        apiBase = apiBaseAttr;
    } else if(await probe(window.location.origin)) {
        apiBase = window.location.origin;
    } else if(fallbackAttr && await probe(fallbackAttr)) {
        apiBase = fallbackAttr;
    } else if(await probe(defaultApiBase)) {
        apiBase = defaultApiBase;
    } else {
        // Last resort: use defaultApiBase regardless (may produce 404 but preserves prior behavior)
        apiBase = defaultApiBase;
    }

    const apiUrl = (endpoint) => `${apiBase}/api/v1${endpoint}`;

    // Listen for OAuth popup messages (demo flow)
    window.addEventListener('message', (e) => {
        try {
            if(e.origin !== window.location.origin) return;
            const data = e.data || {};
            if(data.type === 'oauth' && data.token) {
                authToken = data.token;
                localStorage.setItem('cc_token', authToken);
                mainActionBtn.innerText = "Logout";
                navigate('dashboard');
                initDashboard();
                loadDoubts();
            }
        } catch (err) { /* ignore */ }
    });

    // --- DOM ELEMENTS ---
    const views = document.querySelectorAll('.view');
    const themeBtn = document.getElementById('theme-toggle-btn');
    const mainActionBtn = document.getElementById('main-action-btn');
    const heroCtaBtn = document.getElementById('hero-cta-btn');
    
    // Auth Elements
    const authTitle = document.getElementById('auth-title');
    const authSubtitle = document.getElementById('auth-subtitle');
    const nameGroup = document.getElementById('name-group');
    const authToggleText = document.getElementById('auth-toggle-text');
    const authToggleLink = document.getElementById('auth-toggle-link');
    const authSubmitBtn = document.getElementById('auth-submit-btn');
    
    // Dashboard Elements
    const userNameSpan = document.getElementById('user-name');
    const updateProfileBtn = document.getElementById('update-profile-btn');
    const aiSearchBtn = document.getElementById('ai-search-btn');
    const chatSendBtn = document.getElementById('chat-send-btn');
    const chatInput = document.getElementById('chat-input');

    // --- THREE.JS ANIMATED NETWORK ---
    const initThreeJS = () => {
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('three-canvas'), alpha: true, antialias: true });
        
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        camera.position.z = 30;

        const geometry = new THREE.BufferGeometry();
        const count = 300;
        const positions = new Float32Array(count * 3);
        for(let i = 0; i < count * 3; i++) positions[i] = (Math.random() - 0.5) * 60;
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        
        const material = new THREE.PointsMaterial({ color: 0x2563EB, size: 0.15, transparent: true, opacity: 0.8, blending: THREE.AdditiveBlending });
        const points = new THREE.Points(geometry, material);
        scene.add(points);

        function animate() {
            requestAnimationFrame(animate);
            points.rotation.y += 0.0005;
            points.rotation.x += 0.0002;
            renderer.render(scene, camera);
        }
        animate();

        window.addEventListener('resize', () => { 
            camera.aspect = window.innerWidth / window.innerHeight; 
            camera.updateProjectionMatrix(); 
            renderer.setSize(window.innerWidth, window.innerHeight); 
        });
    };

    // --- PAGE ANIMATIONS (GSAP) ---
    const initAnimations = () => {
        if(typeof gsap === 'undefined') return;
        try{
            // hero entrance
            gsap.from('[data-animate="hero"]', { y: -30, opacity: 0, duration: 0.9, ease: 'power3.out' });
            gsap.from('[data-animate="sub"]', { y: -10, opacity: 0, duration: 0.8, delay: 0.12, ease: 'power3.out' });
            gsap.from('[data-animate="ctas"]', { y: 6, opacity: 0, duration: 0.8, delay: 0.22, ease: 'power3.out' });

            // stagger feature cards
            gsap.from('[data-animate="card"]', { y: 20, opacity: 0, duration: 0.8, stagger: 0.12, delay: 0.3, ease: 'power3.out' });

            // gentle float for feature cards to make UI feel alive
            gsap.utils.toArray('.feature-card').forEach((el,i)=>{
                const delay = 0.6 + (i*0.08);
                gsap.to(el, { y: 6, duration: 3 + (i%3), repeat: -1, yoyo: true, ease: 'sine.inOut', delay });
            });
        }catch(e){ console.warn('GSAP animations failed', e); }
    };

    // --- UI LOGIC ---
    const navigate = (viewId) => {
        views.forEach(v => v.classList.remove('active'));
        document.getElementById(`view-${viewId}`).classList.add('active');
        gsap.from(`#view-${viewId}`, { y: 20, opacity: 0, duration: 0.5, ease: "power3.out" });
    };

    const toggleTheme = () => {
        const html = document.documentElement;
        const next = html.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
        html.setAttribute('data-theme', next);
        localStorage.setItem('cc_theme', next);
        // update button label for clarity
        themeBtn.innerText = next === 'light' ? 'Dark Mode' : 'Light Mode';
    };

    // restore theme from previous selection
    (function restoreTheme(){
        try{
            const saved = localStorage.getItem('cc_theme');
            if(saved) document.documentElement.setAttribute('data-theme', saved);
            themeBtn.innerText = document.documentElement.getAttribute('data-theme') === 'light' ? 'Dark Mode' : 'Light Mode';
        }catch(e){}
    })();

    const toggleAuthMode = (e) => {
        e.preventDefault();
        isRegister = !isRegister;
        nameGroup.style.display = isRegister ? 'block' : 'none';
        authTitle.innerText = isRegister ? "Create Account" : "Welcome Back";
        authSubtitle.innerText = isRegister ? "Join the mentorship network" : "Login to your account";
        authToggleText.innerText = isRegister ? "Already have an account?" : "Don't have an account?";
        authToggleLink.innerText = isRegister ? "Login" : "Register";
    };

    const handleNavAction = () => {
        if(authToken) {
            authToken = null; 
            localStorage.removeItem('cc_token'); 
            if(ws) ws.close();
            navigate('landing');
            mainActionBtn.innerText = "Get Started";
        } else {
            navigate('auth');
        }
    };

    // --- API COMMUNICATION ---
    const api = async (endpoint, method, body = null) => {
        const headers = {};
        if(body) headers['Content-Type'] = 'application/x-www-form-urlencoded';
        if(authToken) headers['Authorization'] = `Bearer ${authToken}`;
        const res = await fetch(apiUrl(endpoint), { method, headers, body: body ? new URLSearchParams(body) : null });
        // tolerate empty or non-json responses
        const text = await res.text();
        let data = null;
        try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }
        if(!res.ok) {
            const msg = (data && (data.detail || data.message)) || text || res.statusText || 'API Error';
            throw new Error(msg);
        }
        return data ?? {};
    };

    // small loading helper for buttons
    const setLoading = (btn, loading, text) => {
        if(!btn) return;
        if(loading) {
            btn.disabled = true;
            btn.dataset.orig = btn.innerText;
            btn.innerText = text || 'Loading...';
            btn.style.opacity = 0.7;
        } else {
            btn.disabled = false;
            if(btn.dataset.orig) btn.innerText = btn.dataset.orig;
            btn.style.opacity = '';
        }
    };

    const handleAuth = async () => {
        try {
            setLoading(authSubmitBtn, true, isRegister ? 'Creating...' : 'Signing in...');
            const email = document.getElementById('auth-email').value;
            const pass = document.getElementById('auth-pass').value;
            let res;
            if(isRegister) {
                const name = document.getElementById('auth-name').value;
                if(!name) throw new Error("Name is required");
                res = await api('/auth/register', 'POST', { email, password: pass, full_name: name });
            } else {
                res = await api('/auth/login', 'POST', { email, password: pass });
            }
            authToken = res.access_token;
            currentUserName = res.full_name;
            localStorage.setItem('cc_token', authToken);
            mainActionBtn.innerText = "Logout";
            navigate('dashboard');
            initDashboard();
            setLoading(authSubmitBtn, false);
        } catch (e) { alert(e.message); setLoading(authSubmitBtn, false); }
    };

    const initDashboard = async () => {
        try {
            const user = await api('/users/me', 'GET');
            currentUserName = user.profile.full_name;
            currentUserRole = user.role || 'STUDENT';
            userNameSpan.innerText = currentUserName;
            document.getElementById('profile-skills').value = user.profile.skills.join(', ');
            document.getElementById('profile-goals').value = user.profile.goals.join(', ');
            initWebSocket();
            // show admin entry if user is admin
            if(currentUserRole === 'ADMIN'){
                const nav = document.querySelector('.nav-actions');
                if(nav && !document.getElementById('admin-btn')){
                    const btn = document.createElement('button');
                    btn.id = 'admin-btn';
                    btn.className = 'btn btn-outline';
                    btn.innerText = 'Admin';
                    btn.addEventListener('click', () => { navigate('admin'); loadAdminPanel(); });
                    nav.insertBefore(btn, nav.firstChild);
                }
            }
        } catch(e) { handleNavAction(); }
    };

    // --- AI INTEGRATION ---
    const updateProfile = async () => {
        try {
            setLoading(updateProfileBtn, true, 'Syncing...');
            const skills = document.getElementById('profile-skills').value;
            const goals = document.getElementById('profile-goals').value;
            const res = await api('/ai/update-profile-embeddings', 'POST', { skills, goals });
            alert(res.message);
            setLoading(updateProfileBtn, false);
        } catch (e) { alert(e.message); setLoading(updateProfileBtn, false); }
    };

    const searchMentors = async () => {
        try {
            setLoading(aiSearchBtn, true, 'Searching...');
            const query = document.getElementById('ai-query').value;
            if(!query) { setLoading(aiSearchBtn, false); return; }
            const res = await api(`/ai/find-mentors?query=${encodeURIComponent(query)}`, 'GET');
            const resultsDiv = document.getElementById('ai-results');
            resultsDiv.innerHTML = "";
            
            if(!res.mentors || !res.mentors.metadatas || res.mentors.metadatas[0].length === 0) {
                resultsDiv.innerHTML = "<div class='ai-result-item'>No mentors found. Try updating your profile first.</div>";
                setLoading(aiSearchBtn, false);
                return;
            }

            res.mentors.metadatas[0].forEach((m, i) => {
                const dist = res.mentors.distances[0][i];
                const score = Math.max(0, 100 - (dist * 100)).toFixed(1);
                resultsDiv.innerHTML += `<div class='ai-result-item'><div><strong>${m.full_name}</strong><div class='meta'>Skills: ${m.skills}</div></div><div>${score}%</div></div>`;
            });
            setLoading(aiSearchBtn, false);
        } catch (e) { document.getElementById('ai-results').innerHTML = "<div class='ai-result-item'>Error searching.</div>"; setLoading(aiSearchBtn, false); }
    };

    // --- DOUBTS BOARD ---
    const postDoubt = async () => {
        try {
            const postBtn = document.getElementById('post-doubt-btn');
            setLoading(postBtn, true, 'Posting...');
            const title = document.getElementById('doubt-title').value.trim();
            const content = document.getElementById('doubt-content').value.trim();
            if(!title || !content) throw new Error('Title and content required');
            const res = await api('/doubts/', 'POST', { title, content });
            alert(res.message);
            document.getElementById('doubt-title').value = '';
            document.getElementById('doubt-content').value = '';
            await loadDoubts();
            setLoading(postBtn, false);
        } catch(e) { alert(e.message); const postBtn = document.getElementById('post-doubt-btn'); setLoading(postBtn, false); }
    };

    const loadDoubts = async () => {
        try {
            const res = await api('/doubts/', 'GET');
            const list = document.getElementById('doubts-list');
            list.innerHTML = '';
            res.doubts.forEach(d => {
                list.innerHTML += `<div class='doubt-item'><strong>${d.title}</strong><div style='font-size:12px;opacity:0.8'>${d.content}</div></div>`;
            });
        } catch(e) { document.getElementById('doubts-list').innerHTML = '<div>No doubts.</div>'; }
    };

    // --- REAL-TIME WEBSOCKET ---
    const initWebSocket = () => {
        if(ws) ws.close();
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        ws = new WebSocket(`${protocol}//${window.location.host}/ws/chat/community_room`);
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if(data.sender !== 'user') appendChatMessage(data.message, false);
        };
    };

    const appendChatMessage = (text, isSelf) => {
        const box = document.getElementById('chat-box');
        const div = document.createElement('div');
        div.className = `chat-msg ${isSelf ? 'self' : ''}`;
        div.innerText = text;
        box.appendChild(div);
        box.scrollTop = box.scrollHeight;
    };

    const sendMessage = () => {
        const text = chatInput.value.trim();
        if(text && ws && ws.readyState === WebSocket.OPEN) {
            ws.send(text);
            appendChatMessage(text, true);
            chatInput.value = '';
        }
    };

    // --- EVENT LISTENERS ---
    themeBtn.addEventListener('click', toggleTheme);
    mainActionBtn.addEventListener('click', handleNavAction);
    heroCtaBtn.addEventListener('click', () => navigate('auth'));
    authToggleLink.addEventListener('click', toggleAuthMode);
    authSubmitBtn.addEventListener('click', handleAuth);
    
    updateProfileBtn.addEventListener('click', updateProfile);
    aiSearchBtn.addEventListener('click', searchMentors);
    document.getElementById('post-doubt-btn').addEventListener('click', postDoubt);
    chatSendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => { if(e.key === 'Enter') sendMessage(); });

    // Social login handlers (frontend-only redirects/popup)
    const openOAuth = (provider) => {
        const url = apiUrl(`/auth/oauth/${provider}`);
        try {
            const w = window.open(url, '_blank', 'toolbar=0,location=0,menubar=0,width=600,height=700');
            if(!w) window.location.href = url;
        } catch (e) { window.location.href = url; }
    };
    const gBtn = document.getElementById('google-login-btn');
    const ghBtn = document.getElementById('github-login-btn');
    const liBtn = document.getElementById('linkedin-login-btn');
    if(gBtn) gBtn.addEventListener('click', () => openOAuth('google'));
    if(ghBtn) ghBtn.addEventListener('click', () => openOAuth('github'));
    if(liBtn) liBtn.addEventListener('click', () => openOAuth('linkedin'));

    // Hero Live Demo button behavior — configurable via body data-demo-url
    const heroDemoBtn = document.getElementById('hero-demo-btn');
    const openLiveDemo = () => {
        const url = document.body.getAttribute('data-demo-url') || apiUrl('/auth/oauth/google');
        try {
            const w = window.open(url, '_blank', 'toolbar=0,location=0,menubar=0,width=1000,height=800');
            if(!w) window.location.href = url;
        } catch(e) { window.location.href = url; }
    };
    if(heroDemoBtn) heroDemoBtn.addEventListener('click', (e) => { e.preventDefault(); openLiveDemo(); });

    // --- INITIALIZATION ---
    initThreeJS();
    initAnimations();
    
    if(authToken) {
        mainActionBtn.innerText = "Logout";
        navigate('dashboard');
        initDashboard();
        loadDoubts();
    } else {
        navigate('landing');
    }
});

// --- ADMIN PANEL FUNCTIONS ---
const loadAdminPanel = async () => {
    try{
        const users = await api('/admin/users', 'GET');
        const usersEl = document.getElementById('admin-users');
        usersEl.innerHTML = '';
        users.forEach(u => {
            const div = document.createElement('div');
            div.style.display = 'flex'; div.style.justifyContent = 'space-between'; div.style.alignItems = 'center';
            div.innerHTML = `<div><strong>${u.email}</strong> <span style="color:var(--text-secondary)">(${u.role})</span></div>`;
            const actions = document.createElement('div');
            const premiumBtn = document.createElement('button');
            premiumBtn.className = 'btn btn-secondary';
            premiumBtn.innerText = u.is_premium ? 'Revoke Premium' : 'Grant Premium';
            premiumBtn.addEventListener('click', async () => {
                await api(`/admin/users/${u.id}/premium`, 'POST', { premium: !u.is_premium });
                loadAdminPanel();
            });
            const roleBtn = document.createElement('button');
            roleBtn.className = 'btn btn-outline';
            roleBtn.style.marginLeft = '8px';
            roleBtn.innerText = u.role === 'ADMIN' ? 'Demote' : 'Make Admin';
            roleBtn.addEventListener('click', async () => {
                const nextRole = u.role === 'ADMIN' ? 'STUDENT' : 'ADMIN';
                await api(`/admin/users/${u.id}/role`, 'POST', { role: nextRole });
                loadAdminPanel();
            });
            actions.appendChild(premiumBtn); actions.appendChild(roleBtn);
            div.appendChild(actions);
            usersEl.appendChild(div);
        });

        const doubts = await api('/admin/doubts', 'GET');
        const doubtsEl = document.getElementById('admin-doubts');
        doubtsEl.innerHTML = '';
        doubts.forEach(d => {
            const div = document.createElement('div');
            div.style.display='flex'; div.style.justifyContent='space-between'; div.style.alignItems='center';
            div.innerHTML = `<div><strong>${d.title}</strong><div style="color:var(--text-secondary)">${d.content}</div></div>`;
            const del = document.createElement('button'); del.className='btn btn-danger'; del.innerText='Delete';
            del.addEventListener('click', async ()=>{ await api(`/admin/doubts/${d.id}`, 'DELETE'); loadAdminPanel(); });
            div.appendChild(del);
            doubtsEl.appendChild(div);
        });
    }catch(e){ alert('Admin load failed: ' + e.message); }
};