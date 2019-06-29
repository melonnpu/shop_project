# 导入
from QQLoginTool.QQtool import OAuthQQ
from django import http
from django.conf import settings
from django.contrib.auth import login


# Create your views here.
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View


from meiduo_mall.utils.response_code import RETCODE
from oauth.models import OAuthQQUser
from oauth.utils import generate_access_token


class QQURLView(View):
    """提供qq登陆页面网址"""

    def get(self,request):
        # next 表示从哪个方面进入到的登陆页面，将来登陆成功后，就自动回到那个页面
        next = request.GET.get('next')

        # 获取QQ登陆页面网址
        # 创建oAuthQQ类的对象
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                        client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI,
                        state=next)
        # 调用对象的获取ｑｑ地址方法
        login_url = oauth.get_qq_url()

        # 返回登陆地址
        return http.JsonResponse({'code': RETCODE.OK,
                                  'errmsg': 'OK',
                                  'login_url': login_url
                                  })


class QQUserView(View):
    """用户扫码登陆的回调处理"""

    def get(self, request):
        """Oauth2.0认证"""
        # 接收Authorization Code
        code = request.GET.get('code')

        if not code:
            return http.HttpResponseForbidden('缺少code')
            # 创建工具对象
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                        client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI)
        # 给第三方软件发送请求，需要ｔｒｙ一下。
        try:
            # 携带 code 向 QQ服务器 请求 access_token
            access_token = oauth.get_access_token(code)

            # 携带 access_token 向 QQ服务器 请求 openid
            openid = oauth.get_open_id(access_token)

        except Exception as e:
            # 如果上面获取 openid 出错, 则验证失败
            print(e)
            # 返回结果
            return http.HttpResponseServerError('OAuth2.0认证失败')

        # 判断 openid 是否绑定过用户(判断用户是不是第一次ｑｑ登陆）
        try:
            oauth_user = OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist:
            # 如果openid没绑定美多商城用户
            # 调用我们封装好的方法，对openid进行加密，生成access_token字符串
            access_token = generate_access_token(openid)
            # 拿到access_code字符串后，拼接字典
            context = {'access_token': access_token}
            # 返回响应，重新渲染
            return render(request, 'oauth_callback.html', context)
        else:
            # 如果openid绑定美多商城用户
            # 根据 user 外键, 获取对应的 QQ用户
            qq_user = oauth_user.user
            # 实现状态保持
            login(request,qq_user)

            # 创建重定向到主页的对象
            response = redirect(reverse('contents:index'))

            # 将用户信息写入到ｃｏｏｋｉｅ中，有效期１５天
            response.set_cookie('username',qq_user.username,max_age=3600)

            # 返回响应
            return response

