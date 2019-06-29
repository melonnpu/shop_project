from django import http
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage
from django.shortcuts import render, redirect

# Create your views here.
from django.urls import reverse
from django.views import View

import json
import re
import logging

from goods.models import SKU
from orders.models import OrderInfo

logger = logging.getLogger('django')

# class RegisterView(View):
#     """用户注册"""
#     def get(self,request):
#         """
#         提供注册界面
#         :param request:请求对象
#         :return: 注册界面
#         """
#         return render(request,'register.html')
from django_redis import get_redis_connection
from pymysql import DatabaseError

from meiduo_mall.utils.models import LoginRequiredJSONMixin
from meiduo_mall.utils.views import LoginRequiredMixin
from users.models import User, Address
from meiduo_mall.utils.response_code import RETCODE


# 注册视图
class RegisterView(View):
    """用户注册"""

    def get(self, request):
        """
        提供注册界面
        :param request: 请求对象
        :return: 注册界面
        """

        return render(request, 'register.html')

    def post(self, request):
        """
        实现用户注册
        :param request: 请求对象
        :return: 注册结果
        """
        # 1.接收参数
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('mobile')
        allow = request.POST.get('allow')
        # 添加短信验证之接收参数
        sms_code_client = request.POST.get('sms_code')

        # 2.校验参数
        # 判断参数是否齐全
        if not all([username, password, password2, mobile, allow]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 判断用户名是否是５－２０个字符
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入5-20个字符的用户名')

        # 判断密码是否是８－２０个字符
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')

        # 判断两次密码是否一致
        if password != password2:
            return http.HttpResponseForbidden('两次输入的密码不一致')

        # 判断手机号是否合法
        if not re.match(r'^1[345789]\d{9}$', mobile):
            return http.HttpResponseForbidden('请输入正确的手机号码')

        # 添加短信验证功能之判断短信验证码是否正确
        # 获取ｒｅｄｉｓ连接对象
        redis_conn = get_redis_connection('verify_code')

        # 从ｒｅｄｉｓ中获取保存的sms_code(验证码)
        sms_code_server = redis_conn.get('sms_code_%s' % mobile)

        # 判断验证码是否存在
        if sms_code_server is None:
            # 不存在直接返回, 说明服务器的过期了, 超时
            return render(request,
                          'register.html',
                          {'sms_code_errmsg': '无效的短信验证码'}
                          )
        # 如果验证码存在，对比浏览器发来的验证码和从服务端获取的验证码
        if sms_code_client != sms_code_server.decode():
            print("输入验证码sms_code_client", sms_code_client)
            print("服务端保存验证码sms_code_server", sms_code_server.decode())
            # 对比失败，说明短信验证码有问题，直接返回
            return render(request,
                          'register.html',
                          {"sms_code_errmsg": "短信验证码有误"}
                          )

        # 判断是否勾选用户协议
        if allow != 'on':
            return http.HttpResponseForbidden('请勾选用户协议')

        # 3.保存注册数据
        try:
            user = User.objects.create_user(username=username, password=password, mobile=mobile, )
        except DatabaseError:
            # 注册我错误，响应错误提示
            return render(request, 'register.html', {'register_errmsg': '注册失败'})

        # 实现状态保持
        login(request, user)
        # # 4.注册成功，响应结果，重定向到首页
        # return redirect(reverse('contents:index'))
        # 生成响应对象
        response = redirect(reverse('contents:index'))
        # 用响应对象设置用户名信息
        # 将名字写入到cookie中，有效期１５天
        response.set_cookie('username', user.username, max_age=3600 * 24 * 15)

        # 返回响应结果
        return response


# 用户名重重复校验
class UsernameCountView(View):
    """用户名重复校验"""

    def get(self, request, username):
        """
        判断用户名是否重复注册
        :param request: 请求对象
        :param username: 用户名
        :return: JSON
        """
        count = User.objects.filter(username=username).count()
        return http.JsonResponse({
            "code": RETCODE.OK,
            "errmsg": 'ok',
            "count": count
        })


# 手机号重复注册
class MobileCountView(View):
    """手机号重复注册"""

    def get(self, request, mobile):
        """
        判断手机号是否重复注册
        :param request: 请求对象
        :param mobile: 手机号码
        :return: JSON
        """
        count = User.objects.filter(mobile=mobile).count()
        return http.JsonResponse({
            "code": RETCODE.OK,
            "errmsg": "OK",
            "count": count
        })


class LoginView(View):
    """用户名登陆"""

    def get(self, request):
        """提供登陆界面的接口"""
        # 返回登陆界面
        return render(request, 'login.html')

    def post(self, request):
        """
        实现登陆验证
        :param request: 请求对象
        :return: 登陆结果
        """
        # 1.接收参数
        username = request.POST.get('username')
        password = request.POST.get('password')
        remembered = request.POST.get('remembered')
        # 这个next是后加的哦
        next = request.GET.get('next')

        # 2.校验参数
        # 总体校验,判断参数是否齐全
        if not all([username, password]):
            return http.HttpResponseForbidden('缺少必传参数')

        # 判断用户名是否是５－２０为字符
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('用户名或密码有误')

        # 判断密码是否是８－２０位数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('用户名或密码有误')

        # 3.获取登陆用户，查看用户是否存在
        user = authenticate(username=username, password=password)
        if user is None:
            return render(request, 'login.html', {'account_errmsg': '用户名或密码错误'})
        # 4.实现状态保持
        login(request, user)

        # 设置状态保持
        if remembered != 'on':
            # 不记住用户，浏览器会话结束就过期
            request.session.set_expiry(0)
        else:
            # 记住密码：None:表示两周后过期
            request.session.set_expiry(None)

        # 5.返回响应对象
        # url = reverse('contents:index')
        # print('url',url)
        # return redirect(reverse('contents:index'))

        # 判断next参数是否存在
        if next:
            # 如果存在，则说明是从别的页面跳过来到，重新回到原来的页面
            response = redirect(next)
        else:
            # 没有参数，则是直接登陆的，生成回到首页的响应对象
            response = redirect(reverse('contents:index'))

        # 在响应对象中设置用户名信息.
        # 将用户名写入到 cookie，有效期 15 天
        response.set_cookie('username', user.username, max_age=3600 * 24 * 15)

        # 返回响应结果
        return response


class LogoutView(View):
    """退出登陆"""

    # 由于首页中用户名是从 cookie 中读取的。
    # 所以退出登录时，需要将 cookie 中用户名清除
    def get(self, request):
        """实现退出登陆逻辑"""

        # 清理　session
        logout(request)

        # 退出登陆，重定向到登陆页
        response = redirect(reverse('contents:index'))

        # 退出登陆时，response对象来清除cookie中的username
        response.delete_cookie('username')

        # 返回响应
        return response


# 第一种验证用户是否登陆的方法
# 缺点：代码复用性底，登录验证很多地方都需要，所以该判断逻辑需要重复编码好多次

# 最终版
class UserInfoView(LoginRequiredMixin, View):
    """用户中心"""

    def get(self, request):
        """提供个人信息界面"""
        # 将验证用户的信息进行拼接
        context = {
            'username': request.user.username,
            'mobile': request.user.mobile,
            'email': request.user.email,
            'email_active': request.user.email_active
        }

        # 返回响应
        return render(request, 'user_center_info.html', context=context)


# 第二种验证用户是否登陆的方法
# login_required装饰器
# 如果通过登录验证则进入到视图内部，执行视图逻辑,正常加载用户中心界面
# 如果未通过登录验证则被重定向到 LOGIN_URL 配置项指定的地址:ｄｅｖ：LOGIN_URL = '/login/'


# 添加邮箱视图
class EmailView(View):
    """添加邮箱"""

    def put(self, request):
        """
        实现添加邮箱逻辑
        :param request: 请求对象
        :return: 返回json
        """
        # 1.接收参数
        json_str = request.body.decode()
        json_dict = json.loads(json_str)
        email = json_dict.get('email')

        # 2.校验参数
        if not email:
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'', email):
            return http.HttpResponseForbidden('邮箱格式错误')

        # 3.添加邮箱（核心操作）
        try:
            request.user.email = email
            request.user.save()
        except Exception as e:
            print(e)
            return http.JsonResponse({
                'code': RETCODE.DBERR,
                'errmsg': '添加邮箱失败'
            })

        # 4.返回结果json
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': '添加邮箱成功'
        })


# # 展示地址页面
# class AddressView(LoginRequiredMixin, View):
#     """用户收货地址"""
#
#     def get(self, request):
#         """提供收获地址界面"""
#         # 获取所有的地址:
#         addresses = Address.objects.filter(user=request.user, is_deleted=False)
#
#         # 创建空的列表
#         address_dict_list = []
#         # 遍历
#         for address in addresses:
#             address_dict = {
#                 "id": address.id,
#                 "title": address.title,
#                 "receiver": address.receiver,
#                 "province": address.province.name,
#                 "city": address.city.name,
#                 "district": address.district.name,
#                 "place": address.place,
#                 "mobile": address.mobile,
#                 "tel": address.tel,
#                 "email": address.email
#             }
#             # 将默认地址移动到最前面
#             default_address = request.user.default_address
#             if default_address.id == address.id:
#                 # 查询集 addresses 没有 insert 方法
#                 address_dict_list.insert(0, address_dict)
#             else:
#                 address_dict_list.append(address_dict)
#         context = {
#             'default_address_id': request.user.default_address_id,
#             'addresses': address_dict_list,
#         }
#
#         return render(request, 'user_center_site.html', context=context)


class CreateAddressView(LoginRequiredJSONMixin, View):
    """新增地址"""

    def post(self, request):
        """提供新增地址逻辑
        """
        # 1.判断地址个数
        count = request.user.addresses.count()
        if count >= 20:
            # RETCODE.THROTTLINGERR:  4002
            return http.JsonResponse({'code': RETCODE.THROTTLINGERR,
                                      'errmsg': '超过地址数量上限'})
        # 2.接收参数
        json_str = request.body.decode()
        json_dict = json.loads(json_str)
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')
        # 3.校验参数
        # 校验参数
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')
        # 4.保存地址信息
        try:
            address = Address.objects.create(
                user=request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
            # 5.设置默认地址
            if not request.user.default_address:
                request.user.default_address = address
                request.user.save()
        except Exception as e:
            print('error', e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '新增地址失败'})
        # 6.整理数据
        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }
        # 7.响应数据
        return http.JsonResponse({'code': RETCODE.OK,
                                  'errmsg': '新增地址成功',
                                  'address': address_dict})


# class UpdateDestroyAddressView(LoginRequiredJSONMixin, View):
#     """修改和删除地址"""
#
#     def put(self, request, address_id):
#         """修改地址"""
#         # 1.接收参数
#         json_str = request.body.decode()
#         json_dict = json.loads(json_str)
#         receiver = json_dict.get('receiver')
#         province_id = json_dict.get('province_id')
#         city_id = json_dict.get('city_id')
#         district_id = json_dict.get('district_id')
#         place = json_dict.get('place')
#         mobile = json_dict.get('mobile')
#         tel = json_dict.get('tel')
#         email = json_dict.get('email')
#         # 2.校验参数
#         # 总体校验
#         if not all([receiver, province_id, city_id, district_id, place, mobile]):
#             return http.HttpResponseForbidden('缺少必传参数')
#         # 个体校验
#         if not re.match(r'^1[3-9]\d{9}$', mobile):
#             return http.HttpResponseForbidden('参数mobile有误')
#         if tel:
#             if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
#                 return http.HttpResponseForbidden('参数tel有误')
#         if email:
#             if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
#                 return http.HttpResponseForbidden('参数email有误')
#         # 3.判断地址是否存在，并更新地址信息
#         try:
#             Address.objects.filter(id=address_id).update(
#                 user=request.user,
#                 title=receiver,
#                 receiver=receiver,
#                 province_id=province_id,
#                 city_id=city_id,
#                 district_id=district_id,
#                 place=place,
#                 mobile=mobile,
#                 tel=tel,
#                 email=email
#             )
#         except Exception as e:
#             # logger.error(e)
#             return http.JsonResponse({'code': RETCODE.DBERR,
#                                       'errmsg': '更新地址失败'})
#         # 4.构造响应数据
#         address = Address.objects.get(id=address_id)
#         address_dict = {
#             "id": address.id,
#             "title": address.title,
#             "receiver": address.receiver,
#             "province": address.province.name,
#             "city": address.city.name,
#             "district": address.district.name,
#             "place": address.place,
#             "mobile": address.mobile,
#             "tel": address.tel,
#             "email": address.email
#         }
#
#         # 5.响应更新地址结果
#         return http.JsonResponse({'code': RETCODE.OK,
#                                   'errmsg': '更新地址成功',
#                                   'address': address_dict})
#
#     def delete(self, request, address_id):
#         """删除地址"""
#         try:
#             # 查询要删除的地址
#             address = Address.objects.get(id=address_id)
#
#             # 将地址逻辑删除设置为True
#             address.is_deleted = True
#             address.save()
#         except Exception as e:
#             return http.JsonResponse(({'code': RETCODE.DBERR, 'errmsg': '删除地址失败'}))
#
#         # 响应删除地址结果
#         return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '删除地址成功'})
#
#
# class DefaultAddressView(LoginRequiredJSONMixin, View):
#     """设置默认地址"""
#
#     def put(self, request, address_id):
#         """设置默认地址"""
#         try:
#             # 接收数据,查询地址
#             address = Address.objects.get(id=address_id)
#             # 设置地址为默认地址
#             request.user.default_address = address
#             request.user.save()
#         except Exception as e:
#             return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '设置默认地址失败'})
#
#         # 响应设置默认地址结果
#         return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '设置默认地址成功'})
#

class UpdateTitleAddressView(LoginRequiredJSONMixin, View):
    """设置地址标题"""

    def put(self, request, address_id):
        """设置地址标题"""
        # 接收参数：地址标题
        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')
        try:
            # 查询数据
            address = Address.objects.get(id=address_id)
            # 设置新的标题
            address.title = title
            address.save()
        except Exception as e:
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '设置地址标题失败'})

        # 响应数据
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '设置地址标题成功'})


class ChangePasswordView(LoginRequiredMixin, View):
    """修改密码"""

    def get(self, request):
        """展示修改密码界面"""
        return render(request, 'user_center_pass.html')

    def post(self, request):
        """实现修改密码逻辑"""
        # 接收参数
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        new_password2 = request.POST.get('new_password2')
        # 校验参数
        if not all([old_password, new_password, new_password2]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 检查密码
        try:
            request.user.check_password(old_password)
        except Exception as e:
            return render(request, 'user_center_pass.html', {'origin_pwd_errmsg': '原始密码错误'})
        if not re.match(r'^[0-9A-Za-z]{8,20}$', new_password):
            return http.HttpResponseForbidden('密码最少8位，最长20位')
        if new_password != new_password2:
            return http.HttpResponseForbidden('两次输入的密码不一致')
        # 修改密码
        try:
            request.user.set_password(new_password)
            request.user.save()
        except Exception as e:

            return render(request, 'user_center_pass.html', {'change_pwd_errmsg': '修改密码失败'})

        # 清理状态保持信息
        logout(request)
        response = redirect(reverse('users:login'))
        response.delete_cookie('username')
        # 响应密码修改结果：重定向到登陆界面
        return response


# 展示地址页面
class AddressView(LoginRequiredMixin, View):
    """用户收货地址"""

    def get(self, request):
        """提供收获地址界面"""
        # 获取所有的地址:
        addresses = Address.objects.filter(user=request.user, is_deleted=False)

        # 创建空的列表
        address_dict_list = []
        # 遍历
        for address in addresses:
            address_dict = {
                "id": address.id,
                "title": address.title,
                "receiver": address.receiver,
                "province": address.province.name,
                "city": address.city.name,
                "district": address.district.name,
                "place": address.place,
                "mobile": address.mobile,
                "tel": address.tel,
                "email": address.email
            }
            # 将默认地址移动到最前面
            default_address = request.user.default_address
            if default_address.id == address.id:
                # 查询集 addresses 没有 insert 方法
                address_dict_list.insert(0, address_dict)
            else:
                address_dict_list.append(address_dict)
        context = {
            'default_address_id': request.user.default_address_id,
            'addresses': address_dict_list,
        }

        return render(request, 'user_center_site.html', context=context)


# 修改和删除地址
class UpdateDestroyAddressView(LoginRequiredJSONMixin, View):
    """修改和删除地址"""

    def put(self, request, address_id):
        """修改地址"""
        # 1.接收参数
        json_str = request.body.decode()
        json_dict = json.loads(json_str)
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')
        # 2.校验参数
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('缺少必传参数')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')

        # 3.修改地址
        # 判断地址是否存在，并更新地址
        try:
            address = Address.objects.get(id=address_id)
            address.user = request.user
            address.title = receiver
            address.receiver = receiver
            address.province_id = province_id
            address.city_id = city_id
            address.district_id = district_id
            address.place = place
            address.mobile = mobile
            address.tel = tel
            address.email = email
            address.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR,
                                      'errmsg': '更新地址失败'})
        # 构造响应数据
        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }

        # 4.响应结果
        return http.JsonResponse({'code': RETCODE.OK,
                                  'errmsg': '更新地址成功',
                                  'address': address_dict})

    def delete(self, request, address_id):
        """删除地址"""
        try:
            # 查询删除的地址
            address = Address.objects.get(id=address_id)
            # 将地址逻辑删除设置为True
            address.is_deleted = True
            address.save()

        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '删除地址失败'})

        # 响应删除地址结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '删除地址成功'})


class DefaultAddressView(LoginRequiredJSONMixin, View):
    """设置默认地址"""

    def put(self, request, address_id):
        """设置默认地址"""
        try:
            # 1.接收参数并获得地址对象
            address = Address.objects.get(id=address_id)

            # 2.设置该地址对象为默认地址
            # request.user＝＝>用户
            request.user.default_address = address
            request.user.save()

            # 3.响应结果
        except Exception as e:
            logger.error(e)
            return http.HttpResponseForbidden({'code': RETCODE.DBERR, 'errmsg': '设置默认地址失败'})


class UserBrowseHistory(LoginRequiredJSONMixin, View):
    """用户浏览记录"""

    def post(self, request):
        """保存用户浏览记录"""
        # 1.接收参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')

        # 2.校验参数
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('sku不存在')

        # 3.保存用户浏览数据（存储逻辑：先去重，再存储，最后截取）
        # 连接ｒｅｄｉｓ数据库
        redis_conn = get_redis_connection('history')
        # 建立管道
        pl = redis_conn.pipeline()
        user_id = request.user.id
        # 去重
        pl.lrem('history_%s' % user_id, 0, sku_id)
        # 再存储
        pl.lpush('history_%s' % user_id, sku_id)
        # 截取
        pl.ltrim('history_%s' % user_id, 0, 4)
        # 执行管道
        pl.execute()
        # 4.响应结果
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': 'OK'
        })

    def get(self, request):
        """获取用户浏览记录"""
        # 1.获取redis存储的sku_id列表信息
        redis_conn = get_redis_connection('history')
        sku_ids = redis_conn.lrange('history_%s' % request.user.id, 0, -1)

        # 2.根据sku_ids列表数据，查询出商品sku信息
        skus = []
        for sku_id in sku_ids:
            sku = SKU.objects.get(id=sku_id)
            skus.append({
                'id': sku.id,
                'name': sku.name,
                'default_image_url': sku.default_image_url,
                'price': sku.price
            })
        # 3.返回数据
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': 'OK',
            'skus': skus
        })


class UserOrderInfoView(LoginRequiredMixin, View):
    """我的订单"""

    def get(self, request, page_num):
        """提供我的订单页面"""
        # 1.创建用户
        user = request.user
        # 2.查询订单
        orders = user.orderinfo_set.all().order_by("-create_time")
        # 3.遍历所用订单
        for order in orders:
            # 4.绑定订单状态
            order.status_name = OrderInfo.ORDER_STATUS_CHOICES[order.status - 1][1]

            # 5.绑定支付方式
            order.pay_method_name = OrderInfo.PAY_METHOD_CHOICES[order.pay_method - 1][1]
            # 6.查询订单商品
            order.sku_list = []
            order_goods = order.skus.all()

            # 7.遍历订单商品
            for order_good in order_goods:
                sku = order_good.sku
                sku.count = order_good.count
                sku.amount = sku.price * sku.count
                order.sku_list.append(sku)
        # 8.分页
        page_num = int(page_num)
        try:
            paginator = Paginator(orders, 2)
            page_orders = paginator.page(page_num)
            total_page = paginator.num_pages
        except EmptyPage:
            return http.HttpResponseNotFound('订单不存在')
        # 9.构建返回数据
        context = {
            "page_orders": page_orders,
            'total_page': total_page,
            'page_num': page_num,
        }
        # 10.返回数据
        return render(request, 'user_center_order.html', context)
