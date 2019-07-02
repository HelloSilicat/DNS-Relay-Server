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

		self.s_listener = None


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
			self.s_listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			self.s_listener.settimeout(5)
        	self.s_listener.bind(('', 53))
        	print("[SUCC]: ", "DNS Listener %d Socket Connect Succeed." % id)
        except Exception as e:
        	print("[FAIL]: ", "DNS Listener %d Socket Connect Fail, Error: ", e)

        while(True):
        	try:
        		data, addr = self.s_listener.recvfrom(20480)
        		dname = dp.getDomainName(data)
        		print("[RECV]: ", "From:{}, Query:{}".format(addr, dname))
        	except Exception as e:
        		print("[FAIL]: ", "DNS Listener Recv Fail. Error: ", e)

        	try:
	        	if len(data) > 4 and data[2:4] == b'\x01\x00' and data[-4:-2] == b'\x00\x01':
	        		if dname in self.local_dns_table:
	        			self.send_lock.acquire()
	        			self.send_queue.put((addr, data, self.local_dns_table[dname]))
	        			print("[DEBUG]: ", "{} find dname in table,{}, {}".format(id, addr, dname))
	        			self.send_lock.release()
	        		else:
	        			self.help_lock.acquire()
	        			self.help_queue.put((addr, data, dname))
	        			print("[DEBUG]: ", "{} can't find dname in table, {}, {}".format(id, addr, dname))
	        			self.help_lock.release()

	        	else:
	        		print("[DEBUG]: ", "DNS Listener Recv Info not A and IN. ", data[2:4], data[-4:-2])
	        
	        except KeyboardException:
	        	break
	        except Exception as e:
	        	print("[Listener Exception]: ", e)


    def dns_server_sender(self):
    	while(not self.s_listener):
    		pass

    	# single or multiple?
    	while True:
    		try: 
	    		response = []
	    		self.send_lock.acquire()
	    		while not self.send_queue.empty():
	    			addr, data, ip = self.send_queue.get()
					res = dp.createResponsePacket(addr, data, ip)
					response.append((res, addr, ip))
	    		self.send_lock.release()

	    		for res, addr, ip in response:
	    			print("[SEND]: ","To: {}, IP: {}".format(addr, ip))
	    			self.s_listener.sendto(res, addr)
	    	except KeyboardException:
	        	break
	        except Exception as e:
	        	print("[Sender Exception]: ", e)

   	def dns_server_helper(self):
		try:
			self.s_helper = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			self.s_helper.settimeout(5)
        	self.s_helper.bind(('', 53))
        	print("[SUCC]: ", "DNS Listener %d Socket Connect Succeed." % id)
        except Exception as e:
        	print("[FAIL]: ", "DNS Listener %d Socket Connect Fail, Error: ", e)
    		
        while True:
        	try:
        		ans = []
        		self.help_lock.acquire()
        		while not self.help_queue.empty():
        			addr, data, dname = self.help_queue.get()
        			query = dp.createQueryPacket(data, dname)

        			

        		self.help_lock.release()

	        except KeyboardException:
	        	break
	        except Exception as e:
	        	print("[Helper Exception]: ", e)



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















