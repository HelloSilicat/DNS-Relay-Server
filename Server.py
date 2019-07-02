import socket
import threading
import DNSProtocol as dp
from queue import Queue

class DNSRelayServer(Object):
	def __init__(self, server_thread=1, remote_dns="", local_dns_file="./dnsrelay.txt", dns_buffer_file="./dnsbuffer.txt", flush=False):
		self.server_thread = server_thread
		self.remote_dns = remote_dns
		self.local_dns_file = local_dns_file
		self.dns_buffer_file = dns_buffer_file

		self.dns_load()
		if flush:
			self.dns_flush()

		self.help_queue = Queue()
		self.send_queue = Queue()
		
		self.help_lock = threading.Lock()
		self.send_lock = threading.Lock()


	# Load Local DNS Table and DNS Buffer
	def dns_load(self):
		self.local_dns_table = {}
		self.dns_buffer = {}
		try:
			with open(self.local_dns_file, 'r') as f:
				for line in f.readlines():
					if line.strip() > 0:
						self.local_dns_file[line.strip().split()[1]] = line.strip().split()[0]
			print("[SUCC]: ", "Load Local DNS Table Succeed. Total ", len(local_dns_file.keys()))
		except Exception as e:
			print("[FAIL]: ", "Load Local DNS Table Fail, Error: ", e)

		try:
			with open(self.dns_buffer_file, 'r') as f:
				for line in f.readlines():
					if line.strip() > 0:
						self.dns_buffer[line.strip().split()[1]] = line.strip().split()[0]
			print("[SUCC]: ", "Load Local DNS Buffer Succeed. Total ", len(query_buffer.keys()))
		except Exception as e:
			print("[FAIL]: ", "Load Local DNS Buffer Fail, Error: ", e)


	# Flush Local DNS Buffer
	def dns_flush(self):
		try:
			with open(self.dns_buffer_file, 'w') as f:
				self.dns_buffer = {}
			print("[SUCC]: ", "Flush DNS Buffer Succeed.")
		except Exception as e:
			print("[FAIL]: ", "Flush DNS Local Buffer Fail, Error: ", e)


	# Write to local dns buffer
	def dns_write_buffer(self, ip, domain_name):
		try:
			with open(self.query_buffer_file, 'a') as f:
				f.write("{} {}\n".format(ip, domain_name))
		except Exception as e:
			print("[FAIL]: ", "Write Buffer Fail, Error: ", e)

	def dns_server_listener(self,id):
		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			s.settimeout(5)
        	s.bind(('', 53))
        	print("[SUCC]: ", "DNS Listener %d Socket Connect Succeed." % id)
        except Exception as e:
        	print("[FAIL]: ", "DNS Listener %d Socket Connect Fail, Error: ", e)

        while(True):
        	try:
        		data, addr = s.recvfrom(20480)
        		dname = dp.getDomainName(data)
        		print("[RECV]: ", "From:{}, Query:{}".format(addr, dname))
        	except Exception as e:
        		print("[FAIL]: ", "DNS Listener Recv Fail. Error: ", e)

        	if len(data) > 4 and data[2:4] == b'\x01\x00' and data[-4:-2] == b'\x00\x01':
        		if dname in self.local_dns_table:
        			self.send_lock.acquire()
        			self.send_queue.put((addr, data, self.local_dns_table[dname]))
        			self.send_lock.release()
        		else:
        			self.help_lock.acquire()
        			self.help_queue.put((addr, data, dname))
        			self.help_lock.release()

        	else:
        		print("[DEBUG]: ", "DNS Listener Recv Info not A and IN. ", data[2:4], data[-4:-2])


	# Start Server
	def start():
		# Start Recv Thread
		try:
			for i in range(self.server_thread):
				t = threading.Thread(target=self.dns_server_listener,args=(i,))
				t.start()
				print("[SUCC]: ", "DNS Listener %d Start Succeed." % i)

		except Exception as e:
			print("[FAIL]: ", "DNS Listener Start Fail, Error: ", e)

		try:
			t = threading.Thread(target=self.dns_server_sender)
			t.start()
			print("[SUCC]: ", "DNS Sender Start Succeed.")
		except Exception as e:
			print("[FAIL]: ", "DNS Sender Start Fail, Error: ", e)

		try:
			t = threading.Thread(target=self.dns_server_helper)
			t.start()
			print("[SUCC]: ", "DNS Helper Start Succeed.")
		except Exception as e:
			print("[FAIL]: ", "DNS Helper Start Fail, Error: ", e)















