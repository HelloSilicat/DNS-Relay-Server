# -*- utf-8 -*-
import threading
import random
import dns.resolver
import string
import time
from queue import Queue
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['KaiTi'] # 指定默认字体
plt.rcParams['axes.unicode_minus'] = False # 解决保存图像是负号'-'显示为方块的问题

my_resolver = dns.resolver.Resolver()
my_resolver.lifetime = 30000

#my_resolver.nameservers = ['10.201.8.81']   #xpr
#my_resolver.nameservers = ['10.28.149.149']
my_resolver.nameservers = ['127.0.0.1']
#my_resolver.nameservers = ['10.28.173.201']
#my_resolver.nameservers = ['10.201.8.73']
#my_resolver.nameservers = ['10.128.241.91']    # cxj


lock = threading.Lock()
record = []
times = 20

def getTimeStamp():
    t = time.time()
    t = (int(round(t * 1000)))

    return t

def generate_random_name():
    ch = list(string.ascii_lowercase) + list(map(str,range(10)))
    rand_ch = random.sample(ch,random.randint(3,10))
    return ''.join(rand_ch)+".pei.com"
    #return "id.google.com.hk"

def start():
    for i in range(times):
        data = generate_random_name()
        t1 = getTimeStamp()
        try:
            res = my_resolver.query(data).response.answer[-1].to_text().split(' ')[-1]
        except KeyboardInterrupt:
            break
        except:
            pass

        t2 = getTimeStamp()
        print(t2 - t1)
        lock.acquire()
        record.append(t2-t1)
        lock.release()


if __name__ == '__main__':

    thread_num = 1
    step = 2
    thread_limit = 20

    Y = []
    X = []
    YY = []
    while True:
        if thread_num > thread_limit:
            break
        record = []
        for i in range(thread_num):
            t = threading.Thread(target=start)
            t.setDaemon(True)
            t.start()
        while len(record) < thread_num * times:
            pass
        if len(record) != 0:
            YY.append(record)
            Y.append(sum(record) / len(record))
            X.append(thread_num * times)
            print("Thread:{}, Avg Time Cost(ms):{}".format(str(thread_num), str(Y[-1])))
        thread_num += step


    f = open("stat.txt", "w")
    for y in YY:
        for yy in y:
            f.write(str(yy)+" ")
        f.write("\n")


    plt.plot(X, Y, "o-", color = "red")
    #for xy in zip(X, Y):
    #    plt.annotate("(%s, %s)" % xy, xy=xy, xytext= )
    plt.title("DNS并发性能测试")
    plt.xlabel("并发量/次")
    plt.ylabel("平均耗时/ms")
    plt.show()



