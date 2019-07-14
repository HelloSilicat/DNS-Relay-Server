from Server import DNSRelayServer
import getopt
import sys

if __name__ == '__main__':
    opts, args = getopt.getopt(sys.argv[1::], 'r:t:b:')

    remote_dns = '10.3.9.5'
    local_dns_file = "./dnsrelay.txt"
    log = False

    for op, value1 in opts:
        if value1[0] == "=":
            value = value1[1:]
        else:
            value = value1
        
        if op == '-r':
            remote_dns = value
        elif op == '-t':
            local_dns_file = value
        elif op == '-b':
            log = True if value == "True" else False

    server = DNSRelayServer(remote_dns=remote_dns, local_dns_file=local_dns_file, log=log)
    server.start()