# -*- coding: utf-8 -*-
import re
from odoo import api, models
from .uom_uom import PACK_PATTERN

# Danh sách các danh mục hệ thống mặc định của Odoo (bỏ qua khi tự động phân loại)
SYSTEM_CATEGORY_NAMES = {
    'all', 'deliveries', 'expenses', 'saleable', 'pos', 'food',
    'services', 'thực phẩm & tiêu dùng', 'all / saleable / pos',
    'all / deliveries', 'all / expenses', 'all / saleable',
}

# Các sản phẩm hệ thống của Odoo không được tự động đổi danh mục
SYSTEM_PRODUCT_NAMES = {
    'down payment (pos)', 'tips', 'standard delivery', 'giao hàng trong nước',
    'free delivery charges', 'gift card', 'ewallet', 'discount',
}

# Từ dừng (stop words) khi tách từ khóa trực tiếp từ tên Danh mục mới do người dùng tạo
CATEGORY_STOP_WORDS = {
    'và', 'các', 'những', 'từ', 'cho', 'của', 'loại', 'nhóm', 'mặt', 'hàng',
    'sản', 'phẩm', 'chế', 'đồ', 'dùng', 'thực', 'tiêu', 'hóa', 'vật', 'dụng',
}

# 5 nhóm danh mục tổng quát ban đầu (độ ưu tiên cơ bản = 1.0; các danh mục chuyên biệt mới tạo sẽ có độ ưu tiên = 1.6)
BROAD_CATEGORY_NAMES = {
    'đồ uống', 'đồ ăn nhanh', 'ăn vặt', 'hàng thiết yếu', 'đồ dùng cá nhân/học tập',
}

# Kho tri thức từ khóa liên quan (Semantic Concept Expansion)
# Khi người dùng tạo bất kỳ danh mục mới nào có tên chứa khóa chủ đề (trigger),
# hệ thống sẽ tự động kích hoạt toàn bộ bộ từ khóa liên quan bên dưới cho danh mục đó.
CONCEPT_KEYWORD_BANK = [
    {
        'triggers': ['sữa', 'chế phẩm từ sữa', 'bơ sữa', 'dairy', 'phô mai'],
        'keywords': [
            'sữa', 'sữa tươi', 'sữa chua', 'sữa đặc', 'sữa bột', 'sữa hạt', 'sữa đậu nành',
            'sữa lúa mạch', 'thức uống lúa mạch', 'phô mai', 'cheese', 'bơ thực vật',
            'whipping cream', 'kem sữa', 'váng sữa', 'áng sữa', 'men sống', 'probi',
            'yakult', 'yomost', 'vinamilk', 'th true milk', 'th milk', 'dutch lady',
            'cô gái hà lan', 'nutriboost', 'milo', 'ovaltine', 'kun', 'hilo', 'a2',
            'tiệt trùng', 'thanh trùng', 'kidsmix', 'zott', 'bega', 'con bò cười',
            'hoff', 'dalatmilk', 'lothamilk', 'fami', 'veyo', 'ensure', 'pediasure',
            'optimum', 'dielac', 'friso', 'nan', 'meiji', 'aptamil', 'nutifood',
            'ông thọ', 'ngôi sao phương nam', 'sữa tắm'  # 'sữa tắm' sẽ bị trừ điểm ở quy tắc loại trừ
        ],
        'exclude': ['sữa tắm', 'sữa rửa mặt', 'sữa dưỡng thể'],
    },
    {
        'triggers': ['đồ uống', 'thức uống', 'nước giải khát', 'nước uống', 'giải khát', 'drinks', 'beverage'],
        'keywords': [
            'thức uống', 'nước uống', 'nước ngọt', 'nước khoáng', 'nước suối', 'nước tinh khiết',
            'nước tăng lực', 'nước ép', 'nước giải khát', 'nước dừa', 'nước mía', 'nước yến',
            'trà', 'trà xanh', 'trà sữa', 'trà ô long', 'cà phê', 'cafe', 'coffee',
            'bia', 'rượu', 'pepsi', 'coca', 'sting', 'redbull', 'bò húc', 'revive',
            'aquafina', 'lavie', 'dasani', 'twister', 'c2', 'không độ', '0 độ',
            'sinh tố', 'soda', 'cacao', 'fanta', 'sprite', 'mirinda', '7up', 'dr thanh',
            'zero calo', 'monster', 'number 1', 'compact', 'warrior', 'wake up 247',
            'pocari', 'aquarius', 'schweppes', 'fuze tea', 'lipton', 'cozy', 'boncha',
            'tea+', 'nescafe', 'g7', 'vinacafe', 'maccoffee', 'highlands', 'tiger',
            'heineken', 'saigon', '333', 'larue', 'budweiser', 'huda', 'strongbow',
            # Fallback cho sữa nếu chưa có danh mục Sữa riêng (điểm thấp hơn danh mục Sữa chuyên biệt)
            'sữa', 'milo', 'ovaltine', 'lúa mạch', 'nutriboost', 'yakult', 'yomost'
        ],
        'exclude': ['nước mắm', 'nước tương', 'nước rửa', 'nước giặt', 'nước xả', 'nước lau', 'nước tẩy', 'nước súc miệng', 'nước hoa'],
    },
    {
        'triggers': ['trà', 'cà phê', 'cafe', 'coffee', 'tea'],
        'keywords': [
            'trà', 'trà xanh', 'trà đen', 'trà ô long', 'trà sữa', 'trà túi lọc', 'trà đào',
            'trà vải', 'trà chanh', 'c2', 'không độ', '0 độ', 'dr thanh', 'fuze tea',
            'boncha', 'lipton', 'cozy', 'tea+', 'cà phê', 'cafe', 'coffee', 'nescafe',
            'g7', 'vinacafe', 'wake up', 'maccoffee', 'highlands', 'the coffee house', 'cacao'
        ],
        'exclude': [],
    },
    {
        'triggers': ['bia', 'rượu', 'cồn', 'đồ uống có cồn', 'vang', 'alcohol'],
        'keywords': [
            'bia', 'rượu', 'vang', 'vodka', 'soju', 'strongbow', 'chill', 'tiger',
            'heineken', 'saigon', '333', 'larue', 'budweiser', 'huda', 'sapporo',
            'blanc 1664', 'hoegaarden', 'corona', 'chivas', 'hennessy'
        ],
        'exclude': ['bìa'],
    },
    {
        'triggers': ['đồ ăn nhanh', 'ăn nhanh', 'ăn liền', 'thực phẩm ăn liền', 'mì', 'phở', 'cháo', 'bún', 'miến', 'fast food'],
        'keywords': [
            'mì', 'miến', 'phở', 'hủ tiếu', 'bún', 'cháo', 'xúc xích', 'bánh bao', 'bánh mì',
            'sandwich', 'hamburger', 'burger', 'pizza', 'cơm cuộn', 'kimbap', 'cơm sườn', 'gà rán',
            'lẩu', 'đồ hộp', 'pate', 'cá hộp', 'thịt hộp', 'mì ly', 'mì gói', 'mì xào', 'mì trộn',
            'hảo hảo', 'omachi', 'kokomi', 'indomie', 'siukay', 'cung đình', 'đệ nhất', 'gấu đỏ',
            'ba miền', 'vifon', 'miliket', 'nhịp sống', 'bích chi', 'lẩu tự sôi', 'tokbokki', 'bánh gạo'
        ],
        'exclude': ['phô mai'],
    },
    {
        'triggers': ['ăn vặt', 'bánh kẹo', 'bánh', 'kẹo', 'snack', 'bim bim', 'đồ ăn vặt'],
        'keywords': [
            'snack', 'bimbim', 'bim bim', 'khoai tây', 'bánh quy', 'bánh ngọt', 'bánh bông lan',
            'kẹo', 'socola', 'chocolate', 'bánh tráng', 'rong biển', 'hạt điều', 'hạt dẻ',
            'hạt hướng dương', 'đậu phộng', 'khô gà', 'khô bò', 'khô mực', 'thạch', 'rau câu',
            'kem', 'bỏng ngô', 'chocopie', 'oreo', 'custas', 'bánh quế', 'bánh xốp', 'bánh gấu',
            'bánh que', 'bánh cá', 'bánh flan', 'pudding', 'ô mai', 'mứt', 'hạt sen', 'da heo',
            'chà bông', 'ruốc', 'oishi', 'lays', 'poca', 'swing', 'chupa chups', 'alpenliebe',
            'mentos', 'haribo', 'doublemint', 'xylitol', 'kitkat', 'snickers', 'cosy', 'solite',
            'afc', 'richeese', 'nabati', 'tipo', 'hura', 'danisa', 'gouté', 'pocky', 'pepero',
            'tao kae noi', 'long hải'
        ],
        'exclude': ['kem đánh răng', 'kem chống nắng', 'kem dưỡng', 'kem sữa', 'bánh mì', 'bánh bao'],
    },
    {
        'triggers': ['gia vị', 'nước chấm', 'dầu ăn', 'nấu ăn', 'chế biến'],
        'keywords': [
            'dầu ăn', 'nước mắm', 'nước tương', 'xì dầu', 'hạt nêm', 'bột ngọt', 'mì chính',
            'muối', 'đường', 'tiêu', 'ớt', 'tỏi', 'hành', 'tương ớt', 'tương cà', 'mayonnaise',
            'bột chiên', 'bột canh', 'dầu hào', 'giấm', 'sa tế', 'ngũ vị hương', 'cà ri',
            'chinsu', 'nam ngư', 'maggi', 'knorr', 'ajinomoto', 'meizan', 'neptune', 'simply',
            'tường an', 'cái lân', 'kewpie', 'cholimex', 'hưng thịnh', 'phú quốc', 'miwon', 'aji-ngon'
        ],
        'exclude': ['ít đường', 'không đường', 'có đường'],
    },
    {
        'triggers': ['gạo', 'lương thực', 'đồ khô', 'thực phẩm khô', 'ngũ cốc', 'nông sản'],
        'keywords': [
            'gạo', 'nếp', 'đậu xanh', 'đậu đen', 'đậu đỏ', 'đậu nành', 'mè', 'vừng',
            'bột mì', 'bột năng', 'bột gạo', 'bột bắp', 'nấm hương', 'mộc nhĩ',
            'bún khô', 'phở khô', 'bánh đa', 'nui', 'mì ý', 'spaghetti', 'yến mạch', 'ngũ cốc', 'st25'
        ],
        'exclude': [],
    },
    {
        'triggers': ['giặt', 'tẩy rửa', 'vệ sinh nhà cửa', 'hóa phẩm', 'chăm sóc nhà cửa', 'khăn giấy', 'giấy vệ sinh'],
        'keywords': [
            'giấy vệ sinh', 'khăn giấy', 'khăn ướt', 'nước rửa chén', 'nước giặt', 'bột giặt',
            'viên giặt', 'nước xả', 'nước lau sàn', 'nước lau kính', 'nước tẩy', 'tẩy bồn cầu',
            'túi rác', 'bao rác', 'màng bọc', 'giấy bạc', 'xịt phòng', 'sáp thơm', 'xịt côn trùng',
            'nhang muỗi', 'sunlight', 'omo', 'ariel', 'tide', 'surf', 'attack', 'lix', 'maxkleen',
            'comfort', 'downy', 'hygiene', 'vim', 'gift', 'myhao', 'mỹ hảo', 'pulppy', 'bless you',
            'watersilk', 'tempo', 'bobby', 'an an', 'raid', 'jumbo vape', 'glade'
        ],
        'exclude': [],
    },
    {
        'triggers': ['hàng thiết yếu', 'nhu yếu phẩm', 'thiết yếu', 'tạp hóa'],
        'keywords': [
            'gạo', 'dầu ăn', 'nước mắm', 'nước tương', 'hạt nêm', 'bột ngọt', 'muối', 'đường',
            'tiêu', 'ớt', 'tỏi', 'hành', 'trứng', 'tương ớt', 'tương cà', 'mayonnaise', 'bột chiên',
            'giấy vệ sinh', 'khăn giấy', 'khăn ướt', 'nước rửa chén', 'nước giặt', 'bột giặt',
            'nước xả', 'nước lau sàn', 'nước tẩy', 'băng vệ sinh', 'túi rác', 'màng bọc',
            'bật lửa', 'nến', 'pin', 'chinsu', 'nam ngư', 'maggi', 'knorr', 'ajinomoto',
            'meizan', 'neptune', 'simply', 'comfort', 'downy', 'omo', 'ariel', 'sunlight',
            'vim', 'dạ lan', 'bobby', 'pulppy', 'bless you'
        ],
        'exclude': ['ít đường', 'không đường', 'có đường'],
    },
    {
        'triggers': ['chăm sóc cá nhân', 'mỹ phẩm', 'vệ sinh cá nhân', 'làm đẹp', 'cá nhân'],
        'keywords': [
            'dầu gội', 'dầu xả', 'sữa tắm', 'xà bông', 'xà phòng', 'kem đánh răng', 'bàn chải',
            'nước súc miệng', 'chỉ nha khoa', 'khăn mặt', 'khăn tắm', 'dao cạo', 'bọt cạo râu',
            'sữa rửa mặt', 'nước tẩy trang', 'bông tẩy trang', 'kem chống nắng', 'kem dưỡng',
            'lăn khử mùi', 'xịt khử mùi', 'nước hoa', 'son', 'khẩu trang', 'bông ngoáy tai',
            'tăm bông', 'băng vệ sinh', 'băng cá nhân', 'dầu gió', 'dép', 'bấm móng tay',
            'clear', 'pantene', 'head & shoulders', 'sunsilk', 'dove', 'tresemme', 'rejoice',
            'romano', 'x-men', 'lifebuoy', 'lux', 'hazeline', 'colgate', 'p/s', 'ps',
            'sensodyne', 'closeup', 'listerine', 'oral-b', 'sunplay', 'biore', 'nivea',
            'vaseline', 'pond', 'simple', 'cetaphil', 'garnier', 'diana', 'kotex', 'laurier', 'gillette'
        ],
        'exclude': [],
    },
    {
        'triggers': ['học tập', 'văn phòng phẩm', 'dụng cụ học tập', 'sách vở', 'trường học'],
        'keywords': [
            'bút', 'viết', 'vở', 'tập', 'sổ', 'thước', 'tẩy', 'gôm', 'bút chì', 'bút bi',
            'bút dạ', 'bút lông', 'bút xóa', 'bút nhớ', 'highlight', 'kéo', 'dao rọc giấy',
            'keo', 'hồ dán', 'bìa', 'giấy in', 'giấy a4', 'giấy note', 'văn phòng phẩm',
            'băng keo', 'băng dính', 'bấm kim', 'kim bấm', 'kẹp giấy', 'compa', 'hộp bút',
            'balo', 'cặp sách', 'màu vẽ', 'sáp màu', 'thiên long', 'campus', 'hồng hà', 'deli', 'pentel'
        ],
        'exclude': ['nước tẩy', 'tẩy trang', 'tẩy bồn cầu'],
    },
    {
        'triggers': ['rau', 'củ', 'quả', 'trái cây', 'tươi sống', 'thịt', 'cá', 'hải sản'],
        'keywords': [
            'rau', 'cải', 'xà lách', 'cà chua', 'dưa leo', 'khoai lang', 'cà rốt', 'bí đỏ',
            'trái cây', 'táo', 'cam', 'nho', 'chuối', 'xoài', 'dưa hấu', 'ổi', 'bưởi',
            'thịt heo', 'thịt bò', 'thịt gà', 'ba rọi', 'sườn', 'cá tươi', 'tôm tươi', 'mực tươi'
        ],
        'exclude': ['hương cam', 'hương dâu', 'hương dứa', 'hương việt quất', 'hương dưa gang', 'hương chanh', 'vị dâu', 'vị cam', 'vị tôm', 'vị bò', 'vị gà', 'khô gà', 'khô bò', 'khô mực'],
    },
    {
        'triggers': ['đông lạnh', 'mát', 'thực phẩm đông lạnh'],
        'keywords': [
            'đông lạnh', 'há cảo', 'xíu mại', 'chả giò', 'chả cá', 'cá viên', 'bò viên',
            'tôm viên', 'mandi', 'mandu', 'bánh xếp', 'gà vòng', 'nuggets', 'khoai tây cọng'
        ],
        'exclude': [],
    },
]


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

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get('skip_auto_reclassify'):
            self.env['product.template'].with_context(skip_auto_reclassify=True)._auto_reclassify_all_products()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals and not self.env.context.get('skip_auto_reclassify'):
            self.env['product.template'].with_context(skip_auto_reclassify=True)._auto_reclassify_all_products()
        return res


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _build_dynamic_category_profiles(self):
        """
        Quét toàn bộ danh mục (product.category) hiện có trong DB và tự động sinh bộ từ khóa
        dựa trên:
        1) Các từ khóa tách trực tiếp từ tên danh mục mới.
        2) Kho từ khóa mở rộng liên quan (CONCEPT_KEYWORD_BANK).
        """
        all_cats = self.env['product.category'].search([])
        profiles = []

        for cat in all_cats:
            cat_name = (cat.name or '').strip()
            cat_lower = cat_name.lower()
            complete_lower = (cat.complete_name or cat_name).lower()

            if not cat_lower or cat_lower in SYSTEM_CATEGORY_NAMES or complete_lower in SYSTEM_CATEGORY_NAMES:
                continue

            # Hệ số ưu tiên: Danh mục chuyên biệt do người dùng thêm mới (VD: "Sữa & Chế phẩm từ sữa")
            # được ưu tiên cao hơn (1.6x) so với 5 danh mục tổng quát ban đầu (1.0x)
            specificity = 1.0 if cat_lower in BROAD_CATEGORY_NAMES else 1.6

            # 1. Tách các từ khóa trực tiếp từ tên Danh mục
            clean_cat = re.sub(r'[&/,\-()]+', ' ', cat_lower)
            cat_words = [w.strip() for w in clean_cat.split() if w.strip() and w.strip() not in CATEGORY_STOP_WORDS and len(w.strip()) > 1]

            direct_keywords = set(cat_words)
            # Thêm cụm từ có nghĩa trong tên danh mục (tách theo dấu & / , -)
            sub_phrases = [p.strip() for p in re.split(r'[&/,\-]| và | từ | các ', cat_lower) if p.strip()]
            for phrase in sub_phrases:
                if phrase not in CATEGORY_STOP_WORDS and len(phrase) > 1:
                    direct_keywords.add(phrase)

            # 2. Mở rộng từ khóa liên quan từ Kho tri thức (CONCEPT_KEYWORD_BANK)
            expanded_keywords = set(direct_keywords)
            excluded_phrases = set()

            for concept in CONCEPT_KEYWORD_BANK:
                matched_concept = False
                for trig in concept['triggers']:
                    trig_low = trig.lower()
                    if trig_low in cat_lower or any(w == trig_low for w in cat_words):
                        matched_concept = True
                        break
                if matched_concept:
                    expanded_keywords.update(concept['keywords'])
                    excluded_phrases.update(concept.get('exclude', []))

            profiles.append({
                'category': cat,
                'name_lower': cat_lower,
                'specificity': specificity,
                'direct_keywords': direct_keywords,
                'keywords': expanded_keywords,
                'exclude': excluded_phrases,
            })

        return profiles

    @api.model
    def _extract_category_from_product_name(self, product_name, profiles=None):
        """Phân tích tên sản phẩm và trả về record product.category phù hợp nhất hiện có trong DB."""
        if not product_name:
            return self.env['product.category'].browse()

        p_trim = product_name.strip()
        if p_trim.lower() in SYSTEM_PRODUCT_NAMES:
            return self.env['product.category'].browse()

        if profiles is None:
            profiles = self._build_dynamic_category_profiles()

        name_clean = p_trim.lower().replace('trong nước', 'nội địa')
        # Chuẩn hóa dấu câu thành khoảng trắng để so khớp từ chính xác
        for ch in '(),;-/=+':
            name_clean = name_clean.replace(ch, ' ')
        name_padded = f" {' '.join(name_clean.split())} "

        best_cat = self.env['product.category'].browse()
        max_score = 0.0

        for prof in profiles:
            # Kiểm tra từ khóa loại trừ (VD: "sữa tắm" không thuộc danh mục "Sữa & Chế phẩm từ sữa")
            if any(ex in name_padded for ex in prof['exclude']):
                continue

            raw_score = 0.0
            # Điểm cộng cao khi tên SP chứa trực tiếp từ khóa nằm trong tên Danh mục (VD: "sữa", "phô mai")
            for dkw in prof['direct_keywords']:
                dkw_pad = f" {dkw} "
                if dkw_pad in name_padded:
                    raw_score += len(dkw.split()) * 4.0

            # Điểm cộng cho bộ từ khóa liên quan mở rộng
            for kw in prof['keywords']:
                kw_low = kw.lower()
                kw_pad = f" {kw_low} "
                if kw_pad in name_padded:
                    raw_score += len(kw_low.split()) * 2.0
                elif len(kw_low) >= 4 and kw_low in name_padded:
                    raw_score += len(kw_low.split()) * 1.0

            final_score = raw_score * prof['specificity']
            if final_score > max_score:
                max_score = final_score
                best_cat = prof['category']

        return best_cat if max_score > 0 else self.env['product.category'].browse()

    @api.model
    def _auto_reclassify_all_products(self):
        """Quét và phân loại lại toàn bộ sản phẩm đang hoạt động khi có danh mục mới được thêm/cập nhật."""
        products = self.search([('active', '=', True)])
        if products:
            products.action_auto_set_uom_from_name(force_reclassify_category=True)
        return True

    @api.model_create_multi
    def create(self, vals_list):
        UoM = self.env['uom.uom']
        default_uom = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        default_uom_id = default_uom.id if default_uom else False

        default_cat = self.env.ref('product.product_category_all', raise_if_not_found=False)
        default_cat_id = default_cat.id if default_cat else False
        profiles = self._build_dynamic_category_profiles()

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
                    detected_cat = self._extract_category_from_product_name(name, profiles=profiles)
                    if detected_cat:
                        vals['categ_id'] = detected_cat.id

            # Đảm bảo uom_po_id luôn cùng nhóm với uom_id
            if vals.get('uom_id'):
                uom_rec = UoM.browse(vals['uom_id'])
                po_uom_id = vals.get('uom_po_id')
                if not po_uom_id or UoM.browse(po_uom_id).category_id != uom_rec.category_id:
                    vals['uom_po_id'] = uom_rec.id

        return super().create(vals_list)

    def action_auto_set_uom_from_name(self, force_reclassify_category=True):
        """Action quét và tự động gán lại Đơn vị tính & Danh mục cho các sản phẩm đã có sẵn."""
        UoM = self.env['uom.uom']
        default_cat = self.env.ref('product.product_category_all', raise_if_not_found=False)
        default_cat_id = default_cat.id if default_cat else False
        profiles = self._build_dynamic_category_profiles()

        for template in self:
            name = (template.name or '').strip()
            if not name or name.lower() in SYSTEM_PRODUCT_NAMES:
                continue

            vals_to_write = {}

            # Cập nhật UoM
            detected_uom = UoM._extract_uom_from_product_name(name)
            if detected_uom and (template.uom_id != detected_uom or template.uom_po_id != detected_uom):
                vals_to_write['uom_id'] = detected_uom.id
                vals_to_write['uom_po_id'] = detected_uom.id

            # Cập nhật Category theo bộ danh mục động mới nhất
            detected_cat = self._extract_category_from_product_name(name, profiles=profiles)
            if detected_cat and template.categ_id != detected_cat:
                if force_reclassify_category or not template.categ_id or template.categ_id.id == default_cat_id or template.categ_id.name == 'All':
                    vals_to_write['categ_id'] = detected_cat.id

            if vals_to_write:
                template.write(vals_to_write)

        return True
