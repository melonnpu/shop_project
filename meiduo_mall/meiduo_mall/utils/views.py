# 定义工具类：LoginRequired
# 继承自：object
from django.contrib.auth.decorators import login_required

# 添加扩展类:
# 因为这类扩展其实就是 Mixin 扩展类的扩展方式
# 所以我们起名时, 最好也加上 Mixin 字样, 不加也可以.


class LoginRequiredMixin(object):
    """验证用户是否登陆的工具类"""

    # 重写　as_view()函数
    # 在这个函数中，对as_view()进行装饰
    @classmethod
    def as_view(cls, **initkwargs):
        # 重写这个方法，但是不做修改操作，只是加个装饰器：判断用户是否登陆
        view = super().as_view()
        # 添加装饰行为
        return login_required(view)
