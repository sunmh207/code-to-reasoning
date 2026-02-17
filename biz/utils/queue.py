from multiprocessing import Process

from biz.utils.log import logger


def handle_queue(func, *args, **kwargs):
    """异步执行，避免阻塞 webhook 响应"""
    p = Process(target=func, args=args, kwargs=kwargs)
    p.start()
