"""
初始化数据脚本
运行方式: python manage.py shell < init_data.py
或者: python manage.py runscript init_data (需要 django-extensions)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import User
from books.models import Category, Book, BookCopy

# 创建管理员账户
admin_user, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'email': 'admin@example.com',
        'role': 'admin',
        'is_staff': True,
        'is_superuser': True,
        'is_active': True,
        'email_verified': True,
    }
)
if created:
    admin_user.set_password('admin123')
    admin_user.save()
    print('创建管理员账户: admin / admin123')
else:
    print('管理员账户已存在')

# 创建测试用户
test_user, created = User.objects.get_or_create(
    username='testuser',
    defaults={
        'email': 'test@example.com',
        'role': 'user',
        'is_active': True,
        'email_verified': True,
    }
)
if created:
    test_user.set_password('test123')
    test_user.save()
    print('创建测试用户: testuser / test123')
else:
    print('测试用户已存在')

# 创建图书分类
categories_data = [
    ('计算机', '计算机科学与技术相关书籍'),
    ('文学', '小说、散文、诗歌等文学作品'),
    ('历史', '历史类书籍'),
    ('科学', '自然科学相关书籍'),
    ('经济', '经济学与管理学书籍'),
    ('哲学', '哲学与思想类书籍'),
    ('心理学', '心理学与自我成长类书籍'),
    ('艺术', '艺术与设计类书籍'),
]

for name, desc in categories_data:
    cat, created = Category.objects.get_or_create(name=name, defaults={'description': desc})
    if created:
        print(f'创建分类: {name}')

# 创建示例图书
books_data = [
    # 计算机类
    {
        'isbn': '978-7-111-42039-5',
        'title': 'Python编程：从入门到实践',
        'author': 'Eric Matthes',
        'publisher': '机械工业出版社',
        'category': '计算机',
        'description': '本书是一本针对所有层次的Python读者而作的Python入门书，全面介绍Python语言基础和实际项目开发。',
        'total_copies': 5,
    },
    {
        'isbn': '978-7-115-42839-5',
        'title': 'JavaScript高级程序设计',
        'author': 'Nicholas C. Zakas',
        'publisher': '人民邮电出版社',
        'category': '计算机',
        'description': '本书是JavaScript超级畅销书的最新版，深入讲解JavaScript核心概念与高级特性。',
        'total_copies': 3,
    },
    {
        'isbn': '978-7-111-40701-3',
        'title': '深入理解计算机系统',
        'author': 'Randal E. Bryant',
        'publisher': '机械工业出版社',
        'category': '计算机',
        'description': '从程序员视角全面剖析计算机系统，被誉为计算机科学的经典教材。',
        'total_copies': 4,
    },
    {
        'isbn': '978-7-115-29Mo0-0',
        'title': '算法导论',
        'author': 'Thomas H. Cormen',
        'publisher': '机械工业出版社',
        'category': '计算机',
        'description': '全面介绍算法设计与分析的经典教材，涵盖排序、图算法、动态规划等核心内容。',
        'total_copies': 3,
    },
    {
        'isbn': '978-7-115-38332-2',
        'title': 'Django Web开发实战',
        'author': '黄永祥',
        'publisher': '人民邮电出版社',
        'category': '计算机',
        'description': '全面讲解Django框架开发Web应用的实战指南，适合Python Web开发者。',
        'total_copies': 4,
    },
    {
        'isbn': '978-7-111-58315-6',
        'title': '机器学习实战',
        'author': 'Peter Harrington',
        'publisher': '人民邮电出版社',
        'category': '计算机',
        'description': '通过精心编排的实例，介绍机器学习的核心算法，适合入门学习者。',
        'total_copies': 5,
    },
    # 文学类
    {
        'isbn': '978-7-020-00220-4',
        'title': '红楼梦',
        'author': '曹雪芹',
        'publisher': '人民文学出版社',
        'category': '文学',
        'description': '中国古典四大名著之一，描写贾、史、王、薛四大家族的兴衰史。',
        'total_copies': 10,
    },
    {
        'isbn': '978-7-020-00221-1',
        'title': '三国演义',
        'author': '罗贯中',
        'publisher': '人民文学出版社',
        'category': '文学',
        'description': '中国古典四大名著之一，描写东汉末年群雄割据的历史小说。',
        'total_copies': 8,
    },
    {
        'isbn': '978-7-020-00222-8',
        'title': '水浒传',
        'author': '施耐庵',
        'publisher': '人民文学出版社',
        'category': '文学',
        'description': '中国古典四大名著之一，讲述梁山好汉的传奇故事。',
        'total_copies': 6,
    },
    {
        'isbn': '978-7-020-00223-5',
        'title': '西游记',
        'author': '吴承恩',
        'publisher': '人民文学出版社',
        'category': '文学',
        'description': '中国古典四大名著之一，描写唐僧师徒西天取经的神话故事。',
        'total_copies': 7,
    },
    {
        'isbn': '978-7-544-27889-4',
        'title': '百年孤独',
        'author': '加西亚·马尔克斯',
        'publisher': '南海出版公司',
        'category': '文学',
        'description': '魔幻现实主义文学的代表作，讲述布恩迪亚家族七代人的传奇故事。',
        'total_copies': 5,
    },
    {
        'isbn': '978-7-020-12345-6',
        'title': '活着',
        'author': '余华',
        'publisher': '作家出版社',
        'category': '文学',
        'description': '讲述福贵一生的悲欢离合，展现中国人在苦难中的坚韧与生命力。',
        'total_copies': 8,
    },
    {
        'isbn': '978-7-530-21234-5',
        'title': '围城',
        'author': '钱钟书',
        'publisher': '人民文学出版社',
        'category': '文学',
        'description': '中国现代文学经典，以幽默讽刺的笔调描写知识分子的生活百态。',
        'total_copies': 6,
    },
    # 历史类
    {
        'isbn': '978-7-101-00384-3',
        'title': '史记',
        'author': '司马迁',
        'publisher': '中华书局',
        'category': '历史',
        'description': '中国历史上第一部纪传体通史，记载从黄帝到汉武帝三千年历史。',
        'total_copies': 4,
    },
    {
        'isbn': '978-7-101-08234-2',
        'title': '资治通鉴',
        'author': '司马光',
        'publisher': '中华书局',
        'category': '历史',
        'description': '中国第一部编年体通史，记载从周威烈王到后周世宗1362年历史。',
        'total_copies': 3,
    },
    {
        'isbn': '978-7-108-03821-5',
        'title': '万历十五年',
        'author': '黄仁宇',
        'publisher': '生活·读书·新知三联书店',
        'category': '历史',
        'description': '以1587年为切入点，剖析明朝社会政治结构的深层问题。',
        'total_copies': 5,
    },
    {
        'isbn': '978-7-020-11234-3',
        'title': '明朝那些事儿',
        'author': '当年明月',
        'publisher': '浙江人民出版社',
        'category': '历史',
        'description': '以通俗幽默的语言讲述明朝三百年历史，深受读者喜爱。',
        'total_copies': 10,
    },
    # 科学类
    {
        'isbn': '978-7-544-27076-8',
        'title': '时间简史',
        'author': '史蒂芬·霍金',
        'publisher': '湖南科学技术出版社',
        'category': '科学',
        'description': '探索时间和空间核心秘密的引人入胜的故事，让普通人也能理解宇宙。',
        'total_copies': 6,
    },
    {
        'isbn': '978-7-535-78901-2',
        'title': '物种起源',
        'author': '查尔斯·达尔文',
        'publisher': '北京大学出版社',
        'category': '科学',
        'description': '进化论的奠基之作，彻底改变人类对生命起源的认识。',
        'total_copies': 4,
    },
    {
        'isbn': '978-7-544-35678-9',
        'title': '宇宙简史',
        'author': '史蒂芬·霍金',
        'publisher': '湖南科学技术出版社',
        'category': '科学',
        'description': '霍金带领读者探索宇宙奥秘，从大爆炸到黑洞的科普经典。',
        'total_copies': 5,
    },
    # 经济类
    {
        'isbn': '978-7-111-45678-9',
        'title': '国富论',
        'author': '亚当·斯密',
        'publisher': '商务印书馆',
        'category': '经济',
        'description': '现代经济学的奠基之作，系统阐述自由市场经济理论。',
        'total_copies': 4,
    },
    {
        'isbn': '978-7-508-67890-1',
        'title': '经济学原理',
        'author': '曼昆',
        'publisher': '北京大学出版社',
        'category': '经济',
        'description': '最受欢迎的经济学入门教材，通俗易懂地讲解经济学基本原理。',
        'total_copies': 6,
    },
    {
        'isbn': '978-7-111-56789-0',
        'title': '穷查理宝典',
        'author': '查理·芒格',
        'publisher': '中信出版社',
        'category': '经济',
        'description': '巴菲特搭档查理·芒格的投资智慧与人生哲学精华集。',
        'total_copies': 5,
    },
    # 哲学类
    {
        'isbn': '978-7-100-01234-5',
        'title': '理想国',
        'author': '柏拉图',
        'publisher': '商务印书馆',
        'category': '哲学',
        'description': '西方哲学的奠基之作，探讨正义、理想国家和人生意义。',
        'total_copies': 4,
    },
    {
        'isbn': '978-7-100-02345-6',
        'title': '道德经',
        'author': '老子',
        'publisher': '中华书局',
        'category': '哲学',
        'description': '道家哲学的经典著作，以简洁深邃的语言阐述宇宙人生的智慧。',
        'total_copies': 8,
    },
    {
        'isbn': '978-7-108-04567-8',
        'title': '苏菲的世界',
        'author': '乔斯坦·贾德',
        'publisher': '作家出版社',
        'category': '哲学',
        'description': '以小说形式介绍西方哲学史，适合哲学入门的经典读物。',
        'total_copies': 6,
    },
    # 心理学类
    {
        'isbn': '978-7-544-23456-7',
        'title': '心理学与生活',
        'author': '理查德·格里格',
        'publisher': '人民邮电出版社',
        'category': '心理学',
        'description': '最经典的心理学入门教材，将心理学知识与日常生活紧密结合。',
        'total_copies': 5,
    },
    {
        'isbn': '978-7-508-65432-1',
        'title': '思考，快与慢',
        'author': '丹尼尔·卡尼曼',
        'publisher': '中信出版社',
        'category': '心理学',
        'description': '诺贝尔经济学奖得主揭示人类思维的两套系统及其对决策的影响。',
        'total_copies': 6,
    },
    {
        'isbn': '978-7-201-12345-8',
        'title': '自卑与超越',
        'author': '阿尔弗雷德·阿德勒',
        'publisher': '天津人民出版社',
        'category': '心理学',
        'description': '个体心理学创始人阿德勒的代表作，探讨人生意义与自我超越。',
        'total_copies': 5,
    },
    # 艺术类
    {
        'isbn': '978-7-535-67890-1',
        'title': '艺术的故事',
        'author': '贡布里希',
        'publisher': '广西美术出版社',
        'category': '艺术',
        'description': '艺术史入门经典，以生动的语言讲述从史前到现代的艺术发展。',
        'total_copies': 4,
    },
    {
        'isbn': '978-7-108-05678-9',
        'title': '美的历程',
        'author': '李泽厚',
        'publisher': '生活·读书·新知三联书店',
        'category': '艺术',
        'description': '从美学角度审视中国艺术发展史，感受中华文明的审美历程。',
        'total_copies': 5,
    },
]

for book_data in books_data:
    category_name = book_data.pop('category')
    total_copies = book_data.pop('total_copies', 3)
    category = Category.objects.get(name=category_name)
    book, created = Book.objects.get_or_create(
        isbn=book_data['isbn'],
        defaults={
            **book_data,
            'category': category,
        }
    )
    if created:
        print(f'创建图书: {book.title}')
        # 创建副本
        for i in range(total_copies):
            BookCopy.objects.create(book=book)
        print(f'  添加 {total_copies} 个副本')

print('\n初始化完成！')
print('管理员账户: admin / admin123')
print('测试用户: testuser / test123')
