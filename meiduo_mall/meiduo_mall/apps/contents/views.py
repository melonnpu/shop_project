from django.shortcuts import render

# Create your views here.
from django.views import View

from contents.models import ContentCategory
from goods.utils import get_categories


class IndexView(View):
    """首页广告"""

    # def get(self,request):
    #     """提供首页广告界面"""
    #     # 查询商品频道和分类
    #     categories = get_categories()
    #
    #     # 定义一个空的字典
    #     dict = {}
    #
    #     # 查询出所有的广告类别
    #     content_categories = ContentCategory.objects.all()
    #     # 遍历所有的广告类别, 然后放入到定义的空字典中:
    #     for cat in content_categories:
    #         # 获取类别所对应的展示数据, 并对数据进行排序:
    #         # key:value  ==>  商品类别.key:具体的所有商品(排过序)
    #         dict[cat.key] = cat.content_set.filter(status=True).order_by('sequence')
    #
    #     # 拼接参数:
    #     context = {
    #         # 这是首页需要的一二级分类信息:
    #         'categories': categories,
    #         # 这是首页需要的能展示的三级信息:
    #         'contents': dict,
    #     }
    #     # 返回界面, 同时传入参数:
    #     return render(request, 'index.html', context=context)

    def get(self, request):
        """首页广告"""
        # 商品频道分类部分
        # 1.获取商品频道分类数据
        categories = get_categories()
        # 广告内容部分
        # 2.获取所用的广告类别
        content_categories = ContentCategory.objects.all()
        # 定义一个空的字典
        dict = {}
        # 3.遍历所有的广告类别，获取每一个
        for cat in content_categories:
            # 4.获取每一个广告类别对应的广告内容，并放到一个新字典中
            # todo 这里要对获取的广告内容进行排序
            dict[cat.key] = cat.content_set.filter(status=True).order_by('sequence')
        # 5.拼接参数
        context = {
            "categories": categories,
            "contents": dict,
        }
        # 6.返回
        return render(request, 'index.html', context=context)
