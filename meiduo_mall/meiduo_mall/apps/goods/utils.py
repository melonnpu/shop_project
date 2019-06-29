"""
                           _
                           \"-._ _.--"~~"--._
                            \   "            ^.    ___
                            /                  \.-~_.-~
                     .-----'     /\/"\ /~-._      /
                    /  __      _/\-.__\L_.-/\     "-.
                   /.-"  \    ( ` \_o>"<o_/  \  .--._\
                  /'      \    \:     "     :/_/     "`
                          /  /\ "\    ~    /~"
                          \ I  \/]"-._ _.-"[
                       ___ \|___/ ./    l   \___   ___
                  .--v~   "v` ( `-.__   __.-' ) ~v"   ~v--.
               .-{   |     :   \_    "~"    _/   :     |   }-.
              /   \  |           ~-.,___,.-~           |  /   \
             ]     \ |                                 | /     [
             /\     \|     :                     :     |/     /\
            /  ^._  _K.___,^                     ^.___,K_  _.^  \
           /   /  "~/  "\                           /"  \~"  \   \
          /   /    /     \ _          :          _ /     \    \   \
        .^--./    /       Y___________l___________Y       \    \.--^.
        [    \   /        |        [/    ]        |        \   /    ]
        |     "v"         l________[____/]________j  -melon }r"     /
        }------t          /                       \       /`-.     /
        |      |         Y                         Y     /    "-._/
        }-----v'         |         :               |     7-.     /
        |   |_|          |         l               |    / . "-._/
        l  .[_]          :          \              :  r[]/_.  /
         \_____]                     "--.             "-.____/
                                            "Bug! No way!"
                                                      ---Melon
         
"""
from collections import OrderedDict

from django.shortcuts import render

from contents.models import ContentCategory
from goods.models import GoodsChannel, GoodsCategory, SKU


# def get_categories():
#     """
#     获取商城商品分类菜单
#     :return 菜单字典
#     """
#     # 商品频道及分类菜单
#     # 下面的代码生成的模板:
#     # categories = {
#     #  (1,  # 组1
#     #       {'channels': [{'id': 1, 'name': '手机','url':'http://shouji.jd.com'},
#     #                     {'id': 2, 'name': '相机','url':'http://www.itcast.cn'},
#     #                     {'id': 3, 'name': '数码','url':'http://www.itcast.cn'}],
#     #        'sub_cats': [ < GoodsCategory: 手机通讯 >,
#     #                      < GoodsCategory: 手机配件 >,
#     #                      < GoodsCategory: 摄影摄像 >,
#     #                      < GoodsCategory: 数码配件 >,
#     #                      < GoodsCategory: 影音娱乐 >,
#     #                      < GoodsCategory: 智能设备 >,
#     #                      < GoodsCategory: 电子教育 >
#     #                    ]
#     #       }
#     #   ),(2, # 组2
#     #        {
#     #
#     #   })
#     # }
#
#     # 第一部分: 从数据库中取数据:
#     # 定义一个有序字典对象
#     categories = OrderedDict()
#     # 对 GoodsChannel 进行 group_id 和 sequence 排序, 获取排序后的结果:
#     channels = GoodsChannel.objects.order_by('group_id', 'sequence')
#     # 遍历排序后的结果: 得到所有的一级菜单( 即,频道 )
#     for channel in channels:
#         # 从频道中得到当前的 组id
#         group_id = channel.group_id
#
#         # 判断: 如果当前 组id 不在我们的有序字典中:
#         if group_id not in categories:
#             # 我们就把 组id 添加到 有序字典中
#             # 并且作为 key值, value值 是 {'channels': [], 'sub_cats': []}
#             categories[group_id] = {'channels': [], 'sub_cats': []}
#
#         # 获取当前频道的分类名称
#         cat1 = channel.category
#
#         # 给刚刚创建的字典中, 追加具体信息:
#         # 即, 给'channels' 后面的 [] 里面添加如下的信息:
#         categories[group_id]['channels'].append({
#             'id': cat1.id,
#             'name': cat1.name,
#             'url': channel.url
#         })
#
#         # 根据 cat1 的外键反向, 获取下一级(二级菜单)的所有分类数据, 并遍历:
#         for cat2 in cat1.goodscategory_set.all():
#             # 创建一个新的列表:
#             cat2.sub_cats = []
#             # 根据 cat2 的外键反向, 获取下一级(三级菜单)的所有分类数据, 并遍历:
#             for cat3 in cat2.goodscategory_set.all():
#                 # 拼接新的列表: key: 二级菜单名称, value: 三级菜单组成的列表
#                 cat2.sub_cats.append(cat3)
#             # 所有内容在增加到 一级菜单生成的 有序字典中去:
#             categories[group_id]['sub_cats'].append(cat2)
#
#     return categories


# 对包屑导航数据的查询进行封装，方便后续直接使用
def get_breadcrumb(category):
    """
    获取面包屑导航
    :param category: 商品类别
    :return: 面包屑导航字典
    """

    # 定义一个字典:
    breadcrumb = dict(
        cat1='',
        cat2='',
        cat3=''
    )
    # 判断 category 是哪一个级别的.
    # 注意: 这里的 category 是 GoodsCategory对象
    if category.parent is None:
        # 当前类别为一级类别
        breadcrumb['cat1'] = category
    # 因为当前这个表示自关联表, 所以关联的对象还是自己:
    elif category.goodscategory_set.count() == 0:
        # 当前类别为三级
        breadcrumb['cat3'] = category
        cat2 = category.parent
        breadcrumb['cat2'] = cat2
        breadcrumb['cat1'] = cat2.parent
    else:
        # 当前类别为二级
        breadcrumb['cat2'] = category
        breadcrumb['cat1'] = category.parent

    return breadcrumb


def get_categories():
    """
    获取商品分类数据
    :return: 商品分类数据
    """
    # 1.创建一个有序字典
    categories = OrderedDict()
    # 2.获取所有的商品频道channels
    channels = GoodsChannel.objects.order_by('group_id', 'sequence')

    # 3.遍历channels，获取每一个channel对象
    for channel in channels:

        # 4.根据channel对象获取group_id
        group_id = channel.group_id
        # 5.判断group_id是否在字典中
        if group_id not in categories:
            # 6.如果不在，添加到有序字典中
            categories[group_id] = {"channels": [], "sub_cats": []}
        # todo 获取当前频道的分类名称 (牢记)
        cat1 = channel.category
        # 7.对channels对应的字典中添加数据
        categories[group_id]["channels"].append({
            "id": cat1.id,
            "name": cat1.name,
            "url": channel.url
        })
        # 8.获取单个的二级分类
        # todo 获取所有的二级分类　cat1.goodscategory_set.all()
        for cat2 in cat1.goodscategory_set.all():

            # 9.在二级分类中添加sub_cats属性
            cat2.sub_cats=[]
            # 10.获取单个的三级分类
            for cat3 in cat2.goodscategory_set.all():

                # 11.把三级分类添加到二级分类的sub_cats
                cat2.sub_cats.append(cat3)
            # 12.把二级分类放到外层sub_cats对应的列表中
            categories[group_id]["sub_cats"].append(cat2)
            # 13.返回有序字典
    return categories



def get_goods_and_spec(sku_id,request):
    # 获取当前sku的信息
    try:
        sku = SKU.objects.get(id=sku_id)
        sku.images = sku.skuimage_set.all()
    except Exception as e:
        return render(request,'404.html')

    # 获取面包屑导航信息中的频道
    # 获取sku的spu
    goods = sku.goods
    # 利用spu获取商品的一级分类，接着获取该频道
    goods_channel = goods.category1.goodschannel_set.all()[0]

    # 构建当前商品的规格键
    # sku_key=[规格1参数id， 规格2参数id， 规格3参数id, ...]
    sku_specs = sku.skuspecification_set.order_by('spec_id')
    sku_key = []
    for spec in sku_specs:
        sku_key.append(spec.option.id)

    # 获取当前商品的所有sku
    skus = goods.sku_set.all()

    # 构建不同规格参数(选项)的ｓｋｕ字典
    spec_sku_map={}
    for s in skus:
        # 获取sku的规格参数
        s_specs = s.skuspecification_set.order_by('spec_id')
        # 用于形成规则参数-sku字典的键
        key = []
        for spec in s_specs:
            key.append(spec.option.id)
        # 向规则参数-sku字典添加记录

        # 获取当前商品的规格信息






