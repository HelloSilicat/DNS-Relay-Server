import threading
 
import time
 
 
def job():
    while(True):
        print("hello,world")
 
if __name__ == "__main__":
    # 运行函数
    job()
    # 创建线程 并开始执行线程
    t1 = threading.Thread(target=job, name="Job1", args=())  ## 可见Thread是一个类，需要修改一些默认参数
    t2 = threading.Thread(target=job, name="Job2", args=())
    # 使用start方法开始进程
    t1.start()
    t2.start()

    while(True):
        print("HHHHH")
