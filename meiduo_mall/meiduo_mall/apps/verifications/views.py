import random

from django import http
from django.shortcuts import render

# Create your views here.
from django.views import View
from django_redis import get_redis_connection

from meiduo_mall.libs.captcha.captcha import captcha
from meiduo_mall.libs.yuntongxun.ccp_sms import CCP
from meiduo_mall.utils.response_code import RETCODE


class ImageCodeView(View):
    """图形验证码"""

    def get(self, request, uuid):
        """

        :param request: 请求对象
        :param uuid: 唯一标识图形验证码所属于的用户
        :return:
        """
        print('uuid', uuid)
        # 1.生成图片验证码
        text, image = captcha.generate_captcha()
        # 2.保存图片验证码(连接数据库）
        redis_conn = get_redis_connection('verify_code')

        # 3.设置图片验证码有效期
        redis_conn.setex('img_%s' % uuid, 300, text)
        # 4.响应图片验证码
        return http.HttpResponse(image, content_type='imgae/jpg')


class SMSCodeView(View):
    """短信验证码"""

    def get(self, request, mobile):
        """
        判断短信验证码
        :param request:请求对象
        :param mobile: 手机号码
        :return:
        """


        # 1.接收参数
        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('image_code_id')

        # 2.校验参数
        if not all([image_code_client, uuid]):
            return http.JsonResponse({
                "code": RETCODE.NECESSARYPARAMERR,
                "errmsg": "缺少必传参数"
            })


        # 提前连接ｒｅｄｉｓ数据库
        redis_coon = get_redis_connection('verify_code')
        # send_flag 用于判断用户是否频繁发送短信验证码
        # 数据库里有值，说明是频繁发送
        send_flag = redis_coon.get('send_flag_%s' % mobile)

        if send_flag:
            return http.JsonResponse({'code': RETCODE.THROTTLINGERR,
                                      'errmsg': '发送短信过于频繁'})

        # 3.创建连接ｒｅｄｉｓ的对象
        # redis_coon = get_redis_connection('verify_code')
        # 4.提取图形验证码
        image_code_server = redis_coon.get('img_%s' % uuid)
        if image_code_server is None:
            # 图形验证码过期或者不存在
            return http.JsonResponse({
                "code": RETCODE.IMAGECODEERR,
                "errmsg": "图形验证码失效"
            })
        # 5.删除图形验证码
        try:
            redis_coon.delete('img_%s' % uuid)
        except Exception as e:
            print('error', e)
        # 6.对比图形验证码
        # bytes 转字符串
        image_code_server_decode = image_code_server.decode()
        # 转小写后比较
        if image_code_client.lower() != image_code_server_decode.lower():
            return http.JsonResponse({
                "code": RETCODE.IMAGECODEERR,
                "errmsg": "输入图形验证码有误"
            })

        # 7.生成短信验证码：生成６位数验证码
        sms_code = '%06d' % random.randint(0, 999999)
        print('短信验证码sms_code', sms_code)
        # # 8.保存短信验证码
        # # 短信验证码有效期
        # redis_coon.setex('sms_code_%s' % mobile, 300, sms_code)
        #
        # # 重新写入send_flag
        # # 60s内是否重复发送的标记
        # # SEND_SMS_CODE_INTERVAL = 60(s)
        # redis_coon.setex('send_flag_%s' % mobile, 60, 1)

        # 创建redis管道
        pl = redis_coon.pipeline()

        # 将redis请求添加到队列
        pl.setex('sms_code_%s' % mobile, 300, sms_code)
        pl.setex('send_flag_%s' % mobile, 60, 1)

        # 执行请求
        pl.execute()

        # 9.发送短信验证码
        # CCP().send_template_sms(mobile, [sms_code, 5], 1)
        # 改为celery发送
        # 调用celery的delay()方法，
        from celery_tasks.sms.tasks import send_sms_code
        send_sms_code.delay(mobile,sms_code)

        # 10.响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '发送短信成功'})
