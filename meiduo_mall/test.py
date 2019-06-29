# -*-coding:utf-8 -*-
import base64
import pickle

if __name__ == '__main__':
    # d = {
    #     '1': {'count': 10, 'selected': True},
    #     '2': {'count': 20, 'selected': False},
    # }
    # print(pickle.dumps(d))
    # d2 = pickle.dumps(d)
    # l = pickle.loads(d2)
    # print(l)
    # b = base64.b64encode(d2)
    # print(b)
    # b2 = base64.b64decode(b)
    # print(b2)
    # b = [1, 2, 3, 4, 5]
    # print(2 in b)
    # print(6 in b)

    import time
    # 得到时间戳
    ticks = time.time()
    print(ticks)
    # 得到当前时间
    now = time.localtime(ticks)
    print(now)
    # 格式化当前时间
    now_time = time.asctime(now)
    print(now_time)
