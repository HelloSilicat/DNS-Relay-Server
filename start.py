from Server import DNSRelayServer
import getopt
import sys

if __name__ == '__main__':
    opts, args = getopt.getopt(sys.argv[1::], 'f:r:t:b:')

    remote_dns = '10.3.9.5' 
    local_dns_file = "./dnsrelay.txt"
    dns_buffer_file = "./dnsbuffer.txt"
    flush = False

    for op, value1 in opts:
        if value1[0] == "=":
            value = value1[1:]
        else:
            value = value1
        if op == '-f':
            flush = True if value == "True" else False
        elif op == '-r':
            remote_dns = value
        elif op == '-t':
            local_dns_file = value
        elif op == '-b':
            dns_buffer_file=value

    server = DNSRelayServer(remote_dns=remote_dns, local_dns_file=local_dns_file, dns_buffer_file=dns_buffer_file, flush=flush)
    server.start()