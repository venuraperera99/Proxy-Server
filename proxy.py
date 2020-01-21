import socket
import select
import sys
import os
import time

HTTP_PORT = 80

def start(timeout):  
    proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    proxy.setblocking(0)
    
    # Bind the socket to the port
    server_address = ('localhost', 8080)
    proxy.bind(server_address)
    proxy.listen(6)

    print('starting up on {} port {}'.format(*server_address))

    inputs = [proxy]
    outputs = []
    message_queues = {}

    clients = set()
    servers = {}

    while inputs:
        #print("//////")
        #print(inputs)
        #print(outputs)
        #print("//////")
        readable, writable, exceptional = select.select(inputs, outputs, inputs)

        for s in readable:
            if s is proxy:
                connection, client_address = s.accept()
                connection.setblocking(0)

                clients.add(connection)
                inputs.append(connection)
                message_queues[connection] = []
            elif s in clients:
                data = get_request_data(s)

                if data:
                    request, host, port, url = parse_http(data)
                    print("//////")
                    print(b"request: " + request)
                    print(host)
                    print(port)
                    print("//////")

                    
                    filename = sanitize_url_for_filename(url)
                    if is_cache_file_valid(filename, timeout):
                        f = open(filename, 'rb')
                        response = f.read()
                        f.close

                        message_queues[s].append(response)
                    else:
                        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        try:
                            server.connect((host, port))

                            servers[server] = (s, filename)
                            
                            outputs.append(server)
                            message_queues.setdefault(server, []).append(request)

                            inputs.remove(s)
                            outputs.append(s)

                            #print(outputs)
                        except Exception as e:
                            print(host)
                            print(port)
                            print(e)
                            remove_sock(s, inputs, outputs, message_queues)
                else:
                    remove_sock(s, inputs, outputs, message_queues)
            else: #server
                response = get_response(s)
                print("//////")
                print(s)
                print(b"response: " + response)
                print("//////")
                                    
                if response:
                    client, filename = servers[s]
                    message_queues[client].append(response)

                    remove_sock(s, inputs, outputs, message_queues)

                    cache_response(response, filename)
                    

        for s in writable:
            if s in servers:
                #queue = message_queues[s]

                request = message_queues[s].pop(0)

                print("//////")
                print(b"sending to server: " + request)
                print("//////")
                
                s.sendall(request)
                outputs.remove(s)
                inputs.append(s)
                    
                """
                if queue:
                    request = queue.pop(0)

                    print("//////")
                    print(b"sending to server: " + request)
                    print("//////")
                
                    s.sendall(request)
                    outputs.remove(s)
                    inputs.append(s)
                else:
                    remove_sock(s, inputs, outputs, message_queues) """
            else: #client
                queue = message_queues[s]
                if queue:
                    response = message_queues[s].pop(0)
                    print("//////")
                    print(b"sending to client: " + response)
                    print("//////")
                    s.sendall(response)
                    
                    remove_sock(s, inputs, outputs, message_queues)
                
        for s in exceptional:
            remove_sock(s, inputs, outputs, message_queues)

def cache_response(response, filename):
    f = open(filename, 'wb')
    f.write(response)
    f.close()

def sanitize_url_for_filename(url):
    return url.replace(b'/', b' ')

def is_cache_file_valid(filename, timeout):
    if os.path.isfile(filename) and (time.time() - os.path.getmtime(filename) < timeout):
        return True

    return False
    

def remove_sock(sock, inputs, outputs, message_queues):
    if sock in inputs:
        inputs.remove(sock)

    if sock in outputs:
        outputs.remove(sock)

    sock.close()

    del message_queues[sock]
                
def get_request_data(connection):
    data = connection.recv(4096)
    
    while data[-4:] != b'\r\n\r\n':
        tmp = connection.recv(4096)
        if tmp == b'': break
        data += tmp

    return data

def get_response(server):
    data = b""
    while True:
        tmp = server.recv(4096)
        data += tmp

        if tmp == b'' or got_all_response(data):
            break
        
    return data
            
    """
    while True:
        try:
            connection, client_address = proxy.accept()
            data = connection.recv(4096)

            #print(data)
            #print(data[-4:])
            #print(data[-4:] != b'\r\n\r\n')
            while data[-4:] != b'\r\n\r\n':
                tmp = connection.recv(4096)
                #print(tmp)
                if tmp == b'': break
                data += tmp
                #print(tmp)

            print(data)
            request, host, port = parse_http(data)
            response = redirect_request(request, host, port)

            connection.sendall(response)
        finally:
            # Clean up the connection
            connection.close()
    proxy.close()
    """

def parse_http(data):
    #print(data)
    port = -1
    http_header = data.split(b'\r\n')
    url_data = http_header[0]

    url_start = url_data.find(b'/') + 1
    url_end = url_data.find(b"HTTP") - 1

    url = url_data[url_start:url_end]
    http_version = url_data[url_end:]
    
    url_port = url.find(b':')
    url_file = url.find(b'/')

    port = HTTP_PORT    
    host = url 

    if url_port == -1 and url_file != -1:
        host = url[:url_file]
    elif url_port != -1 and url_file == -1:
        host = url[:url_port]
        port = url[url_port + 1:]
    elif url_port != -1 and url_file != -1:
        host = url[:url_port]
        port = url[url_port + 1: url_file]
    else:
        url = url+ b"/"

    #print(url)

    request = b"GET http://" + url + http_version + b"\r\n"
    request += b"Host: " + host + b"\r\n"

    #print(http_header)

    for header in http_header[2:len(http_header)-1]:
        if not header.startswith(b"Cookie:"):
            request += header + b"\r\n"

    #print(data)

    return (request, host, port, url)
   # redirect_request(client, request, host, port, url)

    #print("")
    #print(request)
    #print("")

def redirect_request(request, host, port):

    #print("")
    #print(host)
    #print(port)
    #print(request)
    #print("")

    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (host, port)

    data = b""
    try:
        sock.connect(server_address)
        sock.sendall(request)

        #read = 0
        #content_len = -1
        while True:
            #print(read)
            #print(content_len)
            
            #if content_len == read:
             #   break
            
            tmp = sock.recv(4096)
            data += tmp
 
            if tmp == b'' or got_all_response(data):
                break
            
           # print(data)
            """
            print(tmp)

            header_and_data = tmp.split(b'\r\n')

            if content_len != -1:
                #print("")
                #print(tmp)
                #print("split: ")
                #print(len(header_and_data))
                #print(header_and_data)
                read += len(header_and_data[-1])
            else:
                content_len = get_response_content_length(header_and_data)
                if header_and_data[-2] == b'':
                    read += len(header_and_data[-1])"""
            
    except Exception as e:
        print(e)
    finally:
        #a = data.split(b'\r\n')
        #print(data)
        #print(len(a[-1]))
        sock.close()
        print("closing")

    #print(data)
    return data

def got_all_response(data):
    header_end = data.find(b'\r\n\r\n')
    if header_end != -1:
        header_and_data = data.split(b'\r\n')
        body_len = get_response_content_length(header_and_data)

        if body_len == len(header_and_data[-1]):
            return True
        else:
            return False

    return False

def get_response_content_length(header_and_data):
    for line in header_and_data:
        if line.startswith(b"Content-Length:"):
            return int(line[16:])
    return -1

"""def get_host_and_port(data, start, url_file, end):
    if url_file == -1:
        return data[start:end]
    else:
        return data[start:url_file]"""


if __name__=="__main__":
    ## TODO: uncomment for submission
##    if len(sys.argv) != 2:
##        print("incorrect number of arguments. Expected 1 timeout value")
##        sys.exit(1)
##
##    timeout = sys.argv[1]
##    if not timeout.isdigit():
##        print("Timeout is not a number")
##        sys.exit(1)
##    
##    start(int(timeout))

    start(10)
