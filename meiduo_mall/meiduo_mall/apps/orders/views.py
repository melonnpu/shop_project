import json
from decimal import Decimal

from django import http
from django.db import transaction
from django.shortcuts import render

# Create your views here.
from django.utils import timezone
from django.views import View
from django_redis import get_redis_connection

from goods.models import SKU
from meiduo_mall.utils.models import LoginRequiredJSONMixin
from meiduo_mall.utils.response_code import RETCODE
from meiduo_mall.utils.views import LoginRequiredMixin
from orders.models import OrderInfo, OrderGoods
from users.models import Address


class OrderSettlementView(LoginRequiredMixin, View):
    """结算订单"""

    def get(self, request):
        """提供订单结算页面"""
        # 1.获取登陆用户
        user = request.user
        # 2.查询地址信息
        try:
            addresses = Address.objects.filter(user=user, is_deleted=False)
        except Address.DoesNotExist:
            # 3.如果地址信息为空，渲染模板判断，并跳转的地址编译页面
            addresses = None

        # 4.从redis购物车中查询出被勾选的商品信息
        redis_conn = get_redis_connection('carts')
        # 从hash表中取出该用户的所用商品
        item_dict = redis_conn.hgetall('cartss_%s' % user.id)
        # 从set表中取出所有的勾选的商品id
        cart_selected = redis_conn.smembers('selected_%s' % user.id)
        cart = {}
        for sku_id in cart_selected:
            # 组成商品id和商品数量count对应的字典
            cart[int(sku_id)] = int(item_dict[sku_id])
        # 5.准备初始值
        total_count = 0
        total_amount = Decimal('0.00')
        # 6.查询商品信息
        skus = SKU.objects.filter(id__in=cart.keys())
        for sku in skus:
            # 单个商品的数量和总金额
            sku.count = cart[sku.id]
            sku.amount = sku.count * sku.price

            # 计算商品总数量和总金额
            total_count += sku.count
            total_amount += sku.amount
        # 7.补充运费
        freight = Decimal('10.00')
        # 8.渲染页面
        context = {
            'addresses': addresses,
            'skus': skus,
            'total_count': total_count,
            'total_amount': total_amount,
            'freight': freight,
            'payment_amount': total_amount + freight
        }
        # 9.返回数据
        return render(request, 'place_order.html', context)


class OrderCommitView(LoginRequiredJSONMixin, View):
    """订单提交"""

    def post(self, request):
        """保存订单信息和订单商品信息"""
        # 1.接收参数
        # 获取当前要保存的订单数据
        json_dict = json.loads(request.body.decode())
        address_id = json_dict.get('address_id')
        pay_method = json_dict.get('pay_method')
        # 2.校验参数
        if not all([address_id, pay_method]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 判断address_id是否合法
        try:
            address = Address.objects.get(id=address_id)
        except Exception:
            return http.HttpResponseForbidden('参数address_id错误')
        # 判断pay_method是否合法
        if pay_method not in [OrderInfo.PAY_METHODS_ENUM['CASH'],
                              OrderInfo.PAY_METHODS_ENUM['ALIPAY']]:
            return http.HttpResponseForbidden('参数pay_method错误')
        # 3.获取登陆用户
        user = request.user
        # 4.生成订单编号
        order_id = timezone.localtime().strftime('%Y%m%d%H%M%S') + ('%09d' % user.id)

        # 开启一个事务
        with transaction.atomic():
            # 创建保存点
            save_id = transaction.savepoint()

            # 5.保存订单基本信息
            order = OrderInfo.objects.create(
                order_id=order_id,
                user=user,
                address=address,
                total_count=0,
                total_amount=Decimal('0'),
                freight=Decimal('10.00'),
                pay_method=pay_method,
                status=OrderInfo.ORDER_STATUS_ENUM['UNPAID']
                if pay_method == OrderInfo.PAY_METHODS_ENUM['ALIPAY']
                else OrderInfo.ORDER_STATUS_ENUM['UNSEND']
            )
            # 6.从redis读取购物车中被勾选的商品信息
            redis_conn = get_redis_connection('carts')
            item_dict = redis_conn.hgetall('carts_%s' % user.id)
            cart_selected = redis_conn.smembers('selected_%s' % user.id)
            carts = {}
            for sku_id in cart_selected:
                carts[int(sku_id)] = int(item_dict[sku_id])
            # 7.获取选中的商品id
            sku_ids = carts.keys()
            # 8.遍历购物车中被选中的商品信息
            for sku_id in sku_ids:
                # todo 1.增加一个循环
                while True:
                    # 9.查询SKU信息
                    sku = SKU.objects.get(id=sku_id)
                    # todo 2.获取原始库存
                    origin_stock = sku.stock
                    origin_sales = sku.sales

                    # 10.判断SKU库存
                    sku_count = carts[sku.id]
                    if sku_count > sku.stock:
                        # 出错就回滚到保存点
                        transaction.savepoint_rollback(save_id)
                        return http.JsonResponse({'code': RETCODE.STOCKERR,
                                                  'errmsg': '库存不足'})
                    # # 11.SKU减少库存，增加销量
                    # sku.stock -= sku_count
                    # sku.sales += sku_count
                    # sku.save()

                    # todo 3.乐观锁更新库存和销量
                    # 计算差值
                    new_stock = origin_stock - sku_count
                    new_sales = origin_sales + sku_count
                    result = SKU.objects.filter(id=sku_id,
                                                stock=origin_stock
                                                ).update(stock=new_stock, sales=new_sales)
                    # 如果下单失败，但是库存足够时，继续下单
                    if result == 0:
                        continue
                    # 12.修改SPU销量
                    sku.goods.sales += sku_count
                    sku.goods.save()
                    # 13.保存订单商品信息
                    OrderGoods.objects.create(
                        order=order,
                        sku=sku,
                        count=sku_count,
                        price=sku.price,
                    )
                    # 14.保存商品订单中总价和总数量
                    order.total_count += sku_count
                    order.total_amount += (sku_count * sku.price)

                    # todo 4.下单成功或失败，跳出循环
                    break
            # 15.添加邮费和保存订单信息
            order.total_amount += order.freight
            order.save()

            # 提交事务
            transaction.savepoint_commit(save_id)
        # --------------------------保存功能完毕-------------------------
        # 16.清除购物车中已结算的商品
        redis_conn.hdel('carts_%s' % user.id, *cart_selected)
        redis_conn.srem('selected_%s' % user.id, *cart_selected)
        # 17.响应提交订单结果
        return http.JsonResponse({'code': RETCODE.OK,
                                  'errmsg': '下单成功',
                                  'order_id': order.order_id})


class OrderSuccessView(LoginRequiredMixin, View):
    """提交订单成功"""

    def get(self, request):
        order_id = request.GET.get('order_id')
        payment_amount = request.GET.get('payment_amount')
        pay_method = request.GET.get('pay_method')

        context = {
            'order_id': order_id,
            'payment_amount': payment_amount,
            'pay_method': pay_method
        }
        return render(request, 'order_success.html', context)
