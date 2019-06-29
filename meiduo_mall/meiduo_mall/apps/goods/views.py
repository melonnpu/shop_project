from django import http
from django.core.paginator import Paginator, EmptyPage

from django.shortcuts import render

# Create your views here.
from django.views import View

from goods.models import GoodsCategory, SKU
from goods.utils import get_categories, get_breadcrumb
from meiduo_mall.utils.response_code import RETCODE


class ListView(View):
    """商品列表页"""

    def get(self, request, category_id, page_num):
        """提供商品列表页"""
        # 判断category_id是否正确
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseNotFound('GoodsCategory 不存在')

        # 查询商品频道分类
        categories = get_categories()
        # 查询面包屑导航
        breadcrumb = get_breadcrumb(category)

        # 增加的代码部分:
        # 接收sort参数：如果用户不传，就是默认的排序规则
        sort = request.GET.get('sort', 'default')

        # 按照排序规则查询该分类商品SKU信息
        if sort == 'price':
            # 按照价格由低到高
            sortkind = 'price'
        elif sort == 'hot':
            # 按照销量由高到低
            sortkind = '-sales'
        else:
            # 'price'和'sales'以外的所有排序方式都归为'default'
            sort = 'default'
            sortkind = 'create_time'

        # 获取当前分类并且上架的商品.( 并且对商品按照排序字段进行排序 )
        skus = SKU.objects.filter(category=category,
                                  is_launched=True).order_by(sortkind)

        # 创建分页器：每页N条记录
        # # 列表页每页商品数据量
        # GOODS_LIST_LIMIT = 5
        paginator = Paginator(skus, 5)
        # 获取每页商品数据
        try:
            page_skus = paginator.page(page_num)
        except EmptyPage:
            # 如果page_num不正确，默认给用户404
            return http.HttpResponseNotFound('empty page')
        # 获取列表页总页数
        total_page = paginator.num_pages

        # 渲染页面
        context = {
            'categories': categories,  # 频道分类
            'breadcrumb': breadcrumb,  # 面包屑导航
            'sort': sort,  # 排序字段
            'category': category,  # 第三级分类
            'page_skus': page_skus,  # 分页后数据
            'total_page': total_page,  # 总页数
            'page_num': page_num,  # 当前页码
        }
        return render(request, 'list.html', context)


class HotGoodsView(View):
    """商品热销排行"""

    def get(self, request, category_id):
        """提供商品热销排行 JSON 数据"""
        # 根据销量倒序
        skus = SKU.objects.filter(category_id=category_id,
                                  is_launched=True).order_by('-sales')[:2]

        # 序列化
        hot_skus = []
        for sku in skus:
            hot_skus.append({
                'id': sku.id,
                'default_image_url': sku.default_image_url,
                'name': sku.name,
                'price': sku.price
            })

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'hot_skus': hot_skus})


class DetailView(View):
    """商品详情页"""

    def get(self, request, sku_id):
        """提供商品详情页"""
        # 1.获取当前sku的信息
        try:
            # 根据商品的sku_id获取对应的商品
            sku = SKU.objects.get(id=sku_id)
        except Exception as e:
            # 如果商品不存在，返回404
            return render(request, '404.html')
        # 2.查询商品频道分类
        categories = get_categories()
        # 3.渲染页面
        context = {
            'categories': categories,
            'sku': sku,
        }
        return render(request, 'detail.html', context)
