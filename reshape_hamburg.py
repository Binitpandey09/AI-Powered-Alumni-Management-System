import re

with open('templates/dashboard/base_dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Remove the old floating button CSS
css_to_remove = '''/* ── Sidebar toggle button ── */
.sidebar-toggle-btn {
  position: absolute; right: -13px; top: 16px; width: 26px; height: 26px;
  border-radius: 50%; background: white; border: 1px solid #E2E8F0;
  box-shadow: 0 1px 6px rgba(0,0,0,0.12); cursor: pointer; display: flex;
  align-items: center; justify-content: center; z-index: 100; color: #64748B;
  transition: background 0.15s, transform 220ms ease;
}
.sidebar-toggle-btn:hover {
  background: #F1F5F9; color: #0F172A;
}
.dashboard-sidebar.sidebar-collapsed .sidebar-toggle-btn {
  transform: rotate(180deg);
}'''
text = text.replace(css_to_remove, '')

# 2. Remove the old floating button HTML from sidebar
html_btn_to_remove = '''      <button id="sidebar-toggle-btn" class="sidebar-toggle-btn" onclick="toggleSidebar()" title="Toggle sidebar">
        <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 18l-6-6 6-6"/>
        </svg>
      </button>'''
text = text.replace(html_btn_to_remove, '')

# 3. Add Hamburger Button to header next to Logo
header_logo = '''    <div style="display:flex; align-items:center; gap:10px">'''
hamburger_btn = '''    <div style="display:flex; align-items:center; gap:16px">
      <!-- Hamburger Toggle Button -->
      <button id="sidebar-toggle-btn" class="text-slate-500 hover:text-blue-600 transition-colors p-2 rounded-lg hover:bg-slate-100" title="Toggle Sidebar" style="background:none; border:none; cursor:pointer; display:flex; align-items:center; justify-content:center;">
        <svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16"/>
        </svg>
      </button>'''

text = text.replace(header_logo, hamburger_btn)

# 4. Remove inline toggle JS function
inline_js_to_remove = '''  window.toggleSidebar = function() {
    const sidebar = document.getElementById('main-sidebar');
    if (!sidebar) return;
    sidebar.classList.toggle('sidebar-collapsed');
    localStorage.setItem('alumniAI_sidebar_collapsed', sidebar.classList.contains('sidebar-collapsed') ? '1' : '0');
  };'''
text = text.replace(inline_js_to_remove, '')

# 5. Inject safe DOM listener into DOMContentLoaded
dom_load = "document.addEventListener('DOMContentLoaded', () => {"
new_listener = """  document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.getElementById('sidebar-toggle-btn');
    const sidebar = document.getElementById('main-sidebar');
    if (toggleBtn && sidebar) {
      toggleBtn.addEventListener('click', (e) => {
        e.preventDefault();
        sidebar.classList.toggle('sidebar-collapsed');
        localStorage.setItem('alumniAI_sidebar_collapsed', sidebar.classList.contains('sidebar-collapsed') ? '1' : '0');
      });
    }
"""
text = text.replace(dom_load, new_listener)

with open('templates/dashboard/base_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Done toggling!")
