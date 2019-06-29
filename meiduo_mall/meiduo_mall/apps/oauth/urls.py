

from django.conf.urls import url

from oauth import views

urlpatterns = [
    # 首页广告
    url(r'^qq/authorization/$', views.QQURLView.as_view()),
    # QQ用户部分接口,:
    url(r'^oauth_callback/$', views.QQUserView.as_view()),
]
