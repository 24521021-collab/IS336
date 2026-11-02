# -*- coding: utf-8 -*-
import re
from odoo import api, models

PACK_UNITS = (
    r'lốc|thùng|combo|vỉ|túi|bịch|hộp|gói|kiện|khay|bộ|set|dây|cây|chục|tá'
)
BASE_UNITS = (
    r'hộp|lon|chai|gói|bịch|cái|chiếc|cây|ly|hũ|tuýp|cuộn|thanh|viên|miếng|'
    r'quyển|cuốn|tập|tờ|bút|lọ|bình|quả|trái|túi|vỉ|gói'
)

# Khớp các mẫu như: "Lốc 4 hộp", "Thùng 24 lon", "1 lốc = 4 hộp", "Lốc (4 hộp)"
PACK_PATTERN = re.compile(
    rf'\b(?:1\s+)?(?P<pack>{PACK_UNITS})\s*(?:=|\(\s*)?\s*(?P<qty>\d+)\s*(?P<base>{BASE_UNITS})\s*\)?\b',
    re.IGNORECASE | re.UNICODE,
)

# Khớp đơn vị đơn lẻ ở đầu tên SP (VD: "Chai trà xanh...", "Lon Coca...")
LEADING_UNIT_PATTERN = re.compile(
    rf'^\s*(?P<unit>{BASE_UNITS}|{PACK_UNITS})\b',
    re.IGNORECASE | re.UNICODE,
)

# Khớp đơn vị đi kèm định lượng trong tên SP (VD: "... hộp 180ml", "... gói 75g")
INLINE_UNIT_PATTERN = re.compile(
    rf'\b(?P<unit>{BASE_UNITS})\s+\d+(?:[.,]\d+)?\s*(?:ml|l|lít|g|gr|gram|kg|cm|mm|m|tờ|miếng|viên)\b',
    re.IGNORECASE | re.UNICODE,
)


class UoM(models.Model):
    _inherit = 'uom.uom'

    @api.model
    def _normalize_uom_label(self, label):
        clean = (label or '').strip()
        if not clean:
            return ''
        return clean[0].upper() + clean[1:].lower()

    @api.model
    def _get_or_create_base_uom(self, base_name):
        """Tìm hoặc tạo mới một đơn vị tính cơ sở (ví dụ: Hộp, Lon, Chai, Gói...)."""
        norm_name = self._normalize_uom_label(base_name)
        if not norm_name:
            return self.env.ref('uom.product_uom_unit')

        existing = self.with_context(active_test=False).search(
            [('name', '=ilike', norm_name)], limit=1
        )
        if existing:
            if not existing.active:
                existing.active = True
            return existing

        categ_name = f"Đơn vị: {norm_name}"
        UoMCategory = self.env['uom.category']
        category = UoMCategory.search([('name', '=ilike', categ_name)], limit=1)
        if not category:
            category = UoMCategory.create({'name': categ_name})

        ref_uom = self.with_context(active_test=False).search(
            [('category_id', '=', category.id), ('uom_type', '=', 'reference')],
            limit=1,
        )
        if ref_uom:
            return ref_uom

        return self.create({
            'name': norm_name,
            'category_id': category.id,
            'uom_type': 'reference',
            'factor': 1.0,
            'rounding': 0.01,
            'active': True,
        })

    @api.model
    def _get_or_create_pack_uom(self, pack_label, qty, base_label):
        """
        Tạo đơn vị đóng gói lớn hơn dựa trên đơn vị cơ sở.
        Ví dụ: pack_label='Lốc', qty=4, base_label='hộp'
        -> Đơn vị cơ sở: 'Hộp' (reference = 1)
        -> Đơn vị đóng gói: 'Lốc 4 hộp' (bigger, ratio = 4 -> 1 Lốc 4 hộp = 4 Hộp)
        """
        qty_int = int(qty)
        base_uom = self._get_or_create_base_uom(base_label)
        if qty_int <= 1 or pack_label.strip().lower() == base_label.strip().lower():
            return base_uom

        pack_norm = self._normalize_uom_label(pack_label)
        base_lower = base_label.strip().lower()
        pack_uom_name = f"{pack_norm} {qty_int} {base_lower}"

        existing = self.with_context(active_test=False).search([
            ('name', '=ilike', pack_uom_name),
            ('category_id', '=', base_uom.category_id.id),
        ], limit=1)
        if existing:
            if not existing.active:
                existing.active = True
            return existing

        base_factor_inv = base_uom.factor_inv or 1.0
        target_factor_inv = float(qty_int) * base_factor_inv

        return self.create({
            'name': pack_uom_name,
            'category_id': base_uom.category_id.id,
            'uom_type': 'bigger',
            'factor_inv': target_factor_inv,
            'rounding': 0.01,
            'active': True,
        })

    @api.model
    def _get_or_create_from_text(self, text):
        """Phân tích chuỗi đơn vị tính từ file import và tự động tạo nếu chưa có."""
        clean = (text or '').strip()
        if not clean:
            return self.env.ref('uom.product_uom_unit')

        match = PACK_PATTERN.search(clean)
        if match:
            return self._get_or_create_pack_uom(
                match.group('pack'),
                int(match.group('qty')),
                match.group('base'),
            )

        existing = self.with_context(active_test=False).search(
            [('name', '=ilike', clean)], limit=1
        )
        if existing:
            if not existing.active:
                existing.active = True
            return existing

        return self._get_or_create_base_uom(clean)

    @api.model
    def _extract_uom_from_product_name(self, product_name):
        """
        Tự động phân tích tên sản phẩm để suy ra đơn vị tính:
        1. Ưu tiên quy cách đóng gói (VD: 'Lốc 4 hộp sữa lúa mạch ít đường Milo A2 180ml' -> 1 Lốc 4 hộp = 4 Hộp).
        2. Nếu không phải quy cách gộp, kiểm tra đơn vị đơn lẻ (VD: 'Chai ...', '... hộp 180ml').
        """
        if not product_name:
            return self.browse()

        pack_match = PACK_PATTERN.search(product_name)
        if pack_match:
            pack = pack_match.group('pack')
            qty = int(pack_match.group('qty'))
            base = pack_match.group('base')
            if qty > 1 and pack.lower() != base.lower():
                return self._get_or_create_pack_uom(pack, qty, base)

        inline_match = INLINE_UNIT_PATTERN.search(product_name)
        if inline_match:
            return self._get_or_create_base_uom(inline_match.group('unit'))

        leading_match = LEADING_UNIT_PATTERN.search(product_name)
        if leading_match:
            return self._get_or_create_base_uom(leading_match.group('unit'))

        return self.browse()

    @api.model
    def name_create(self, name):
        uom = self._get_or_create_from_text(name)
        return uom.id, uom.display_name

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        res = super().name_search(name=name, args=args, operator=operator, limit=limit)
        if not res and name and name.strip():
            clean = name.strip()
            uoms = self.search([('name', '=ilike', clean)] + (args or []), limit=limit)
            if uoms:
                return [(u.id, u.display_name) for u in uoms]
            if self.env.context.get('import_file') or operator == '=':
                created = self.name_create(clean)
                return [created]
        return res

