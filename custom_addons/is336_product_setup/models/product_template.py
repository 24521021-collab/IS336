# -*- coding: utf-8 -*-
import re
import unicodedata
from odoo import api, models
from .uom_uom import PACK_PATTERN

# Danh sách các danh mục hệ thống mặc định của Odoo (bỏ qua khi tự động phân loại)
SYSTEM_CATEGORY_NAMES = {
    'all', 'deliveries', 'expenses', 'saleable', 'pos', 'food',
    'services', 'thực phẩm & tiêu dùng', 'all / saleable / pos',
    'all / deliveries', 'all / expenses', 'all / saleable',
    'all / saleable / pos / food',
}

# Các sản phẩm hệ thống của Odoo không được tự động đổi danh mục
SYSTEM_PRODUCT_NAMES = {
    'down payment (pos)', 'tips', 'standard delivery', 'giao hàng trong nước',
    'free delivery charges', 'gift card', 'ewallet', 'discount',
}

# Từ dừng khi tách từ đơn từ tên Danh mục (chặn tách từ ghép 'cá nhân' -> 'cá', 'nhân')
CATEGORY_STOP_WORDS = {
    'và', 'các', 'những', 'từ', 'cho', 'của', 'loại', 'nhóm', 'mặt', 'hàng',
    'sản', 'phẩm', 'chế', 'đồ', 'dùng', 'thực', 'tiêu', 'hóa', 'vật', 'dụng',
    'cá', 'nhân', 'học', 'tập', 'ăn', 'uống', 'nhanh', 'vặt', 'thiết', 'yếu',
}

# 5 nhóm danh mục tổng quát ban đầu (độ ưu tiên cơ bản = 1.0; danh mục chuyên biệt = 1.6)
BROAD_CATEGORY_NAMES = {
    'đồ uống', 'đồ ăn nhanh', 'ăn vặt', 'hàng thiết yếu', 'đồ dùng cá nhân/học tập',
}

# Kho tri thức từ khóa liên quan (Semantic Concept Expansion)
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
            'ông thọ', 'ngôi sao phương nam'
        ],
        'exclude': ['sữa tắm', 'sữa rửa mặt', 'sữa dưỡng thể'],
    },
    {
        'triggers': ['đồ uống', 'thức uống', 'nước giải khát', 'nước uống', 'giải khát', 'drinks', 'beverage'],
        'keywords': [
            'thức uống', 'nước uống', 'nước ngọt', 'nước khoáng', 'nước suối', 'nước tinh khiết',
            'nước tăng lực', 'nước ép', 'nước giải khát', 'nước dừa', 'nước mía', 'nước yến',
            'nước hồng sâm', 'tổ yến chưng', 'nước cốt', 'trà', 'trà xanh', 'trà sữa', 'trà ô long',
            'cà phê', 'cà phê hòa tan', 'cafe', 'café', 'coffee', 'bia', 'rượu',
            'pepsi', 'coca', 'sting', 'redbull', 'bò húc', 'revive', 'aquafina', 'lavie', 'dasani',
            'twister', 'c2', 'không độ', '0 độ', 'sinh tố', 'soda', 'cacao', 'fanta', 'sprite',
            'mirinda', '7up', 'dr thanh', 'zero calo', 'monster', 'number 1', 'compact', 'warrior',
            'wake up 247', 'pocari', 'aquarius', 'schweppes', 'fuze tea', 'lipton', 'cozy', 'boncha',
            'tea+', 'nescafe', 'nescafé', 'g7', 'vinacafe', 'vinacafé', 'maccoffee', 'highlands',
            'tiger', 'heineken', 'saigon', '333', 'larue', 'budweiser', 'huda', 'strongbow',
            'sữa', 'milo', 'ovaltine', 'lúa mạch', 'nutriboost', 'yakult', 'yomost'
        ],
        'exclude': [
            'nước mắm', 'nước tương', 'nước rửa', 'nước giặt', 'nước xả', 'nước lau',
            'nước tẩy', 'nước súc miệng', 'nước hoa', 'kẹo ngậm', 'kẹo dẻo', 'kẹo cứng',
            'bánh quy', 'bánh bông lan'
        ],
    },
    {
        'triggers': ['trà', 'cà phê', 'cafe', 'café', 'coffee', 'tea'],
        'keywords': [
            'trà', 'trà xanh', 'trà đen', 'trà ô long', 'trà sữa', 'trà túi lọc', 'trà đào',
            'trà vải', 'trà chanh', 'c2', 'không độ', '0 độ', 'dr thanh', 'fuze tea',
            'boncha', 'lipton', 'cozy', 'tea+', 'cà phê', 'cà phê hòa tan', 'cafe', 'café',
            'coffee', 'nescafe', 'nescafé', 'g7', 'vinacafe', 'vinacafé', 'wake up', 'maccoffee',
            'highlands', 'the coffee house', 'cacao'
        ],
        'exclude': ['kẹo ngậm', 'kẹo'],
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
            'mì', 'miến', 'phở', 'hủ tiếu', 'bún', 'cháo', 'cháo tươi', 'cháo tổ yến', 'xúc xích',
            'bánh bao', 'bánh mì', 'sandwich', 'hamburger', 'burger', 'pizza', 'cơm cuộn', 'kimbap',
            'cơm sườn', 'gà rán', 'lẩu', 'đồ hộp', 'pate', 'cá hộp', 'thịt hộp', 'mì ly', 'mì gói',
            'mì xào', 'mì trộn', 'mì bò', 'mì tôm', 'mì gà', 'mì chay', 'hảo hảo', 'omachi', 'kokomi',
            'indomie', 'siukay', 'cung đình', 'đệ nhất', 'gấu đỏ', '3 miền', 'ba miền', 'unif',
            'vifon', 'miliket', 'nhịp sống', 'bích chi', 'lẩu tự sôi', 'tokbokki', 'bánh gạo', 'koreno', 'ottogi'
        ],
        'exclude': ['phô mai'],
    },
    {
        'triggers': ['ăn vặt', 'bánh kẹo', 'bánh', 'kẹo', 'snack', 'bim bim', 'đồ ăn vặt'],
        'keywords': [
            'snack', 'bimbim', 'bim bim', 'khoai tây', 'bánh quy', 'bánh ngọt', 'bánh bông lan',
            'bánh sô cô la', 'bánh socola', 'kẹo', 'kẹo ngậm', 'kẹo dẻo', 'kẹo mút', 'kẹo cao su',
            'socola', 'sô cô la', 'chocolate', 'bánh tráng', 'rong biển', 'hạt điều', 'hạt dẻ',
            'hạt hướng dương', 'hạnh nhân', 'óc chó', 'mắc ca', 'hạt bí', 'đậu phộng',
            'xoài sấy', 'mít sấy', 'chuối sấy', 'khoai lang sấy', 'trái cây sấy', 'sấy dẻo', 'sấy giòn',
            'khô gà', 'khô bò', 'khô mực', 'thạch', 'rau câu', 'kem', 'bỏng ngô', 'chocopie',
            'oreo', 'custas', 'bánh quế', 'bánh xốp', 'bánh gấu', 'bánh que', 'bánh cá',
            'bánh flan', 'pudding', 'ô mai', 'mứt', 'hạt sen', 'da heo', 'chà bông', 'ruốc',
            'oishi', 'lays', 'lay stax', 'stax', 'pringles', 'slide', 'poca', 'swing',
            'chupa chups', 'alpenliebe', 'mentos', 'haribo', 'doublemint', 'xylitol', 'pure fresh',
            'kitkat', 'snickers', 'cosy', 'solite', 'afc', 'richeese', 'nabati', 'tipo', 'hura',
            'danisa', 'gouté', 'pocky', 'pepero', 'tao kae noi', 'long hải', 'tuấn đạt'
        ],
        'exclude': ['kem đánh răng', 'kem chống nắng', 'kem dưỡng', 'kem sữa', 'bánh mì', 'bánh bao', 'mì khoai tây'],
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
            'bún khô', 'phở khô', 'bánh đa', 'nui', 'mì ý', 'spaghetti', 'yến mạch',
            'ngũ cốc', 'hạt chia', 'st25', 'xuân an', 'quaker'
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
            'gạo', 'ngũ cốc', 'yến mạch', 'hạt chia', 'dầu ăn', 'nước mắm', 'nước tương',
            'hạt nêm', 'bột ngọt', 'muối', 'đường', 'tiêu', 'ớt', 'tỏi', 'hành', 'trứng',
            'tương ớt', 'tương cà', 'mayonnaise', 'bột chiên', 'giấy vệ sinh', 'khăn giấy',
            'khăn ướt', 'nước rửa chén', 'nước giặt', 'bột giặt', 'nước xả', 'nước lau sàn',
            'nước tẩy', 'băng vệ sinh', 'túi rác', 'màng bọc', 'bật lửa', 'nến', 'pin',
            'chinsu', 'nam ngư', 'maggi', 'knorr', 'ajinomoto', 'meizan', 'neptune', 'simply',
            'comfort', 'downy', 'omo', 'ariel', 'sunlight', 'vim', 'dạ lan', 'bobby', 'pulppy',
            'bless you', 'xuân an'
        ],
        'exclude': ['ít đường', 'không đường', 'có đường'],
    },
    {
        'triggers': ['chăm sóc cá nhân', 'đồ dùng cá nhân', 'mỹ phẩm', 'vệ sinh cá nhân', 'làm đẹp'],
        'keywords': [
            'dầu gội', 'dầu xả', 'sữa tắm', 'xà bông', 'xà phòng', 'kem đánh răng', 'bàn chải',
            'nước súc miệng', 'chỉ nha khoa', 'khăn mặt', 'khăn tắm', 'dao cạo', 'bọt cạo râu',
            'sữa rửa mặt', 'nước tẩy trang', 'bông tẩy trang', 'kem chống nắng', 'kem dưỡng',
            'lăn khử mùi', 'xịt khử mùi', 'nước hoa', 'son môi', 'khẩu trang', 'bông ngoáy tai',
            'tăm bông', 'băng vệ sinh', 'băng cá nhân', 'dầu gió', 'dép', 'bấm móng tay',
            'clear', 'pantene', 'head & shoulders', 'sunsilk', 'dove', 'tresemme', 'rejoice',
            'romano', 'x-men', 'lifebuoy', 'lux', 'hazeline', 'colgate', 'p/s', 'sensodyne',
            'closeup', 'listerine', 'oral-b', 'sunplay', 'biore', 'nivea', 'vaseline', 'pond',
            'cetaphil', 'garnier', 'diana', 'kotex', 'laurier', 'gillette'
        ],
        'exclude': [],
    },
    {
        'triggers': ['học tập', 'văn phòng phẩm', 'dụng cụ học tập', 'sách vở', 'trường học'],
        'keywords': [
            'bút', 'viết', 'vở', 'tập học sinh', 'tập vở', 'sổ tay', 'thước kẻ', 'thước',
            'tẩy chì', 'gôm tẩy', 'gôm', 'bút chì', 'bút bi', 'bút dạ', 'bút lông', 'bút xóa',
            'bút nhớ', 'highlight', 'kéo văn phòng', 'dao rọc giấy', 'keo dán', 'hồ dán',
            'bìa hồ sơ', 'giấy in', 'giấy a4', 'giấy note', 'văn phòng phẩm', 'băng keo',
            'băng dính', 'bấm kim', 'kim bấm', 'kẹp giấy', 'compa', 'hộp bút', 'balo',
            'cặp sách', 'màu vẽ', 'sáp màu', 'thiên long', 'campus', 'hồng hà', 'deli', 'pentel'
        ],
        'exclude': ['nước tẩy', 'tẩy trang', 'tẩy bồn cầu'],
    },
    {
        'triggers': ['rau củ', 'trái cây', 'tươi sống', 'thịt tươi', 'cá tươi', 'hải sản'],
        'keywords': [
            'rau củ', 'cải ngọt', 'cải xanh', 'xà lách', 'cà chua', 'dưa leo', 'khoai lang',
            'cà rốt', 'bí đỏ', 'trái cây tươi', 'táo tươi', 'cam sành', 'nho tươi', 'chuối tươi',
            'xoài tươi', 'dưa hấu', 'thịt heo', 'thịt bò', 'thịt gà', 'ba rọi', 'sườn heo',
            'cá tươi', 'tôm tươi', 'mực tươi'
        ],
        'exclude': [
            'hương cam', 'hương dâu', 'hương dứa', 'hương việt quất', 'hương dưa gang',
            'hương chanh', 'vị dâu', 'vị cam', 'vị tôm', 'vị bò', 'vị gà', 'khô gà',
            'khô bò', 'khô mực', 'xoài sấy', 'mít sấy', 'chuối sấy', 'sấy dẻo', 'rau thơm'
        ],
    },
    {
        'triggers': ['đông lạnh', 'thực phẩm đông lạnh'],
        'keywords': [
            'đông lạnh', 'há cảo', 'xíu mại', 'chả giò', 'chả cá', 'cá viên', 'bò viên',
            'tôm viên', 'mandi', 'mandu', 'bánh xếp', 'gà vòng', 'nuggets', 'khoai tây cọng'
        ],
        'exclude': [],
    },
]

# Từ điển các thương hiệu phổ biến trong ngành FMCG / Bán lẻ Việt Nam
BRAND_CODE_MAP = [
    ('hao hao', 'HAOHAO'), ('3 mien', '3MIEN'), ('ba mien', '3MIEN'),
    ('omachi', 'OMACHI'), ('kokomi', 'KOKOMI'), ('cung dinh', 'CUNGDINH'),
    ('miliket', 'MILIKET'), ('vifon', 'VIFON'), ('a-one', 'AONE'),
    ('gau do', 'GAUDO'), ('gau cay', 'GAUCAY'), ('nissin', 'NISSIN'),
    ('indomie', 'INDOMIE'), ('koreno', 'KORENO'), ('ottogi', 'OTTOGI'),
    ('de nhat', 'DENHAT'), ('ohya', 'OHYA'), ('tieu nhi', 'TIEUNHI'),
    ('unif', 'UNIF'), ('vi huong', 'VIHUONG'), ('xuxifarm', 'XUXIFARM'),
    ('siu bep', 'SIUBEP'), ('lc foods', 'LCFOODS'), ('th true milk', 'TH'),
    ('th milk', 'TH'), ('dutch lady', 'DUTCH'), ('nutimilk', 'NUTIMILK'),
    ('probi', 'PROBI'), ('yomost', 'YOMOST'), ('vinamilk', 'VNM'),
    ('ovaltine', 'OVALTINE'), ('milo', 'MILO'), ('kun', 'KUN'),
    ('bega', 'BEGA'), ('zott', 'ZOTT'), ('kidsmix', 'KIDSMIX'),
    ('avonmore', 'AVONMORE'), ('coca cola', 'COCA'), ('coca', 'COCA'),
    ('pepsi', 'PEPSI'), ('mirinda', 'MIRINDA'), ('sprite', 'SPRITE'),
    ('warrior', 'WARRIOR'), ('red bull', 'REDBULL'), ('redbull', 'REDBULL'),
    ('pocari', 'POCARI'), ('aquarius', 'AQUARIUS'), ('aquafina', 'AQUAFINA'),
    ('rockstar', 'ROCKSTAR'), ('fuzetea', 'FUZETEA'), ('c2', 'C2'),
    ('tea+', 'TEA+'), ('vinacafe', 'VINACAFE'), ('nescafe', 'NESCAFE'),
    ('kitkat', 'KITKAT'), ('lay stax', 'STAX'), ('lays', 'LAYS'),
    ('slide', 'SLIDE'), ('pringles', 'PRINGLES'), ('gingerbon', 'GINGERBON'),
    ('mentos', 'MENTOS'), ('bento', 'BENTO'), ('zaizai', 'ZAIZAI'),
    ('vfood', 'VFOOD'), ('tuan dat', 'TUANDAT'), ('xuan an', 'XUANAN'),
    ('viet dai', 'VIETDAI'), ('yen viet', 'YENVIET'), ('bfast', 'BFAST'),
    ('chinsu', 'CHINSU'), ('nam ngu', 'NAMNGU'), ('knorr', 'KNORR'),
    ('omo', 'OMO'), ('ariel', 'ARIEL'), ('sunlight', 'SUNLIGHT'),
    ('comfort', 'COMFORT'), ('downy', 'DOWNY'), ('clear', 'CLEAR'),
    ('lifebuoy', 'LIFEBUOY'), ('colgate', 'COLGATE'), ('thien long', 'THIENLONG'),
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


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _remove_diacritics(self, text):
        """Chuyển chuỗi tiếng Việt có dấu thành không dấu chữ hoa, hỗ trợ tạo SKU."""
        if not text:
            return ""
        norm = unicodedata.normalize('NFD', text)
        clean = ''.join(c for c in norm if unicodedata.category(c) != 'Mn')
        return clean.replace('đ', 'd').replace('Đ', 'D').replace('–', '-').replace('—', '-')

    @api.model
    def _generate_short_default_code(self, name, category_name='', current_code=''):
        """
        Tự động tạo mã Tham chiếu nội bộ (default_code / SKU) ngắn gọn chuẩn Bán lẻ (Cách 2):
        Cấu trúc: [Nhóm]-[Thương hiệu/Tên]-[Quy cách/Trọng lượng] (dưới 15 ký tự).
        Chỉ can thiệp khi:
          - Chưa có mã tham chiếu (rỗng)
          - Hoặc mã quá dài (> 20 ký tự) do crawler web cào nguyên URL slug.
        Nếu người dùng đã chủ động đặt mã ngắn gọn (<= 20 ký tự): giữ nguyên 100%.
        """
        cur = (current_code or '').strip()
        # Nếu đã có mã ngắn và không phải mã rác cào từ web, giữ nguyên
        if cur and len(cur) <= 20 and not cur.startswith(('WEB-', 'BHX-')) and not cur.startswith('Delivery_'):
            return cur

        if not name:
            return cur

        n_clean = self._remove_diacritics(name).lower()
        cat_lower = (category_name or '').lower()

        # 1. Tiền tố phân nhóm (Prefix: 2-3 ký tự)
        pfx = "SP"
        if 'đồ ăn nhanh' in cat_lower or 'thực phẩm ăn liền' in cat_lower:
            if 'mi ' in n_clean or n_clean.startswith('mi'):
                pfx = "MI"
            elif 'xuc xich' in n_clean:
                pfx = "XX"
            else:
                pfx = "AN"
        elif 'ăn vặt' in cat_lower or 'bánh kẹo' in cat_lower:
            if 'snack' in n_clean or 'khoai tay' in n_clean:
                pfx = "SNK"
            elif 'banh' in n_clean:
                pfx = "BNH"
            elif 'keo' in n_clean:
                pfx = "KEO"
            elif 'thach' in n_clean:
                pfx = "TCH"
            else:
                pfx = "AV"
        elif 'sữa' in cat_lower:
            if 'sua chua' in n_clean:
                pfx = "SCU"
            elif 'pho mai' in n_clean:
                pfx = "PM"
            else:
                pfx = "SUA"
        elif 'đồ uống' in cat_lower:
            if 'tra ' in n_clean or n_clean.startswith('tra'):
                pfx = "TRA"
            elif 'cafe' in n_clean or 'ca phe' in n_clean:
                pfx = "CF"
            elif 'tang luc' in n_clean:
                pfx = "TL"
            elif 'khoang' in n_clean or 'tinh khiet' in n_clean:
                pfx = "NK"
            else:
                pfx = "DU"
        elif 'hàng thiết yếu' in cat_lower or 'thiết yếu' in cat_lower:
            if 'ngu coc' in n_clean:
                pfx = "NGC"
            elif 'yen' in n_clean:
                pfx = "YEN"
            else:
                pfx = "TY"
        elif 'học tập' in cat_lower or 'cá nhân' in cat_lower:
            if any(w in n_clean for w in ('but', 'vo', 'tap', 'so', 'thuoc', 'tay', 'gom')):
                pfx = "VPP"
            else:
                pfx = "CSCN"

        # 2. Định danh Thương hiệu / Tên chính (Brand: 3-8 ký tự)
        brand = ""
        for kw, code in BRAND_CODE_MAP:
            if kw in n_clean:
                brand = code
                break

        if not brand:
            # Lấy từ có nghĩa đầu tiên trong tên SP
            clean_words = re.sub(r'[(),;/=+\-]', ' ', n_clean).split()
            meaningful = [
                w for w in clean_words
                if len(w) > 1 and w not in ('loc', 'thung', 'chai', 'hop', 'goi', 'lon', 'vi', 'combo', 'huong', 'nuoc', 'banh', 'sua', 'mi')
            ]
            brand = meaningful[0].upper() if meaningful else "GEN"

        # 3. Định lượng / Quy cách đóng gói (Spec)
        spec = ""
        # Ưu tiên kiểm tra quy cách đóng gói (VD: lốc 4 hộp -> L4, thùng 24 chai -> T24, gói 12 thanh -> G12)
        m_pack = re.search(r'(?i)(thung\s*\d+\s*chai|loc\s*\d+\s*(?:chai|hop|lon|goi)|goi\s*\d+\s*thanh|vi\s*\d+\s*hop)', n_clean)
        if m_pack:
            raw_p = m_pack.group(1).lower()
            raw_p = re.sub(r'thung\s*', 'T', raw_p)
            raw_p = re.sub(r'loc\s*', 'L', raw_p)
            raw_p = re.sub(r'vi\s*', 'V', raw_p)
            raw_p = re.sub(r'goi\s*', 'G', raw_p)
            spec = re.sub(r'\s*(?:chai|hop|lon|goi|thanh)', '', raw_p).upper()
        else:
            # Kiểm tra trọng lượng / thể tích (VD: 160g -> 160G, 1.5l -> 1.5L)
            m_weight = re.search(r'(?i)(\d+(?:\.\d+)?\s*(?:ml|lit|l|gr|gram|g|kg))', n_clean)
            if m_weight:
                w_str = m_weight.group(1).upper().replace(' ', '')
                w_str = w_str.replace('LIT', 'L').replace('GRAM', 'G').replace('GR', 'G')
                spec = w_str

        candidate = f"{pfx}-{brand}-{spec}" if spec else f"{pfx}-{brand}"

        # Đảm bảo mã không bị trùng với sản phẩm khác đã có trong hệ thống
        existing = self.search([('default_code', '=like', f"{candidate}%"), ('name', '!=', name)])
        if existing:
            used_codes = set(existing.mapped('default_code'))
            if candidate in used_codes:
                suffix = 2
                while f"{candidate}-{suffix}" in used_codes:
                    suffix += 1
                candidate = f"{candidate}-{suffix}"

        return candidate

    @api.model
    def _build_dynamic_category_profiles(self):
        """
        Quét toàn bộ danh mục (product.category) hiện có trong DB và tự động sinh bộ từ khóa.
        Sử dụng so khớp ranh giới từ (word boundary) để tránh tách sai từ ghép như 'cá nhân' -> 'cá', 'nhân'.
        """
        all_cats = self.env['product.category'].search([])
        profiles = []

        for cat in all_cats:
            cat_name = (cat.name or '').strip()
            cat_lower = cat_name.lower()
            complete_lower = (cat.complete_name or cat_name).lower()

            if not cat_lower or cat_lower in SYSTEM_CATEGORY_NAMES or complete_lower in SYSTEM_CATEGORY_NAMES:
                continue

            specificity = 1.0 if cat_lower in BROAD_CATEGORY_NAMES else 1.6

            clean_cat = re.sub(r'[&/,\-()]+', ' ', cat_lower)
            clean_cat_padded = f" {' '.join(clean_cat.split())} "
            cat_words = [
                w.strip() for w in clean_cat.split()
                if w.strip() and w.strip() not in CATEGORY_STOP_WORDS and len(w.strip()) > 1
            ]

            direct_keywords = set(cat_words)
            sub_phrases = [p.strip() for p in re.split(r'[&/,\-]| và | từ | các ', cat_lower) if p.strip()]
            for phrase in sub_phrases:
                if phrase not in CATEGORY_STOP_WORDS and len(phrase) > 1:
                    direct_keywords.add(phrase)

            expanded_keywords = set(direct_keywords)
            excluded_phrases = set()

            for concept in CONCEPT_KEYWORD_BANK:
                matched_concept = False
                for trig in concept['triggers']:
                    trig_low = trig.lower().strip()
                    if f" {trig_low} " in clean_cat_padded or trig_low == cat_lower:
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
        for ch in '(),;-/=+':
            name_clean = name_clean.replace(ch, ' ')
        name_clean = ' '.join(name_clean.split())
        name_padded = f" {name_clean} "

        # Trích xuất danh từ đứng đầu câu để ưu tiên
        clean_tokens = [t for t in name_clean.split() if t]
        idx = 0
        while idx < len(clean_tokens):
            if clean_tokens[idx] in ('loc', 'thung', 'combo', 'vi', 'tui', 'bich', 'hop', 'goi', 'lon', 'chai') or clean_tokens[idx].isdigit() or clean_tokens[idx] == 'x':
                idx += 1
            else:
                break
        head_tokens = clean_tokens[idx:idx + 3] if idx < len(clean_tokens) else clean_tokens[:3]
        head_padded = f" {' '.join(head_tokens)} "

        best_cat = self.env['product.category'].browse()
        max_score = 0.0

        for prof in profiles:
            if any(f" {ex} " in name_padded or ex in name_padded for ex in prof['exclude']):
                continue

            raw_score = 0.0
            for dkw in prof['direct_keywords']:
                dkw_pad = f" {dkw} "
                if dkw_pad in name_padded:
                    raw_score += len(dkw.split()) * 4.0
                    if head_padded.startswith(dkw_pad) or dkw_pad in head_padded:
                        raw_score += 6.0

            for kw in prof['keywords']:
                kw_low = kw.lower().strip()
                kw_pad = f" {kw_low} "
                if kw_pad in name_padded:
                    raw_score += len(kw_low.split()) * 2.0
                    if head_padded.startswith(kw_pad) or kw_pad in head_padded:
                        raw_score += 6.0

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
            current_code = (vals.get('default_code') or '').strip()

            detected_cat = None
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

                # 2. Tự động nhận diện Danh mục sản phẩm (Category) - chỉ khi chưa chọn danh mục riêng
                if not current_cat_id or current_cat_id == default_cat_id:
                    detected_cat = self._extract_category_from_product_name(name, profiles=profiles)
                    if detected_cat:
                        vals['categ_id'] = detected_cat.id

                # 3. Tự động rút gọn Mã Tham chiếu nội bộ (default_code) nếu chưa có hoặc quá dài (>20 ký tự từ crawler)
                cat_name = detected_cat.name if detected_cat else (self.env['product.category'].browse(current_cat_id).name if current_cat_id else '')
                if not current_code or len(current_code) > 20 or current_code.startswith(('WEB-', 'BHX-')):
                    vals['default_code'] = self._generate_short_default_code(name, cat_name, current_code)

            # Đảm bảo uom_po_id luôn cùng nhóm với uom_id
            if vals.get('uom_id'):
                uom_rec = UoM.browse(vals['uom_id'])
                po_uom_id = vals.get('uom_po_id')
                if not po_uom_id or UoM.browse(po_uom_id).category_id != uom_rec.category_id:
                    vals['uom_po_id'] = uom_rec.id

        return super().create(vals_list)

    def action_auto_set_uom_from_name(self, force_reclassify_category=True):
        """Action quét và tự động gán lại Đơn vị tính, Danh mục và rút gọn Mã Tham chiếu cho các sản phẩm đã có sẵn."""
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

            # Rút gọn default_code nếu quá dài
            cur_code = (template.default_code or '').strip()
            if not cur_code or len(cur_code) > 20 or cur_code.startswith(('WEB-', 'BHX-')):
                cat_n = detected_cat.name if detected_cat else (template.categ_id.name if template.categ_id else '')
                short_code = self._generate_short_default_code(name, cat_n, cur_code)
                if short_code and short_code != cur_code:
                    vals_to_write['default_code'] = short_code

            if vals_to_write:
                template.write(vals_to_write)

        return True
