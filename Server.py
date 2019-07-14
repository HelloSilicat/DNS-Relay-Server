import socket
import threading
from multiprocessing import Process, Queue
import DNSProtocol as dp
import datetime
import time

def getNowTime():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

class DNSRelayServer():
    def __init__(self, remote_dns='10.3.9.5', local_dns_file="./dnsrelay.txt", log=False):
        self.remote_dns = remote_dns           # 远程DNS服务器地址
        self.local_dns_file = local_dns_file   # 本地IP-域名表

        self.dns_load()                        # 加载本地IP-域名表

        self.s_listener = None                 # 53端口监听socket
        self.id_data = {}                      # DNS报文ID与请求包映射 
        self.id_addr = {}                      # DNS报文ID与请求包地址映射
        self.id_dname = {}                     # DNS报文ID与请求包域名映射
                       
        self.printSwitch = log                 # 日志开关


    # 加载本地IP-域名表
    def dns_load(self):
        self.local_dns_table = {}
        self.dns_buffer = {}
        try:
            with open(self.local_dns_file, 'r') as f:
                for line in f.readlines():
                    if len(line.strip()) > 0:
                        self.local_dns_table[line.strip().split()[1]] = line.strip().split()[0]
            print("[SUCC %s]: "%getNowTime(), "Load Local DNS Table Succeed. Total ", len(self.local_dns_table.keys()))
        except Exception as e:
            print("[FAIL %s]: "%getNowTime(), "Load Local DNS Table Fail, Error: ", e)



    # 写入本地缓存
    def dns_update_buffer(self, ip, domain_name):
        try:
            if type(ip) == type("ip"):
                self.dns_buffer[domain_name] = ip
            if len(self.dns_buffer.keys()) > 50000:
                self.dns_buffer.clear
        except Exception as e:
            print("[FAIL %s]: "%getNowTime(), "Write Buffer Fail, Error: ", e)


    # 持续监听用户DNS请求，分发任务
    def dns_server_listener(self, help_queue, send_queue):
        while(True): 
            try:
                # 非阻塞监听用户DNS解析请求
                try:
                    data, addr = self.s_listener.recvfrom(1024)
                except:
                    continue
                # 获取请求域名
                dname = dp.getDomainName(data)
                if self.printSwitch:
                    print("[RECV %s]: "%getNowTime(), "From:{}, Query:{}".format(addr, dname))

                # 校验DNS请求有效性：A类型且是查询报文
                if len(data) > 4 and data[2:4] == b'\x01\x00' and data[-4:-2] == b'\x00\x01':
                    if dname in self.local_dns_table:        # 如果本地查询表存在，直接给ip
                        send_queue.put((addr, data, self.local_dns_table[dname]))
                    elif dname in self.dns_buffer:           # 如果缓冲区中存在，直接给ip
                        send_queue.put((addr, data, self.dns_buffer[dname]))
                    else:                                    # 如果均不存在，向远程查询
                        help_queue.put((addr, data, dname))
            	
            except KeyboardInterrupt:
            	break
            except Exception as e:
            	if self.printSwitch and str(e).strip() != "timed out" and str(e).strip()[:16] != "[WinError 10054]":
                	print("[Listener Exception %s]: "%getNowTime(), e)

    # 持续发回包给用户
    def dns_server_sender(self, send_queue):
        while True:
            try: 
                # 从发送队列中获取数据，构造回包
                response = []
                while not send_queue.empty():
                    # 从队列获取数据
                    addr, data, ip = send_queue.get()
                    # 构造回包
                    res = dp.createResponsePacket(addr, data, ip)
                    dname = dp.getDomainName(data)
                    response.append((res, addr, ip, dname))

                # 发送回包
                for res, addr, ip, dname in response:
                    if self.printSwitch and type(ip) == type("ip"):
                        print("[SEND %s]: "%getNowTime(),"To: {}, IP: {}, Query: {}".format(addr, ip, dname))
                    elif self.printSwitch:
                        print("[SEND %s]: "%getNowTime(),"To: {}, Query: {}".format(addr, dname))
                    self.s_listener.sendto(res, addr)

            except KeyboardInterrupt:
                break
            except Exception as e:
                if self.printSwitch:
                    print("[Sender Exception %s]: "%getNowTime(), e)

    # 持续向远程服务器发送查询，并将结果填入发送队列
    def dns_server_helper(self, help_queue, send_queue):
        while True:
            try:
                ans = []
                # 从请求队列中获取数据，构造请求包
                while not help_queue.empty():
                    # 获取数据
                    addr, data, dname = help_queue.get()
                    id = dp.createId(addr,self.id_data.keys())
                    self.id_addr[id] = addr
                    self.id_data[id] = data
                    self.id_dname[id] = dname
                    # 构造请求包
                    query = dp.createQueryPacket(data, id, dname)
                    if self.printSwitch:
                        print("[HELP %s]: "%getNowTime(), "To:('{}', 53), Query:{}".format(self.remote_dns, dname))
                    self.s_helper.sendto(query, (self.remote_dns, 53))

                data = None
                try:
                    data, _ = self.s_helper.recvfrom(1024)
                except:
                    pass

                # 来自远程DNS服务器的合法回包
                if data != None and len(data) > 4:
                    ip = dp.getPacketIp(data)
                    id = dp.getPacketId(data)
                    addr = self.id_addr[id]
                    # 更新本地缓存
                    self.dns_update_buffer(ip, self.id_dname[id])
                    if self.printSwitch and type(ip) == type("ip"):
                        print("[SUCC %s]: "%getNowTime(), "From {}, Answer {}".format(addr, ip))

                    # 写入发送队列
                    send_queue.put((addr, self.id_data[id], ip))

            except KeyboardInterrupt:
                break
            except Exception as e:
            	if self.printSwitch and str(e).strip() != "timed out" and str(e).strip()[:15] != "[WinError 10054]":
                	print("[Helper Exception %s]: "%getNowTime(), e)

    def start(self):
        help_queue = Queue()
        send_queue = Queue()

        # 获取请求进程
        try:
            self.s_listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.s_listener.settimeout(0)
            self.s_listener.bind(('', 53))
            print("[SUCC %s]: "%getNowTime(), "DNS Listener Socket Connect Succeed.")

            
            for i in range(1):
                t = Process(target=self.dns_server_listener, args=(help_queue, send_queue, ))
                t.daemon = True 
                t.start()
                print("[SUCC %s]: "%getNowTime(), "DNS Listener %d Start Succeed." % i)

        except Exception as e:
            print("[FAIL %s]: "%getNowTime(), "DNS Listener Start Fail, Error: ", e)

        # 发送回包进程
        try:
            for i in range(1):
                t = Process(target=self.dns_server_sender, args=(send_queue, ))
                t.daemon = True 
                t.start()
                print("[SUCC %s]: "%getNowTime(), "DNS Sender %d Start Succeed." % i)
        except Exception as e:
            print("[FAIL %s]: "%getNowTime(), "DNS Sender Start Fail, Error: ", e)

        # 远程查询进程
        try:
            self.s_helper = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.s_helper.settimeout(0)
            self.s_helper.bind(('', 12345))
            print("[SUCC %s]: "%getNowTime(), "DNS Helper Socket Connect Succeed.")

            for i in range(1):
                t = Process(target=self.dns_server_helper, args=(help_queue, send_queue))
                t.daemon=True 
                t.start()
                print("[SUCC %s]: "%getNowTime(), "DNS Helper %d Start Succeed." % i)
        except Exception as e:
            print("[FAIL %s]: "%getNowTime(), "DNS Helper Start Fail, Error: ", e)
        
        while(1):
        	pass














