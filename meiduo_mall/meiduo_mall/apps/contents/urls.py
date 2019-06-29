# -*-coding:utf-8 -*-
from django.conf.urls import url

from contents import views

urlpatterns = [
    # 首页广告
    url(r'^$', views.IndexView.as_view(), name='index'),
]