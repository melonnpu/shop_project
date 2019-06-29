from django import http
from django.core.cache import cache
from django.shortcuts import render

# Create your views here.
from django.views import View

from areas.models import Area
from meiduo_mall.utils.response_code import RETCODE


# 增加省级数据
class ProvinceAreasView(View):
    """省级地区"""

    def get(self, request):
        """提供省级地区数据
        1.查询省级数据
        2.序列化(整理)省级数据
        3.响应省级数据
        4.补充缓存逻辑
        """
        # 增加：判断是否有缓存
        province_list = cache.get('province_list')
        if not province_list:
            try:
                # 1.查询省级数据
                province_query_set = Area.objects.filter(parent__isnull=True)

                # 2.整理数据

                province_list = []
                for province_model in province_query_set:
                    province_list.append({
                        'id': province_model.id,
                        'name': province_model.name
                    })
                # 增加省级缓存
                cache.set('province_list', province_list, 3600)
            except Exception as e:
                # 如果报错，则返回错误原因
                # DBERR:5000
                return http.JsonResponse({
                    'code': RETCODE.DBERR,
                    'errmsg': '省份数据有误'
                })

        # 3.响应省级数据
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': 'ok',
            'province_list': province_list
        })


# 请求市区数据
class SubAreasView(View):
    """子级地区：市和区县"""

    def get(self, request, pk):
        """提供市或区县数据
        1.查询是或区县数据
        2.序列化是或区县数据
        3.响应市或区县数据
        4.添加缓存
        """
        # 查看缓存
        sub_data = cache.get('sub_area' + pk)
        if not sub_data:
            # 1.接收参数，查询数据
            try:
                # 根据省份id查询市数据
                sub_model_set = Area.objects.filter(parent_id=pk)
                parent_model = Area.objects.get(id=pk)

                # 2.序列化数据
                sub_list = []
                for sub_model in sub_model_set:
                    sub_list.append({
                        'id': sub_model.id,
                        'name': sub_model.name
                    })
                sub_data = {
                    'id': parent_model.id,  # pk
                    'name': parent_model.name,
                    'subs': sub_list
                }
                cache.set('sub_area'+pk, sub_data, 3600)
            except Exception as e:
                return http.JsonResponse({
                    'code': RETCODE.DBERR,
                    'errmsg': '城市或区县数据错误'
                })
        # 3.响应数据
        return http.JsonResponse({'code': RETCODE.OK,
                                  'errmsg': 'OK',
                                  'sub_data': sub_data})

