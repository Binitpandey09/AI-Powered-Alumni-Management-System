with open('templates/dashboard/base_dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Replace old CSS tooltip block with sidebar-label and JS tooltip styles
old_css = (
    "/* Custom tooltips for collapsed state */\n"
    ".dashboard-sidebar.sidebar-collapsed .sidebar-link::after {"
)
new_css = (
    "/* Sidebar label — hidden when collapsed */\n"
    ".dashboard-sidebar.sidebar-collapsed .sidebar-label {\n"
    "  display: none !important;\n"
    "}\n\n"
    "/* JS tooltip (appended to body, never clipped by overflow) */\n"
    "#sidebar-js-tooltip {\n"
    "  position: fixed; z-index: 99999;\n"
    "  background: #1e293b; color: #fff;\n"
    "  padding: 5px 12px; border-radius: 6px;\n"
    "  font-size: 0.75rem; font-weight: 500;\n"
    "  white-space: nowrap; pointer-events: none;\n"
    "  box-shadow: 0 4px 12px rgba(0,0,0,0.18);\n"
    "  opacity: 0; transition: opacity 0.15s;\n"
    "}\n"
    "#sidebar-js-tooltip.visible { opacity: 1; }\n"
    "/* OLD CSS ::after removed — was clipped by overflow-y:auto */\n"
    "/* placeholder-end */"
)

# Find and remove everything from the ::after block to ::before closing
import re
pattern = r'/\* Custom tooltips for collapsed state \*/.*?\.dashboard-sidebar\.sidebar-collapsed \.sidebar-link:hover::before \{[^}]+\}'
text = re.sub(pattern, new_css, text, flags=re.DOTALL)

# 2. Replace JS tooltip extraction block with hover-based body tooltip
old_js_snippet = "// Auto-collapse on nav link click + tooltip extraction"
new_js = """    // Sidebar link: hover tooltip + collapse on click
    if (sidebar) {
      let tip = document.getElementById('sidebar-js-tooltip');
      if (!tip) {
        tip = document.createElement('div');
        tip.id = 'sidebar-js-tooltip';
        document.body.appendChild(tip);
      }

      sidebar.querySelectorAll('.sidebar-link').forEach(link => {
        link.addEventListener('mouseenter', () => {
          if (!sidebar.classList.contains('sidebar-collapsed')) return;
          const label = link.getAttribute('data-tooltip');
          if (!label) return;
          tip.textContent = label;
          const rect = link.getBoundingClientRect();
          tip.style.top = (rect.top + rect.height / 2) + 'px';
          tip.style.left = (rect.right + 12) + 'px';
          tip.style.transform = 'translateY(-50%)';
          tip.classList.add('visible');
        });
        link.addEventListener('mouseleave', () => tip.classList.remove('visible'));

        link.addEventListener('click', () => {
          tip.classList.remove('visible');
          if (window.innerWidth >= 1024) {
            sidebar.classList.add('sidebar-collapsed');
            localStorage.setItem('alumniAI_sidebar_collapsed', '1');
            if (iconOpen)  iconOpen.classList.add('hidden');
            if (iconClose) iconClose.classList.remove('hidden');
          }
        });
      });
    }"""

# Find the old block and replace to end of the if(sidebar){...}
old_pattern = r'// Auto-collapse on nav link click \+ tooltip extraction\s*if \(sidebar\) \{.*?\}\s*\}'
text = re.sub(old_pattern, new_js, text, flags=re.DOTALL)

with open('templates/dashboard/base_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Done! Lines:", text.count('\n'))
