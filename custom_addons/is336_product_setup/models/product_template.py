# -*- coding: utf-8 -*-
from odoo import api, models
from .uom_uom import PACK_PATTERN


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

    @api.model_create_multi
    def create(self, vals_list):
        UoM = self.env['uom.uom']
        default_uom = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        default_uom_id = default_uom.id if default_uom else False

        for vals in vals_list:
            name = (vals.get('name') or '').strip()
            current_uom_id = vals.get('uom_id')

            if name:
                # 1. Nếu tên SP chứa quy cách đóng gói (VD: "Lốc 4 hộp..."), luôn ưu tiên gán UoM quy cách đó
                if PACK_PATTERN.search(name):
                    detected_uom = UoM._extract_uom_from_product_name(name)
                    if detected_uom:
                        vals['uom_id'] = detected_uom.id
                        vals['uom_po_id'] = detected_uom.id
                # 2. Nếu chưa chỉ định UoM (hoặc đang là Units mặc định), tự suy đơn vị lẻ từ tên SP
                elif not current_uom_id or current_uom_id == default_uom_id:
                    detected_uom = UoM._extract_uom_from_product_name(name)
                    if detected_uom:
                        vals['uom_id'] = detected_uom.id
                        vals['uom_po_id'] = detected_uom.id

            # Đảm bảo uom_po_id luôn cùng nhóm (category_id) với uom_id để tránh lỗi ràng buộc của Odoo
            if vals.get('uom_id'):
                uom_rec = UoM.browse(vals['uom_id'])
                po_uom_id = vals.get('uom_po_id')
                if not po_uom_id or UoM.browse(po_uom_id).category_id != uom_rec.category_id:
                    vals['uom_po_id'] = uom_rec.id

        return super().create(vals_list)

    def action_auto_set_uom_from_name(self):
        """Action cho phép quét và tự động gán lại Đơn vị tính cho các sản phẩm đã có sẵn."""
        UoM = self.env['uom.uom']
        for template in self:
            detected_uom = UoM._extract_uom_from_product_name(template.name)
            if detected_uom and template.uom_id != detected_uom:
                template.write({
                    'uom_id': detected_uom.id,
                    'uom_po_id': detected_uom.id,
                })
        return True

