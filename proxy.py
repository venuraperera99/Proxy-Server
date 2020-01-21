import socket
import select
import sys

HTTP_PORT = 80
LOCAL_PORT = 8888

def start():  
    proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    proxy.setblocking(0)
    
    # Bind the socket to the port
    server_address = ('localhost', LOCAL_PORT)
    proxy.bind(server_address)
    proxy.listen(6)

    print('starting up on {} port {}'.format(*server_address))

    inputs = [proxy]
    outputs = []
    message_queues = {}

    clients = set()
    servers = {}

    while inputs:
        
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
                    request, host, port = parse_http(data)
                    
                    print(b"request: " + request)
                   
                    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        server.connect((host, port))

                        servers[server] = s
                        
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
                
                print(b"response: " + response)
                
                                    
                if response:
                    message_queues[servers[s]].append(response)
                    outputs.append(s)

                    remove_sock(s, inputs, outputs, message_queues)
                    

        for s in writable:
            if s in servers:
                #queue = message_queues[s]

                request = message_queues[s].pop(0)

                
                print(b"sending to server: " + request)
                
                
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
                    
                    print(b"sending to client: " + response)
                    
                    s.sendall(response)
                    
                    remove_sock(s, inputs, outputs, message_queues)
                
        for s in exceptional:
            remove_sock(s, inputs, outputs, message_queues)
                    
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
            
    
def parse_http(data):
    
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

    request = b"GET http://" + url + http_version + b"\r\n"
    request += b"Host: " + host + b"\r\n"

    

    for header in http_header[2:len(http_header)-1]:
        if not header.startswith(b"Cookie:"):
            request += header + b"\r\n"

    

    return (request, host, port)
    redirect_request(client, request, host, port)

    

def redirect_request(request, host, port):
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (host, port)

    data = b""
    try:
        sock.connect(server_address)
        sock.sendall(request)

       
        while True:
            
            
            tmp = sock.recv(4096)
            data += tmp
 
            if tmp == b'' or got_all_response(data):
                break
            
           
            
    except Exception as e:
        print(e)
    finally:
        sock.close()
        print("closing")

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


if __name__=="__main__":
    start()