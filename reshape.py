import re
import os

with open('templates/dashboard/base_dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

def get_block(start_regex, end_regex):
    match = re.search(start_regex + r'.*?' + end_regex, text, re.DOTALL)
    if not match: raise ValueError("Could not find block: " + start_regex)
    return match.group(0)

# Pull sections
js_block = get_block(r'{% block extra_js %}', r'{% endblock %}')

# Bell
bell_start = r'<!-- Notification Bell -->'
bell_end = r'<!-- Panel footer -->\s*<div.*?>\s*<a.*?>.*?</a>\s*</div>\s*</div>\s*</div>'
bell_html = get_block(bell_start, bell_end)

# Avatar
avatar_start = r'<!-- Avatar button -->'
avatar_end = r'<!-- /dropdown -->\s*</div>'
avatar_html = get_block(avatar_start, avatar_end)

# User card
card_match = re.search(r'<!-- User card \+ Logout -->\s*<div class="mt-auto pt-4 border-t border-slate-100">(.*?)\s*</aside>', text, re.DOTALL)
user_card_html = card_match.group(1).rsplit('</div>\n  </aside>', 1)[0] # clean up

css = """
{% block extra_css %}
<style>
/* ── Main header ── */
#main-header {
  position: sticky; top: 0; z-index: 50; height: 60px; background: white;
  border-bottom: 1px solid #E2E8F0; display: flex; align-items: center; justify-content: space-between;
  padding: 0 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); box-sizing: border-box;
}

/* ── Below-header layout container ── */
.page-body {
  display: flex; height: calc(100vh - 60px); overflow: hidden;
}

/* ── Sidebar ── */
.dashboard-sidebar {
  width: 240px; min-width: 240px; background: white; border-right: 1px solid #E2E8F0;
  height: 100%; display: flex; flex-direction: column; overflow-y: auto; overflow-x: hidden;
  position: relative; flex-shrink: 0; transition: width 220ms ease, min-width 220ms ease;
}
.dashboard-sidebar.sidebar-collapsed {
  width: 64px; min-width: 64px;
}

/* ── Main content ── */
.page-main {
  flex: 1; min-width: 0; overflow-y: auto; background: #F8FAFC;
}

/* ── Sidebar toggle button ── */
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
}

/* ── Sidebar nav links ── */
.sidebar-link {
  display: flex; align-items: center; gap: 10px; padding: 10px 14px;
  border-radius: 8px; text-decoration: none; color: #64748B; font-size: 14px;
  font-weight: 500; transition: all 0.15s; margin-bottom: 2px;
  border-left: 3px solid transparent; box-sizing: border-box; width: 100%;
}
.sidebar-link:hover {
  background: #F1F5F9; color: #0F172A;
}
.sidebar-active {
  background: #EFF6FF !important; color: #2563EB !important;
  font-weight: 600; border-left-color: #2563EB;
}

.soon-badge {
  margin-left: auto; font-size: 0.65rem; color: #94a3b8;
  background: #f1f5f9; padding: 1px 6px; border-radius: 9999px;
}

/* ── Hide labels when collapsed ── */
.dashboard-sidebar.sidebar-collapsed .logo-text,
.dashboard-sidebar.sidebar-collapsed .soon-badge,
.dashboard-sidebar.sidebar-collapsed .user-info-text,
.dashboard-sidebar.sidebar-collapsed .role-badge-container {
  display: none !important;
}
.dashboard-sidebar.sidebar-collapsed .sidebar-link {
  justify-content: center !important; padding-left: 0 !important; padding-right: 0 !important; font-size: 0;
}
.dashboard-sidebar.sidebar-collapsed #logout-btn {
  font-size: 0; justify-content: center; padding-left: 0; padding-right: 0;
}
.dashboard-sidebar.sidebar-collapsed .user-profile-container {
  justify-content: center; padding: 0; margin-bottom: 0.5rem;
}

/* Custom tooltips for collapsed state */
.dashboard-sidebar.sidebar-collapsed .sidebar-link::after {
  content: attr(data-tooltip); position: absolute; left: 100%; margin-left: 14px;
  background: #1e293b; color: #fff; padding: 5px 10px; border-radius: 6px; font-size: 0.75rem;
  font-weight: 500; white-space: nowrap; opacity: 0; pointer-events: none; transition: opacity 0.2s; z-index: 50; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
}
.dashboard-sidebar.sidebar-collapsed .sidebar-link:hover::after {
  opacity: 1;
}
.dashboard-sidebar.sidebar-collapsed .sidebar-link::before {
  content: ''; position: absolute; left: 100%; margin-left: 6px; border-width: 4px;
  border-style: solid; border-color: transparent #1e293b transparent transparent; opacity: 0; pointer-events: none; transition: opacity 0.2s; z-index: 50;
}
.dashboard-sidebar.sidebar-collapsed .sidebar-link:hover::before {
  opacity: 1;
}
</style>
{% endblock %}
"""

body = f"""
{{% block body %}}
  <!-- ══ TOP HEADER BAR ══ -->
  <header id="main-header">
    <div style="display:flex; align-items:center; gap:10px">
      <a href="/" style="display:flex; align-items:center; gap:8px; text-decoration:none; cursor:pointer" class="hover:opacity-80 transition-opacity">
        <svg class="w-[30px] h-[30px] text-blue-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path d="M12 3L1 9l11 6 9-4.91V17M1 9v8" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M5 12.5v5a7 7 0 0014 0v-5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span style="font-size:18px; font-weight:700; color:#2563EB; letter-spacing:-0.3px">AlumniAI</span>
      </a>
    </div>

    <!-- RIGHT: Notification bell + User avatar dropdown -->
    <div style="display:flex; align-items:center; gap:12px">
      {bell_html}
      {avatar_html}
    </div>
  </header>

  <!-- ══ BELOW HEADER: SIDEBAR + MAIN CONTENT ══ -->
  <div class="page-body">

    <!-- LEFT: Sidebar -->
    <aside class="dashboard-sidebar hidden lg:flex" id="main-sidebar">
      <button id="sidebar-toggle-btn" class="sidebar-toggle-btn" onclick="toggleSidebar()" title="Toggle sidebar">
        <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 18l-6-6 6-6"/>
        </svg>
      </button>

      <nav style="padding:12px 8px; flex:1">
        {{% block sidebar_links %}}
          {{% include 'partials/sidebar.html' %}}
        {{% endblock %}}
      </nav>

      <div class="sidebar-user-card" style="padding:12px 14px; border-top:1px solid #E2E8F0; display:flex; flex-direction:column; gap:0.5rem">
        {user_card_html}
      </div>
    </aside>

    <!-- RIGHT: Main content area -->
    <main class="page-main p-5 lg:p-6" style="padding:20px 24px">
      {{% block dashboard_content %}}{{% endblock %}}
    </main>

  </div>
{{% endblock %}}
"""

# Fix JS block classes to match user spec
js_block = js_block.replace("'collapsed'", "'sidebar-collapsed'")
js_block = js_block.replace(".classList.toggle(\"collapsed\")", ".classList.toggle(\"sidebar-collapsed\")")
js_block = js_block.replace(".classList.add(\"collapsed\")", ".classList.add(\"sidebar-collapsed\")")
js_block = js_block.replace(".classList.contains(\"collapsed\")", ".classList.contains(\"sidebar-collapsed\")")
js_block = js_block.replace("'sidebarCollapsed'", "'alumniAI_sidebar_collapsed'")
js_block = js_block.replace("localStorage.setItem('alumniAI_sidebar_collapsed', 'true')", "localStorage.setItem('alumniAI_sidebar_collapsed', '1')")
js_block = js_block.replace("localStorage.setItem('alumniAI_sidebar_collapsed', sidebar.classList.contains('sidebar-collapsed'))", "localStorage.setItem('alumniAI_sidebar_collapsed', sidebar.classList.contains('sidebar-collapsed') ? '1' : '0')")
js_block = js_block.replace("localStorage.getItem('alumniAI_sidebar_collapsed') === 'true'", "localStorage.getItem('alumniAI_sidebar_collapsed') === '1'")

# Provide the global toggleSidebar that was requested inside extra_js script body:
toggle_js = """
  window.toggleSidebar = function() {
    const sidebar = document.getElementById('main-sidebar');
    if (!sidebar) return;
    sidebar.classList.toggle('sidebar-collapsed');
    localStorage.setItem('alumniAI_sidebar_collapsed', sidebar.classList.contains('sidebar-collapsed') ? '1' : '0');
  };
"""
js_block = js_block.replace("<script>", "<script>\\n" + toggle_js)

full = "{% extends 'base.html' %}\n{% load static %}\n\n" + css + "\n\n" + body + "\n\n" + js_block + "\n"

with open('templates/dashboard/base_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(full)

print("done")
