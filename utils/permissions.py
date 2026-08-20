"""
Permission matrix cho Admin.
Roles:
  - user          : người dùng thường
  - content_admin : bài viết, FAQ
  - nutrition_admin: món ăn, nguyên liệu, thực đơn, import
  - ai_admin      : chatbot, RAG, AI monitor
  - admin         : full (tương thích cũ)
  - super_admin   : full + quản lý admin + system
"""

# Tất cả permission keys
ALL_PERMISSIONS = [
    'manage_users',
    'manage_foods',
    'manage_ingredients',
    'manage_menus',
    'manage_articles',
    'manage_chatbot',
    'manage_rag',
    'manage_ai',
    'view_statistics',
    'manage_system',
    'manage_admins',
    'view_audit',
    'manage_backups',
]

ROLE_PERMISSIONS = {
    'user': [],
    'content_admin': [
        'manage_articles',
        'view_statistics',
    ],
    'nutrition_admin': [
        'manage_foods',
        'manage_ingredients',
        'manage_menus',
        'view_statistics',
    ],
    'ai_admin': [
        'manage_chatbot',
        'manage_rag',
        'manage_ai',
        'view_statistics',
    ],
    'admin': list(ALL_PERMISSIONS),  # full (legacy)
    'super_admin': list(ALL_PERMISSIONS),
}

# Role được coi là "admin-level" (truy cập panel)
ADMIN_ROLES = {'admin', 'super_admin', 'content_admin', 'nutrition_admin', 'ai_admin'}


def is_admin_role(role):
    return (role or '') in ADMIN_ROLES


def get_permissions(role):
    return list(ROLE_PERMISSIONS.get(role or 'user', []))


def has_permission(role, permission):
    if not permission:
        return is_admin_role(role)
    return permission in get_permissions(role)
