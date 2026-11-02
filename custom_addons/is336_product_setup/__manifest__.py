# -*- coding: utf-8 -*-
{
    'name': 'IS336 - Thiết lập Danh mục & Tự động Đơn vị tính (Auto UoM)',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Thiết lập 5 nhóm sản phẩm chính và tự động tạo/gán đơn vị tính từ file import crawler & tên sản phẩm',
    'depends': ['product', 'uom'],
    'data': [
        'data/product_category_data.xml',
        'data/server_action_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

