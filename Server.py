import socket
import threading
import DNSProtocol as dp
from queue import Queue
import datetime

def getNowTime():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

class DNSRelayServer():
    def __init__(self, remote_dns='10.3.9.5', local_dns_file="./dnsrelay.txt", dns_buffer_file="./dnsbuffer.txt", flush=False):
        self.server_thread = 1
        self.sender_thread = 3
        self.helper_thread = 3
        self.remote_dns = remote_dns
        self.local_dns_file = local_dns_file
        self.dns_buffer_file = dns_buffer_file

        if flush:
            self.dns_flush()

        self.dns_load()

        self.help_queue = Queue()
        self.send_queue = Queue()
        
        self.help_lock = threading.Lock()
        self.send_lock = threading.Lock()

        self.s_listener = None
        self.id_data = {}
        self.id_addr = {}
        self.id_dname = {}

        self.in_id = set()


    # Load Local DNS Table and DNS Buffer
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

        try:
            with open(self.dns_buffer_file, 'r') as f:
                for line in f.readlines():
                    if len(line.strip()) > 0:
                        self.dns_buffer[line.strip().split()[1]] = line.strip().split()[0]
            print("[SUCC %s]: "%getNowTime(), "Load Local DNS Buffer Succeed. Total ", len(self.dns_buffer.keys()))
        except Exception as e:
            print("[FAIL %s]: "%getNowTime(), "Load Local DNS Buffer Fail, Error:", e)


    # Flush Local DNS Buffer
    def dns_flush(self):
        try:
            with open(self.dns_buffer_file, 'w') as f:
                self.dns_buffer = {}
            print("[SUCC %s]: "%getNowTime(), "Flush DNS Buffer Succeed.")
        except Exception as e:
            print("[FAIL %s]: "%getNowTime(), "Flush DNS Local Buffer Fail, Error: ", e)


    # Write to local dns buffer
    def dns_update_buffer(self, ip, domain_name):
        try:
            self.dns_buffer[domain_name] = ip
            with open(self.dns_buffer_file, 'a') as f:
                f.write("{} {}\n".format(ip, domain_name))
        except Exception as e:
            print("[FAIL %s]: "%getNowTime(), "Write Buffer Fail, Error: ", e)

    def dns_server_listener(self):
        while(True): 
            try:
                data, addr = self.s_listener.recvfrom(1024)
                if dp.getPacketId(data) in self.in_id:
                	continue
                self.in_id.add(dp.getPacketId(data))
                dname = dp.getDomainName(data)
                print("[RECV %s]: "%getNowTime(), "From:{}, Query:{}".format(addr, dname))


                if len(data) > 4 and data[2:4] == b'\x01\x00' and data[-4:-2] == b'\x00\x01':
                    if dname in self.local_dns_table:
                        self.send_queue.put((addr, data, self.local_dns_table[dname]))
                    elif dname in self.dns_buffer:
                    	self.send_queue.put((addr, data, self.dns_buffer[dname]))
                    else:
                        self.help_queue.put((addr, data, dname))

                else:
                	pass
            	
            except KeyboardInterrupt:
            	break
            except Exception as e:
            	if str(e).strip() != "timed out" and str(e).strip()[:16] != "[WinError 10054]":
                	print("[Listener Exception %s]: "%getNowTime(), e)


    def dns_server_sender(self):
        while(not self.s_listener):
            pass

        while True:
            try: 
                response = []
                while not self.send_queue.empty():
                    addr, data, ip = self.send_queue.get()
                    res = dp.createResponsePacket(addr, data, ip)
                    response.append((res, addr, ip))

                
                for res, addr, ip in response:
                    print("[SEND %s]: "%getNowTime(),"To: {}, IP: {}".format(addr, ip))
                    self.s_listener.sendto(res, addr)
                    self.in_id.remove(dp.getPacketId(res))
            except KeyboardInterrupt:
                break
            except Exception as e:
                print("[Sender Exception %s]: "%getNowTime(), e)

    def dns_server_helper(self):
        while True:
            try:
                ans = []
                while not self.help_queue.empty():
                    addr, data, dname = self.help_queue.get()
                    id = dp.createId(addr,self.id_data.keys())
                    self.id_addr[id] = addr
                    self.id_data[id] = data
                    self.id_dname[id] = dname
                    query = dp.createQueryPacket(data, id, dname)
                    self.s_helper.sendto(query, (self.remote_dns, 53))

                data, _ = self.s_helper.recvfrom(20480)
                ip = dp.getPacketIp(data)
                id = dp.getPacketId(data)
                addr = self.id_addr[id]
                self.dns_update_buffer(ip, self.id_dname[id])
                print("[SUCC %s]: "%getNowTime(), "From {}, Answer {}".format(addr, ip))

                self.send_lock.acquire()
                self.send_queue.put((addr, self.id_data[id], ip))
                self.send_lock.release()

            except KeyboardInterrupt:
                break
            except Exception as e:
            	if str(e).strip() != "timed out" and str(e).strip()[:15] != "[WinError 10054]":
                	print("[Helper Exception %s]: "%getNowTime(), e)

    def start(self):
        try:
            self.s_listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.s_listener.settimeout(5)
            self.s_listener.bind(('', 53))
            print("[SUCC %s]: "%getNowTime(), "DNS Listener Socket Connect Succeed.")
            
            for i in range(self.server_thread):
                t = threading.Thread(target=self.dns_server_listener)
                t.setDaemon(True) 
                t.start()
                print("[SUCC %s]: "%getNowTime(), "DNS Listener %d Start Succeed." % i)

        except Exception as e:
            print("[FAIL %s]: "%getNowTime(), "DNS Listener Start Fail, Error: ", e)


        try:
            for i in range(self.sender_thread):
                t = threading.Thread(target=self.dns_server_sender)
                t.setDaemon(True) 
                t.start()
                print("[SUCC %s]: "%getNowTime(), "DNS Sender %d Start Succeed." % i)
        except Exception as e:
            print("[FAIL %s]: "%getNowTime(), "DNS Sender Start Fail, Error: ", e)

        try:
            self.s_helper = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.s_helper.settimeout(5)
            self.s_helper.bind(('', 12345))
            print("[SUCC %s]: "%getNowTime(), "DNS Helper Socket Connect Succeed.")
            
            for i in range(self.helper_thread):
                t = threading.Thread(target=self.dns_server_helper)
                t.setDaemon(True) 
                t.start()
                print("[SUCC %s]: "%getNowTime(), "DNS Helper %d Start Succeed." % i)
        except Exception as e:
            print("[FAIL %s]: "%getNowTime(), "DNS Helper Start Fail, Error: ", e)
        
        while(1):
        	pass














