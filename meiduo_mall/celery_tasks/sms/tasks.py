"""
                           _
                           \"-._ _.--"~~"--._
                            \   "            ^.    ___
                            /                  \.-~_.-~
                     .-----'     /\/"\ /~-._      /
                    /  __      _/\-.__\L_.-/\     "-.
                   /.-"  \    ( ` \_o>"<o_/  \  .--._\
                  /'      \    \:     "     :/_/     "`
                          /  /\ "\    ~    /~"
                          \ I  \/]"-._ _.-"[
                       ___ \|___/ ./    l   \___   ___
                  .--v~   "v` ( `-.__   __.-' ) ~v"   ~v--.
               .-{   |     :   \_    "~"    _/   :     |   }-.
              /   \  |           ~-.,___,.-~           |  /   \
             ]     \ |                                 | /     [
             /\     \|     :                     :     |/     /\
            /  ^._  _K.___,^                     ^.___,K_  _.^  \
           /   /  "~/  "\                           /"  \~"  \   \
          /   /    /     \ _          :          _ /     \    \   \
        .^--./    /       Y___________l___________Y       \    \.--^.
        [    \   /        |        [/    ]        |        \   /    ]
        |     "v"         l________[____/]________j  -melon }r"     /
        }------t          /                       \       /`-.     /
        |      |         Y                         Y     /    "-._/
        }-----v'         |         :               |     7-.     /
        |   |_|          |         l               |    / . "-._/
        l  .[_]          :          \              :  r[]/_.  /
         \_____]                     "--.             "-.____/
                                            "Bug! No way!"
                                                      ---Melon
         
"""
from celery_tasks.yuntongxun.ccp_sms import CCP
from celery_tasks.main import celery_apps


@celery_apps.task(bind=True, name="send_sms_code", retry_backoff=3)
def send_sms_code(self, mobile, sms_code):
    """
    使用celery发送短信
    :return: result
    """
    try:
        result = CCP().send_template_sms(mobile, [sms_code, 5], 1)
    except Exception as e:
        raise self.retry(exc=e, max_retries=3)
    if result != "0":
        # 发送失败
        raise self.retry(exc=Exception('发送失败'), max_retries=3)
    return result
