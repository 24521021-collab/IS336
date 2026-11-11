# -*- coding: utf-8 -*-
{
    'name': 'IS336 - Thiết lập Danh mục & Tự động Đơn vị tính (Auto UoM)',
    'version': '18.0.1.2.0',
    'category': 'Inventory/Inventory',
    'summary': 'Tự động nhận diện Đơn vị tính & Danh mục sản phẩm động (tự mở rộng từ khóa liên quan khi thêm Danh mục mới)',
    'depends': ['product', 'uom', 'base_automation'],
    'data': [
        'data/product_category_data.xml',
        'data/server_action_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

