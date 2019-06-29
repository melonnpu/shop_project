from django.db import models


# Create your models here.


# 创建省市区数据表
class Area(models.Model):
    """
    行政划分
    """
    # 创建name字段，用户保存名称
    name = models.CharField(max_length=20, verbose_name='名称')
    # 自关联字段　parent
    # 第一个参数是self:parent关联自己
    parent = models.ForeignKey('self',
                               on_delete=models.SET_NULL,
                               related_name='subs',
                               null=True,
                               blank=True,
                               verbose_name='上级行政区划'
                               )

    class Meta:
        db_table = 'tb_areas'
        verbose_name = '行政区划'
        verbose_name_plural = '行政区划'

    def __str__(self):
        return self.name

