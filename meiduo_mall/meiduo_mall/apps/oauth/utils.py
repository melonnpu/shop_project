from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer


# 接收传入的 openid , 并将其序列化( 可以理解为加密 )为 token 解码后返回
def generate_access_token(openid):
    """
    签名 openid
    :param openid: 用户的 openid
    :return: access_token
    """

    # QQ登录保存用户数据的token有效期
    # settings.SECRET_KEY: 加密使用的秘钥
    # SAVE_QQ_USER_TOKEN_EXPIRES = 600: 过期时间
    serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY,
                                                 expires_in=600)
    data = {'openid': openid}
    token = serializer.dumps(data)
    return token.decode()

