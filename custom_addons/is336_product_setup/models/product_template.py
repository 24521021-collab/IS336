# -*- coding: utf-8 -*-
from odoo import api, models
from .uom_uom import PACK_PATTERN

CATEGORY_KEYWORDS = {
    'Đồ uống': [
        'sữa', 'thức uống', 'nước uống', 'nước ngọt', 'nước khoáng', 'nước suối', 'nước tinh khiết',
        'nước tăng lực', 'nước ép', 'nước giải khát', 'nước dừa', 'nước mía', 'nước yến', 'trà',
        'cà phê', 'cafe', 'bia', 'rượu', 'pepsi', 'coca', 'sting', 'redbull', 'bò húc', 'revive',
        'aquafina', 'lavie', 'dasani', 'nutriboost', 'milo', 'ovaltine', 'lúa mạch', 'th true milk',
        'vinamilk', 'dutch lady', 'kun', 'yakult', 'yomost', 'twister', 'c2', 'không độ', '0 độ',
        'sinh tố', 'soda', 'trà sữa', 'cacao', 'fanta', 'sprite', 'mirinda', '7up', 'dr thanh',
        'zero calo', 'hilo', 'a2', 'tiệt trùng', 'thanh trùng'
    ],
    'Đồ ăn nhanh': [
        'mì', 'miến', 'phở', 'hủ tiếu', 'bún', 'cháo', 'xúc xích', 'bánh bao', 'bánh mì',
        'sandwich', 'hamburger', 'burger', 'pizza', 'cơm cuộn', 'kimbap', 'cơm sườn', 'gà rán',
        'lẩu', 'đồ hộp', 'pate', 'cá hộp', 'thịt hộp', 'mì ly', 'mì gói', 'mì xào',
        'hảo hảo', 'omachi', 'kokomi', 'indomie', 'siukay', 'cung đình', 'lẩu tự sôi'
    ],
    'Ăn vặt': [
        'snack', 'bimbim', 'bim bim', 'khoai tây', 'bánh quy', 'bánh ngọt', 'kẹo', 'socola',
        'chocolate', 'bánh tráng', 'rong biển', 'hạt điều', 'hạt dẻ', 'hạt hướng dương',
        'đậu phộng', 'khô gà', 'khô bò', 'khô mực', 'thạch', 'kem', 'bỏng ngô', 'chocopie',
        'oreo', 'custas', 'bánh quế', 'bánh xốp', 'bánh gấu', 'bánh que', 'bánh cá',
        'bánh flan', 'pudding', 'ô mai', 'mứt', 'hạt sen', 'da heo', 'chà bông', 'ruốc'
    ],
    'Hàng thiết yếu': [
        'gạo', 'dầu ăn', 'nước mắm', 'nước tương', 'hạt nêm', 'bột ngọt', 'muối', 'đường',
        'tiêu', 'ớt', 'tỏi', 'hành', 'trứng', 'tương ớt', 'tương cà', 'mayonnaise', 'bột chiên',
        'giấy vệ sinh', 'khăn giấy', 'nước rửa chén', 'nước giặt', 'bột giặt', 'nước xả',
        'nước lau sàn', 'nước tẩy', 'băng vệ sinh', 'túi rác', 'màng bọc', 'bật lửa', 'nến',
        'pin', 'chinsu', 'nam ngư', 'maggi', 'knorr', 'ajinomoto', 'meizan', 'neptune',
        'simply', 'comfort', 'downy', 'omo', 'ariel', 'sunlight', 'vim', 'dạ lan'
    ],
    'Đồ dùng cá nhân/học tập': [
        'bút', 'viết', 'vở', 'tập', 'sổ', 'thước', 'tẩy', 'gôm', 'bút chì', 'bút bi',
        'bút dạ', 'bút lông', 'kéo', 'dao rọc giấy', 'keo', 'hồ dán', 'bìa', 'giấy in',
        'dầu gội', 'dầu xả', 'sữa tắm', 'xà bông', 'xà phòng', 'kem đánh răng', 'bàn chải',
        'khăn mặt', 'khăn tắm', 'dao cạo', 'bọt cạo râu', 'sữa rửa mặt', 'kem chống nắng',
        'khẩu trang', 'bông ngoáy tai', 'tăm bông', 'dép', 'văn phòng phẩm', 'băng keo',
        'bấm kim', 'kim bấm', 'compa', 'hộp bút', 'balo', 'cặp sách', 'clear', 'pantene',
        'head & shoulders', 'lifebuoy', 'colgate', 'ps', 'sensodyne', 'sunplay', 'biore'
    ]
}


class ProductCategory(models.Model):
    _inherit = 'product.category'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        res = super().name_search(name=name, args=args, operator=operator, limit=limit)
        if not res and name and name.strip():
            clean = name.strip()
            leaf_name = clean.split('/')[-1].strip() if '/' in clean else clean
            cats = self.search(
                ['|', ('name', '=ilike', clean), ('name', '=ilike', leaf_name)] + (args or []),
                limit=limit,
            )
            if cats:
                return [(c.id, c.display_name) for c in cats]
            if self.env.context.get('import_file') or operator == '=':
                created = self.name_create(leaf_name)
                return [created]
        return res


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _extract_category_from_product_name(self, product_name):
        """Phân tích tên sản phẩm và trả về record product.category tương ứng (hoặc rỗng)."""
        if not product_name:
            return self.env['product.category'].browse()

        name_clean = product_name.lower().replace('trong nước', 'nội địa')
        name_lower = f" {name_clean} "
        best_cat_name = None
        max_score = 0

        for cat_name, keywords in CATEGORY_KEYWORDS.items():
            score = 0
            for kw in keywords:
                kw_padded = f" {kw.lower()} "
                if kw_padded in name_lower:
                    score += len(kw.split()) * 2
                elif kw.lower() in name_lower:
                    score += len(kw.split())

            if score > max_score:
                max_score = score
                best_cat_name = cat_name

        if best_cat_name and max_score > 0:
            cat = self.env['product.category'].search([('name', '=', best_cat_name)], limit=1)
            if not cat:
                cat = self.env['product.category'].create({'name': best_cat_name})
            return cat

        return self.env['product.category'].browse()

    @api.model_create_multi
    def create(self, vals_list):
        UoM = self.env['uom.uom']
        default_uom = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        default_uom_id = default_uom.id if default_uom else False

        default_cat = self.env.ref('product.product_category_all', raise_if_not_found=False)
        default_cat_id = default_cat.id if default_cat else False

        for vals in vals_list:
            name = (vals.get('name') or '').strip()
            current_uom_id = vals.get('uom_id')
            current_cat_id = vals.get('categ_id')

            if name:
                # 1. Tự động nhận diện Đơn vị tính (UoM)
                if PACK_PATTERN.search(name):
                    detected_uom = UoM._extract_uom_from_product_name(name)
                    if detected_uom:
                        vals['uom_id'] = detected_uom.id
                        vals['uom_po_id'] = detected_uom.id
                elif not current_uom_id or current_uom_id == default_uom_id:
                    detected_uom = UoM._extract_uom_from_product_name(name)
                    if detected_uom:
                        vals['uom_id'] = detected_uom.id
                        vals['uom_po_id'] = detected_uom.id

                # 2. Tự động nhận diện Danh mục sản phẩm (Category)
                if not current_cat_id or current_cat_id == default_cat_id:
                    detected_cat = self._extract_category_from_product_name(name)
                    if detected_cat:
                        vals['categ_id'] = detected_cat.id

            # Đảm bảo uom_po_id luôn cùng nhóm với uom_id
            if vals.get('uom_id'):
                uom_rec = UoM.browse(vals['uom_id'])
                po_uom_id = vals.get('uom_po_id')
                if not po_uom_id or UoM.browse(po_uom_id).category_id != uom_rec.category_id:
                    vals['uom_po_id'] = uom_rec.id

        return super().create(vals_list)

    def action_auto_set_uom_from_name(self):
        """Action quét và tự động gán lại Đơn vị tính & Danh mục cho các sản phẩm đã có sẵn."""
        UoM = self.env['uom.uom']
        default_cat = self.env.ref('product.product_category_all', raise_if_not_found=False)
        default_cat_id = default_cat.id if default_cat else False

        for template in self:
            vals_to_write = {}

            # Cập nhật UoM
            detected_uom = UoM._extract_uom_from_product_name(template.name)
            if detected_uom and (template.uom_id != detected_uom or template.uom_po_id != detected_uom):
                vals_to_write['uom_id'] = detected_uom.id
                vals_to_write['uom_po_id'] = detected_uom.id

            # Cập nhật Category nếu đang là mặc định (All) hoặc chưa đúng
            detected_cat = self._extract_category_from_product_name(template.name)
            if detected_cat and (not template.categ_id or template.categ_id.id == default_cat_id or template.categ_id.name == 'All'):
                vals_to_write['categ_id'] = detected_cat.id

            if vals_to_write:
                template.write(vals_to_write)

        return True
