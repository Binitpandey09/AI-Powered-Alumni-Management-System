import sys, re

def check_html(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    errors = []
    if '{% block extra_js %}' in content and '{{ block.super }}' not in content:
        errors.append('Missing {{ block.super }} in extra_js')
    if '{% block extra_css %}' in content and '{{ block.super }}' not in content:
        errors.append('Missing {{ block.super }} in extra_css')
        
    tags = re.findall(r'<[a-zA-Z0-9]+([^>]+)>', content)
    for t in tags:
        attrs = re.findall(r'([a-zA-Z\-]+)=', t)
        if len(attrs) != len(set(attrs)):
            errors.append(f'Duplicate attributes in tag: {t}')
            
    # Check invalid style inline
    if 'truncate;' in content:
        errors.append('truncate; in style attribute')
        
    print(f"{path}:\n  {errors}")

check_html(r'D:\AI powered Alumni system\templates\feed\feed.html')
check_html(r'D:\AI powered Alumni system\templates\referrals\referral_board.html')
check_html(r'D:\AI powered Alumni system\templates\sessions_app\session_detail.html')
